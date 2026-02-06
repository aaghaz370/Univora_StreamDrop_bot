# app.py (THE REAL, FINAL, CLEAN, EASY-TO-READ FULL CODE)

import os
import asyncio
import secrets
import traceback
import uvicorn
import re
import logging
from contextlib import asynccontextmanager

from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from pyrogram.errors import FloodWait, UserNotParticipant
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pyrogram.file_id import FileId
from pyrogram import raw
from pyrogram.session import Session, Auth
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import math

# Project ki dusri files se important cheezein import karo
from config import Config
from database import db

# =====================================================================================
# --- SETUP: BOT, WEB SERVER, AUR LOGGING ---
# =====================================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Yeh function bot ko web server ke saath start aur stop karta hai.
    """
    print("--- Lifespan: Server chalu ho raha hai... ---")
    
    await db.connect()
    
    try:
        print("Starting main Pyrogram bot...")
        await bot.start()
        
        me = await bot.get_me()
        Config.BOT_USERNAME = me.username
        print(f"✅ Main Bot [@{Config.BOT_USERNAME}] safaltapoorvak start ho gaya.")

        if len(multi_clients) > 1:
            print(f"✅ Multi-Client Mode Enabled. Total Clients: {len(multi_clients)}")

        # Ensure we know about the channels
        # force_refresh_dialogs removed as it is not supported for bots

        print(f"Verifying storage channel ({Config.STORAGE_CHANNEL})...")
        try:
            await bot.get_chat(Config.STORAGE_CHANNEL)
            print("✅ Storage channel accessible hai.")
        except Exception as e:
            print(f"!!! ERROR: Could not access Storage Channel ({Config.STORAGE_CHANNEL}). Make sure the bot is a MEMBER and ADMIN in this channel. Error: {e}")

        if Config.FORCE_SUB_CHANNEL:
            try:
                print(f"Verifying force sub channel ({Config.FORCE_SUB_CHANNEL})...")
                await bot.get_chat(Config.FORCE_SUB_CHANNEL)
                print("✅ Force Sub channel accessible hai.")
            except Exception as e:
                print(f"!!! WARNING: Bot cannot access Force Sub channel ({Config.FORCE_SUB_CHANNEL}). Bot, Force Sub channel mein admin nahi hai ya link galat hai. Error: {e}")

        # Verify Backup Channels
        if Config.BACKUP_CHANNELS:
            print(f"Verifying {len(Config.BACKUP_CHANNELS)} Backup Channels...")
            for ch_id in Config.BACKUP_CHANNELS:
                try:
                    await bot.get_chat(ch_id)
                    print(f"✅ Backup Channel {ch_id} accessible.")
                except Exception as e:
                    print(f"!!! WARNING: Backup Channel {ch_id} not accessible (Make sure bot is ADMIN). Error: {e}")
        
        try:
            await cleanup_channel(bot)
        except Exception as e:
            print(f"Warning: Channel cleanup fail ho gaya. Error: {e}")

        print("--- Lifespan: Startup safaltapoorvak poora hua. ---")
    
    except Exception as e:
        print(f"!!! FATAL ERROR: Bot startup ke dauraan error aa gaya: {traceback.format_exc()}")
    
    yield
    
    print("--- Lifespan: Server band ho raha hai... ---")
    if bot.is_initialized:
        await bot.stop()
    print("--- Lifespan: Shutdown poora hua. ---")

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOG FILTER: YEH SIRF /dl/ WALE LOGS KO CHUPAYEGA ---
# class HideDLFilter(logging.Filter):
#     def filter(self, record: logging.LogRecord) -> bool:
#         # Agar log message mein "GET /dl/" hai, toh usse mat dikhao
#         return "GET /dl/" not in record.getMessage()

# Uvicorn ke 'access' logger par filter lagao
# logging.getLogger("uvicorn.access").addFilter(HideDLFilter())
# --- FIX KHATAM ---

bot = Client("SimpleStreamBot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN, in_memory=False)
multi_clients = {}; work_loads = {}; class_cache = {}

# =====================================================================================
# --- MULTI-CLIENT LOGIC ---
# =====================================================================================

class TokenParser:
    """ Environment variables se MULTI_TOKENs ko parse karta hai. """
    @staticmethod
    def parse_from_env():
        return {
            c + 1: t
            for c, (_, t) in enumerate(
                filter(lambda n: n[0].startswith("MULTI_TOKEN"), sorted(os.environ.items()))
            )
        }

async def start_client(client_id, bot_token):
    """ Ek naye client bot ko start karta hai. """
    try:
        print(f"Attempting to start Client: {client_id}")
        client = await Client(
            name=str(client_id), 
            api_id=Config.API_ID, 
            api_hash=Config.API_HASH,
            bot_token=bot_token, 
            no_updates=True, 
            in_memory=True
        ).start()
        work_loads[client_id] = 0
        multi_clients[client_id] = client
        print(f"✅ Client {client_id} started successfully.")
    except Exception as e:
        print(f"!!! CRITICAL ERROR: Failed to start Client {client_id} - Error: {e}")

async def initialize_clients():
    """ Saare additional clients ko initialize karta hai. """
    all_tokens = TokenParser.parse_from_env()
    if not all_tokens:
        print("No additional clients found. Using default bot only.")
        return
    
    print(f"Found {len(all_tokens)} extra clients. Starting them...")
    tasks = [start_client(i, token) for i, token in all_tokens.items()]
    await asyncio.gather(*tasks)

    if len(multi_clients) > 1:
        print(f"✅ Multi-Client Mode Enabled. Total Clients: {len(multi_clients)}")

# =====================================================================================
# --- HELPER FUNCTIONS ---
# =====================================================================================

def get_readable_file_size(size_in_bytes):
    if not size_in_bytes:
        return '0B'
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size_in_bytes >= power and n < len(power_labels) - 1:
        size_in_bytes /= power
        n += 1
    return f"{size_in_bytes:.2f} {power_labels[n]}"

def mask_filename(name: str):
    if not name:
        return "Protected File"
    base, ext = os.path.splitext(name)
    metadata_pattern = re.compile(
        r'((19|20)\d{2}|4k|2160p|1080p|720p|480p|360p|HEVC|x265|BluRay|WEB-DL|HDRip)',
        re.IGNORECASE
    )
    match = metadata_pattern.search(base)
    if match:
        title_part = base[:match.start()].strip(' .-_')
        metadata_part = base[match.start():]
    else:
        title_part = base
        metadata_part = ""
    masked_title = ''.join(c if (i % 3 == 0 and c.isalnum()) else ('*' if c.isalnum() else c) for i, c in enumerate(title_part))
    return f"{masked_title} {metadata_part}{ext}".strip()

# =====================================================================================
# --- PYROGRAM BOT HANDLERS ---
# =====================================================================================

@bot.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    # --- SECURITY CHECK ---
    if user_id != Config.OWNER_ID:
        await message.reply_text("🚫 **Access Denied!**\n\nThis bot is private and you are not authorized to use it.")
        return
    # ----------------------

    user_name = message.from_user.first_name
    
    if len(message.command) > 1 and message.command[1].startswith("verify_"):
        unique_id = message.command[1].split("_", 1)[1]
        
        # Note: Force Sub removed for owner-only bot, but keeping logic clean
        
        final_link = f"{Config.BASE_URL}/show/{unique_id}"
        reply_text = f"__✅ Verification Successful!\n\nCopy Link:__ `{final_link}`"
        
        button = None
        # FIX: Telegram Invalid URL for localhost
        # Telegram does not allow 'localhost' or '127.0.0.1' in button URLs.
        # If running locally, we just send the text link, or use a dummy public URL if needed.
        if "localhost" not in Config.BASE_URL and "127.0.0.1" not in Config.BASE_URL:
            button = InlineKeyboardMarkup([[InlineKeyboardButton("Open Link", url=final_link)]])
        
        await message.reply_text(reply_text, reply_markup=button, quote=True, disable_web_page_preview=True)

    else:
        reply_text = f"""
👋 **Hello Owner!**

I am ready to store your files with **Triple Redundancy** (MongoDB).

**Commands:**
/stats - Check Database Stats
/dashboard - Manage All Files

Send me any file to start.
"""
        await message.reply_text(reply_text)

@bot.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    count = await db.count_links()
    await message.reply_text(f"📊 **Database Stats**\n\n**Total Files Stored:** `{count}`\n**Database:** MongoDB Atlas")

@bot.on_message(filters.command("dashboard") & filters.private)
async def dashboard_command(client: Client, message: Message):
    if message.from_user.id != Config.OWNER_ID: return
    link = f"{Config.BASE_URL}/dashboard?key={Config.ADMIN_SECRET}"
    
    # Use Button for clickable action
    button = InlineKeyboardMarkup([[InlineKeyboardButton("🎛 Open Dashboard", url=link)]])
    
    # Check for localhost warning (Telegram blocks localhost buttons)
    if "localhost" in link or "127.0.0.1" in link:
        await message.reply_text(f"🎛 **Admin Dashboard**\n\nLink: `{link}`\n\n(Buttons disabled on localhost)", disable_web_page_preview=True)
    else:
        await message.reply_text(f"🎛 **Admin Dashboard**\n\nClick below to manage files.", reply_markup=button)

async def handle_file_upload(message: Message, user_id: int):
    # --- SECURITY CHECK ---
    if user_id != Config.OWNER_ID:
        await message.reply_text("🚫 **Access Denied!**")
        return
    # ----------------------
    
    status_msg = await message.reply_text("⏳ **Processing & Backing up...**", quote=True)
    
    try:
        # 1. Main Channel Upload
        main_msg = await message.copy(chat_id=Config.STORAGE_CHANNEL)
        main_id = main_msg.id
        
        # 2. Backup Channels Upload
        backups = {}
        for ch_id in Config.BACKUP_CHANNELS:
            try:
                # Force refresh if needed by calling get_chat first
                # If peer id invalid, it usually means we haven't 'seen' this chat.
                # But copy() should work if bot is admin. 
                # Let's try to get_chat blindly first to cache the peer.
                try: await bot.get_chat(ch_id) 
                except: pass
                
                b_msg = await message.copy(chat_id=ch_id)
                backups[str(ch_id)] = b_msg.id
            except Exception as e:
                print(f"Backup failed for {ch_id}: {e}")
        
        unique_id = secrets.token_urlsafe(8)
        
        # Extract File Name & Size
        media = message.document or message.video or message.audio
        file_name = media.file_name if media and media.file_name else "file"
        file_size = get_readable_file_size(media.file_size)
        safe_file_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
        
        # Save to MongoDB
        await db.save_link(unique_id, main_id, backups, file_name, file_size)
        
        stream_link = f"{Config.BASE_URL}/show/{unique_id}"
        download_link = f"{Config.BASE_URL}/dl/{unique_id}/{safe_file_name}"
        embed_link = f"{Config.BASE_URL}/embed/{unique_id}"

        text = f"""
**📂 File Name:** `{file_name}`

**▶️ Stream Link:**
`{stream_link}`

**📥 Download Link:**
`{download_link}`

**🔗 Embed Link:**
`{embed_link}`
"""
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📥 Download", url=download_link),
                InlineKeyboardButton("📺 Stream", url=stream_link)
            ]
        ])

        try:
            await status_msg.edit_text(text, reply_markup=buttons)
        except Exception as e:
            if "BUTTON_URL_INVALID" in str(e):
                # Fallback for localhost/private IPs which Telegram rejects
                text += "\n\n⚠️ **Note:** Buttons cannot contain 'localhost' links due to Telegram API restrictions. Please copy the links above."
                await status_msg.edit_text(text)
            else:
                # If it's another error, print it but still show text
                print(f"Error sending buttons: {e}")
                await status_msg.edit_text(text)
    except Exception as e:
        print(f"!!! ERROR: {traceback.format_exc()}")
        await status_msg.edit_text(f"Error: {e}")

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def file_handler(_, message: Message):
    await handle_file_upload(message, message.from_user.id)

# Gatekeeper removed or simplified since it's owner only but keeping cleanup for safety
async def cleanup_channel(c: Client):
    pass # No cleanup needed for personal bot usually

# Helper for Advanced Failover Logic
async def get_target_message(client, main_msg_id, backups):
    """
    Tries to get the message from the Main Channel first.
    If that fails (deleted/banned/not found), iterates through Backup Channels.
    Returns the first valid Message object found, or None.
    """
    # List of candidates: (Channel ID, Message ID)
    candidates = [(Config.STORAGE_CHANNEL, main_msg_id)]
    
    if backups:
        for ch_id, msg_id in backups.items():
            try:
                candidates.append((int(ch_id), int(msg_id)))
            except:
                pass

    for ch_id, msg_id in candidates:
        try:
            # print(f"DEBUG: Trying to fetch from {ch_id}:{msg_id}")
            msg = await client.get_messages(ch_id, msg_id)
            if not msg.empty and (msg.document or msg.video or msg.audio):
                print(f"DEBUG: Success fetching from {ch_id}")
                return msg
        except Exception as e:
            # print(f"DEBUG: Failed fetching from {ch_id}: {e}")
            continue
            
    return None

@app.get("/api/file/{unique_id}", response_class=JSONResponse)
async def get_file_details_api(request: Request, unique_id: str):
    message_id, backups = await db.get_link(unique_id)
    if not message_id:
        raise HTTPException(status_code=404, detail="Link expired or invalid.")
    
    main_bot = multi_clients.get(0) or bot
    if not main_bot: raise HTTPException(503, "Bot not ready")

    # Use Advanced Failover
    target_msg = await get_target_message(main_bot, message_id, backups)
    
    if not target_msg:
        raise HTTPException(status_code=404, detail="File NOT FOUND in any channel (Main + Backups).")

    media = target_msg.document or target_msg.video or target_msg.audio
    if not media:
        raise HTTPException(status_code=404, detail="Media not found.")
        
    file_name = media.file_name or "file"
    safe_file_name = "".join(c for c in file_name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
    mime_type = media.mime_type or "application/octet-stream"
    
    response_data = {
        "file_name": file_name, 
        "file_size": get_readable_file_size(media.file_size),
        "is_media": mime_type.startswith(("video", "audio")),
        "mime_type": mime_type, # Added mime_type for embed player
        "direct_dl_link": f"{Config.BASE_URL}/dl/{unique_id}/{safe_file_name}",
        "embed_link": f"{Config.BASE_URL}/embed/{unique_id}", # Added Embed Link
        "mx_player_link": f"intent:{Config.BASE_URL}/dl/{unique_id}/{safe_file_name}#Intent;action=android.intent.action.VIEW;type={mime_type};end",
        "vlc_player_link": f"intent:{Config.BASE_URL}/dl/{unique_id}/{safe_file_name}#Intent;action=android.intent.action.VIEW;type={mime_type};package=org.videolan.vlc;end"
    }
    return response_data

# =====================================================================================
# --- FASTAPI WEB SERVER ---
# =====================================================================================
 
@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Univora Server Running"}

@app.get("/show/{unique_id}", response_class=HTMLResponse)
async def show_page(request: Request, unique_id: str):
    return templates.TemplateResponse("show.html", {"request": request})

@app.get("/embed/{unique_id}", response_class=HTMLResponse)
async def embed_page(request: Request, unique_id: str):
    # --- DOMAIN RESTRICTION LOGIC ---
    allowed_domains = [d.strip().lower() for d in Config.ALLOWED_DOMAINS if d.strip()]
    
    # Use generic 'allow' if list is empty
    # If list has items -> Strict Mode
    
    if allowed_domains:
        referer = request.headers.get("referer", "")
        is_allowed = False
        ref_domain = "Direct/Unknown"

        if referer:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(referer)
                ref_domain = parsed.netloc.lower()
                if ":" in ref_domain: ref_domain = ref_domain.split(":")[0]
                
                # Check match
                for allowed in allowed_domains:
                     if ref_domain == allowed or ref_domain.endswith(f".{allowed}"):
                         is_allowed = True
                         break
            except:
                pass
        
        # Localhost Exception for testing (always allow localhost to see if it works)
        if ref_domain in ["localhost", "127.0.0.1"]:
            is_allowed = True
            
        print(f"DEBUG EMBED: Ref='{ref_domain}' | Allowed={is_allowed} | Whitelist={allowed_domains}")

        if not is_allowed:
            # --- RESTRICTED PAGE ---
            # We must ensure this error page ITSELF allows framing so the user sees the message!
            error_html = """
                <html>
                <body style="background:black; color:red; display:flex; justify-content:center; align-items:center; height:100vh; font-family:sans-serif; text-align:center; margin:0;">
                    <div>
                        <h1 style="font-size:3rem; margin:0;">ACCESS DENIED !</h1>
                        <h2 style="font-size:4rem; margin:10px 0;">FUCK YOU !</h2>
                        <p>Unauthorized Domain. Use only on allowed websites.</p>
                    </div>
                </body>
                </html>
                """
            return HTMLResponse(
                status_code=403,
                content=error_html,
                headers={
                    "Content-Security-Policy": "frame-ancestors *", # Allow error to be shown anywhere
                    "X-Frame-Options": "ALLOWALL"
                }
            )

    # --- SUCCESS ---
    response = templates.TemplateResponse("embed.html", {"request": request})
    
    # Headers for Embedding
    response.headers["Access-Control-Allow-Origin"] = "*"
    # response.headers["X-Frame-Options"] = "ALLOWALL" # Deprecated but sometimes useful, conflicting with CSP?
    # Better to omit X-Frame-Options if using CSP frame-ancestors.
    
    if allowed_domains:
        csp_domains = " ".join([f"https://{d} http://{d} https://*.{d} http://*.{d}" for d in allowed_domains])
        # Add localhost for testing explicitly in CSP
        response.headers["Content-Security-Policy"] = f"frame-ancestors 'self' {csp_domains} http://localhost:* https://localhost:* http://127.0.0.1:* https://127.0.0.1:*"
        # If no domains restricted, allow everything
        response.headers["Content-Security-Policy"] = "frame-ancestors *"
        
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, key: str = ""):
    if key != Config.ADMIN_SECRET:
        return HTMLResponse("<h1>403 Forbidden - Invalid Secret Key</h1>", status_code=403)
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/all_files")
async def api_all_files(key: str = ""):
    if key != Config.ADMIN_SECRET:
         raise HTTPException(403, "Invalid Key")
    
    files = await db.get_all_links()
    # Sanitize for JSON
    safe_files = []
    for f in files:
        f_safe = f.copy()
        f_safe["_id"] = str(f["_id"])
        if "backups" in f_safe: del f_safe["backups"] # Clean from frontend
        safe_files.append(f_safe)
        
    return safe_files

class ByteStreamer:
    def __init__(self, c: Client):
        self.client = c

    @staticmethod
    async def get_location(f: FileId):
        return raw.types.InputDocumentFileLocation(
            id=f.media_id,
            access_hash=f.access_hash,
            file_reference=f.file_reference,
            thumb_size=f.thumbnail_size
        )

    async def fetch_chunk(self, ms, loc, offset, limit):
        for attempt in range(5):
            try:
                r = await ms.invoke(
                    raw.functions.upload.GetFile(location=loc, offset=offset, limit=limit),
                    retries=1
                )
                if isinstance(r, raw.types.upload.File):
                    return r.bytes
                elif isinstance(r, raw.types.upload.FileCdnRedirect):
                    print("DEBUG: CDN Redirect")
                    break
            except (FloodWait) as e:
                await asyncio.sleep(e.value + 1)
            except Exception as e:
                await asyncio.sleep(0.5)
        return None

    async def yield_file(self, f: FileId, i: int, start_byte: int, end_byte: int, chunk_size: int):
        c = self.client
        if i not in work_loads:
            work_loads[i] = 0
        work_loads[i] += 1
        
        # Session Retrieval / Creation with Retry
        ms = None
        for _ in range(3):
            try:
                ms = c.media_sessions.get(f.dc_id)
                if ms is None:
                    if f.dc_id != await c.storage.dc_id():
                        ak = await Auth(c, f.dc_id, await c.storage.test_mode()).create()
                        ms = Session(c, f.dc_id, ak, await c.storage.test_mode(), is_media=True)
                        await ms.start()
                        
                        # Re-export/Import Auth
                        ea = await c.invoke(raw.functions.auth.ExportAuthorization(dc_id=f.dc_id))
                        await ms.invoke(raw.functions.auth.ImportAuthorization(id=ea.id, bytes=ea.bytes))
                    else:
                        ms = c.session
                    c.media_sessions[f.dc_id] = ms
                break
            except Exception as e:
                print(f"DEBUG: Session creation failed, retrying... {e}")
                await asyncio.sleep(1)

        if not ms:
            print("CRITICAL: Could not create media session.")
            if i in work_loads: work_loads[i] -= 1
            return 

        loc = await self.get_location(f)
        
        try:
            current_pos = start_byte
            bytes_remaining = end_byte - start_byte + 1
            
            while bytes_remaining > 0:
                chunk_index = current_pos // chunk_size
                req_offset = chunk_index * chunk_size
                
                chunk_data = await self.fetch_chunk(ms, loc, req_offset, chunk_size)
                
                if chunk_data is None:
                    print(f"CRITICAL: Failed to fetch chunk at {req_offset}")
                    break
                
                offset_in_chunk = current_pos % chunk_size
                
                if offset_in_chunk >= len(chunk_data):
                     break

                # Slice what we need
                available = len(chunk_data) - offset_in_chunk
                to_take = min(available, bytes_remaining)
                
                payload = chunk_data[offset_in_chunk : offset_in_chunk + to_take]
                
                yield payload
                
                sent_len = len(payload)
                current_pos += sent_len
                bytes_remaining -= sent_len
                
                if sent_len == 0:
                    break

        except Exception as e:
            print(f"Stream Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
             if i in work_loads: work_loads[i] -= 1

@app.get("/dl/{unique_id}/{fname}")
async def stream_media(r:Request,unique_id:str,fname:str):
    # Lookup DB
    message_id, backups = await db.get_link(unique_id)
    if not message_id: raise HTTPException(404, "Link invalid")

    # Fallback logic for client selection
    c = None
    client_id = 0
    if work_loads and multi_clients:
        client_id = min(work_loads, key=work_loads.get)
        c = multi_clients.get(client_id)
    if not c: c = bot or multi_clients.get(0)
    
    tc=class_cache.get(c) or ByteStreamer(c);class_cache[c]=tc
    
    # Use Advanced Failover
    target_msg = await get_target_message(c, message_id, backups)

    if not target_msg: raise HTTPException(404, "Lost File - All sources failed")
    
    try:
        m=target_msg.document or target_msg.video or target_msg.audio
        if not m:raise FileNotFoundError
        fid=FileId.decode(m.file_id);fsize=m.file_size;rh=r.headers.get("Range","");fb,ub=0,fsize-1
        if rh:
            rps=rh.replace("bytes=","").split("-");fb=int(rps[0])
            if len(rps)>1 and rps[1]:ub=int(rps[1])
        if(ub>=fsize)or(fb<0):raise HTTPException(416)
        rl=ub-fb+1;cs=1024*1024
        
        body=tc.yield_file(fid,client_id,fb,ub,cs)
        
        sc=206 if rh else 200
        hdrs={"Content-Type":m.mime_type or "application/octet-stream","Accept-Ranges":"bytes","Content-Disposition":f'inline; filename="{m.file_name}"',"Content-Length":str(rl)}
        if rh:hdrs["Content-Range"]=f"bytes {fb}-{ub}/{fsize}"
        return StreamingResponse(body,status_code=sc,headers=hdrs)
    except FileNotFoundError:raise HTTPException(404)
    except Exception:print(traceback.format_exc());raise HTTPException(500)

# =====================================================================================
# --- MAIN EXECUTION BLOCK ---
# =====================================================================================

@app.on_event("shutdown")
async def shutdown_event():
    print("🔻 Shutting down... Killing Telegram Bot...")
    if bot.is_connected:
       await bot.stop()
    print("✅ Bot stopped.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # timeout_keep_alive=0 helps aggressive killing of old connections
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info", timeout_keep_alive=5)
