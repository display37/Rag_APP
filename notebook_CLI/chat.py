import os
import json
from dotenv import load_dotenv

# 🔹 Load environment variables
load_dotenv()

# 🔹 LangChain imports
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient

from langchain_groq import ChatGroq

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


# ----------------------------
# CONFIG
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

Response Behavior (VERY IMPORTANT):

👉 If the question asks for steps, process, method, or instructions:
- Extract ALL steps across the document
- Combine them into a clean ordered list
- Present them clearly

👉 If the question asks for explanation:
- Give a clear, concise explanation

👉 If the question asks for summary:
- Provide a short and meaningful summary

👉 If the question is factual:
- Give a direct answer

👉 Do NOT force one format for every answer.

Answer naturally like a human who has read the full document.

Context:
{context}

Question:
{question}

Answer:
"""


def main():
    print("🔌 Connecting to Qdrant...")

    # 🔹 Embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    # 🔹 Vector DB
    vectorstore = Qdrant(
        client=QdrantClient(host="localhost", port=6333),
        collection_name=COLLECTION_NAME,
        embeddings=embeddings
    )

    # 🔹 Retriever (IMPORTANT)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

    # 🔹 LLM (Groq)
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0
    )

    # 🔹 Prompt + parser
    prompt = PromptTemplate.from_template(SYSTEM_PROMPT)
    parser = StrOutputParser()

    print("\n💬 RAG CLI Ready! Type 'exit' to quit.\n")

    while True:
        query = input("🧑 You: ")

        if query.lower() == "exit":
            break

        # ----------------------------
        # STEP 1: Retrieve docs
        # ----------------------------
        docs = retriever.invoke(query)

        # 🔍 DEBUG: See what is retrieved
        print("\n🔍 Retrieved Context:\n")
        for doc in docs:
            print(f"Page {doc.metadata.get('page')}:\n{doc.page_content[:200]}\n")

        # ----------------------------
        # STEP 2: Build context
        # ----------------------------
        context = "\n\n".join(
            [f"Page {doc.metadata.get('page', 'N/A')}:\n{doc.page_content}" for doc in docs]
        )

        # ----------------------------
        # STEP 3: Run chain
        # ----------------------------
        chain = prompt | llm | parser

        response = chain.invoke({
            "context": context,
            "question": query
        })

        # ----------------------------
        # STEP 4: Parse JSON safely
        # ----------------------------
        try:
            parsed = json.loads(response)
            print("\n🤖 AI:", parsed["answer"])
            print("📄 Sources:", parsed["sources"], "\n")
        except:
            print("\n⚠️ Raw Response:\n", response, "\n")


if __name__ == "__main__":
    main()