import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_GROUP_ID = os.getenv("ADMIN_GROUP_ID")

if ADMIN_GROUP_ID:
    try:
        ADMIN_GROUP_ID = int(ADMIN_GROUP_ID)
    except ValueError:
        ADMIN_GROUP_ID = None

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in environment variables.")
