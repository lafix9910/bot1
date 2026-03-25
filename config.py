import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]

ADMIN_USERNAMES = []
admin_usernames_str = os.getenv("ADMIN_USERNAMES", "")
if admin_usernames_str:
    ADMIN_USERNAMES = [x.strip().lstrip("@") for x in admin_usernames_str.split(",") if x.strip()]

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nail_bot.db")

WORKING_HOURS_START = int(os.getenv("WORKING_HOURS_START", "9"))
WORKING_HOURS_END = int(os.getenv("WORKING_HOURS_END", "20"))
SLOT_DURATION_MINUTES = int(os.getenv("SLOT_DURATION_MINUTES", "60"))
DAYS_IN_ADVANCE = int(os.getenv("DAYS_IN_ADVANCE", "14"))

ADMIN_PHONE = os.getenv("ADMIN_PHONE", "+7 (999) 000-00-00")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "username")
