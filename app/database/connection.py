from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

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
    import asyncpg
    from sqlalchemy.engine.url import make_url
    
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

    from app.models.base import Base
    from app.models.user import User
    from app.models.wardrobe import WardrobeItem  # noqa: F401 — ensure table is registered
    from sqlalchemy import select

    # Drop and recreate tables for clean state
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
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
                    password_hash="pbkdf2:sha256:260000$dummyhash",
                    is_verified=True
                )
                session.add(default_user)
                await session.flush()
                # Sync sequence in postgres so auto-increment works correctly
                from sqlalchemy import text
                await session.execute(text("SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1)) FROM users"))
