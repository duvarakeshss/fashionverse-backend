"""
User Profile Unit Tests.
Tests user profile updates, field validation constraints, profile image uploads, public URL resolution, and route security.
"""
import io
from unittest.mock import patch
from sqlalchemy import select

from app.models.user import User
from app.services.auth_service import create_access_token
from tests.base import BaseTestCase, test_session_maker


class TestProfile(BaseTestCase):
    """Verifies profile detail management and profile image uploads."""

    async def test_profile_crud_and_validation(self) -> None:
        # Initialize default user (ID: 1)
        token = create_access_token(1)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Get profile (should be empty initially except default values)
        response = self.client.get("/api/v1/users/1/profile", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], 1)
        self.assertIsNone(data["shopping_for"])

        # 2. Update profile with valid values
        update_payload = {
            "shopping_for": "Women",
            "height": 168.0,
            "body_type": "Hourglass",
            "preferred_palettes": ["Cool Summer"],
            "weekly_occasions": ["Office", "Casual"],
            "climate": "Temperate",
            "fashion_goals": ["Build a capsule wardrobe"],
            "budget_range": "$$$",
            "preferred_brands": ["Zara", "Mango"]
        }
        response = self.client.post("/api/v1/users/1/profile", json=update_payload, headers=headers)
        self.assertEqual(response.status_code, 200)
        updated_data = response.json()
        self.assertEqual(updated_data["shopping_for"], "Women")
        self.assertEqual(updated_data["height"], 168.0)
        self.assertEqual(updated_data["preferred_brands"], ["Zara", "Mango"])

        # Verify values persisted in database
        async with test_session_maker() as session:
            result = await session.execute(select(User).where(User.id == 1))
            db_user = result.scalar_one()
            self.assertEqual(db_user.height, 168.0)
            self.assertEqual(db_user.preferred_brands, ["Zara", "Mango"])

        # 3. Update profile with invalid height constraint
        invalid_payload = {"height": 400.0}  # limit is 300
        response = self.client.post("/api/v1/users/1/profile", json=invalid_payload, headers=headers)
        self.assertEqual(response.status_code, 422)

    async def test_profile_image_upload_and_public_url(self) -> None:
        # Initialize default user (ID: 1)
        token = create_access_token(1)
        headers = {"Authorization": f"Bearer {token}"}

        # Verify profile_image is None initially
        response = self.client.get("/api/v1/users/1/profile", headers=headers)
        self.assertIsNone(response.json()["profile_image"])

        # Prepare dummy image bytes
        from PIL import Image
        dummy_img = io.BytesIO()
        img = Image.new("RGB", (80, 60), color="blue")
        img.save(dummy_img, format="JPEG")
        dummy_img.seek(0)

        # Upload profile image
        response = self.client.post(
            "/api/v1/users/1/profile-image",
            files={"file": ("profile.jpg", dummy_img, "image/jpeg")},
            headers=headers
        )
        self.assertEqual(response.status_code, 201)
        upload_data = response.json()
        self.assertTrue(upload_data["success"])
        self.assertIn("/uploads/profiles/1/", upload_data["image_url"])

        # Verify profile image relative path in DB
        async with test_session_maker() as session:
            result = await session.execute(select(User).where(User.id == 1))
            db_user = result.scalar_one()
            self.assertIsNotNone(db_user.profile_image)
            self.assertTrue(db_user.profile_image.startswith("profiles/1/"))

        # Verify getting profile automatically returns the resolved public URL
        response = self.client.get("/api/v1/users/1/profile", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("/uploads/profiles/1/", response.json()["profile_image"])

    async def test_profile_security_protection(self) -> None:
        # Initialize default user (ID: 1)
        
        # User 1 token
        token_1 = create_access_token(1)
        headers_1 = {"Authorization": f"Bearer {token_1}"}

        # Try to access User 2's profile with User 1's token (should raise 403 Forbidden)
        response = self.client.get("/api/v1/users/2/profile", headers=headers_1)
        self.assertEqual(response.status_code, 403)

        # Try to update User 2's profile with User 1's token (should raise 403 Forbidden)
        response = self.client.post("/api/v1/users/2/profile", json={"shopping_for": "Men"}, headers=headers_1)
        self.assertEqual(response.status_code, 403)
