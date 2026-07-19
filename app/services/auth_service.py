import hashlib
import os
import random
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import UserRegisterRequest, UserVerifyRequest, UserLoginRequest, TokenResponse, UserResponse
from app.services.email_service import EmailService
from app.utils.exceptions import UploadError
from app.config import settings

# Password hashing helpers using built-in hashlib (PBKDF2-HMAC-SHA256)
import jwt

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        parts = hashed.split('$')
        if len(parts) != 3 or parts[0] != "pbkdf2:sha256:100000":
            return False
        _, salt, key_hex = parts
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return key.hex() == key_hex
    except Exception:
        return False

def parse_expiration_time(expiration_str: str) -> timedelta:
    try:
        val = int(expiration_str[:-1])
        unit = expiration_str[-1].lower()
        if unit == 'h':
            return timedelta(hours=val)
        elif unit == 'd':
            return timedelta(days=val)
        elif unit == 'm':
            return timedelta(minutes=val)
    except Exception:
        pass
    return timedelta(hours=24)

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + parse_expiration_time(settings.JWT_EXPIRATION)
    payload = {
        "sub": str(user_id),
        "exp": expire
    }
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


class AuthService:
    """Service to handle user registration, verification, and authentication."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, req: UserRegisterRequest) -> UserResponse:
        # Check if email is already taken
        result = await self.db.execute(select(User).where(User.email == req.email))
        if result.scalar_one_or_none():
            raise UploadError("Email already registered", status_code=400)

        # Generate 6-digit code and expiration (15 minutes)
        code = f"{random.randint(100000, 999999)}"
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        new_user = User(
            name=req.name,
            email=req.email,
            password_hash=hash_password(req.password),
            is_verified=False,
            verification_code=code,
            verification_code_expires_at=expires_at
        )

        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)

        # Send verification email using SMTP Service
        await EmailService.send_verification_email(new_user.email, new_user.name, code)

        return UserResponse.model_validate(new_user)

    async def verify_user(self, req: UserVerifyRequest) -> dict:
        result = await self.db.execute(select(User).where(User.email == req.email))
        user = result.scalar_one_or_none()
        if not user:
            raise UploadError("User not found", status_code=404)

        if user.is_verified:
            return {"success": True, "message": "Email is already verified."}

        if user.verification_code != req.code:
            raise UploadError("Invalid verification code", status_code=400)

        if user.verification_code_expires_at and datetime.utcnow() > user.verification_code_expires_at:
            # Code expired. Generate a new one and send
            code = f"{random.randint(100000, 999999)}"
            user.verification_code = code
            user.verification_code_expires_at = datetime.utcnow() + timedelta(minutes=15)
            await self.db.commit()
            await EmailService.send_verification_email(user.email, user.name, code)
            raise UploadError("Verification code has expired. A new code has been sent to your email.", status_code=400)

        # Mark user as verified
        user.is_verified = True
        user.verification_code = None
        user.verification_code_expires_at = None
        await self.db.commit()

        return {"success": True, "message": "Email verified successfully. You can now log in."}

    async def login_user(self, req: UserLoginRequest) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.email == req.email))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(req.password, user.password_hash):
            raise UploadError("Invalid email or password", status_code=401)

        if not user.is_verified:
            # Resend code if they try to login unverified
            code = user.verification_code
            if not code or (user.verification_code_expires_at and datetime.utcnow() > user.verification_code_expires_at):
                code = f"{random.randint(100000, 999999)}"
                user.verification_code = code
                user.verification_code_expires_at = datetime.utcnow() + timedelta(minutes=15)
                await self.db.commit()
            await EmailService.send_verification_email(user.email, user.name, code)
            raise UploadError("Email not verified. A verification code has been sent to your email.", status_code=403)

        # Return token response
        token = create_access_token(user.id)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status

oauth2_scheme = HTTPBearer()

async def get_current_user_id(
    token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
) -> int:
    try:
        payload = jwt.decode(
            token.credentials, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject"
            )
        return int(user_id)
    except jwt.exceptions.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
