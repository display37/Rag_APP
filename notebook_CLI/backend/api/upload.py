from fastapi import APIRouter, UploadFile, File
from services.file_service import process_file

router = APIRouter()

@router.post("/upload/{chat_id}")
async def upload_file(chat_id: int, file: UploadFile = File(...)):
    result = process_file(file, chat_id)
    return result