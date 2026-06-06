"""
Adorkable AI Master Outfit Scorer

Core intelligence engine that scores outfits based on color harmony,
skin tone flattery, body shape suitability, weather, and occasion matching.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from backend.config import (
    SCORING_WEIGHTS, BODY_SHAPE_RULES, SKIN_TONE_PALETTE_PATH,
    TRENDS_PATH, STYLE_PREFERENCES
)
from backend.database import GarmentItem, UserProfile
from backend.engine.color_theory import (
    color_harmony_score, is_flattering_for_skin, is_neutral_color_name
)
from backend.engine.weather_rules import (
    weather_suitability_score, check_layering_needs, get_weather_explanation
)


# =============================================================================
# Trend Checking
# =============================================================================

def get_current_season() -> str:
    """
    Determine current season based on month.
    
    Returns:
        Season string (spring_summer or autumn_winter)
    """
    month = datetime.now().month
    
    # Spring/Summer: March - August
    if 3 <= month <= 8:
        return "spring_summer"
    else:
        return "autumn_winter"


def load_trends(season: str) -> Dict:
    """
    Load trend data for a season.
    
    Args:
        season: Season string
        
    Returns:
        Trends dictionary
    """
    try:
        with open(TRENDS_PATH, 'r') as f:
            all_trends = json.load(f)
            return all_trends.get(f"2026_{season}", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def check_trending(
    outfit_colors: List[str],
    outfit_style: str,
    categories: List[str]
) -> Tuple[bool, str]:
    """
    Check if an outfit matches current trends.
    
    Args:
        outfit_colors: List of color names in outfit
        outfit_style: Style of outfit
        categories: List of garment categories
        
    Returns:
        Tuple of (is_trending, trending_reason)
    """
    season = get_current_season()
    trends = load_trends(season)
    
    if not trends:
        return False, ""
    
    trending_colors = [c.lower() for c in trends.get("colors", [])]
    trending_styles = [s.lower() for s in trends.get("styles", [])]
    eastern_trends = [t.lower() for t in trends.get("eastern_trends", [])]
    western_trends = [t.lower() for t in trends.get("western_trends", [])]
    
    matches = []
    
    # Check color matches
    color_matches = []
    for color in outfit_colors:
        for trend_color in trending_colors:
            if color.lower() in trend_color or trend_color in color.lower():
                color_matches.append(trend_color)
    
    if color_matches:
        matches.append(f"on-trend colors ({', '.join(set(color_matches[:2]))})")
    
    # Check style match
    if outfit_style.lower() in trending_styles:
        matches.append(f"{outfit_style} style trending")
    
    # Check category trends
    category_str = ' '.join(c.lower() for c in categories)
    
    if any(trend in category_str for trend in eastern_trends):
        matches.append("Eastern fashion trending")
    
    if any(trend in category_str for trend in western_trends):
        matches.append("Western silhouettes trending")
    
    if matches:
        return True, f"This outfit features {', '.join(matches)} this season! 🔥"
    
    return False, ""


# =============================================================================
# Body Shape Scoring
# =============================================================================

def score_body_shape_suitability(
    garments: List[GarmentItem],
    body_shape: str
) -> Tuple[float, str]:
    """
    Score how well garments suit the body shape.
    
    Args:
        garments: List of garments
        body_shape: Body shape label
        
    Returns:
        Tuple of (score, explanation)
    """
    if body_shape not in BODY_SHAPE_RULES:
        return 0.5, "Body shape profile not available"
    
    rules = BODY_SHAPE_RULES[body_shape]
    best_silhouettes = [s.lower() for s in rules.get("best_silhouettes", [])]
    avoid = [s.lower() for s in rules.get("avoid", [])]
    
    scores = []
    
    for garment in garments:
        garment_category = garment.category.lower()
        garment_style = garment.style.lower()
        
        score = 0.5  # Default neutral score
        
        # Check category against recommendations
        if any(s in garment_category for s in best_silhouettes):
            score = 1.0
        elif any(s in garment_style for s in best_silhouettes):
            score = 0.9
        elif any(s in garment_category for s in avoid):
            score = 0.2
        elif any(s in garment_style for s in avoid):
            score = 0.3
        
        scores.append(score)
    
    avg_score = sum(scores) / len(scores) if scores else 0.5
    
    # Generate explanation
    if avg_score > 0.8:
        explanation = f"Excellent choices for your {body_shape} shape!"
    elif avg_score > 0.6:
        explanation = f"Good match for your {body_shape} shape"
    else:
        explanation = f"Consider silhouettes better suited for {body_shape} shapes"
    
    return avg_score, explanation


# =============================================================================
# Skin Tone Scoring
# =============================================================================

def score_skin_tone_flattery(
    garments: List[GarmentItem],
    skin_tone: str,
    undertone: str
) -> Tuple[float, str]:
    """
    Score how well colors flatter the skin tone.
    
    Args:
        garments: List of garments
        skin_tone: Skin tone (Fair, Medium, Dark)
        undertone: Undertone (Warm, Cool, Neutral)
        
    Returns:
        Tuple of (score, explanation)
    """
    scores = []
    flattering_colors = []
    
    for garment in garments:
        score = is_flattering_for_skin(
            garment.dominant_color,
            skin_tone,
            undertone
        )
        scores.append(score)
        
        if score >= 0.9:
            flattering_colors.append(garment.dominant_color)
    
    avg_score = sum(scores) / len(scores) if scores else 0.5
    
    # Generate explanation
    if flattering_colors:
        color_str = ', '.join(set(flattering_colors[:2]))
        explanation = f"{color_str} beautifully complements your {skin_tone}-{undertone} skin"
    elif avg_score > 0.7:
        explanation = f"These colors work well with your {skin_tone}-{undertone} complexion"
    else:
        explanation = f"Consider colors that better suit {skin_tone}-{undertone} skin tones"
    
    return avg_score, explanation


# =============================================================================
# Occasion Scoring
# =============================================================================

def score_occasion_match(
    garments: List[GarmentItem],
    occasion: str
) -> Tuple[float, str]:
    """
    Score how well outfit matches the occasion.
    
    Args:
        garments: List of garments
        occasion: Occasion (Casual, Formal, Academic)
        
    Returns:
        Tuple of (score, explanation)
    """
    occasion_lower = occasion.lower()
    
    scores = []
    mismatches = []
    
    for garment in garments:
        tags = garment.get_occasion_tags_list()
        tags_lower = [t.lower() for t in tags]
        style_lower = garment.style.lower()
        
        # Check if garment matches occasion
        if occasion_lower in tags_lower:
            scores.append(1.0)
        elif occasion_lower in style_lower:
            scores.append(0.9)
        elif "casual" in occasion_lower and ("casual" in style_lower or "casual" in tags_lower):
            scores.append(0.8)
        elif "formal" in occasion_lower and ("formal" in style_lower or "formal" in tags_lower):
            scores.append(0.8)
        elif "academic" in occasion_lower and ("academic" in style_lower or "academic" in tags_lower):
            scores.append(0.8)
        else:
            scores.append(0.3)
            mismatches.append(garment.category)
    
    avg_score = sum(scores) / len(scores) if scores else 0.5
    
    # Generate explanation
    if avg_score >= 0.8:
        explanation = f"Perfect for {occasion} occasions"
    elif avg_score >= 0.5:
        explanation = f"Suitable for {occasion} occasions"
    else:
        explanation = f"Some pieces may not be ideal for {occasion} settings"
    
    return avg_score, explanation


# =============================================================================
# Style Preference Scoring
# =============================================================================

def score_style_preference(
    garments: List[GarmentItem],
    style_pref: str
) -> Tuple[float, str]:
    """
    Score how well outfit matches style preference.
    
    Args:
        garments: List of garments
        style_pref: Style preference (Eastern or Western)
        
    Returns:
        Tuple of (score, penalty_applied)
    """
    if not style_pref or style_pref not in STYLE_PREFERENCES:
        return 1.0, False
    
    pref_lower = style_pref.lower()
    
    eastern_categories = ["ethnic_top", "ethnic_bottom"]
    western_categories = ["top", "bottom", "dress", "outerwear"]
    
    scores = []
    
    for garment in garments:
        cat = garment.category.lower()
        style = garment.style.lower()
        
        if pref_lower == "eastern":
            if cat in eastern_categories or "ethnic" in style:
                scores.append(1.0)
            elif cat in western_categories and "western" not in style:
                scores.append(0.6)  # Can mix but not ideal
            else:
                scores.append(0.4)
        else:  # Western preference
            if cat in western_categories and "ethnic" not in style:
                scores.append(1.0)
            elif cat in eastern_categories:
                scores.append(0.5)  # Eastern pieces with Western pref
            else:
                scores.append(0.7)
    
    avg_score = sum(scores) / len(scores) if scores else 0.5
    
    # Apply penalty if significantly mismatched
    penalty_applied = avg_score < 0.5
    
    return avg_score, penalty_applied


# =============================================================================
# Color Harmony Scoring
# =============================================================================

def score_color_harmony(
    garments: List[GarmentItem]
) -> Tuple[float, str]:
    """
    Score color harmony of outfit.
    
    Args:
        garments: List of garments
        
    Returns:
        Tuple of (score, explanation)
    """
    if len(garments) < 2:
        return 0.8, "Single color outfit - classic and clean"
    
    harmony_scores = []
    
    # Compare each garment with every other garment
    for i, g1 in enumerate(garments):
        for g2 in garments[i+1:]:
            score = color_harmony_score(
                g1.color_hex,
                g2.color_hex,
                g1.dominant_color,
                g2.dominant_color
            )
            harmony_scores.append(score)
    
    avg_harmony = sum(harmony_scores) / len(harmony_scores) if harmony_scores else 0.5
    
    # Generate explanation
    if avg_harmony >= 0.9:
        explanation = "Beautifully complementary colors"
    elif avg_harmony >= 0.75:
        explanation = f"Harmonious {get_harmony_type(garments)} color palette"
    elif avg_harmony >= 0.5:
        explanation = "Pleasant color combination"
    else:
        explanation = "Consider more harmonious color pairing"
    
    return avg_harmony, explanation


def get_harmony_type(garments: List[GarmentItem]) -> str:
    """Get the type of color harmony in the outfit."""
    from backend.engine.color_theory import (
        is_complementary, is_analogous, is_monochromatic
    )
    
    if len(garments) < 2:
        return "monochromatic"
    
    g1, g2 = garments[0], garments[1]
    
    if is_complementary(g1.color_hex, g2.color_hex):
        return "complementary"
    elif is_analogous(g1.color_hex, g2.color_hex):
        return "analogous"
    elif is_monochromatic(g1.color_hex, g2.color_hex):
        return "monochromatic"
    
    return "coordinated"


# =============================================================================
# Master Scoring Function
# =============================================================================

def score_outfit(
    garments: List[GarmentItem],
    user_profile: Optional[UserProfile],
    weather: Dict,
    occasion: str,
    style_pref: str
) -> Dict:
    """
    Calculate comprehensive outfit score.
    
    Scoring breakdown (100 base + 5 bonus = 105 max):
        - Color Harmony: 30 points
        - Skin Tone Flattery: 20 points
        - Body Shape Suitability: 20 points
        - Weather Suitability: 20 points
        - Occasion Match: 10 points
        - Trending Bonus: 5 points
    
    Args:
        garments: List of garments in outfit
        user_profile: User profile with skin tone and body shape
        weather: Weather dict with temp_c and condition
        occasion: Occasion label
        style_pref: Style preference (Eastern/Western)
        
    Returns:
        Complete scoring result dictionary
    """
    weights = SCORING_WEIGHTS
    
    # Color Harmony Score (30 pts)
    color_score, color_explanation = score_color_harmony(garments)
    color_weighted = color_score * weights["color_harmony"]
    
    # Skin Tone Flattery (20 pts)
    if user_profile and user_profile.skin_tone:
        skin_score, skin_explanation = score_skin_tone_flattery(
            garments,
            user_profile.skin_tone,
            user_profile.skin_undertone or "Neutral"
        )
    else:
        skin_score, skin_explanation = 0.5, "Skin tone profile not set"
    skin_weighted = skin_score * weights["skin_flattery"]
    
    # Body Shape Suitability (20 pts)
    if user_profile and user_profile.body_shape:
        body_score, body_explanation = score_body_shape_suitability(
            garments,
            user_profile.body_shape
        )
    else:
        body_score, body_explanation = 0.5, "Body shape profile not set"
    body_weighted = body_score * weights["body_shape"]
    
    # Weather Suitability (20 pts)
    temp_c = weather.get("temp_c", 22)
    condition = weather.get("condition", "Clear")
    
    weather_scores = [
        weather_suitability_score(g, temp_c, condition) for g in garments
    ]
    weather_score = sum(weather_scores) / len(weather_scores) if weather_scores else 0.5
    weather_weighted = weather_score * weights["weather"]
    
    # Occasion Match (10 pts)
    occasion_score, occasion_explanation = score_occasion_match(garments, occasion)
    occasion_weighted = occasion_score * weights["occasion"]
    
    # Calculate base score
    base_score = (
        color_weighted + skin_weighted + body_weighted + 
        weather_weighted + occasion_weighted
    )
    
    # Style Preference Check
    style_score, style_penalty = score_style_preference(garments, style_pref)
    if style_penalty:
        base_score -= 10  # Penalty for style mismatch
    
    # Trending Check
    colors = [g.dominant_color for g in garments]
    style = garments[0].style if garments else "casual"
    categories = [g.category for g in garments]
    
    is_trending, trending_reason = check_trending(colors, style, categories)
    
    # Add trending bonus
    final_score = base_score
    if is_trending:
        final_score += weights["trending_bonus"]
    
    # Clamp to valid range
    final_score = max(0, min(105, final_score))
    
    # Generate comprehensive explanation
    explanation = generate_why_explanation(
        garments, color_explanation, skin_explanation,
        body_explanation, temp_c, is_trending
    )
    
    # Determine top/bottom/dress/outerwear
    top = next((g for g in garments if g.category in ["top", "ethnic_top"]), None)
    bottom = next((g for g in garments if g.category in ["bottom", "ethnic_bottom"]), None)
    dress = next((g for g in garments if g.category == "dress"), None)
    outerwear = next((g for g in garments if g.category == "outerwear"), None)
    
    return {
        "score": round(final_score, 1),
        "top": top,
        "bottom": bottom,
        "dress": dress,
        "outerwear": outerwear,
        "color_harmony": round(color_score, 2),
        "skin_flattery": round(skin_score, 2),
        "body_shape_score": round(body_score, 2),
        "weather_score": round(weather_score, 2),
        "occasion_score": round(occasion_score, 2),
        "trending": is_trending,
        "trending_reason": trending_reason,
        "why_this_suits_you": explanation,
        "weather_explanation": get_weather_explanation(temp_c, condition),
        "style_penalty_applied": style_penalty,
        "garments": garments
    }


def generate_why_explanation(
    garments: List[GarmentItem],
    color_explanation: str,
    skin_explanation: str,
    body_explanation: str,
    temp_c: float,
    trending: bool
) -> str:
    """
    Generate human-readable explanation of why outfit works.
    
    Args:
        garments: List of garments
        color_explanation: Color harmony explanation
        skin_explanation: Skin tone explanation
        body_explanation: Body shape explanation
        temp_c: Temperature
        trending: Whether outfit is trending
        
    Returns:
        Formatted explanation string
    """
    # Build garment description
    descriptions = []
    
    for g in garments:
        if g.category in ["top", "ethnic_top"]:
            descriptions.append(f"{g.dominant_color.lower()} {g.category.replace('_', ' ')}")
        elif g.category in ["bottom", "ethnic_bottom"]:
            descriptions.append(f"{g.dominant_color.lower()} {g.category.replace('_', ' ')}")
        elif g.category == "dress":
            descriptions.append(f"{g.dominant_color.lower()} dress")
        elif g.category == "outerwear":
            descriptions.append(f"{g.dominant_color.lower()} outer layer")
    
    garment_desc = " paired with ".join(descriptions) if descriptions else "This outfit"
    
    # Build explanation
    parts = [f"{garment_desc} suits you beautifully."]
    
    parts.append(color_explanation)
    
    if "profile not set" not in skin_explanation.lower():
        parts.append(skin_explanation)
    
    if "profile not set" not in body_explanation.lower():
        parts.append(body_explanation)
    
    # Add temperature context
    if temp_c < 15:
        parts.append("It's perfectly cozy for the chilly weather.")
    elif temp_c > 28:
        parts.append("The breathable fabrics are ideal for the heat.")
    
    if trending:
        parts.append("✨ These tones are trending this season!")
    
    return " ".join(parts)


# ✅ backend/engine/outfit_scorer.py generated — Adorkable AI
