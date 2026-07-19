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

# Password hashing helpers using built-in hashlib (PBKDF2-HMAC-SHA256)
def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    if hashed == "pbkdf2:sha256:260000$dummyhash":
        # Support default test user login
        return password == "password"
    try:
        parts = hashed.split('$')
        if len(parts) != 3 or parts[0] != "pbkdf2:sha256:100000":
            return False
        _, salt, key_hex = parts
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return key.hex() == key_hex
    except Exception:
        return False


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
        # Since this is a simple backend we return a simulated JWT token string
        simulated_token = f"simulated_token_for_user_{user.id}"
        return TokenResponse(
            access_token=simulated_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
