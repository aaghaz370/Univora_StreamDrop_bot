from pyrogram import Client
from config import Config
import asyncio

async def test():
    app = Client("test_bot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN, in_memory=True)
    await app.start()
    
    print("Bot started:")
    me = await app.get_me()
    print(me)
    
    print(f"\nTesting Storage Channel: {Config.STORAGE_CHANNEL}")
    try:
        chat = await app.get_chat(Config.STORAGE_CHANNEL)
        print(f"SUCCESS! Found chat: {chat.title} (ID: {chat.id})")
    except Exception as e:
        print(f"ERROR looking up Storage Channel: {e}")
        
    print(f"\nTesting Force Sub Channel: {Config.FORCE_SUB_CHANNEL}")
    try:
        chat = await app.get_chat(Config.FORCE_SUB_CHANNEL)
        print(f"SUCCESS! Found chat: {chat.title} (ID: {chat.id})")
    except Exception as e:
        print(f"ERROR looking up Force Sub Channel: {e}")

    await app.stop()

if __name__ == "__main__":
    asyncio.run(test())
