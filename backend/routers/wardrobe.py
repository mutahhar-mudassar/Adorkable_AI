"""
Adorkable AI Wardrobe Router

FastAPI routes for uploading, managing, and tracking garments.
"""

import os
import json
from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user
from backend.database import (
    get_db, User, GarmentItem,
    get_user_wardrobe, get_garment_by_id,
)
from backend.engine.outfit_constraints import (
    catalog_item_matches_user_gender,
    normalize_starter_gender,
)
from backend.utils.image_utils import (
    save_uploaded_image, delete_image_file, is_valid_image
)
from backend.ml.classifier import classify_garment
from backend.ml.color_extractor import extract_dominant_color
from backend.config import UPLOAD_DIR
# =============================================================================
# Pydantic Schemas
# =============================================================================

class GarmentUploadResponse(BaseModel):
    """Response schema for garment upload."""
    id: int
    category: str
    style: str
    dominant_color: str
    color_hex: str
    tradition: str
    fabric_weight: str
    message: str


class GarmentAnalysisResponse(BaseModel):
    """AI analysis response without persistence."""
    category: str
    style: str
    dominant_color: str
    color_hex: str
    tradition: str
    fabric_weight: str


class PreloadedGarmentOut(BaseModel):
    """Catalog item for starter wardrobe."""
    id: str
    title: str
    image_path: str
    category: str
    style: str
    tradition: str
    target_gender: str
    occasion_tags: List[str]
    season_tags: List[str]
    search_tags: List[str]
    suggested_fabric_weight: str
    dominant_color: str
    color_hex: str


class PreloadedImportItem(BaseModel):
    """Editable import payload for preloaded garments."""
    id: str
    category: str
    style: str
    dominant_color: str
    color_hex: str
    fabric_weight: str = "medium"
    occasion_tags: List[str] = []


class PreloadedImportRequest(BaseModel):
    """Batch import request for starter wardrobe."""
    items: List[PreloadedImportItem]


class PreloadedAnalyzeRequest(BaseModel):
    """Analyze selected preloaded IDs."""
    ids: List[str]


class GarmentOut(BaseModel):
    """Garment output schema."""
    id: int
    image_path: str
    category: str
    style: str
    dominant_color: str
    color_hex: str
    fabric_weight: str
    occasion_tags: List[str]
    gender_fit: Optional[str] = None
    tradition: str
    search_tags: List[str]
    wear_count: int
    last_worn: Optional[date]
    uploaded_at: date
    
    class Config:
        from_attributes = True


class WardrobeStats(BaseModel):
    """Wardrobe statistics schema."""
    total_items: int
    items_by_category: dict
    items_by_color: dict
    least_worn: List[dict]


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/wardrobe", tags=["Wardrobe"])

PRELOADED_CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "preloaded_wardrobe.json")


def _load_preloaded_catalog() -> List[dict]:
    """Load starter wardrobe catalog from JSON."""
    try:
        with open(PRELOADED_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("items", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _abs_path_from_catalog(image_path: str) -> str:
    """Convert catalog path to absolute local file path."""
    normalized = image_path.replace("/", os.sep)
    if os.path.isabs(normalized):
        return normalized
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), normalized)


def _filtered_catalog_for_user(current_user: User) -> List[dict]:
    """Return starter catalog filtered by user's profile gender."""
    catalog = _load_preloaded_catalog()
    bucket = normalize_starter_gender(current_user.gender)
    
    # For unisex/other, return all items
    if bucket == "unisex":
        return catalog
    
    # For female/male, show matching gender + unisex items
    filtered = []
    for item in catalog:
        target = (item.get("target_gender") or "unisex").strip().lower()
        if target == "unisex" or target == bucket:
            filtered.append(item)
    
    return filtered if filtered else catalog


def _infer_tradition_from_labels(category: str, style: str) -> str:
    cat = (category or "").lower()
    sty = (style or "").lower()
    return "Eastern" if ("traditional" in cat or "traditional" in sty) else "Western"


def _build_search_tags(
    category: str,
    style: str,
    color_name: str,
    occasion_tags: List[str],
) -> List[str]:
    tags = {
        (category or "").lower(),
        (style or "").lower(),
        _infer_tradition_from_labels(category, style).lower(),
        (color_name or "").lower(),
    }
    tags.update((x or "").strip().lower() for x in (occasion_tags or []))
    return sorted([t for t in tags if t])


@router.post("/analyze-image", response_model=GarmentAnalysisResponse)
async def analyze_uploaded_garment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze a garment image first without saving it.
    User can then correct AI output before final save.
    """
    _ = current_user  # auth guard
    contents = await file.read()

    if not is_valid_image(contents):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file")

    temp_dir = os.path.join(UPLOAD_DIR, "tmp_analysis")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"analysis_{current_user.id}_{file.filename or 'image.jpg'}")
    with open(temp_path, "wb") as f:
        f.write(contents)

    try:
        classification = classify_garment(temp_path)
        hex_color, color_name = extract_dominant_color(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return GarmentAnalysisResponse(
        category=classification.get("category", "top"),
        style=classification.get("style", "casual"),
        dominant_color=color_name,
        color_hex=hex_color,
        tradition=_infer_tradition_from_labels(
            classification.get("category", "top"),
            classification.get("style", "casual"),
        ),
        fabric_weight="medium",
    )


@router.get("/preloaded/catalog", response_model=List[PreloadedGarmentOut])
async def get_preloaded_catalog(current_user: User = Depends(get_current_user)):
    """Get starter wardrobe catalog that can be imported by the user."""
    catalog = _filtered_catalog_for_user(current_user)
    return [
        PreloadedGarmentOut(
            id=item.get("id", ""),
            title=item.get("title", "Starter Item"),
            image_path=item.get("image_path", ""),
            category=item.get("category", "top"),
            style="traditional_eastern" if item.get("tradition") == "Eastern" else "western",
            tradition=item.get("tradition", "Western"),
            target_gender=(item.get("target_gender") or "unisex").strip().lower(),
            occasion_tags=item.get("occasion_tags", []),
            season_tags=item.get("season_tags", []),
            search_tags=item.get("search_tags", []),
            suggested_fabric_weight=item.get("fabric_weight", "medium"),
            dominant_color=item.get("dominant_color", "Unknown"),
            color_hex=item.get("color_hex", "#808080"),
        )
        for item in catalog
        if item.get("id") and item.get("image_path")
    ]


@router.post("/preloaded/import")
async def import_preloaded_items(
    payload: PreloadedImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Import selected starter wardrobe items into current user's wardrobe."""
    catalog = {item.get("id"): item for item in _filtered_catalog_for_user(current_user)}
    imported_ids = []

    for item in payload.items:
        catalog_item = catalog.get(item.id)
        if not catalog_item:
            continue

        source_abs = _abs_path_from_catalog(catalog_item.get("image_path", ""))
        if not os.path.exists(source_abs):
            continue

        with open(source_abs, "rb") as f:
            file_bytes = f.read()

        saved_path = save_uploaded_image(
            file_bytes,
            current_user.id,
            filename=f"preloaded_{item.id}.png",
        )

        gender_fit = (
            (catalog_item.get("target_gender") or "unisex").strip().lower()
        )
        garment = GarmentItem(
            user_id=current_user.id,
            image_path=saved_path,
            category=item.category.lower(),
            style=item.style.lower().replace(" ", "_"),
            dominant_color=item.dominant_color,
            color_hex=item.color_hex,
            fabric_weight=item.fabric_weight,
            occasion_tags=json.dumps(item.occasion_tags or []),
            gender_fit=gender_fit,
        )
        db.add(garment)
        imported_ids.append(item.id)

    await db.commit()
    return {"imported_count": len(imported_ids), "imported_ids": imported_ids}


@router.post("/preloaded/analyze")
async def analyze_preloaded_items(
    payload: PreloadedAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    """Run AI analysis on selected starter items before importing."""
    catalog = {item.get("id"): item for item in _filtered_catalog_for_user(current_user)}
    analyzed = []

    for item_id in payload.ids:
        catalog_item = catalog.get(item_id)
        if not catalog_item:
            continue
        source_abs = _abs_path_from_catalog(catalog_item.get("image_path", ""))
        if not os.path.exists(source_abs):
            continue

        classification = classify_garment(source_abs)
        hex_color, color_name = extract_dominant_color(source_abs)
        # Derive style from tradition
        tradition = catalog_item.get("tradition", "Western")
        derived_style = "traditional_eastern" if tradition == "Eastern" else "western"
        analyzed.append({
            "id": item_id,
            "title": catalog_item.get("title"),
            "category": classification.get("category", "top"),
            "style": derived_style,
            "tradition": tradition,
            "dominant_color": color_name,
            "color_hex": hex_color,
            "fabric_weight": catalog_item.get("fabric_weight", "medium"),
            "search_tags": catalog_item.get("search_tags", []),
        })

    return {"items": analyzed}


@router.delete("/preloaded/clear")
async def clear_preloaded_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove all imported preloaded items for current user."""
    wardrobe = await get_user_wardrobe(db, current_user.id)
    to_delete = [g for g in wardrobe if os.path.basename(g.image_path).startswith("preloaded_")]

    for garment in to_delete:
        delete_image_file(garment.image_path)
        await db.delete(garment)

    await db.commit()
    return {"removed_count": len(to_delete)}


@router.post("/upload", response_model=GarmentUploadResponse)
async def upload_garment(
    file: UploadFile = File(...),
    category: str = Form(""),
    style: str = Form(""),
    dominant_color: str = Form(""),
    color_hex: str = Form(""),
    fabric_weight: str = Form("medium"),
    occasion_tags: str = Form("[]"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a new garment to the wardrobe.

    - **file**: Image file of the garment
    - **category**: Garment category (e.g., top, bottom, dress). If empty, AI will classify.
    - **style**: Garment style (e.g., casual, formal, ethnic). If empty, AI will classify.
    - **fabric_weight**: light/light-medium/medium/medium-heavy/heavy
    - **occasion_tags**: JSON array of occasions ["Casual", "Formal"]
    """
    # Validate image
    contents = await file.read()

    if not is_valid_image(contents):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )

    # Save image
    image_path = save_uploaded_image(
        contents,
        current_user.id,
        filename=file.filename
    )

    # Extract dominant color (AI default)
    try:
        detected_hex_color, detected_color_name = extract_dominant_color(image_path)
    except Exception:
        detected_hex_color, detected_color_name = "#808080", "Gray"

    # Use user-provided category/style if given, otherwise AI classifies
    if category and style:
        # User specified both, use their input
        final_category = category.lower()
        final_style = style.lower().replace(" ", "_")
    else:
        # AI classification as fallback
        classification = classify_garment(image_path)
        final_category = classification["category"]
        final_style = classification["style"]

    # Allow user-corrected color input from UI (hex wheel + name).
    final_color_hex = color_hex.strip() if color_hex and color_hex.strip().startswith("#") else detected_hex_color
    final_color_name = dominant_color.strip() if dominant_color and dominant_color.strip() else detected_color_name

    gender_fit = normalize_starter_gender(current_user.gender)

    # Create garment record
    garment = GarmentItem(
        user_id=current_user.id,
        image_path=image_path,
        category=final_category,
        style=final_style,
        dominant_color=final_color_name,
        color_hex=final_color_hex,
        fabric_weight=fabric_weight,
        occasion_tags=occasion_tags,
        gender_fit=gender_fit,
    )
    
    db.add(garment)
    await db.commit()
    await db.refresh(garment)

    return GarmentUploadResponse(
        id=garment.id,
        category=final_category,
        style=final_style,
        dominant_color=final_color_name,
        color_hex=final_color_hex,
        tradition=_infer_tradition_from_labels(final_category, final_style),
        fabric_weight=fabric_weight,
        message=f"Successfully uploaded: {final_category} ({final_style}) - Color: {final_color_name}"
    )


@router.get("/", response_model=List[GarmentOut])
async def get_wardrobe(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all garments in user's wardrobe.
    
    Optional filter by category.
    """
    wardrobe = await get_user_wardrobe(db, current_user.id)
    
    # Filter by category if provided
    if category:
        wardrobe = [g for g in wardrobe if g.category == category]
    
    return [
        GarmentOut(
            id=g.id,
            image_path=g.image_path,
            category=g.category,
            style=g.style,
            dominant_color=g.dominant_color,
            color_hex=g.color_hex,
            fabric_weight=g.fabric_weight,
            occasion_tags=g.get_occasion_tags_list(),
            gender_fit=g.gender_fit,
            tradition=_infer_tradition_from_labels(g.category, g.style),
            search_tags=_build_search_tags(
                g.category, g.style, g.dominant_color, g.get_occasion_tags_list()
            ),
            wear_count=g.wear_count,
            last_worn=g.last_worn,
            uploaded_at=g.uploaded_at.date()
        )
        for g in wardrobe
    ]


@router.delete("/{item_id}")
async def delete_garment(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a garment from the wardrobe.
    """
    garment = await get_garment_by_id(db, item_id)
    
    if not garment or garment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garment not found"
        )
    
    # Delete image file
    delete_image_file(garment.image_path)
    
    # Delete from database
    await db.delete(garment)
    await db.commit()
    
    return {"message": "Garment deleted successfully"}


@router.patch("/{item_id}/wear")
async def mark_as_worn(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a garment as worn today.
    
    Increments wear_count and sets last_worn to today.
    """
    garment = await get_garment_by_id(db, item_id)
    
    if not garment or garment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Garment not found"
        )
    
    garment.wear_count += 1
    garment.last_worn = date.today()
    
    await db.commit()
    
    return {
        "message": "Marked as worn today",
        "wear_count": garment.wear_count,
        "last_worn": garment.last_worn
    }


@router.get("/stats", response_model=WardrobeStats)
async def get_wardrobe_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get wardrobe statistics.
    
    Returns:
        - Total items count
        - Breakdown by category
        - Breakdown by color
        - Least worn items
    """
    wardrobe = await get_user_wardrobe(db, current_user.id)
    
    # Total items
    total_items = len(wardrobe)
    
    # Items by category
    by_category = {}
    for g in wardrobe:
        by_category[g.category] = by_category.get(g.category, 0) + 1
    
    # Items by color
    by_color = {}
    for g in wardrobe:
        color = g.dominant_color
        by_color[color] = by_color.get(color, 0) + 1
    
    # Least worn items
    sorted_by_wear = sorted(wardrobe, key=lambda g: (g.wear_count, g.uploaded_at))
    least_worn = [
        {
            "id": g.id,
            "category": g.category,
            "color": g.dominant_color,
            "wear_count": g.wear_count,
            "last_worn": g.last_worn
        }
        for g in sorted_by_wear[:3]
    ]
    
    return WardrobeStats(
        total_items=total_items,
        items_by_category=by_category,
        items_by_color=by_color,
        least_worn=least_worn
    )


# ✅ backend/routers/wardrobe.py generated — Adorkable AI
