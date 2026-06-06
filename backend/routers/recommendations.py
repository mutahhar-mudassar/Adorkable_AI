"""
Adorkable AI Recommendations Router

FastAPI routes for daily outfit recommendations.
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user
from backend.database import (
    get_db, User, GarmentItem, OutfitLog,
    get_user_profile, get_user_wardrobe
)
from backend.routers.helpers import select_hijab_for_female, garment_to_dict
from backend.utils.weather_api import get_current_weather
from backend.engine.stochastic_selector import weighted_random_select
from backend.engine.outfit_constraints import generate_wardrobe_outfit_candidates
from backend.services.starter_wardrobe import ensure_user_has_wardrobe, _load_catalog, _resolve_abs_path
from backend.engine.outfit_constraints import normalize_starter_gender, catalog_item_matches_user_gender
from backend.utils.image_utils import save_uploaded_image
import os


# =============================================================================
# Pydantic Schemas
# =============================================================================

class DailyRecommendRequest(BaseModel):
    """Request body for daily recommendation."""
    occasion: str = "Casual"
    style_pref: str = "Western"
    weather_override: Optional[float] = None
    reimagine_step: int = 0


class GarmentSimple(BaseModel):
    """Simplified garment for response."""
    id: int
    category: str
    dominant_color: str
    color_hex: str
    image_path: str


class OutfitResponse(BaseModel):
    """Outfit recommendation response."""
    score: float
    top: Optional[GarmentSimple]
    bottom: Optional[GarmentSimple]
    dress: Optional[GarmentSimple]
    outerwear: Optional[GarmentSimple]
    hijab: Optional[GarmentSimple]  # For female users, hijab is compulsory
    color_harmony: float
    skin_flattery: float
    body_shape_score: float
    weather_score: float
    occasion_score: float
    trending: bool
    trending_reason: str
    why_this_suits_you: str
    weather_explanation: str
    weather: dict


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


async def get_combined_wardrobe_with_starter(
    db: AsyncSession,
    user: User,
    min_items: int = 3
) -> List[GarmentItem]:
    """
    Get user's wardrobe. If less than min_items, add starter wardrobe items.
    
    Args:
        db: Database session
        user: Current user
        min_items: Minimum items needed before adding starter wardrobe
        
    Returns:
        Combined list of personal + starter wardrobe items
    """
    # Get personal wardrobe
    personal_wardrobe = await get_user_wardrobe(db, user.id)
    
    # If personal wardrobe has enough items, return it
    if len(personal_wardrobe) >= min_items:
        return personal_wardrobe
    
    # Need to add starter items
    bucket = normalize_starter_gender(user.gender)
    catalog = _load_catalog()
    
    # Filter catalog by gender
    if bucket == "unisex":
        filtered_catalog = catalog
    else:
        filtered_catalog = [
            item for item in catalog
            if (item.get("target_gender") or "unisex").strip().lower() in ["unisex", bucket]
        ]
    
    # Create virtual GarmentItems from catalog (without saving to DB)
    starter_items = []
    for item in filtered_catalog[:10]:  # Limit to 10 starter items max
        garment = GarmentItem(
            id=-1,  # Negative ID indicates starter item
            user_id=user.id,
            image_path=_resolve_abs_path(item.get("image_path", "")),
            category=item.get("category", "top"),
            style=item.get("style", "casual"),
            dominant_color=item.get("dominant_color", "Unknown"),
            color_hex=item.get("color_hex", "#808080"),
            fabric_weight=item.get("fabric_weight", "medium"),
            occasion_tags=json.dumps(item.get("occasion_tags", ["Casual"])),
            gender_fit=(item.get("target_gender") or "unisex").strip().lower(),
            search_tags=json.dumps(item.get("search_tags", [])),
            wear_count=0,
        )
        starter_items.append(garment)
    
    # Combine personal + starter items
    return personal_wardrobe + starter_items


@router.post("/daily", response_model=OutfitResponse)
async def get_daily_recommendation(
    request: DailyRecommendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily outfit recommendation.
    
    Generates outfit based on:
    - Weather in user's city
    - User profile (skin tone, body shape)
    - Occasion and style preference
    - Stochastic selection for variety
    """
    # Get user profile
    profile = await get_user_profile(db, current_user.id)
    
    # Get combined wardrobe (personal + starter if personal < 3 items)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    
    if not wardrobe:
        raise HTTPException(status_code=400, detail="No garments in wardrobe")
    
    # Get weather
    if request.weather_override is not None:
        weather = {
            "temp_c": request.weather_override,
            "condition": "Clear",
            "humidity": 50
        }
    elif current_user.city:
        weather = await run_in_threadpool(get_current_weather, current_user.city)
    else:
        weather = {"temp_c": 22, "condition": "Clear", "humidity": 50}
    
    if "humidity" not in weather:
        weather = {**weather, "humidity": 50}

    candidates = generate_wardrobe_outfit_candidates(
        wardrobe,
        profile,
        weather,
        request.occasion,
        request.style_pref,
        min_score=30.0,
    )

    if not candidates:
        raise HTTPException(status_code=400, detail="Could not generate outfit recommendation")
    
    # Rank candidates high -> low for deterministic re-imagination.
    ranked = sorted(candidates, key=lambda x: x["score"], reverse=True)
    if request.reimagine_step > 0:
        idx = min(request.reimagine_step, len(ranked) - 1)
        selected = ranked[idx]
    else:
        # First generation keeps stochastic variety within strong candidates.
        selected = weighted_random_select(ranked)
    
    # Select hijab for female users (compulsory)
    hijab = select_hijab_for_female(current_user.gender, wardrobe)
    
    # Log outfit (including hijab_id if applicable)
    log = OutfitLog(
        user_id=current_user.id,
        top_id=selected.get("top", {}).id if selected.get("top") else None,
        bottom_id=selected.get("bottom", {}).id if selected.get("bottom") else None,
        dress_id=selected.get("dress", {}).id if selected.get("dress") else None,
        outerwear_id=selected.get("outerwear", {}).id if selected.get("outerwear") else None,
        occasion=request.occasion,
        score=selected["score"],
        trending_badge=selected["trending"],
        worn_date=date.today()
    )
    db.add(log)
    await db.commit()
    
    def _to_gs(g):
        d = garment_to_dict(g)
        if not d:
            return None
        return GarmentSimple(**d)

    return OutfitResponse(
        score=selected["score"],
        top=_to_gs(selected.get("top")),
        bottom=_to_gs(selected.get("bottom")),
        dress=_to_gs(selected.get("dress")),
        outerwear=_to_gs(selected.get("outerwear")),
        hijab=_to_gs(hijab) if hijab else None,
        color_harmony=selected["color_harmony"],
        skin_flattery=selected["skin_flattery"],
        body_shape_score=selected["body_shape_score"],
        weather_score=selected["weather_score"],
        occasion_score=selected["occasion_score"],
        trending=selected["trending"],
        trending_reason=selected["trending_reason"],
        why_this_suits_you=selected["why_this_suits_you"],
        weather_explanation=selected["weather_explanation"],
        weather=weather
    )


# ✅ backend/routers/recommendations.py generated — Adorkable AI
