"""
Adorkable AI Profile Router

FastAPI routes for managing user profile including skin tone and body shape.
"""

import json
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user
from backend.database import get_db, User, UserProfile, get_user_profile
from backend.utils.image_utils import save_profile_image, is_valid_image
from backend.ml.skin_tone import (
    analyze_skin_tone, 
    get_full_profile_recommendations
)
from backend.ml.body_shape import analyze_body_shape, get_full_body_profile
from backend.engine.color_theory import suggest_color_combinations
from backend.config import COLOR_MAPPING_PATH


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ProfileOut(BaseModel):
    """User profile output schema."""
    id: int
    skin_tone: Optional[str]
    skin_undertone: Optional[str]
    body_shape: Optional[str]
    selfie_path: Optional[str]
    body_photo_path: Optional[str]
    updated_at: str
    
    class Config:
        from_attributes = True


class ProfileWithRecommendations(BaseModel):
    """Profile with color recommendations."""
    profile: ProfileOut
    skin_recommendations: dict
    body_recommendations: dict


class AnalysisResponse(BaseModel):
    """Skin tone or body shape analysis response."""
    result: dict
    message: str


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/profile", tags=["Profile"])


def _load_color_name_to_hex_map() -> Dict[str, str]:
    """Load color name to hex mapping from color data file."""
    try:
        with open(COLOR_MAPPING_PATH, "r", encoding="utf-8") as f:
            mapping_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

    colors = mapping_data.get("colors", [])
    return {
        item.get("name", "").strip().lower(): item.get("hex", "").strip()
        for item in colors
        if item.get("name") and item.get("hex")
    }


@router.get("/", response_model=ProfileWithRecommendations)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's complete profile with recommendations.
    """
    profile = await get_user_profile(db, current_user.id)
    
    if not profile:
        # Create empty profile
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    
    # Get recommendations if profile is complete
    skin_recs = {}
    body_recs = {}
    
    if profile.skin_tone and profile.skin_undertone:
        skin_recs = get_full_profile_recommendations(
            profile.skin_tone,
            profile.skin_undertone
        )
    
    if profile.body_shape:
        body_recs = get_full_body_profile(profile.body_shape)
    
    return ProfileWithRecommendations(
        profile=ProfileOut(
            id=profile.id,
            skin_tone=profile.skin_tone,
            skin_undertone=profile.skin_undertone,
            body_shape=profile.body_shape,
            selfie_path=profile.selfie_path,
            body_photo_path=profile.body_photo_path,
            updated_at=str(profile.updated_at)
        ),
        skin_recommendations=skin_recs,
        body_recommendations=body_recs
    )


@router.post("/selfie", response_model=AnalysisResponse)
async def upload_selfie(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload selfie for skin tone analysis.
    
    Analyzes face and determines skin tone and undertone.
    """
    # Validate image
    contents = await file.read()
    
    if not is_valid_image(contents):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )
    
    # Save image
    image_path = save_profile_image(contents, current_user.id, "selfie")
    
    # Analyze skin tone
    analysis = analyze_skin_tone(image_path)
    
    # Update or create profile
    profile = await get_user_profile(db, current_user.id)
    
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    profile.selfie_path = image_path
    
    if not analysis.get("error"):
        profile.skin_tone = analysis.get("skin_tone")
        profile.skin_undertone = analysis.get("undertone")
    
    await db.commit()
    
    if analysis.get("error"):
        message = f"⚠️ {analysis['error']}"
    else:
        tone = analysis.get("skin_tone")
        undertone = analysis.get("undertone")
        message = f"✨ Your skin tone: {tone}-{undertone}"
    
    return AnalysisResponse(result=analysis, message=message)


@router.post("/body", response_model=AnalysisResponse)
async def upload_body_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload full-body photo for body shape analysis.
    
    Detects body shape from shoulder-to-hip ratio.
    """
    # Validate image
    contents = await file.read()
    
    if not is_valid_image(contents):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )
    
    # Save image
    image_path = save_profile_image(contents, current_user.id, "body")
    
    # Analyze body shape
    analysis = analyze_body_shape(image_path)
    
    # Update or create profile
    profile = await get_user_profile(db, current_user.id)
    
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    
    profile.body_photo_path = image_path
    
    if not analysis.get("error"):
        profile.body_shape = analysis.get("body_shape")
    
    await db.commit()
    
    if analysis.get("error"):
        message = f"⚠️ {analysis['error']}"
    else:
        shape = analysis.get("body_shape")
        message = f"⏳ Body shape detected: {shape}"
    
    return AnalysisResponse(result=analysis, message=message)


@router.get("/color-palette")
async def get_color_palette(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recommended color palette based on skin tone.
    """
    profile = await get_user_profile(db, current_user.id)
    
    if not profile or not profile.skin_tone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skin tone analysis not completed. Upload a selfie first."
        )
    
    recommendations = get_full_profile_recommendations(
        profile.skin_tone,
        profile.skin_undertone or "Neutral"
    )
    
    best_colors = recommendations.get("best_colors", [])
    colors_to_avoid = recommendations.get("colors_to_avoid", [])
    recommended_metals = recommendations.get("recommended_metals", [])

    # Build color harmony sets from the best colors that have known hex values.
    name_to_hex = _load_color_name_to_hex_map()
    harmony_sets = []
    for color_name in best_colors:
        base_hex = name_to_hex.get(color_name.lower())
        if not base_hex:
            continue

        harmony_sets.append({
            "base_color": color_name,
            "base_hex": base_hex,
            "suggestions": suggest_color_combinations(base_hex, combination_type="all")
        })

        # Keep payload compact while still giving useful options.
        if len(harmony_sets) >= 3:
            break

    return {
        "skin_tone": profile.skin_tone,
        "undertone": profile.skin_undertone,
        "best_colors": best_colors,
        "colors_to_avoid": colors_to_avoid,
        "recommended_metals": recommended_metals,
        "description": recommendations.get("description", ""),
        "color_harmony_sets": harmony_sets
    }


# ✅ backend/routers/profile.py generated — Adorkable AI
