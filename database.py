# database.py (MONGODB VERSION)
import motor.motor_asyncio
import time
from config import Config

class Database:
    def __init__(self):
        self._client = None
        self.db = None
        self.col = None

    async def connect(self):
        print(f"Connecting to MongoDB...")
        self._client = motor.motor_asyncio.AsyncIOMotorClient(Config.DATABASE_URL)
        self.db = self._client["UnivoraStreamDrop"]
        self.col = self.db.links
        print("✅ Database connection established (MongoDB).")

    async def disconnect(self):
        if self._client:
            self._client.close()

    async def save_link(self, unique_id, message_id, backups: dict, file_name: str = "Unknown", file_size: str = "Unknown"):
        data = {
            "_id": unique_id,
            "msg_id": int(message_id),
            "backups": backups,
            "file_name": file_name,
            "file_size": file_size,
            "timestamp": int(time.time()),
            "date_str": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        await self.col.update_one({"_id": unique_id}, {"$set": data}, upsert=True)
        print(f"DEBUG DB: Saved {unique_id} to MongoDB.")

    async def get_link(self, unique_id):
        link = await self.col.find_one({"_id": unique_id})
        if link:
            return link["msg_id"], link.get("backups", {})
        return None, None

    async def get_all_links(self):
        cursor = self.col.find().sort("timestamp", -1)
        links = []
        async for document in cursor:
            links.append(document)
        return links
        
    async def delete_link(self, unique_id):
        await self.col.delete_one({"_id": unique_id})
        
    async def count_links(self):
        return await self.col.count_documents({})

db = Database()
