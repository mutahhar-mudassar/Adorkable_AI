"""
Adorkable AI Color Theory Engine

Comprehensive color harmony system with HSL conversions, complementary/
analogous/monochromatic rules, and flattery scoring.
"""

import colorsys
import math
from typing import Tuple, List, Optional, Dict

from backend.config import NEUTRAL_COLORS


# =============================================================================
# Color Conversions
# =============================================================================

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """
    Convert hex color string to RGB tuple.
    
    Args:
        hex_str: Hex color (e.g., "#FF5733" or "FF5733")
        
    Returns:
        RGB tuple (r, g, b) with values 0-255
    """
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:  # Short form like "F57"
        hex_str = ''.join([c*2 for c in hex_str])
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """
    Convert RGB values to hex color string.
    
    Args:
        r, g, b: RGB values 0-255
        
    Returns:
        Hex color string (e.g., "#FF5733")
    """
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_hsl(hex_str: str) -> Tuple[float, float, float]:
    """
    Convert hex color to HSL tuple.
    
    Args:
        hex_str: Hex color string
        
    Returns:
        HSL tuple (hue 0-360, saturation 0-100, lightness 0-100)
    """
    r, g, b = hex_to_rgb(hex_str)
    
    # Normalize to 0-1
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    
    # Convert to HSL using colorsys
    h_norm, l_norm, s_norm = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
    
    # Convert to degrees and percentages
    h = h_norm * 360
    s = s_norm * 100
    l = l_norm * 100
    
    return (h, s, l)


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """
    Convert HSL values to hex color.
    
    Args:
        h: Hue (0-360)
        s: Saturation (0-100)
        l: Lightness (0-100)
        
    Returns:
        Hex color string
    """
    # Normalize
    h_norm = h / 360.0
    s_norm = s / 100.0
    l_norm = l / 100.0
    
    # Convert to RGB
    r_norm, g_norm, b_norm = colorsys.hls_to_rgb(h_norm, l_norm, s_norm)
    
    # Convert to 0-255
    r = int(r_norm * 255)
    g = int(g_norm * 255)
    b = int(b_norm * 255)
    
    return rgb_to_hex(r, g, b)


# =============================================================================
# Color Harmony Rules
# =============================================================================

def get_complementary_colors(hex_str: str) -> List[str]:
    """
    Get complementary colors (opposite on color wheel, 180° apart).
    
    Args:
        hex_str: Base color hex
        
    Returns:
        List of complementary hex colors
    """
    h, s, l = hex_to_hsl(hex_str)
    
    # Complementary is 180° opposite
    comp_h = (h + 180) % 360
    
    # Return main complementary + slight variations
    colors = [
        hsl_to_hex(comp_h, s, l),           # Same saturation/lightness
        hsl_to_hex(comp_h, max(s - 10, 0), l),  # Less saturated
        hsl_to_hex(comp_h, s, max(l - 10, 10)), # Darker
    ]
    
    return colors


def get_analogous_colors(hex_str: str) -> List[str]:
    """
    Get analogous colors (adjacent on color wheel, ±30°, ±60°).
    
    Args:
        hex_str: Base color hex
        
    Returns:
        List of 4 analogous hex colors
    """
    h, s, l = hex_to_hsl(hex_str)
    
    colors = [
        hsl_to_hex((h + 30) % 360, s, l),   # +30°
        hsl_to_hex((h - 30) % 360, s, l),   # -30°
        hsl_to_hex((h + 60) % 360, s, l),   # +60°
        hsl_to_hex((h - 60) % 360, s, l),   # -60°
    ]
    
    return colors


def get_monochromatic_colors(hex_str: str) -> List[str]:
    """
    Get monochromatic colors (same hue, varying lightness).
    
    Args:
        hex_str: Base color hex
        
    Returns:
        List of 4 monochromatic hex colors
    """
    h, s, l = hex_to_hsl(hex_str)
    
    colors = [
        hsl_to_hex(h, s, min(l + 40, 95)),  # Much lighter
        hsl_to_hex(h, s, min(l + 20, 90)),  # Lighter
        hsl_to_hex(h, s, max(l - 20, 5)),   # Darker
        hsl_to_hex(h, s, max(l - 40, 5)),   # Much darker
    ]
    
    return colors


def get_triadic_colors(hex_str: str) -> List[str]:
    """
    Get triadic colors (120° apart on color wheel).
    
    Args:
        hex_str: Base color hex
        
    Returns:
        List of triadic hex colors
    """
    h, s, l = hex_to_hsl(hex_str)
    
    colors = [
        hsl_to_hex((h + 120) % 360, s, l),
        hsl_to_hex((h - 120) % 360, s, l),
    ]
    
    return colors


def get_split_complementary(hex_str: str) -> List[str]:
    """
    Get split complementary colors (complementary ±30°).
    
    Args:
        hex_str: Base color hex
        
    Returns:
        List of split complementary hex colors
    """
    h, s, l = hex_to_hsl(hex_str)
    
    comp_h = (h + 180) % 360
    
    colors = [
        hsl_to_hex((comp_h + 30) % 360, s, l),
        hsl_to_hex((comp_h - 30) % 360, s, l),
    ]
    
    return colors


# =============================================================================
# Color Harmony Scoring
# =============================================================================

def color_distance(color1_hex: str, color2_hex: str) -> float:
    """
    Calculate Euclidean distance between two colors in RGB space.
    
    Args:
        color1_hex, color2_hex: Hex color strings
        
    Returns:
        Euclidean distance (0-441.7 max)
    """
    r1, g1, b1 = hex_to_rgb(color1_hex)
    r2, g2, b2 = hex_to_rgb(color2_hex)
    
    return math.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2)


def hue_distance(color1_hex: str, color2_hex: str) -> float:
    """
    Calculate hue distance in degrees.
    
    Args:
        color1_hex, color2_hex: Hex color strings
        
    Returns:
        Minimum hue distance (0-180)
    """
    h1, _, _ = hex_to_hsl(color1_hex)
    h2, _, _ = hex_to_hsl(color2_hex)
    
    diff = abs(h1 - h2)
    return min(diff, 360 - diff)


def is_complementary(color1_hex: str, color2_hex: str, tolerance: float = 15) -> bool:
    """
    Check if two colors are complementary.
    
    Args:
        color1_hex, color2_hex: Hex color strings
        tolerance: Hue tolerance in degrees
        
    Returns:
        True if complementary (180° apart within tolerance)
    """
    h1, _, _ = hex_to_hsl(color1_hex)
    h2, _, _ = hex_to_hsl(color2_hex)
    
    diff = abs((h1 + 180) % 360 - h2)
    return diff <= tolerance or diff >= (360 - tolerance)


def is_analogous(color1_hex: str, color2_hex: str, tolerance: float = 30) -> bool:
    """
    Check if two colors are analogous.
    
    Args:
        color1_hex, color2_hex: Hex color strings
        tolerance: Hue tolerance in degrees
        
    Returns:
        True if analogous (within tolerance degrees)
    """
    return hue_distance(color1_hex, color2_hex) <= tolerance


def is_monochromatic(color1_hex: str, color2_hex: str, hue_tolerance: float = 10) -> bool:
    """
    Check if two colors are monochromatic (same hue).
    
    Args:
        color1_hex, color2_hex: Hex color strings
        hue_tolerance: Hue tolerance in degrees
        
    Returns:
        True if monochromatic
    """
    h1, _, _ = hex_to_hsl(color1_hex)
    h2, _, _ = hex_to_hsl(color2_hex)
    
    diff = abs(h1 - h2)
    hue_diff = min(diff, 360 - diff)
    
    return hue_diff <= hue_tolerance


def is_neutral_color_name(color_name: str) -> bool:
    """
    Check if a color name is neutral.
    
    Args:
        color_name: Fashion color name
        
    Returns:
        True if neutral color
    """
    return color_name.lower() in NEUTRAL_COLORS


def color_harmony_score(
    color1_hex: str,
    color2_hex: str,
    color1_name: Optional[str] = None,
    color2_name: Optional[str] = None
) -> float:
    """
    Calculate color harmony score between two colors.
    
    Scoring:
        - Complementary: 1.0 (highest harmony)
        - Analogous: 0.85
        - Monochromatic: 0.75
        - Neutral + Any: 0.90
        - Clashing (similar hue, different sat/light): 0.2
        - Default: 0.5
    
    Args:
        color1_hex: First color hex
        color2_hex: Second color hex
        color1_name: Optional first color name
        color2_name: Optional second color name
        
    Returns:
        Harmony score (0.0 to 1.0)
    """
    # Check for neutral colors
    is_neutral_1 = color1_name and is_neutral_color_name(color1_name)
    is_neutral_2 = color2_name and is_neutral_color_name(color2_name)
    
    if is_neutral_1 or is_neutral_2:
        # Neutral colors go well with almost anything
        return 0.90
    
    # Check for complementary
    if is_complementary(color1_hex, color2_hex):
        return 1.0
    
    # Check for analogous
    if is_analogous(color1_hex, color2_hex):
        return 0.85
    
    # Check for monochromatic
    if is_monochromatic(color1_hex, color2_hex):
        return 0.75
    
    # Check for clashing (similar hue, very different saturation/lightness)
    h1, s1, l1 = hex_to_hsl(color1_hex)
    h2, s2, l2 = hex_to_hsl(color2_hex)
    
    hue_diff = hue_distance(color1_hex, color2_hex)
    sat_diff = abs(s1 - s2)
    light_diff = abs(l1 - l2)
    
    # Clashing: similar hue but very different saturation or lightness
    if hue_diff < 30 and (sat_diff > 40 or light_diff > 30):
        return 0.2
    
    # Default moderate harmony
    return 0.5


def is_flattering_for_skin(
    color_name: str,
    skin_tone: str,
    undertone: str
) -> float:
    """
    Check if a color is flattering for a skin tone + undertone combination.
    
    Args:
        color_name: Fashion color name
        skin_tone: Skin tone (Fair, Medium, Dark)
        undertone: Undertone (Warm, Cool, Neutral)
        
    Returns:
        Flattery score (0.0 to 1.0)
    """
    import json
    from backend.config import SKIN_TONE_PALETTE_PATH
    
    try:
        with open(SKIN_TONE_PALETTE_PATH, 'r') as f:
            palettes = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Default scoring if palette not available
        if is_neutral_color_name(color_name):
            return 0.8
        return 0.6
    
    key = f"{skin_tone}_{undertone}"
    palette = palettes.get(key, {})
    
    best_colors = [c.lower() for c in palette.get("best_colors", [])]
    avoid_colors = [c.lower() for c in palette.get("avoid", [])]
    color_lower = color_name.lower()
    
    # Check exact match
    if color_lower in best_colors:
        return 1.0
    
    if color_lower in avoid_colors:
        return 0.0
    
    # Check partial matches
    for best in best_colors:
        if best in color_lower or color_lower in best:
            return 0.9
    
    for avoid in avoid_colors:
        if avoid in color_lower or color_lower in avoid:
            return 0.1
    
    # Neutral colors generally work for everyone
    if is_neutral_color_name(color_name):
        return 0.8
    
    # Default moderate flattery
    return 0.6


def suggest_color_combinations(
    base_color_hex: str,
    combination_type: str = "all"
) -> Dict[str, List[str]]:
    """
    Suggest color combinations for a base color.
    
    Args:
        base_color_hex: Base color hex
        combination_type: Type of combinations (all, complementary, analogous, monochromatic)
        
    Returns:
        Dictionary with color suggestions
    """
    suggestions = {}
    
    if combination_type in ["all", "complementary"]:
        suggestions["complementary"] = get_complementary_colors(base_color_hex)
    
    if combination_type in ["all", "analogous"]:
        suggestions["analogous"] = get_analogous_colors(base_color_hex)
    
    if combination_type in ["all", "monochromatic"]:
        suggestions["monochromatic"] = get_monochromatic_colors(base_color_hex)
    
    if combination_type in ["all", "triadic"]:
        suggestions["triadic"] = get_triadic_colors(base_color_hex)
    
    if combination_type in ["all", "split_complementary"]:
        suggestions["split_complementary"] = get_split_complementary(base_color_hex)
    
    return suggestions


# ✅ backend/engine/color_theory.py generated — Adorkable AI
