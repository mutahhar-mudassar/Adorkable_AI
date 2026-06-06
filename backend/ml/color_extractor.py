"""
Adorkable AI Color Extraction Module

K-Means based dominant color extraction from garment images with
hex to fashion color name mapping.
"""

import json
import os
from typing import Tuple, List, Optional
import math

import cv2
import numpy as np
from sklearn.cluster import KMeans

from backend.config import COLOR_MAPPING_PATH
from backend.utils.image_utils import resolve_stored_image_path


# =============================================================================
# Color Mapping Loading
# =============================================================================

def load_color_mapping() -> List[dict]:
    """
    Load color mapping from JSON file.
    
    Returns:
        List of color dictionaries with name, hex, family, season
    """
    try:
        with open(COLOR_MAPPING_PATH, 'r') as f:
            data = json.load(f)
            return data.get("colors", [])
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback colors if file not found
        return [
            {"name": "Black", "hex": "#000000", "family": "neutral"},
            {"name": "White", "hex": "#FFFFFF", "family": "neutral"},
            {"name": "Navy Blue", "hex": "#000080", "family": "blue"},
            {"name": "Red", "hex": "#FF0000", "family": "red"},
            {"name": "Green", "hex": "#008000", "family": "green"},
        ]


# Cache color mapping
_COLOR_MAPPING: Optional[List[dict]] = None


def get_cached_color_mapping() -> List[dict]:
    """Get cached color mapping, loading if necessary."""
    global _COLOR_MAPPING
    if _COLOR_MAPPING is None:
        _COLOR_MAPPING = load_color_mapping()
    return _COLOR_MAPPING


# =============================================================================
# Hex / RGB Conversions
# =============================================================================

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """
    Convert hex color string to RGB tuple.
    
    Args:
        hex_str: Hex color (e.g., "#FF5733" or "FF5733")
        
    Returns:
        RGB tuple (r, g, b)
    """
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """
    Convert RGB tuple to hex color string.
    
    Args:
        rgb: RGB tuple (r, g, b)
        
    Returns:
        Hex color string (e.g., "#FF5733")
    """
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert RGB to HSL color space.
    
    Args:
        r, g, b: RGB values (0-255)
        
    Returns:
        HSL tuple (hue 0-360, saturation 0-100, lightness 0-100)
    """
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    
    max_val = max(r_norm, g_norm, b_norm)
    min_val = min(r_norm, g_norm, b_norm)
    diff = max_val - min_val
    
    # Calculate lightness
    l = (max_val + min_val) / 2.0
    
    # Calculate saturation
    if diff == 0:
        s = 0
    else:
        s = diff / (2 - max_val - min_val) if l > 0.5 else diff / (max_val + min_val)
    
    # Calculate hue
    if diff == 0:
        h = 0
    elif max_val == r_norm:
        h = (60 * ((g_norm - b_norm) / diff) + 360) % 360
    elif max_val == g_norm:
        h = (60 * ((b_norm - r_norm) / diff) + 120) % 360
    else:
        h = (60 * ((r_norm - g_norm) / diff) + 240) % 360
    
    return (h, s * 100, l * 100)


def color_distance_rgb(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """
    Calculate Euclidean distance between two RGB colors.
    
    Args:
        rgb1, rgb2: RGB tuples
        
    Returns:
        Euclidean distance
    """
    return math.sqrt(
        (rgb1[0] - rgb2[0]) ** 2 +
        (rgb1[1] - rgb2[1]) ** 2 +
        (rgb1[2] - rgb2[2]) ** 2
    )


# =============================================================================
# Color Name Resolution
# =============================================================================

def hex_to_color_name(hex_str: str) -> str:
    """
    Find the closest fashion color name for a given hex color.
    
    Uses Euclidean distance in RGB space to find the nearest color from
    the color mapping database.
    
    Args:
        hex_str: Hex color string (e.g., "#A0522D")
        
    Returns:
        Fashion color name (e.g., "Sage Green", "Navy Blue")
    """
    target_rgb = hex_to_rgb(hex_str)
    color_mapping = get_cached_color_mapping()
    
    closest_color = None
    min_distance = float('inf')
    
    for color in color_mapping:
        try:
            color_rgb = hex_to_rgb(color["hex"])
            distance = color_distance_rgb(target_rgb, color_rgb)
            
            if distance < min_distance:
                min_distance = distance
                closest_color = color["name"]
        except (KeyError, ValueError):
            continue
    
    return closest_color if closest_color else "Unknown"


def get_color_family(color_name: str) -> str:
    """
    Get the color family for a given color name.
    
    Args:
        color_name: Fashion color name
        
    Returns:
        Color family (e.g., "red", "blue", "neutral")
    """
    color_mapping = get_cached_color_mapping()
    
    for color in color_mapping:
        if color["name"].lower() == color_name.lower():
            return color.get("family", "unknown")
    
    return "unknown"


# =============================================================================
# Dominant Color Extraction
# =============================================================================

def extract_dominant_color(image_path: str, n_clusters: int = 5) -> Tuple[str, str]:
    """
    Extract the dominant color from a garment image using K-Means clustering.
    
    Process:
        1. Load image
        2. Resize to optimize processing speed (if large)
        3. Reshape to pixel array
        4. Apply K-Means clustering
        5. Find largest cluster as dominant color
        6. Convert to hex and find fashion color name
    
    Args:
        image_path: Path to the image file
        n_clusters: Number of clusters for K-Means (default 5)
        
    Returns:
        Tuple of (hex_color, color_name)
        
    Example:
        >>> hex_color, color_name = extract_dominant_color("shirt.jpg")
        >>> print(f"Dominant color: {color_name} ({hex_color})")
        Dominant color: Navy Blue (#000080)
    """
    # Load image
    img = cv2.imread(resolve_stored_image_path(image_path))
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    # OPTIMIZATION: Resize large images to speed up K-Means (max 300x300)
    max_size = 300
    h, w = img.shape[:2]
    if h > max_size or w > max_size:
        scale = max_size / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Reshape to (N, 3) array of pixels
    pixels = img_rgb.reshape((-1, 3))
    pixels = np.float32(pixels)
    
    # Filter out very dark (shadows) and very bright (highlights) pixels
    # Keep pixels with reasonable brightness
    brightness = np.mean(pixels, axis=1)
    mask = (brightness > 30) & (brightness < 240)
    filtered_pixels = pixels[mask]
    
    # If too few pixels after filtering, use all
    if len(filtered_pixels) < 100:
        filtered_pixels = pixels
    
    # Apply K-Means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(filtered_pixels)
    
    # Find the largest cluster (dominant color)
    labels = kmeans.labels_
    counts = np.bincount(labels)
    dominant_cluster_idx = np.argmax(counts)
    
    # Get dominant color centroid
    dominant_color = kmeans.cluster_centers_[dominant_cluster_idx]
    dominant_rgb = tuple(map(int, dominant_color))
    
    # Convert to hex
    hex_color = rgb_to_hex(dominant_rgb)
    
    # Get color name
    color_name = hex_to_color_name(hex_color)
    
    return hex_color, color_name


def extract_top_colors(image_path: str, n_colors: int = 3) -> List[Tuple[str, str, float]]:
    """
    Extract top N dominant colors from an image with their proportions.
    
    Args:
        image_path: Path to the image
        n_colors: Number of colors to extract (default 3)
        
    Returns:
        List of (hex_color, color_name, proportion) tuples
    """
    # Load image
    img = cv2.imread(resolve_stored_image_path(image_path))
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    # Convert to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pixels = img_rgb.reshape((-1, 3))
    pixels = np.float32(pixels)
    
    # Apply K-Means
    kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    
    # Get cluster sizes
    labels = kmeans.labels_
    total_pixels = len(labels)
    
    results = []
    for i in range(n_colors):
        count = np.sum(labels == i)
        proportion = count / total_pixels
        
        color_rgb = tuple(map(int, kmeans.cluster_centers_[i]))
        hex_color = rgb_to_hex(color_rgb)
        color_name = hex_to_color_name(hex_color)
        
        results.append((hex_color, color_name, proportion))
    
    # Sort by proportion descending
    results.sort(key=lambda x: x[2], reverse=True)
    
    return results


def is_neutral_color(color_name: str) -> bool:
    """
    Check if a color is considered neutral in fashion.
    
    Args:
        color_name: Fashion color name
        
    Returns:
        True if neutral color
    """
    neutral_colors = [
        "black", "white", "gray", "grey", "beige", "cream", "ivory",
        "tan", "brown", "charcoal", "navy blue", "khaki", "taupe",
        "camel", "off white", "warm beige", "warm white"
    ]
    return color_name.lower() in neutral_colors


def suggest_complementary_colors(color_name: str) -> List[str]:
    """
    Suggest colors that complement the given color.
    
    Args:
        color_name: Base color name
        
    Returns:
        List of complementary color names
    """
    # Color family to complementary mapping
    complement_map = {
        "red": ["green", "navy blue", "gray"],
        "pink": ["navy blue", "gray", "white"],
        "orange": ["navy blue", "teal", "white"],
        "yellow": ["navy blue", "purple", "gray"],
        "green": ["brown", "burgundy", "cream"],
        "blue": ["orange", "tan", "white", "gold"],
        "purple": ["yellow", "gold", "cream"],
        "neutral": ["any color", "bold accent"]
    }
    
    family = get_color_family(color_name)
    
    if family in complement_map:
        return complement_map[family]
    
    return ["navy blue", "white", "gray"]  # Safe defaults


# ✅ backend/ml/color_extractor.py generated — Adorkable AI
