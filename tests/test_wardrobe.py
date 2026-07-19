"""
Wardrobe API Unit Tests.
Tests wardrobe item uploads, automated ML classification mocking, semantic searches, and AI outfit queries.
"""
import io
from unittest.mock import patch

from app.services.auth_service import create_access_token
from tests.base import BaseTestCase


class TestWardrobe(BaseTestCase):
    """Verifies wardrobe upload processing, semantic search similarity, and AI recommendation query endpoints."""

    async def test_wardrobe_upload_search_and_query_flow(self) -> None:
        # Initialize default user (ID: 1)
        token = create_access_token(1)
        headers = {"Authorization": f"Bearer {token}"}

        # Prepare a dummy image
        from PIL import Image
        dummy_img = io.BytesIO()
        img = Image.new("RGB", (80, 60), color="blue")
        img.save(dummy_img, format="JPEG")
        dummy_img.seek(0)

        # Mock ML classification response: predicted_category_raw, res_str, res list
        mock_ml_return = ("top", "Tshirts for men", ["Tshirts", "men", "Blue", "summer", "casual"])
        
        # Patch ML classification, embedding generation, and thumbnail generation
        def mock_thumb_effect(src, dst):
            with open(dst, "wb") as f:
                f.write(b"dummy thumbnail data")

        with patch("app.ml.recognition_module.single_classification", return_value=mock_ml_return) as mock_single_class, \
             patch("app.services.upload_service.generate_thumbnail") as mock_gen_thumb:
            
            mock_gen_thumb.side_effect = mock_thumb_effect

            # Perform upload
            response = self.client.post(
                "/api/v1/wardrobe/1/upload",
                files={"file": ("blue_shirt.jpg", dummy_img, "image/jpeg")},
                data={"brand": "BrandX", "notes": "My favorite shirt"},
                headers=headers
            )
            self.assertEqual(response.status_code, 201)
            mock_single_class.assert_called_once()
            mock_gen_thumb.assert_called_once()

        upload_data = response.json()
        self.assertEqual(upload_data["user_id"], 1)
        self.assertEqual(upload_data["category"], "top")
        self.assertEqual(upload_data["brand"], "BrandX")
        self.assertEqual(upload_data["type"], "Tshirts")
        self.assertEqual(upload_data["color"], "Blue")
        self.assertEqual(upload_data["season"], "summer")
        self.assertEqual(upload_data["usage"], "casual")
        self.assertIn("A blue tshirts for men, suitable for summer in casual occasions. Brand: BrandX.", upload_data["description"])

        # 2. Test semantic search endpoint
        search_response = self.client.get(
            "/api/v1/wardrobe/1/search?q=blue+summer+shirt&limit=5",
            headers=headers
        )
        self.assertEqual(search_response.status_code, 200)
        items = search_response.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], upload_data["id"])

        # 3. Test AI outfit query endpoint
        query_payload = {
            "query": "What should I wear for a casual summer day?",
            "limit": 5
        }
        
        mock_recommendation = "You should wear your blue BrandX T-shirt for a casual summer look."
        
        with patch("app.services.llm_service.LLMService.generate_outfit_recommendation", return_value=mock_recommendation) as mock_llm:
            query_response = self.client.post(
                "/api/v1/wardrobe/1/query",
                json=query_payload,
                headers=headers
            )
            self.assertEqual(query_response.status_code, 200)
            mock_llm.assert_called_once()

        query_data = query_response.json()
        self.assertEqual(query_data["query"], "What should I wear for a casual summer day?")
        self.assertEqual(query_data["recommendation"], mock_recommendation)
        self.assertEqual(len(query_data["matched_items"]), 1)
        self.assertEqual(query_data["matched_items"][0]["brand"], "BrandX")
        # Ensure public URL was resolved for the wardrobe image
        self.assertIn("/uploads/wardrobe/1/", query_data["matched_items"][0]["image_url"])
