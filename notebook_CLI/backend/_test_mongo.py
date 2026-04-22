import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
#mongodb+srv://someshg897_db_user:<db_password>@aiagent.albdljr.mongodb.net/?appName=AIAgent
async def test():
    client = AsyncIOMotorClient(
        "mongodb+srv://someshg897_db_user:xsH8Jg94y0L9tNd0@aiagent.albdljr.mongodb.net/rag_app?retryWrites=true&w=majority"
    )

    db = client["rag_app"]
    cols = await db.list_collection_names()
    print("MongoDB OK. Collections:", cols)

    # Test insert + read
    result = await db["messages"].insert_one({"chat_id": -1, "role": "test", "text": "ping"})
    print("Insert OK. ID:", result.inserted_id)

    # Cleanup
    await db["messages"].delete_many({"chat_id": -1})
    print("Cleanup OK.")
    client.close()

asyncio.run(test())
