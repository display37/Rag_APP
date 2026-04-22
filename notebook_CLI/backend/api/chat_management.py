from fastapi import APIRouter, HTTPException
from db.mysql import SessionLocal
from db.models import Chat, User, File
from db.mongo import messages_collection

router = APIRouter()


# CREATE CHAT
@router.post("/chat/create")
def create_chat(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(name=email.split("@")[0], email=email)
            db.add(user)
            db.commit()
            db.refresh(user)

        new_chat = Chat(user_id=user.id, title="New Chat")
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        return {"chat_id": new_chat.id}
    finally:
        db.close()


# GET ALL CHATS — isolated by user
@router.get("/chat/list")
def get_chats(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return []

        chats = db.query(Chat).filter(Chat.user_id == user.id).all()
        return [
            {
                "id": c.id,
                "title": c.title,
                "last_message": c.last_message or ""
            }
            for c in chats
        ]
    finally:
        db.close()


# GET CHAT HISTORY
@router.get("/chat/history/{chat_id}")
async def get_chat_history(chat_id: int):
    cursor = messages_collection.find({"chat_id": chat_id}).sort("_id", 1)
    messages = await cursor.to_list(length=100)
    return [{"role": m["role"], "text": m["text"]} for m in messages]


# DELETE CHAT — removes MySQL row + all Mongo messages for this chat
@router.delete("/chat/delete/{chat_id}")
async def delete_chat(chat_id: int):
    # 1. Delete from MySQL
    db = SessionLocal()
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Manually delete associated files to avoid foreign key IntegrityError
        db.query(File).filter(File.chat_id == chat_id).delete()
        
        db.delete(chat)
        db.commit()
    finally:
        db.close()

    # 2. Delete all messages from MongoDB
    await messages_collection.delete_many({"chat_id": chat_id})

    return {"success": True, "deleted_chat_id": chat_id}