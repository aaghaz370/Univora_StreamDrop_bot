import asyncio
import os
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("Error: .env file missing or empty API_ID/API_HASH/BOT_TOKEN.")
    exit(1)

async def main():
    print("--- Generating Session String ---")
    print("Connecting...")
    
    # Initialize with memory storage to create a fresh string
    app = Client(
        "UnivoraGenerator",
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )
    
    await app.start()
    
    # Export
    s = await app.export_session_string()
    print("\n✅ SESSION STRING GENERATED:\n")
    print(s)
    print("\n--------------------------------------------------------------")
    print("COPY THE STRING ABOVE AND ADD IT TO RENDER ENV VARS AS 'SESSION_STRING'")
    print("--------------------------------------------------------------")

    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
