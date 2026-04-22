import os
import shutil
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ----------------------------
# CONFIG (UNCHANGED)
# ----------------------------
COLLECTION_NAME = "rag_collection"

SYSTEM_PROMPT = """
You are an intelligent AI assistant that reads documents like a human and answers questions based on the provided context.

Your goal is to understand, summarize, and extract only the most relevant information.

General Rules:
1. Read ALL context carefully before answering.
2. Combine information across multiple pages if needed.
3. Do NOT copy raw text blindly.
4. Remove unnecessary or repeated information.
5. Provide a clear, complete, and human-like answer.
6. If the answer is not found, say:
   "I could not find this in the document."
7. If only partial information is available, say:
   "The document provides partial information."

Response Behavior:

- If steps → return clean ordered steps
- If explanation → explain clearly
- If summary → short summary
- If factual → direct answer

Answer naturally like a human who has read the full document.

Context:
{context}

Question:
{question}

Answer:
"""

# ----------------------------
# INIT MODELS
# ----------------------------
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

client = QdrantClient(host="localhost", port=6333)

vectorstore = Qdrant(
    client=client,
    collection_name=COLLECTION_NAME,
    embeddings=embeddings
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 12})

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0
)

prompt = PromptTemplate.from_template(SYSTEM_PROMPT)

# ----------------------------
# FASTAPI
# ----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    history: list = []

# ----------------------------
# RERANK
# ----------------------------
def score_doc(doc, query):
    text = doc.page_content.lower()
    return sum(text.count(word) for word in query.lower().split())

# ----------------------------
# UPLOAD (FIXED)
# ----------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = f"temp_{file_id}.pdf"

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Load PDF
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        # Split
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = splitter.split_documents(docs)

        # Store in Qdrant
        vectorstore.add_documents(chunks)

        # 🔥 IMPORTANT: refresh retriever
        global retriever
        retriever = vectorstore.as_retriever(search_kwargs={"k": 12})

        return {"message": "Uploaded & indexed successfully"}

    finally:
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

# ----------------------------
# CHAT (STREAM FIXED)
# ----------------------------
@app.post("/chat")
def chat(request: QueryRequest):
    query = request.question

    # Retrieve
    docs = retriever.invoke(query)

    # Rerank
    scored = [(doc, score_doc(doc, query)) for doc in docs]
    scored = sorted(scored, key=lambda x: x[1], reverse=True)
    docs = [doc for doc, _ in scored[:6]]

    # Remove duplicates
    unique = {}
    for doc in docs:
        page = doc.metadata.get("page")
        if page not in unique:
            unique[page] = doc
    docs = list(unique.values())

    # Build context
    context = "\n\n".join([doc.page_content for doc in docs])

    # History
    history_text = "\n".join(
        [f"{msg['role']}: {msg['text']}" for msg in request.history]
    )

    final_input = {
        "context": context,
        "question": f"{history_text}\nUser: {query}"
    }

    def generate():
        try:
            chain = prompt | llm

            # 🔥 STREAM TOKENS
            for chunk in chain.stream(final_input):
                if hasattr(chunk, "content"):
                    yield chunk.content

            # 🔥 SEND SOURCES
            sources = [
                {
                    "page": doc.metadata.get("page"),
                    "text": doc.page_content[:120]
                }
                for doc in docs
            ]

            yield "\n\n###SOURCES###" + json.dumps(sources)

        except Exception as e:
            yield f"\n\n⚠️ Error: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")