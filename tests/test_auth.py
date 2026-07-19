"""
Authentication Unit Tests.
Tests user registration, email verification code flows, login, token returns, and protected route access.
"""
from unittest.mock import patch
from sqlalchemy import select

from tests.base import BaseTestCase, test_session_maker
from app.models.user import User


class TestAuth(BaseTestCase):
    """Verifies all authentication, verification, and API protection rules."""

    async def test_user_registration_and_verification_flow(self) -> None:
        # 1. Register a new user
        reg_payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "securepassword"
        }
        
        # Mock EmailService.send_verification_email to avoid SMTP calls
        with patch("app.services.email_service.EmailService.send_verification_email") as mock_send_email:
            response = self.client.post("/api/v1/auth/register", json=reg_payload)
            self.assertEqual(response.status_code, 201)
            mock_send_email.assert_called_once()
            
        data = response.json()
        self.assertEqual(data["name"], "Jane Doe")
        self.assertEqual(data["email"], "jane@example.com")
        self.assertFalse(data["is_verified"])
        self.assertIsNone(data.get("password_hash"))

        # Verify user was saved in DB and retrieve verification code
        async with test_session_maker() as session:
            result = await session.execute(select(User).where(User.email == "jane@example.com"))
            db_user = result.scalar_one()
            self.assertFalse(db_user.is_verified)
            self.assertIsNotNone(db_user.verification_code)
            verification_code = db_user.verification_code

        # 2. Verify with invalid code should fail
        verify_fail_payload = {
            "email": "jane@example.com",
            "code": "000000"
        }
        response = self.client.post("/api/v1/auth/verify", json=verify_fail_payload)
        self.assertEqual(response.status_code, 400)

        # 3. Verify with correct code should succeed
        verify_success_payload = {
            "email": "jane@example.com",
            "code": verification_code
        }
        response = self.client.post("/api/v1/auth/verify", json=verify_success_payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        # Check DB to ensure status is now verified
        async with test_session_maker() as session:
            result = await session.execute(select(User).where(User.email == "jane@example.com"))
            db_user = result.scalar_one()
            self.assertTrue(db_user.is_verified)
            self.assertIsNone(db_user.verification_code)

        # 4. Attempt login with correct credentials
        login_payload = {
            "email": "jane@example.com",
            "password": "securepassword"
        }
        response = self.client.post("/api/v1/auth/login", json=login_payload)
        self.assertEqual(response.status_code, 200)
        login_data = response.json()
        self.assertEqual(login_data["token_type"], "bearer")
        self.assertIsNotNone(login_data["access_token"])
        self.assertEqual(login_data["user"]["email"], "jane@example.com")
        self.assertTrue(login_data["user"]["is_verified"])

    async def test_login_unverified_resends_code(self) -> None:
        # Register user
        reg_payload = {
            "name": "Unverified User",
            "email": "unverified@example.com",
            "password": "somepassword"
        }
        with patch("app.services.email_service.EmailService.send_verification_email") as mock_send_email:
            response = self.client.post("/api/v1/auth/register", json=reg_payload)
            self.assertEqual(response.status_code, 201)

        # Try logging in before verifying (should raise 403 and resend verification email)
        login_payload = {
            "email": "unverified@example.com",
            "password": "somepassword"
        }
        with patch("app.services.email_service.EmailService.send_verification_email") as mock_send_email:
            response = self.client.post("/api/v1/auth/login", json=login_payload)
            self.assertEqual(response.status_code, 403)
            self.assertIn("Email not verified", response.json()["detail"])
            mock_send_email.assert_called_once()

    async def test_protected_routes_require_valid_jwt(self) -> None:
        # Try to access a protected route without authorization header
        response = self.client.get("/api/v1/users/1/profile")
        self.assertEqual(response.status_code, 401)

        # Try to access with a malformed token
        headers = {"Authorization": "Bearer invalidtokenhere"}
        response = self.client.get("/api/v1/users/1/profile", headers=headers)
        self.assertEqual(response.status_code, 401)
