import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.database.connection import init_db
from app.api.users import router as users_router
from app.api.wardrobe import router as wardrobe_router
from app.api.outfits import router as outfits_router
from app.api.auth import router as auth_router
from app.utils.exceptions import UploadError

# Set up server-side logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fashionverse")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for database initialization on startup."""
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
    
    # Ensure upload directories exist
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "profiles").mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "wardrobe").mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "processed").mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "thumbnails").mkdir(parents=True, exist_ok=True)
    (settings.UPLOAD_DIR / "temp").mkdir(parents=True, exist_ok=True)
    
    yield

app = FastAPI(
    title="FashionVerse - Image Upload API",
    version="1.0.0",
    lifespan=lifespan
)

# Mount uploads static files directory to serve uploaded images
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Include routers
app.include_router(users_router, prefix="/api/v1")
app.include_router(wardrobe_router, prefix="/api/v1")
app.include_router(outfits_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

# Global Exception Handlers

@app.exception_handler(UploadError)
async def upload_exception_handler(request: Request, exc: UploadError):
    """Shared handler for validated custom upload errors (Empty, Size, Type, Decodability, 404)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Shared handler for standard Pydantic validation errors (category enum check)."""
    # Try to extract a clean string message or return raw validation errors
    errors = exc.errors()
    clean_details = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "Validation error")
        clean_details.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "detail": "; ".join(clean_details) or "Validation failed"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global handler for unexpected server errors (500), logging traceback server-side and hiding details from client."""
    logger.exception("An unexpected server error occurred:")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "Internal server error"
        }
    )
