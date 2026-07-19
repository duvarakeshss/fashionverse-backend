import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.outfits import router as outfits_router
from app.api.users import router as users_router
from app.api.wardrobe import router as wardrobe_router
from app.config import settings
from app.database.connection import init_db
from app.utils.exceptions import UploadError


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fashionverse")


# -----------------------------------------------------------------------------
# Application Lifespan
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")

    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize database")

    # Initialize storage backend
    from app.services.storage_service import get_storage_backend
    storage = get_storage_backend()
    logger.info("Initializing storage backend...")
    await storage.initialize()
    logger.info("Storage backend initialized successfully.")

    try:
        yield
    finally:
        logger.info("Closing storage backend...")
        await storage.close()
        logger.info("Application shutdown.")


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------

app = FastAPI(
    title="FashionVerse - Image Upload API",
    version="1.0.0",
    lifespan=lifespan,
)


# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Serving Uploaded Files
# -----------------------------------------------------------------------------

from fastapi import Depends
from fastapi.responses import RedirectResponse, FileResponse
from app.services.storage_service import get_storage_backend, LocalStorageBackend, StorageBackend

@app.get("/uploads/{file_path:path}")
async def serve_uploaded_file(
    file_path: str,
    storage: StorageBackend = Depends(get_storage_backend)
):
    # If using a cloud storage backend (like Azure), redirect to the direct URL
    if not isinstance(storage, LocalStorageBackend):
        return RedirectResponse(storage.get_url(file_path))
    
    # Otherwise serve from local uploads directory
    local_path = settings.UPLOAD_DIR / file_path
    if not local_path.exists() or not local_path.is_file():
        return JSONResponse(status_code=404, content={"detail": "File not found"})
    return FileResponse(local_path)


# -----------------------------------------------------------------------------
# Routers
# -----------------------------------------------------------------------------

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(wardrobe_router, prefix="/api/v1")
app.include_router(outfits_router, prefix="/api/v1")


# -----------------------------------------------------------------------------
# Exception Handlers
# -----------------------------------------------------------------------------

@app.exception_handler(UploadError)
async def upload_exception_handler(request: Request, exc: UploadError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        f'{" -> ".join(map(str, err.get("loc", [])))}: {err.get("msg", "Validation error")}'
        for err in exc.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "detail": "; ".join(errors) or "Validation failed",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unexpected server error")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "Internal server error",
        },
    )