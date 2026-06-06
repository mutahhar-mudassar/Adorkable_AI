"""
Adorkable AI Weekly Planner

Generates 7-day outfit plans considering weather, occasions, and
ensuring garment variety throughout the week.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional

from backend.database import GarmentItem, UserProfile
from backend.engine.stochastic_selector import weighted_random_select, select_with_exclusion
from backend.engine.outfit_constraints import generate_wardrobe_outfit_candidates
from backend.utils.weather_api import get_7day_forecast


def _boost_unused_bottoms(candidates: List[Dict], used_bottom_ids: List[int]) -> List[Dict]:
    """
    Boost scores of outfits that use bottoms not in used_bottom_ids.
    This encourages variety in bottom selection.
    """
    boosted = []
    for outfit in candidates:
        bottom = outfit.get("bottom")
        if bottom and bottom.id not in used_bottom_ids:
            # Boost score by 15 points for unused bottoms
            outfit_copy = dict(outfit)
            outfit_copy["score"] = outfit.get("score", 0) + 15.0
            outfit_copy["_boosted"] = True  # Mark for debugging
            boosted.append(outfit_copy)
        else:
            boosted.append(outfit)
    return boosted


def generate_weekly_plan(
    user_profile: Optional[UserProfile],
    wardrobe: List[GarmentItem],
    city: str,
    occasions: List[str],
    style_pref: str = "Western"
) -> List[Dict]:
    """
    Generate a 7-day outfit plan.
    
    Args:
        user_profile: User profile with preferences
        wardrobe: All available garments
        city: City for weather forecast
        occasions: List of 7 occasion strings (one per day)
        style_pref: Style preference (Eastern/Western)
        
    Returns:
        List of 7 outfit dictionaries
    """
    if len(occasions) != 7:
        raise ValueError("Must provide exactly 7 occasions (one per day)")
    
    # Get 7-day forecast (for display only, not for constraints)
    forecast = get_7day_forecast(city)
    
    # Track used garments with day info to allow reuse after cooldown
    # Cooldown: item can be reused after 2 days (Monday -> Wednesday)
    used_items_with_day = []  # List of (item_id, day_idx)
    
    weekly_plan = []
    today = datetime.now()
    
    # Count available items for error messages
    tops = [g for g in wardrobe if g.category in ["top", "traditional_top"]]
    bottoms = [g for g in wardrobe if g.category in ["bottom", "traditional_bottom"]]
    dresses = [g for g in wardrobe if g.category == "dress"]
    
    # Validate wardrobe has enough items
    if not tops and not dresses:
        raise ValueError(f"No tops or dresses in wardrobe. You have {len(wardrobe)} items total.")
    if not bottoms and not dresses:
        raise ValueError(f"No bottoms or dresses in wardrobe. You have {len(wardrobe)} items total.")
    
    for day_idx in range(7):
        date = today + timedelta(days=day_idx)
        day_name = date.strftime("%A")
        
        # Get weather for this day (for display only)
        if day_idx < len(forecast):
            weather = forecast[day_idx]
        else:
            weather = {"temp_c": 22, "condition": "Clear"}
        
        occasion = occasions[day_idx]
        
        # Generate outfit candidates for this day (no strict weather constraints)
        candidates = _generate_candidates_for_day(
            wardrobe,
            user_profile,
            weather,
            occasion,
            style_pref,
            strict_weather=False  # Allow all items regardless of weather
        )
        
        # Calculate items currently in cooldown (used within last 2 days)
        COOLDOWN_DAYS = 2  # Can reuse after 2 days
        recently_used = [
            item_id for item_id, used_day in used_items_with_day 
            if day_idx - used_day < COOLDOWN_DAYS
        ]
        
        # Track bottoms used specifically for variety
        bottoms_used_recently = [
            item_id for item_id, used_day in used_items_with_day 
            if day_idx - used_day < COOLDOWN_DAYS and any(
                g.category in ["bottom", "traditional_bottom"] 
                for g in wardrobe if g.id == item_id
            )
        ]
        
        # Boost candidates with unused bottoms to encourage variety
        candidates = _boost_unused_bottoms(candidates, bottoms_used_recently)
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # Combine all recently used items
        all_recently_used = list(set(recently_used + bottoms_used_recently))
        
        # Select outfit, avoiding recently used items (especially bottoms)
        selected = select_with_exclusion(candidates, all_recently_used)
        
        if not selected:
            # If no valid outfit found, try with just bottoms excluded
            selected = select_with_exclusion(candidates, bottoms_used_recently)
        
        if not selected:
            # If still no valid outfit, allow reuse but add randomization
            import random
            if candidates:
                # Pick from top 3 candidates randomly to ensure variety
                top_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:3]
                selected = random.choice(top_candidates) if top_candidates else weighted_random_select(candidates)
            else:
                selected = None
        
        if selected:
            # Mark garments as used with current day
            for key in ["top", "bottom", "dress", "outerwear"]:
                item = selected.get(key)
                if item:
                    used_items_with_day.append((item.id, day_idx))
            
            # Add date info to selected outfit
            selected["date"] = date.strftime("%Y-%m-%d")
            selected["day_name"] = day_name
            # Store actual weather forecast (not the 22C override used for scoring)
            selected["weather"] = weather
            selected["occasion"] = occasion
            
            # Update weather explanation to reflect actual forecast temperature
            actual_temp = weather.get("temp_c", 22)
            condition = weather.get("condition", "Clear")
            if actual_temp < 10:
                selected["weather_explanation"] = f"It's cold at {actual_temp}°C — layer up with warm pieces for {condition.lower()} conditions."
            elif actual_temp < 18:
                selected["weather_explanation"] = f"It's cool at {actual_temp}°C — light layering works well for {condition.lower()} weather."
            elif actual_temp < 25:
                selected["weather_explanation"] = f"It's pleasant at {actual_temp}°C — comfortable single layers or light layering for {condition.lower()} conditions."
            elif actual_temp < 32:
                selected["weather_explanation"] = f"It's warm at {actual_temp}°C — breathable, lightweight pieces ideal for {condition.lower()} weather."
            else:
                selected["weather_explanation"] = f"It's hot at {actual_temp}°C — minimal, airy garments best for {condition.lower()} conditions."
        else:
            # Fallback outfit with actual weather
            actual_temp = weather.get("temp_c", 22)
            condition = weather.get("condition", "Clear")
            if actual_temp < 10:
                weather_exp = f"It's cold at {actual_temp}°C — layer up with warm pieces for {condition.lower()} conditions."
            elif actual_temp < 18:
                weather_exp = f"It's cool at {actual_temp}°C — light layering works well for {condition.lower()} weather."
            elif actual_temp < 25:
                weather_exp = f"It's pleasant at {actual_temp}°C — comfortable single layers or light layering for {condition.lower()} conditions."
            elif actual_temp < 32:
                weather_exp = f"It's warm at {actual_temp}°C — breathable, lightweight pieces ideal for {condition.lower()} weather."
            else:
                weather_exp = f"It's hot at {actual_temp}°C — minimal, airy garments best for {condition.lower()} conditions."
            
            selected = {
                "score": 0,
                "top": None,
                "bottom": None,
                "dress": None,
                "outerwear": None,
                "garments": [],
                "why_this_suits_you": "No suitable outfit found in wardrobe",
                "weather_explanation": weather_exp,
                "date": date.strftime("%Y-%m-%d"),
                "day_name": day_name,
                "weather": weather,
                "occasion": occasion
            }
        
        weekly_plan.append(selected)
    
    return weekly_plan


def _generate_candidates_for_day(
    wardrobe: List[GarmentItem],
    user_profile: Optional[UserProfile],
    weather: Dict,
    occasion: str,
    style_pref: str,
    strict_weather: bool = True
) -> List[Dict]:
    """
    Generate outfit candidates for a specific day.
    
    Uses the same pairing, cold-weather, and formal rules as daily recommendations.
    """
    w = dict(weather)
    w.setdefault("humidity", 50)
    
    # If not strict weather, override temp to neutral value (22C = mild)
    if not strict_weather:
        w["temp_c"] = 22  # Neutral temperature allows all fabric weights
    
    candidates = generate_wardrobe_outfit_candidates(
        wardrobe,
        user_profile,
        w,
        occasion,
        style_pref,
        min_score=5.0,  # Very low threshold to get maximum variety
    )
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def generate_quick_plan(
    wardrobe: List[GarmentItem],
    user_profile: Optional[UserProfile],
    city: str,
    style_pref: str = "Western"
) -> List[Dict]:
    """
    Generate a quick 7-day plan with default occasions.
    
    Args:
        wardrobe: All garments
        user_profile: User profile
        city: City
        style_pref: Style preference (Eastern/Western)
        
    Returns:
        7-day plan with alternating casual/formal
    """
    # Default occasions pattern
    default_occasions = [
        "Casual",      # Monday
        "Academic",    # Tuesday
        "Casual",      # Wednesday
        "Formal",      # Thursday
        "Casual",      # Friday
        "Casual",      # Saturday
        "Formal"       # Sunday
    ]
    
    return generate_weekly_plan(
        user_profile,
        wardrobe,
        city,
        default_occasions,
        style_pref
    )


def get_weekly_stats(weekly_plan: List[Dict]) -> Dict:
    """
    Calculate statistics for a weekly plan.
    
    Args:
        weekly_plan: List of 7 daily outfits
        
    Returns:
        Statistics dictionary
    """
    total_score = sum(d.get("score", 0) for d in weekly_plan)
    avg_score = total_score / len(weekly_plan) if weekly_plan else 0
    
    trending_count = sum(1 for d in weekly_plan if d.get("trending"))
    
    # Count unique garments used
    used_ids = set()
    for day in weekly_plan:
        for key in ["top", "bottom", "dress", "outerwear"]:
            item = day.get(key)
            if item:
                used_ids.add(item.id)
    
    return {
        "average_score": round(avg_score, 1),
        "total_score": round(total_score, 1),
        "trending_days": trending_count,
        "unique_garments_used": len(used_ids),
        "coverage_percentage": round(len(used_ids) / max(1, len([d for d in weekly_plan if d.get("garments")])) * 100, 1)
    }


# ✅ backend/engine/weekly_planner.py generated — Adorkable AI
