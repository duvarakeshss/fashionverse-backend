"""
Database Connection and Initialization Service.
Manages the SQLAlchemy async engine and sessionmaker, initializes schemas, and handles database seeding.
"""
from collections.abc import AsyncGenerator
import asyncpg
from sqlalchemy import select, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.models.base import Base
from app.models.user import User
from app.models.wardrobe import WardrobeItem  # noqa: F401 — ensure table is registered
from app.services.auth_service import hash_password

# Create async engine and sessionmaker
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection provider for database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize the database tables and seed test data if necessary."""
    url = make_url(settings.DATABASE_URL)
    target_db = url.database
    
    try:
        conn = await asyncpg.connect(
            user=url.username,
            password=url.password,
            host=url.host,
            port=url.port,
            database="postgres"
        )
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", 
                target_db
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{target_db}"')
        finally:
            await conn.close()
    except Exception:
        pass

    # Create tables if they do not exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default user if not exists
    async with async_session_maker() as session:
        async with session.begin():
            # Check if default test user exists
            result = await session.execute(select(User).where(User.id == 1))
            user = result.scalar_one_or_none()
            if not user:
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
                await session.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users"))

