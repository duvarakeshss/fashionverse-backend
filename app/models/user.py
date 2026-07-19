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

    # Personal Information
    age: Mapped[int | None] = mapped_column(nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    climate_preference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Body Information
    skin_tone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    body_shape: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preferred_fit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Style Basics
    preferred_style: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    favorite_colors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    colors_to_avoid: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    wardrobe_items: Mapped[list["WardrobeItem"]] = relationship(
        "WardrobeItem", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
