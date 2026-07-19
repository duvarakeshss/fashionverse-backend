"""
Base Test Case Class.
Handles setup/teardown of test database tables, local storage fallback for testing, and FastAPI TestClient dependency overrides.
"""
import asyncio
import shutil
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.config import settings
from app.database.connection import get_db
from app.models.base import Base
from app.services.storage_service import get_storage_backend, LocalStorageBackend

# Use a separate test uploads folder
TEST_UPLOAD_DIR = Path(__file__).resolve().parent / "temp_uploads"

# Create a dedicated test engine with NullPool to prevent transaction conflicts
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
test_session_maker = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def override_get_db():
    """Yields sessions from the isolated test database engine."""
    async with test_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


class BaseTestCase(unittest.IsolatedAsyncioTestCase):
    """Base class for all application tests providing isolated DB and storage environments."""

    async def asyncSetUp(self) -> None:
        # 1. Clean up and recreate the test uploads directory
        if TEST_UPLOAD_DIR.exists():
            shutil.rmtree(TEST_UPLOAD_DIR)
        TEST_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        (TEST_UPLOAD_DIR / "temp").mkdir(parents=True, exist_ok=True)

        # 2. Reset database schema for clean isolation using the test engine
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        # Seed default test user (ID: 1)
        from app.models.user import User
        from app.services.auth_service import hash_password
        from sqlalchemy import text
        async with test_session_maker() as session:
            async with session.begin():
                default_user = User(
                    id=1,
                    name="Test User",
                    email="test@example.com",
                    password_hash=hash_password("password"),
                    is_verified=True
                )
                session.add(default_user)
                await session.flush()
                # Sync sequence in postgres so auto-increment works correctly
                if "postgresql" in settings.DATABASE_URL:
                    await session.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users"))

        # 3. Setup Test Client
        self.client = TestClient(app)

        # 4. Dependency overrides
        app.dependency_overrides[get_db] = override_get_db
        self.test_storage = LocalStorageBackend(base_dir=TEST_UPLOAD_DIR)
        await self.test_storage.initialize()
        app.dependency_overrides[get_storage_backend] = lambda: self.test_storage

        # Force active storage backend singleton to use test storage (for direct calls in Pydantic validators)
        import app.services.storage_service as storage_service_module
        self._old_active_storage = storage_service_module._active_storage_backend
        storage_service_module._active_storage_backend = self.test_storage

    async def asyncTearDown(self) -> None:
        # Restore active storage backend singleton
        import app.services.storage_service as storage_service_module
        storage_service_module._active_storage_backend = self._old_active_storage

        # Remove dependency overrides
        app.dependency_overrides.clear()

        # Clean up storage backend
        await self.test_storage.close()

        # Dispose connection pool
        await test_engine.dispose()

        # Clean up files
        if TEST_UPLOAD_DIR.exists():
            shutil.rmtree(TEST_UPLOAD_DIR)

