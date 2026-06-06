"""
Adorkable AI Planner Router

FastAPI routes for weekly outfit planning.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user
from backend.database import get_db, User, GarmentItem, get_user_profile, get_user_wardrobe
from backend.engine.weekly_planner import (
    generate_weekly_plan, 
    generate_quick_plan,
    get_weekly_stats
)
from backend.services.starter_wardrobe import ensure_user_has_wardrobe, _load_catalog, _resolve_abs_path
from backend.engine.outfit_constraints import normalize_starter_gender
from backend.routers.helpers import select_hijab_for_female, garment_to_dict
import json


# =============================================================================
# Helper Functions
# =============================================================================

async def get_combined_wardrobe_with_starter(
    db: AsyncSession,
    user: User,
    min_items: int = 3
) -> List[GarmentItem]:
    """
    Get user's wardrobe. If less than min_items, add starter wardrobe items.
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

class WeeklyPlanRequest(BaseModel):
    """Request body for weekly plan."""
    occasions: List[str] = Field(
        ..., 
        min_length=7, 
        max_length=7,
        description="7 occasion strings (one per day)"
    )
    style_pref: str = "Western"


class DailyPlan(BaseModel):
    """Single day outfit plan."""
    date: str
    day_name: str
    occasion: str
    score: float
    trending: bool
    trending_reason: str
    why_this_suits_you: str
    weather_explanation: str
    weather: dict
    top: Optional[dict] = None
    bottom: Optional[dict] = None
    dress: Optional[dict] = None
    outerwear: Optional[dict] = None
    hijab: Optional[dict] = None  # Hijab for female users


class WeeklyPlanResponse(BaseModel):
    """Weekly plan response."""
    plan: List[DailyPlan]
    stats: dict


class WeeklyStats(BaseModel):
    """Weekly plan statistics."""
    average_score: float
    total_score: float
    trending_days: int
    unique_garments_used: int
    coverage_percentage: float


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/plan", tags=["Planner"])


@router.post("/weekly", response_model=WeeklyPlanResponse)
async def create_weekly_plan(
    request: WeeklyPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a 7-day outfit plan.
    
    Requires 7 occasion strings (one per day, starting from today).
    
    Example occasions:
    - Casual, Formal, Academic, Casual, Formal, Casual, Casual
    """
    # Validate occasions
    if len(request.occasions) != 7:
        raise HTTPException(
            status_code=400,
            detail="Must provide exactly 7 occasions (one per day)"
        )
    
    # Get user profile and wardrobe (combined with starter if needed)
    profile = await get_user_profile(db, current_user.id)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    
    if not wardrobe:
        raise HTTPException(status_code=400, detail="No garments in wardrobe")
    
    # Get city
    city = current_user.city or "London"
    
    # Generate plan with error handling
    try:
        plan = await run_in_threadpool(
            generate_weekly_plan,
            profile,
            wardrobe,
            city,
            request.occasions,
            request.style_pref
        )
    except ValueError as e:
        # Wardrobe validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")
    
    # Calculate stats
    stats = get_weekly_stats(plan)
    
    # Convert to response format
    daily_plans = []
    for day_idx, day in enumerate(plan):
        # Select hijab for female users (compulsory) - rotate by day_idx for variety
        hijab = select_hijab_for_female(current_user.gender, wardrobe, day_idx=day_idx, rotate=True)
        
        daily_plans.append(DailyPlan(
            date=day.get("date", ""),
            day_name=day.get("day_name", ""),
            occasion=day.get("occasion", ""),
            score=day.get("score", 0),
            trending=day.get("trending", False),
            trending_reason=day.get("trending_reason", ""),
            why_this_suits_you=day.get("why_this_suits_you", ""),
            weather_explanation=day.get("weather_explanation", ""),
            weather=day.get("weather", {}),
            top=garment_to_dict(day.get("top")),
            bottom=garment_to_dict(day.get("bottom")),
            dress=garment_to_dict(day.get("dress")),
            outerwear=garment_to_dict(day.get("outerwear")),
            hijab=garment_to_dict(hijab)
        ))
    
    return WeeklyPlanResponse(
        plan=daily_plans,
        stats=stats
    )


@router.get("/quick", response_model=WeeklyPlanResponse)
async def get_quick_plan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a quick 7-day plan with default occasions.
    
    Uses alternating casual/formal pattern.
    """
    # Get user profile and wardrobe (combined with starter if needed)
    profile = await get_user_profile(db, current_user.id)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    
    if not wardrobe:
        raise HTTPException(status_code=400, detail="No garments in wardrobe")
    
    # Get city and style preference
    city = current_user.city or "London"
    # Get style preference from request or default to Western
    # Note: UserProfile doesn't have style field, we use "Western" as default
    style_pref = "Western"
    
    # Generate quick plan with error handling
    try:
        plan = await run_in_threadpool(generate_quick_plan, wardrobe, profile, city, style_pref)
    except ValueError as e:
        # Wardrobe validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=f"Failed to generate plan: {str(e)}")
    
    # Calculate stats
    stats = get_weekly_stats(plan)
    
    # Convert to response format
    daily_plans = []
    for day_idx, day in enumerate(plan):
        # Select hijab for female users (compulsory) - rotate by day_idx for variety
        hijab = select_hijab_for_female(current_user.gender, wardrobe, day_idx=day_idx, rotate=True)
        
        daily_plans.append(DailyPlan(
            date=day.get("date", ""),
            day_name=day.get("day_name", ""),
            occasion=day.get("occasion", ""),
            score=day.get("score", 0),
            trending=day.get("trending", False),
            trending_reason=day.get("trending_reason", ""),
            why_this_suits_you=day.get("why_this_suits_you", ""),
            weather_explanation=day.get("weather_explanation", ""),
            weather=day.get("weather", {}),
            top=garment_to_dict(day.get("top")),
            bottom=garment_to_dict(day.get("bottom")),
            dress=garment_to_dict(day.get("dress")),
            outerwear=garment_to_dict(day.get("outerwear")),
            hijab=garment_to_dict(hijab)
        ))
    
    return WeeklyPlanResponse(
        plan=daily_plans,
        stats=stats
    )


# ✅ backend/routers/planner.py generated — Adorkable AI
