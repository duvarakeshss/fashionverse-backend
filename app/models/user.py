from datetime import datetime
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class User(Base):
    """User database model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    verification_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    verification_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Personal Information & Preferences
    shopping_for: Mapped[str | None] = mapped_column(String(100), nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_palettes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    weekly_occasions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    climate: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fashion_goals: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    budget_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_brands: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    wardrobe_items: Mapped[list["WardrobeItem"]] = relationship(
        "WardrobeItem", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
