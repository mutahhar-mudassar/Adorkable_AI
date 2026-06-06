"""
Adorkable AI Weather Rules Engine

Temperature-based fabric and layering recommendations with weather
suitability scoring for garments.
"""

from typing import Dict, Optional, List

from backend.database import GarmentItem
from backend.utils.weather_api import is_rainy_condition


# =============================================================================
# Fabric Weight Classification
# =============================================================================

def get_fabric_weight_needed(temp_c: float) -> str:
    """
    Determine the ideal fabric weight for given temperature.
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        Fabric weight category:
            - "heavy" for < 10°C
            - "medium-heavy" for 10-15°C
            - "medium" for 15-22°C
            - "light-medium" for 22-28°C
            - "light" for > 28°C
            
    Example:
        >>> get_fabric_weight_needed(5)
        'heavy'
        >>> get_fabric_weight_needed(25)
        'light-medium'
    """
    if temp_c < 10:
        return "heavy"
    elif temp_c < 15:
        return "medium-heavy"
    elif temp_c < 22:
        return "medium"
    elif temp_c < 28:
        return "light-medium"
    else:
        return "light"


# Fabric weight order for comparison
FABRIC_WEIGHT_ORDER = ["light", "light-medium", "medium", "medium-heavy", "heavy"]


def get_fabric_weight_level(weight: str) -> int:
    """
    Get numeric level for fabric weight.
    
    Args:
        weight: Fabric weight string
        
    Returns:
        Numeric level (0-4)
    """
    try:
        return FABRIC_WEIGHT_ORDER.index(weight)
    except ValueError:
        return 2  # Default to medium


def get_fabric_difference(weight1: str, weight2: str) -> int:
    """
    Calculate difference between two fabric weights.
    
    Args:
        weight1, weight2: Fabric weight strings
        
    Returns:
        Absolute difference in levels
    """
    return abs(get_fabric_weight_level(weight1) - get_fabric_weight_level(weight2))


# =============================================================================
# Weather Suitability Scoring
# =============================================================================

def weather_suitability_score(
    garment: GarmentItem,
    temp_c: float,
    condition: str,
    has_outerwear: bool = False
) -> float:
    """
    Calculate how suitable a garment is for current weather.
    
    Scoring logic:
        - Perfect fabric weight match: 1.0
        - Off by one level: 0.6
        - Off by two levels: 0.2
        - Rain + no outerwear: penalty -0.3
        - Rain + outerwear present: bonus +0.2
        - Score clamped to 0.0-1.0
    
    Args:
        garment: Garment item to evaluate
        temp_c: Current temperature in Celsius
        condition: Weather condition (e.g., "Clear", "Rain")
        has_outerwear: Whether outfit includes outerwear
        
    Returns:
        Suitability score (0.0 to 1.0)
        
    Example:
        >>> garment.fabric_weight = "medium"
        >>> weather_suitability_score(garment, 18, "Clear")
        1.0
    """
    # Get required fabric weight for temperature
    needed_weight = get_fabric_weight_needed(temp_c)
    garment_weight = garment.fabric_weight
    
    # Calculate base score from fabric match
    weight_diff = get_fabric_difference(needed_weight, garment_weight)
    
    if weight_diff == 0:
        base_score = 1.0
    elif weight_diff == 1:
        base_score = 0.6
    elif weight_diff == 2:
        base_score = 0.2
    else:
        base_score = 0.0
    
    # Adjust for rain conditions
    is_rain = is_rainy_condition(condition)
    
    if is_rain:
        # Check if this is an outerwear item
        if garment.category == "outerwear":
            base_score += 0.2  # Bonus for wearing outerwear in rain
        elif not has_outerwear:
            # Penalty for non-outerwear without outerwear layer
            base_score -= 0.3
    
    # Clamp to valid range
    return max(0.0, min(1.0, base_score))


def check_layering_needs(
    temp_c: float,
    humidity: int = 50
) -> Dict[str, any]:
    """
    Determine layering recommendations based on weather.
    
    Args:
        temp_c: Temperature in Celsius
        humidity: Humidity percentage
        
    Returns:
        Dictionary with layering advice
    """
    needs = {
        "needs_base_layer": False,
        "needs_mid_layer": False,
        "needs_outerwear": False,
        "min_layers": 1,
        "max_layers": 1,
        "recommended_fabric": get_fabric_weight_needed(temp_c),
        "thermal_underwear_recommended": False
    }
    
    if temp_c < 5:
        needs["needs_base_layer"] = True
        needs["needs_mid_layer"] = True
        needs["needs_outerwear"] = True
        needs["min_layers"] = 3
        needs["max_layers"] = 4
        needs["thermal_underwear_recommended"] = True
    elif temp_c < 10:
        needs["needs_mid_layer"] = True
        needs["needs_outerwear"] = True
        needs["min_layers"] = 2
        needs["max_layers"] = 3
    elif temp_c < 15:
        needs["needs_outerwear"] = True
        needs["min_layers"] = 2
        needs["max_layers"] = 2
    elif temp_c < 20:
        needs["min_layers"] = 1
        needs["max_layers"] = 2
    else:
        needs["min_layers"] = 1
        needs["max_layers"] = 1
    
    # High humidity makes it feel warmer
    if humidity > 70 and temp_c > 20:
        needs["recommended_fabric"] = "light"
    
    return needs


def must_include_outerwear(temp_c: float) -> bool:
    """
    Check if outerwear is required for temperature.
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        True if outerwear should be included
    """
    return temp_c < 15


def get_temperature_comfort_zone(temp_c: float) -> str:
    """
    Get comfort zone description for temperature.
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        Comfort zone description
    """
    if temp_c < 5:
        return "freezing"
    elif temp_c < 10:
        return "very_cold"
    elif temp_c < 15:
        return "cold"
    elif temp_c < 20:
        return "cool"
    elif temp_c < 25:
        return "mild"
    elif temp_c < 30:
        return "warm"
    else:
        return "hot"


# =============================================================================
# Weather Explanations
# =============================================================================

def get_weather_explanation(temp_c: float, condition: str) -> str:
    """
    Generate human-readable weather explanation for outfit recommendations.
    
    Args:
        temp_c: Temperature in Celsius
        condition: Weather condition
        
    Returns:
        Human-readable explanation string
        
    Example:
        >>> get_weather_explanation(12, "Cloudy")
        "It's 12°C and cloudy — a layered look with a light jacket is ideal."
    """
    zone = get_temperature_comfort_zone(temp_c)
    is_rain = is_rainy_condition(condition)
    
    # Base temperature descriptions
    temp_descriptions = {
        "freezing": f"It's {temp_c}°C and freezing",
        "very_cold": f"It's {temp_c}°C and very cold",
        "cold": f"It's {temp_c}°C and cold",
        "cool": f"It's {temp_c}°C and cool",
        "mild": f"It's a mild {temp_c}°C",
        "warm": f"It's a warm {temp_c}°C",
        "hot": f"It's {temp_c}°C and hot"
    }
    
    base_desc = temp_descriptions.get(zone, f"It's {temp_c}°C")
    
    # Add condition
    if condition.lower() not in ["clear", "sunny", "clouds", "cloudy"]:
        base_desc += f" with {condition.lower()}"
    
    # Add recommendation
    if is_rain:
        if zone in ["cold", "very_cold", "freezing"]:
            recommendation = " — bundle up with waterproof outerwear"
        else:
            recommendation = " — bring a rain jacket or umbrella"
    elif zone in ["freezing", "very_cold"]:
        recommendation = " — heavy layering with warm fabrics is essential"
    elif zone == "cold":
        recommendation = " — a layered look with warm pieces is ideal"
    elif zone == "cool":
        recommendation = " — a layered look with a light jacket is ideal"
    elif zone == "mild":
        recommendation = " — comfortable single layers or light layering works well"
    elif zone == "warm":
        recommendation = " — breathable, lightweight fabrics are best"
    else:  # hot
        recommendation = " — stick to minimal, breathable clothing"
    
    return base_desc + recommendation


def get_fabric_recommendations(temp_c: float) -> List[str]:
    """
    Get specific fabric recommendations for temperature.
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        List of recommended fabric types
    """
    if temp_c < 10:
        return ["wool", "tweed", "velvet", "corduroy", "heavy cotton", "fleece"]
    elif temp_c < 15:
        return ["cotton blend", "light wool", "denim", "corduroy"]
    elif temp_c < 22:
        return ["cotton", "linen blend", "light denim", "jersey"]
    elif temp_c < 28:
        return ["cotton voile", "light linen", "chiffon", "rayon", "jersey"]
    else:
        return ["silk", "cotton", "linen", "chiffon", "organza", "viscose"]


# =============================================================================
# Outfit Weather Scoring
# =============================================================================

def score_outfit_for_weather(
    garments: List[GarmentItem],
    temp_c: float,
    condition: str
) -> Dict:
    """
    Score a complete outfit for weather suitability.
    
    Args:
        garments: List of garments in the outfit
        temp_c: Temperature
        condition: Weather condition
        
    Returns:
        Dictionary with scoring results
    """
    has_outerwear = any(g.category == "outerwear" for g in garments)
    
    scores = []
    garment_scores = []
    
    for garment in garments:
        score = weather_suitability_score(garment, temp_c, condition, has_outerwear)
        scores.append(score)
        garment_scores.append({
            "garment_id": garment.id,
            "category": garment.category,
            "fabric_weight": garment.fabric_weight,
            "score": score
        })
    
    # Calculate overall score
    if scores:
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
    else:
        avg_score = 0.0
        min_score = 0.0
    
    # Check layering
    layering_needs = check_layering_needs(temp_c)
    actual_layers = len([g for g in garments if g.category not in ["shoes", "accessory"]])
    
    layering_ok = (
        layering_needs["min_layers"] <= actual_layers <= layering_needs["max_layers"]
    )
    
    return {
        "average_score": round(avg_score, 2),
        "min_score": round(min_score, 2),
        "garment_scores": garment_scores,
        "has_outerwear": has_outerwear,
        "layering_appropriate": layering_ok,
        "recommended_layers": f"{layering_needs['min_layers']}-{layering_needs['max_layers']}",
        "actual_layers": actual_layers,
        "weather_explanation": get_weather_explanation(temp_c, condition),
        "recommended_fabrics": get_fabric_recommendations(temp_c)
    }


# ✅ backend/engine/weather_rules.py generated — Adorkable AI
