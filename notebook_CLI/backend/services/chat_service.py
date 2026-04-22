import json

from rag.retriever import retriever, vectorstore
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from db.mongo import messages_collection

# 🔥 NEW (MySQL)
from db.mysql import SessionLocal
from db.models import Chat


SYSTEM_PROMPT = """You are an intelligent AI assistant that reads documents like a human and answers questions based on the provided context.

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


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0
)

prompt = PromptTemplate.from_template(SYSTEM_PROMPT)


# ----------------------------
# RERANK
# ----------------------------
def score_doc(doc, query):
    text = doc.page_content.lower()
    return sum(text.count(word) for word in query.lower().split())


# ----------------------------
# SAVE MESSAGE (Mongo)
# ----------------------------
async def save_message(chat_id, role, text):
    await messages_collection.insert_one({
        "chat_id": chat_id,
        "role": role,
        "text": text
    })


# ----------------------------
# MAIN RESPONSE GENERATOR
# ----------------------------
def generate_response(query, history, chat_id):

    # 🔥 FIX: Use vectorstore directly to filter by chat_id
    docs = vectorstore.similarity_search(query, k=12, filter={"chat_id": chat_id})

    # ----------------------------
    # GUARD: no documents indexed yet
    # ----------------------------
    if not docs:
        async def no_docs_stream():
            msg = "No documents have been uploaded for this chat yet. Please upload a PDF first."
            await save_message(chat_id, "user", query)
            await save_message(chat_id, "bot", msg)
            yield msg
        return no_docs_stream

    # ----------------------------
    # RERANK
    # ----------------------------
    scored = [(doc, score_doc(doc, query)) for doc in docs]
    scored = sorted(scored, key=lambda x: x[1], reverse=True)
    docs = [doc for doc, _ in scored[:6]]

    # ----------------------------
    # REMOVE DUPLICATES
    # ----------------------------
    unique = {}
    for doc in docs:
        page = doc.metadata.get("page")
        if page not in unique:
            unique[page] = doc
    docs = list(unique.values())

    # ----------------------------
    # BUILD CONTEXT
    # ----------------------------
    context = "\n\n".join([doc.page_content for doc in docs])

    history_text = "\n".join(
        [f"{msg['role']}: {msg['text']}" for msg in history]
    )

    final_input = {
        "context": context,
        "question": f"{history_text}\nUser: {query}"
    }

    chain = prompt | llm

    # ----------------------------
    # STREAM FUNCTION
    # ----------------------------
    async def stream():
        bot_text = ""

        # ✅ Save user message
        await save_message(chat_id, "user", query)

        # 🔥 FIX: wrap sync stream in async loop
        async for chunk in chain.astream(final_input):
            if hasattr(chunk, "content"):
                bot_text += chunk.content
                yield chunk.content

        # ✅ Save bot message
        await save_message(chat_id, "bot", bot_text)

        # ----------------------------
        # 🔥 UPDATE MYSQL (NEW)
        # ----------------------------
        db = SessionLocal()
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()

            if chat:
                # Auto title
                if chat.title == "New Chat":
                    chat.title = query[:40]

                # Last message preview
                chat.last_message = bot_text[:80]

                db.commit()

        except Exception as e:
            print("MySQL update error:", e)
        finally:
            db.close()

        # ----------------------------
        # SEND SOURCES
        # ----------------------------
        sources = [
            {
                "page": doc.metadata.get("page"),
                "text": doc.page_content[:120]
            }
            for doc in docs
        ]

        yield "\n\n###SOURCES###" + json.dumps(sources)

    return stream