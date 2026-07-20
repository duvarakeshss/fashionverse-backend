"""
Wardrobe API Router.
Handles wardrobe item uploads, semantic searches, and outfit queries.
"""
from typing import List
import numpy as np
from fastapi import APIRouter, Depends, File, UploadFile, Request, Form, Body, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.connection import get_db
from app.models.wardrobe import WardrobeItem
from app.schemas.wardrobe import (
    WardrobeItemResponse, WardrobeCategory,
    WardrobeQueryRequest, WardrobeQueryResponse, WardrobeQueryItemResult
)
from app.services.auth_service import get_current_user_id
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.storage_service import StorageBackend, get_storage_backend
from app.services.upload_service import UploadService
from app.utils.exceptions import FileTooLargeError

router = APIRouter(tags=["wardrobe"])

@router.post(
    "/wardrobe/{user_id}/upload", 
    status_code=201, 
    response_model=WardrobeItemResponse,
    summary="Upload Wardrobe Item",
    description="Validates, processes, classifies, and uploads a new wardrobe item."
)
async def upload_wardrobe_item(
    user_id: int,
    request: Request,
    file: UploadFile = File(...),
    brand: str | None = Form(None),
    notes: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's wardrobe")

    # Early check on Content-Length header
    content_length_header = request.headers.get("content-length")
    if content_length_header is not None:
        try:
            cl = int(content_length_header)
            if cl > settings.MAX_CONTENT_LENGTH:
                raise FileTooLargeError()
        except ValueError:
            pass

    # Read the full file bytes
    file_bytes = await file.read()
    
    service = UploadService(db, storage)
    item = await service.upload_wardrobe_item(
        user_id=user_id,
        file_bytes=file_bytes,
        original_filename=file.filename or "item.jpg",
        content_length=len(file_bytes),
        brand=brand,
        notes=notes
    )

    # Build response with resolved public URL
    response = WardrobeItemResponse.model_validate(item)
    response.image_url = storage.get_url(item.image_path)
    return response

@router.get(
    "/wardrobe/{user_id}/search",
    response_model=List[WardrobeItemResponse],
    summary="Semantic Wardrobe Search",
    description="Searches wardrobe items using semantic text similarity query."
)
async def search_wardrobe(
    user_id: int,
    q: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to search this wardrobe")

    query_embedding = EmbeddingService.get_embedding(q)

    stmt = select(WardrobeItem).where(WardrobeItem.user_id == user_id)
    result = await db.execute(stmt)
    all_items = result.scalars().all()

    top_items = _cosine_similarity_search(all_items, query_embedding, limit)

    # Build responses with resolved public URLs
    responses = []
    for item in top_items:
        r = WardrobeItemResponse.model_validate(item)
        r.image_url = storage.get_url(item.image_path)
        responses.append(r)
    return responses


def _cosine_similarity_search(
    all_items: list,
    query_embedding: list[float],
    limit: int
) -> list:
    """Compute cosine similarity in-memory and return top K items sorted by relevance."""
    q_vec = np.array(query_embedding, dtype=np.float32)
    q_norm = np.linalg.norm(q_vec)

    scored_items = []
    for item in all_items:
        if item.embedding is None:
            continue
        item_vec = np.array(item.embedding, dtype=np.float32)
        item_norm = np.linalg.norm(item_vec)
        if q_norm > 0 and item_norm > 0:
            similarity = float(np.dot(q_vec, item_vec) / (q_norm * item_norm))
        else:
            similarity = 0.0
        scored_items.append((similarity, item))

    scored_items.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored_items[:limit]]


@router.post(
    "/wardrobe/{user_id}/query",
    response_model=WardrobeQueryResponse,
    summary="AI Outfit Query",
    description=(
        "Performs semantic search over the user's wardrobe, then uses an OpenRouter LLM "
        "to generate a personalized outfit recommendation. "
        "Returns the AI response and matched items with public Azure Blob image URLs."
    )
)
async def query_outfit(
    user_id: int,
    body: WardrobeQueryRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
    current_user_id: int = Depends(get_current_user_id)
):
    if user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to query this wardrobe")

    # 1. Embed the user's query
    query_embedding = EmbeddingService.get_embedding(body.query)

    # 2. Load all wardrobe items and rank by cosine similarity
    stmt = select(WardrobeItem).where(WardrobeItem.user_id == user_id)
    result = await db.execute(stmt)
    all_items = result.scalars().all()

    top_items = _cosine_similarity_search(all_items, query_embedding, body.limit)

    # 3. Resolve public image URLs from Azure Blob Storage (or local)
    matched_results: list[WardrobeQueryItemResult] = []
    items_for_llm: list[dict] = []

    for item in top_items:
        public_url = storage.get_url(item.image_path)
        matched_results.append(
            WardrobeQueryItemResult(
                id=item.id,
                user_id=item.user_id,
                category=item.category,
                image_url=public_url,
                brand=item.brand,
                notes=item.notes,
                type=item.type,
                gender=item.gender,
                color=item.color,
                season=item.season,
                usage=item.usage,
                description=item.description,
                created_at=item.created_at,
            )
        )
        items_for_llm.append({
            "category": item.category,
            "type": item.type,
            "color": item.color,
            "gender": item.gender,
            "season": item.season,
            "usage": item.usage,
            "brand": item.brand,
            "description": item.description,
        })

    # 4. Call OpenRouter LLM to generate outfit recommendation
    try:
        recommendation = await LLMService.generate_outfit_recommendation(
            query=body.query,
            matched_items=items_for_llm,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return WardrobeQueryResponse(
        query=body.query,
        recommendation=recommendation,
        matched_items=matched_results,
    )
