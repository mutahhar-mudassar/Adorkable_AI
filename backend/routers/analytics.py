"""
Adorkable AI Analytics Router

FastAPI routes for wardrobe analytics and visualization data.
"""

from typing import List, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from backend.auth import get_current_user
from backend.database import (
    get_db, User, GarmentItem, OutfitLog,
    get_user_wardrobe
)
from backend.services.starter_wardrobe import _load_catalog, _resolve_abs_path
from backend.engine.outfit_constraints import normalize_starter_gender
import json


# =============================================================================
# Helper Functions
# =============================================================================

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

class ColorDistribution(BaseModel):
    """Color distribution for charts."""
    color: str
    count: int
    hex: str


class GarmentUsage(BaseModel):
    """Garment usage data."""
    garment_id: int
    category: str
    color: str
    wear_count: int
    last_worn: str


class OutfitHistoryItem(BaseModel):
    """Single outfit log entry."""
    id: int
    date: str
    occasion: str
    score: float
    trending_badge: bool


class AnalyticsResponse(BaseModel):
    """Complete analytics response."""
    wardrobe_colors: List[ColorDistribution]
    garment_usage: List[GarmentUsage]
    total_combinations: int
    outfit_history: List[OutfitHistoryItem]


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/wardrobe-colors", response_model=List[ColorDistribution])
async def get_wardrobe_colors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get color distribution data for donut chart.
    
    Returns count of garments by color for visualization.
    """
    # Get combined wardrobe (personal + starter if personal < 3 items)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    
    # Count by color
    color_counts = {}
    color_hexes = {}
    
    for g in wardrobe:
        color = g.dominant_color
        color_counts[color] = color_counts.get(color, 0) + 1
        color_hexes[color] = g.color_hex
    
    result = [
        ColorDistribution(
            color=color,
            count=count,
            hex=color_hexes.get(color, "#808080")
        )
        for color, count in color_counts.items()
    ]
    
    # Sort by count descending
    result.sort(key=lambda x: x.count, reverse=True)
    
    return result


@router.get("/garment-usage", response_model=List[GarmentUsage])
async def get_garment_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get per-item wear count for heatmap visualization.
    
    Returns garment usage data sorted by wear count.
    """
    # Get combined wardrobe (personal + starter if personal < 3 items)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    
    result = [
        GarmentUsage(
            garment_id=g.id,
            category=g.category,
            color=g.dominant_color,
            wear_count=g.wear_count,
            last_worn=str(g.last_worn) if g.last_worn else "Never"
        )
        for g in wardrobe
    ]
    
    # Sort by wear count
    result.sort(key=lambda x: x.wear_count, reverse=True)
    
    return result


@router.get("/combinability")
async def get_combinability(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get total valid outfit combination count.
    
    Returns the theoretical number of valid outfit combinations
    from the current wardrobe.
    """
    # Get combined wardrobe (personal + starter if personal < 3 items)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    
    # Count by category (including traditional variants and hijabs)
    tops = len([g for g in wardrobe if g.category in ["top", "traditional_top"]])
    bottoms = len([g for g in wardrobe if g.category in ["bottom", "traditional_bottom"]])
    dresses = len([g for g in wardrobe if g.category == "dress"])
    outerwear = len([g for g in wardrobe if g.category == "outerwear"])
    shoes = len([g for g in wardrobe if g.category == "shoes"])
    accessories = len([g for g in wardrobe if g.category == "accessory"])
    hijabs = len([g for g in wardrobe if g.category == "hijab"])
    
    # Calculate combinations
    # (top + bottom combinations) + (dresses standalone) * (outerwear options)
    top_bottom_combos = tops * bottoms
    dress_combos = dresses
    
    # With outerwear layering
    if outerwear > 0:
        total = (top_bottom_combos + dress_combos) * (outerwear + 1)
    else:
        total = top_bottom_combos + dress_combos
    
    return {
        "total_combinations": total,
        "by_category": {
            "tops": tops,
            "bottoms": bottoms,
            "dresses": dresses,
            "outerwear": outerwear,
            "shoes": shoes,
            "accessories": accessories,
            "hijabs": hijabs
        }
    }


@router.get("/outfit-history", response_model=List[OutfitHistoryItem])
async def get_outfit_history(
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get last 30 outfit logs with scores.
    
    Returns outfit history for score trend visualization.
    """
    result = await db.execute(
        select(OutfitLog)
        .where(OutfitLog.user_id == current_user.id)
        .order_by(OutfitLog.created_at.desc())
        .limit(limit)
    )
    
    logs = result.scalars().all()
    
    return [
        OutfitHistoryItem(
            id=log.id,
            date=str(log.worn_date),
            occasion=log.occasion,
            score=log.score,
            trending_badge=log.trending_badge
        )
        for log in logs
    ]


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics for dashboard.
    
    Returns key metrics for the main dashboard.
    """
    # Get combined wardrobe (personal + starter if personal < 3 items)
    wardrobe = await get_combined_wardrobe_with_starter(db, current_user, min_items=3)
    
    # Basic counts
    total_items = len(wardrobe)
    
    if total_items == 0:
        return {
            "total_items": 0,
            "most_worn": None,
            "least_worn": None,
            "favorite_color": None,
            "last_outfit_score": None
        }
    
    # Most/least worn
    sorted_by_wear = sorted(wardrobe, key=lambda g: g.wear_count, reverse=True)
    most_worn = sorted_by_wear[0]
    least_worn = sorted_by_wear[-1]
    
    # Favorite color
    from collections import Counter
    colors = [g.dominant_color for g in wardrobe]
    favorite_color = Counter(colors).most_common(1)[0][0]
    
    # Last outfit score
    result = await db.execute(
        select(OutfitLog)
        .where(OutfitLog.user_id == current_user.id)
        .order_by(OutfitLog.created_at.desc())
        .limit(1)
    )
    last_log = result.scalar_one_or_none()
    last_score = last_log.score if last_log else None
    
    return {
        "total_items": total_items,
        "most_worn": {
            "id": most_worn.id,
            "category": most_worn.category,
            "wear_count": most_worn.wear_count
        },
        "least_worn": {
            "id": least_worn.id,
            "category": least_worn.category,
            "wear_count": least_worn.wear_count
        },
        "favorite_color": favorite_color,
        "last_outfit_score": last_score
    }


# ✅ backend/routers/analytics.py generated — Adorkable AI
