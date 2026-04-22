import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://someshg897_db_user:xsH8Jg94y0L9tNd0@aiagent.albdljr.mongodb.net/rag_app?retryWrites=true&w=majority")

client = AsyncIOMotorClient(MONGO_URL)

db = client["rag_app"]

messages_collection = db["messages"]
#xsH8Jg94y0L9tNd0