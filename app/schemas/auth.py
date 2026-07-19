from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not EMAIL_REGEX.match(v_clean):
            raise ValueError("Invalid email format")
        return v_clean

class UserVerifyRequest(BaseModel):
    """Schema for email verification request."""
    email: str = Field(..., max_length=255)
    code: str = Field(..., min_length=6, max_length=6)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not EMAIL_REGEX.match(v_clean):
            raise ValueError("Invalid email format")
        return v_clean

class UserLoginRequest(BaseModel):
    """Schema for user login request."""
    email: str
    password: str

class UserResponse(BaseModel):
    """Schema for returning user details."""
    id: int
    name: str
    email: str
    is_verified: bool
    profile_image: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    location: Optional[str] = None
    climate_preference: Optional[str] = None
    skin_tone: Optional[str] = None
    body_shape: Optional[str] = None
    preferred_fit: Optional[str] = None
    preferred_style: Optional[List[str]] = None
    favorite_colors: Optional[List[str]] = None
    colors_to_avoid: Optional[List[str]] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """Schema for returning access token and user info upon successful login."""
    access_token: str
    token_type: str
    user: UserResponse
