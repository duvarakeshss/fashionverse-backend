import os
from pathlib import Path
from dotenv import load_dotenv

# Load env file from the project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:1234@localhost:5433/fashionVerse"
    )
    # Ensure DATABASE_URL starts with postgresql+asyncpg for async SQLAlchemy
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Strip schema query parameter if present since asyncpg doesn't support it
    if "?" in DATABASE_URL:
        base_url, query_str = DATABASE_URL.split("?", 1)
        params = [p for p in query_str.split("&") if not p.startswith("schema=")]
        DATABASE_URL = f"{base_url}?{'&'.join(params)}" if params else base_url
        
    UPLOAD_DIR: Path = ROOT_DIR / "uploads"
    MAX_CONTENT_LENGTH: int = 10 * 1024 * 1024  # 10 MB in bytes
    
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}

    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "FashionVerse <no-reply@fashionverse.com>")

settings = Settings()

# Ensure all uploads directories exist at import time
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "profiles").mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "wardrobe").mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "processed").mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "thumbnails").mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "temp").mkdir(parents=True, exist_ok=True)
