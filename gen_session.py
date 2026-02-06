import asyncio
import os
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
STORAGE_CHANNEL = os.environ.get("STORAGE_CHANNEL")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("Error: .env file missing or empty API_ID/API_HASH/BOT_TOKEN.")
    exit(1)

async def main():
    print("=================================================")
    print("   UNIVORA SESSION GENERATOR (The Fixer)   ")
    print("=================================================")
    print("1. Connecting to Bot...")
    
    app = Client(
        "UnivoraGen",
        api_id=int(API_ID),
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )
    
    await app.start()
    print("✅ Bot Connected!")
    
    if STORAGE_CHANNEL:
        try:
            chat_id = int(STORAGE_CHANNEL)
            print(f"\n2. Testing Access to Storage Channel ({chat_id})...")
            try:
                chat = await app.get_chat(chat_id)
                print(f"   ✅ Success! Found channel: {chat.title}")
            except Exception as e:
                print(f"   ❌ Access Failed: {e}")
                print("   👉 ACTION REQUIRED: Go to Telegram and send a message to the Storage Channel NOW.")
                print("   I will wait 60 seconds...")
                for i in range(60):
                    await asyncio.sleep(1)
                    try:
                       await app.get_chat(chat_id)
                       print("   ✅ DETECTED! Channel access confirmed.")
                       break
                    except:
                        if i % 10 == 0: print(f"   ...waiting {60-i}s")
        except:
            print("   ⚠️ Invalid Storage Channel ID in .env")

    print("\n3. Generating Session String...")
    s = await app.export_session_string()
    
    print("\n" + "="*50)
    print("✅ YOUR NEW, VERIFIED SESSION STRING:")
    print("="*50)
    print(s)
    print("="*50)
    print("INSTRUCTIONS:")
    print("1. Copy the string above.")
    print("2. Go to RENDER -> Environment Variables.")
    print("3. Delete old 'SESSION_STRING'.")
    print("4. Add new 'SESSION_STRING' with this value.")
    print("5. Redeploy.")
    print("=================================================")

    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
