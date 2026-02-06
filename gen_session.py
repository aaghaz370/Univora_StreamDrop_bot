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
    print("--- GENERATING STRING FROM LOCAL SESSION ---")
    print("This will convert your working local 'SimpleStreamBot.session' file into a string.")
    
    # Use the SAME session name as app.py to load the existing file
    app = Client(
        "SimpleStreamBot",
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        # in_memory=False ensures we load the file
        in_memory=False
    )
    
    try:
        await app.start()
    except Exception as e:
        print(f"Error starting bot: {e}")
        print("Make sure 'SimpleStreamBot.session' exists and is not corrupt.")
        return

    # Export Session String directly from the loaded file
    s = await app.export_session_string()
    print("\n✅ SUPER SESSION STRING GENERATED:\n")
    print(s)
    print("\n--------------------------------------------------------------")
    print("1. COPY the string above.")
    print("2. PASTE it into Render Environment Variables as 'SESSION_STRING'.")
    print("3. REDEPLOY.")
    print("--------------------------------------------------------------")

    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
