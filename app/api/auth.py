from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.auth import UserRegisterRequest, UserVerifyRequest, UserLoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new unverified user and triggers a 6-digit verification code email via SMTP."
)
async def register(
    req: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    return await service.register_user(req)

@router.post(
    "/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify user email address",
    description="Validates the 6-digit verification code sent to the user's email address."
)
async def verify(
    req: UserVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    return await service.verify_user(req)

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and obtain token",
    description="Authenticates credentials. Raises error if the user is not verified, resending the verification email."
)
async def login(
    req: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    service = AuthService(db)
    return await service.login_user(req)
