import shutil
import uuid
import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.retriever import vectorstore

from db.mysql import SessionLocal
from db.models import File


def process_file(file, chat_id):
    db = SessionLocal()
    try:
        # Save file metadata to MySQL
        file_record = File(chat_id=chat_id, filename=file.filename)
        db.add(file_record)
        db.commit()
    finally:
        db.close()

    file_id = str(uuid.uuid4())
    file_path = f"temp_{file_id}.pdf"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        chunks = splitter.split_documents(docs)

        # Tag every chunk with chat_id so we can filter later
        for chunk in chunks:
            chunk.metadata["chat_id"] = chat_id
            chunk.metadata["source_file"] = file.filename

        vectorstore.add_documents(chunks)

        return {
            "message": "Uploaded & indexed successfully",
            "filename": file.filename,
            "chunks_indexed": len(chunks)
        }

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)