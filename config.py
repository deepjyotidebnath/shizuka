import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")          # optional, e.g. +91XXXXXXXXXX
SESSION_NAME = os.getenv("SESSION_NAME", "broadcaster_session")  # CLI file-session fallback only

# Optional: a Telethon StringSession. If set, the app logs in with it and
# never needs a session file. On Streamlit Cloud put it in Secrets.
SESSION_STRING = os.getenv("TG_SESSION", "")

# Optional: if set, the Streamlit app asks for this password before showing anything.
APP_PASSWORD = os.getenv("APP_PASSWORD", "")

MESSAGE_TEXT = os.getenv("MESSAGE_TEXT", "Hii ...........")
DELAY_BETWEEN_SENDS = int(os.getenv("DELAY_BETWEEN_SENDS", "30"))

LOG_FILE = os.getenv("LOG_FILE", "broadcaster.log")
