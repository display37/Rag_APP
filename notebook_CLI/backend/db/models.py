from sqlalchemy import Column, Integer, String, ForeignKey, Text
from db.mysql import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    email = Column(String(255), unique=True)


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255), default="New Chat")
    last_message = Column(Text)


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    filename = Column(String(255))