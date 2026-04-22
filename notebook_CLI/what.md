🧠 1. Architecture (Keep this in your head)
PDF → Chunking → Embeddings (Gemini) → Qdrant (store vectors)

User Query → Embed → Similarity Search → Context → Gemini → Answer

📂 Project Structure
rag-cli-agent/
│── index.py
│── chat.py
│── requirements.txt
│── .env
│── data/        ← your PDFs