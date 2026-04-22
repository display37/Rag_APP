from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.chat_service import generate_response

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    history: list = []
    chat_id: int

@router.post("/chat")
def chat(request: QueryRequest):
    stream_func = generate_response(request.question, request.history, request.chat_id)
    return StreamingResponse(stream_func(), media_type="text/plain")