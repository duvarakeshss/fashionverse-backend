"""
LLM Service — calls OpenRouter to generate AI outfit recommendations.

Model: openai/gpt-4.1 (OpenRouter-hosted GPT-class model)
Endpoint: https://openrouter.ai/api/v1/chat/completions
"""
import json
import asyncio
import urllib.request
import urllib.error
from typing import Any

from app.config import settings


class LLMService:
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "openai/gpt-4.1"  # Maps to gpt-oss-120b class on OpenRouter

    @classmethod
    def _build_context(cls, matched_items: list[dict[str, Any]]) -> str:
        """Formats matched wardrobe items into a readable context string for the LLM."""
        if not matched_items:
            return "No specific items found in the wardrobe matching the query."

        lines = []
        for i, item in enumerate(matched_items, 1):
            parts = [f"Item {i}:"]
            if item.get("category"):
                parts.append(f"  Category: {item['category']}")
            if item.get("type"):
                parts.append(f"  Type: {item['type']}")
            if item.get("color"):
                parts.append(f"  Color: {item['color']}")
            if item.get("gender"):
                parts.append(f"  Gender: {item['gender']}")
            if item.get("season"):
                parts.append(f"  Season: {item['season']}")
            if item.get("usage"):
                parts.append(f"  Usage: {item['usage']}")
            if item.get("brand"):
                parts.append(f"  Brand: {item['brand']}")
            if item.get("description"):
                parts.append(f"  Description: {item['description']}")
            lines.append("\n".join(parts))

        return "\n\n".join(lines)

    @classmethod
    def _call_openrouter_sync(cls, messages: list[dict], api_key: str) -> str:
        """
        Synchronous HTTP call to OpenRouter using stdlib urllib only.
        Returns the assistant reply text.
        """
        payload = json.dumps({
            "model": cls.MODEL,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
        }).encode("utf-8")

        req = urllib.request.Request(
            cls.OPENROUTER_URL,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://fashionverse.app",
                "X-Title": "FashionVerse",
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenRouter API error {e.code}: {error_body}"
            ) from e

    @classmethod
    async def generate_outfit_recommendation(
        cls,
        query: str,
        matched_items: list[dict[str, Any]],
    ) -> str:
        """
        Generates an outfit recommendation using the OpenRouter LLM.

        Args:
            query: The user's natural language query / style request.
            matched_items: Serialized WardrobeItem dicts returned from semantic search.

        Returns:
            AI-generated outfit recommendation string.

        Raises:
            RuntimeError: If OPENROUTER_API_KEY is missing or the request fails.
        """
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not configured. "
                "Set it in your .env file."
            )

        # Strip accidental leading underscore (copy-paste artefact from shell export)
        api_key = api_key.lstrip("_")

        wardrobe_context = cls._build_context(matched_items)

        system_prompt = (
            "You are FashionVerse AI, a professional personal fashion stylist. "
            "Give clear, concise, and stylish outfit recommendations based on the "
            "user's wardrobe items and their request. "
            "Be friendly and specific — mention the actual item types and colors from the context. "
            "Keep your response to 3–5 sentences."
        )

        user_message = (
            f"User Request: {query}\n\n"
            f"Matching Wardrobe Items:\n{wardrobe_context}\n\n"
            "Please provide a personalized outfit recommendation."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        # Run blocking urllib call in a thread pool to keep the event loop free
        loop = asyncio.get_event_loop()
        recommendation = await loop.run_in_executor(
            None, cls._call_openrouter_sync, messages, api_key
        )
        return recommendation
