import os
from dotenv import load_dotenv
load_dotenv()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_community.embeddings import HuggingFaceEmbeddings

from langchain_huggingface import HuggingFaceEmbeddings

from qdrant_client import QdrantClient
from langchain_community.vectorstores import Qdrant

load_dotenv()

# ----------------------------
# CONFIG
# ----------------------------
DATA_PATH = "data"
COLLECTION_NAME = "rag_collection"

# ----------------------------
# LOAD PDF FILES
# ----------------------------
def load_documents():
    docs = []
    for file in os.listdir(DATA_PATH):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(DATA_PATH, file))
            docs.extend(loader.load())
    return docs

# ----------------------------
# SPLIT INTO CHUNKS
# ----------------------------
def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    return splitter.split_documents(documents)

# ----------------------------
# MAIN INDEXING
# ----------------------------
def main():
    print("📥 Loading documents...")
    docs = load_documents()

    print("✂️ Splitting documents...")
    chunks = split_documents(docs)

    print("🔗 Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

    print("🗄️ Connecting to Qdrant...")
    client = QdrantClient(host="localhost", port=6333)

    print("📦 Storing vectors...")
    Qdrant.from_documents(
        chunks,
        embeddings,
        url="http://localhost:6333",
        collection_name=COLLECTION_NAME
    )

    print("✅ Indexing complete!")

if __name__ == "__main__":
    main()