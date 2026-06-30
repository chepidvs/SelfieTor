import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
SUBMISSIONS_DIR = DATA_DIR / "submissions"
DB_PATH = DATA_DIR / "selfietor.db"

APP_PASSWORD_HASH = os.getenv("APP_PASSWORD_HASH", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")

SESSION_COOKIE = "selfietor_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 jam

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
