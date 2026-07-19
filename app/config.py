"""
Application Settings and Configuration.
Loads environment variables and sets up application-wide constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load env file from the project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

class Settings:
    DATABASE_URL: str | None = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is missing/empty")

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

    # Azure Storage Settings
    AZURE_STORAGE_CONNECTION_STRING: str | None = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_BLOB_CONTAINER_NAME: str | None = os.getenv("AZURE_BLOB_CONTAINER_NAME")

    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_ACCESS_SECRET")
    JWT_REFRESH_SECRET_KEY: str = os.getenv("JWT_REFRESH_SECRET")
    JWT_EXPIRATION: str = os.getenv("JWT_ACCESS_EXPIRATION")
    JWT_REFRESH_EXPIRATION: str  = os.getenv("JWT_REFRESH_EXPIRATION")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM")

    # Enforce that JWT settings are defined in env
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_ACCESS_SECRET environment variable is missing/empty")
    if not JWT_REFRESH_SECRET_KEY:
        raise ValueError("JWT_REFRESH_SECRET environment variable is missing/empty")
    if not JWT_EXPIRATION:
        raise ValueError("JWT_ACCESS_EXPIRATION environment variable is missing/empty")
    if not JWT_REFRESH_EXPIRATION:
        raise ValueError("JWT_REFRESH_EXPIRATION environment variable is missing/empty")
    if not JWT_ALGORITHM:
        raise ValueError("JWT_ALGORITHM environment variable is missing/empty")

    # OpenRouter LLM API
    OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")

    # SMTP Settings
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "FashionVerse <no-reply@fashionverse.com>")

settings = Settings()

# Ensure necessary uploads directories exist at import time
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(settings.UPLOAD_DIR / "temp").mkdir(parents=True, exist_ok=True) # Always needed for local ML image processing

# Only create fallback storage folders if we are running in local fallback mode (no Azure)
if not settings.AZURE_STORAGE_CONNECTION_STRING:
    (settings.UPLOAD_DIR / "profiles").mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "wardrobe").mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "processed").mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "thumbnails").mkdir(parents=True, exist_ok=True)
