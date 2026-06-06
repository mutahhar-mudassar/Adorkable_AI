"""
Adorkable AI Combo Router

FastAPI routes for smart combo generation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user
from backend.database import (
    get_db, User, GarmentItem, get_user_wardrobe, get_garment_by_id
)
from backend.routers.helpers import select_hijab_for_female, garment_to_dict
from backend.engine.combo_generator import generate_combos
from backend.utils.weather_api import get_current_weather
from backend.database import get_user_profile
from backend.services.starter_wardrobe import ensure_user_has_wardrobe, _load_catalog, _resolve_abs_path
from backend.engine.outfit_constraints import normalize_starter_gender
import json


async def get_combined_wardrobe_with_starter(
    db: AsyncSession,
    user: User,
    min_items: int = 3
) -> List[GarmentItem]:
    """Get user's wardrobe. If less than min_items, add starter wardrobe items."""
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
            style="traditional_eastern" if item.get("tradition") == "Eastern" else "western",
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


# =============================================================================
# Pydantic Schemas
# =============================================================================

class GarmentSimple(BaseModel):
    """Simplified garment for response."""
    id: int
    category: str
    dominant_color: str
    color_hex: str
    image_path: str


class ComboResponse(BaseModel):
    """Single combo response."""
    score: float
    top: Optional[GarmentSimple]
    bottom: Optional[GarmentSimple]
    dress: Optional[GarmentSimple]
    outerwear: Optional[GarmentSimple]
    hijab: Optional[GarmentSimple] = None  # Hijab for female users
    color_harmony: float
    skin_flattery: float
    body_shape_score: float
    weather_score: float
    occasion_score: float
    trending: bool
    trending_reason: str
    why_this_suits_you: str


class ComboListResponse(BaseModel):
    """List of combos response."""
    selected_item: GarmentSimple
    combos: List[ComboResponse]
    total_combos: int


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/combo", tags=["Combo Generator"])


@router.get("/{item_id}", response_model=ComboListResponse)
async def get_combos_for_item(
    item_id: int,
    occasion: str = Query("Casual", description="Occasion for outfit"),
    style_pref: str = Query("Western", description="Style preference"),
    weather_override: Optional[float] = Query(None, description="Override temperature"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get outfit combinations featuring a specific garment.
    
    Returns ranked list of outfits that include the selected item.
    """
    # Get selected garment
    selected = await get_garment_by_id(db, item_id)
    
    if not selected or selected.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Garment not found")
    
    # Get user's wardrobe (combined with starter if needed)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    other_garments = [g for g in wardrobe if g.id != item_id]
    
    if not other_garments:
        raise HTTPException(status_code=400, detail="Need more garments to create combos")
    
    # Get weather
    if weather_override is not None:
        weather = {
            "temp_c": weather_override,
            "condition": "Clear",
            "humidity": 50,
        }
    elif current_user.city:
        weather = await run_in_threadpool(get_current_weather, current_user.city)
        if "humidity" not in weather:
            weather = {**weather, "humidity": 50}
    else:
        weather = {"temp_c": 22, "condition": "Clear", "humidity": 50}
    
    # Get user profile
    profile = await get_user_profile(db, current_user.id)
    
    # Generate combos
    combos = generate_combos(
        selected,
        other_garments,
        profile,
        occasion,
        style_pref,
        weather
    )
    
    def garment_to_simple(g):
        d = garment_to_dict(g)
        if not d:
            return None
        return GarmentSimple(**d)
    
    combo_responses = []
    for combo in combos[:10]:  # Limit to top 10
        # Select hijab for female users (compulsory)
        hijab = select_hijab_for_female(current_user.gender, wardrobe)
        
        combo_responses.append(ComboResponse(
            score=combo["score"],
            top=garment_to_simple(combo.get("top")),
            bottom=garment_to_simple(combo.get("bottom")),
            dress=garment_to_simple(combo.get("dress")),
            outerwear=garment_to_simple(combo.get("outerwear")),
            hijab=garment_to_simple(hijab),
            color_harmony=combo["color_harmony"],
            skin_flattery=combo["skin_flattery"],
            body_shape_score=combo["body_shape_score"],
            weather_score=combo["weather_score"],
            occasion_score=combo["occasion_score"],
            trending=combo["trending"],
            trending_reason=combo["trending_reason"],
            why_this_suits_you=combo["why_this_suits_you"]
        ))
    
    return ComboListResponse(
        selected_item=garment_to_simple(selected),
        combos=combo_responses,
        total_combos=len(combos)
    )


# ✅ backend/routers/combo.py generated — Adorkable AI
