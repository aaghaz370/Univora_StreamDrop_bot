# config.py (UPDATED)

import os
from dotenv import load_dotenv

load_dotenv(".env", override=True)

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    SESSION_STRING = os.environ.get("SESSION_STRING", "")
    OWNER_ID = int(os.environ.get("OWNER_ID", 0))
    
    _storage_channel_str = os.environ.get("STORAGE_CHANNEL")
    if _storage_channel_str:
        try: STORAGE_CHANNEL = int(_storage_channel_str)
        except ValueError: STORAGE_CHANNEL = _storage_channel_str
    else: STORAGE_CHANNEL = 0
    
    BASE_URL = os.environ.get("BASE_URL", "").rstrip('/')
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "univora_admin") # Default secret if missing
    BLOGGER_PAGE_URL = os.environ.get("BLOGGER_PAGE_URL", "")
    
    # --- YAHAN BADLAV KIYA GAYA HAI ---
    # Force Subscribe ke liye channel ID/username
    _fsub_channel_str = os.environ.get("FORCE_SUB_CHANNEL")
    if _fsub_channel_str:
        try: FORCE_SUB_CHANNEL = int(_fsub_channel_str)
        except ValueError: FORCE_SUB_CHANNEL = _fsub_channel_str
    else: FORCE_SUB_CHANNEL = 0
        
    # Yeh bot ka username store karega
    BOT_USERNAME = ""
    
    # Backup Channels List
    _backup_str = os.environ.get("BACKUP_CHANNELS", "")
    BACKUP_CHANNELS = [int(x) for x in _backup_str.split(",") if x.strip()] if _backup_str else []

    # Allowed Domains for Embed (Add your domains here)
    # Example: ["mysite.com", "another-site.com"]
    # Empty list means ALLOW ALL
    ALLOWED_DOMAINS = os.environ.get("ALLOWED_DOMAINS", "").split(",") if os.environ.get("ALLOWED_DOMAINS") else []
    
    DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() in ("true", "1", "t")
