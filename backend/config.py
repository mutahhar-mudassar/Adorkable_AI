"""
Adorkable AI Configuration Module

Loads environment variables and defines application constants.
"""

import os
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =============================================================================
# API Keys & Secrets
# =============================================================================
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
SECRET_KEY: str = os.getenv("SECRET_KEY", "adorkable-secret-key-32-chars-long")
APP_ENV: str = os.getenv("APP_ENV", "development").lower()
CORS_ALLOWED_ORIGINS: List[str] = [
    origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

# =============================================================================
# Database & Paths
# =============================================================================
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./adorkable.db")
MODEL_PATH: str = os.getenv("MODEL_PATH", os.path.join(BASE_DIR, "models", "clothing_classifier"))
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

# =============================================================================
# JWT Settings
# =============================================================================
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

# =============================================================================
# ML/AI Constants
# =============================================================================
IMAGE_SIZE: tuple[int, int] = (224, 224)
COLOR_EXTRACTION_CLUSTERS: int = 5

# =============================================================================
# Skin Tone Labels (6 Types)
# =============================================================================
SKIN_TONE_LABELS: List[str] = [
    "Very Fair",      # Porcelain, ivory
    "Fair",           # Light skin
    "Light Medium",   # Olive, light tan
    "Medium",         # Tan, golden
    "Medium Dark",    # Brown, caramel
    "Dark"            # Deep, rich
]
SKIN_TONE_UNDERTONES: List[str] = ["Warm", "Cool", "Neutral"]

# =============================================================================
# Body Shapes
# =============================================================================
BODY_SHAPES: List[str] = [
    "Hourglass",
    "Pear",
    "Inverted Triangle",
    "Rectangle",
    "Apple",
    "Athletic",
]

# Body shape style rules for scoring
BODY_SHAPE_RULES: Dict[str, Dict[str, Any]] = {
    "Hourglass": {
        "best_silhouettes": ["fitted", "belted", "wrap", "A-line"],
        "avoid": ["boxy", "oversized", "shapeless"],
        "description": "Balanced proportions with defined waist"
    },
    "Pear": {
        "best_silhouettes": ["A-line", "fit-and-flare", "wide-leg", "structured shoulder"],
        "avoid": ["pencil skirt", "skinny bottom", "volume on hips"],
        "description": "Wider hips than shoulders"
    },
    "Inverted Triangle": {
        "best_silhouettes": ["flared bottom", "wide-leg", "hip details", "V-neck"],
        "avoid": ["shoulder pads", "puffed sleeves", "boat neck"],
        "description": "Broader shoulders than hips"
    },
    "Rectangle": {
        "best_silhouettes": ["belted", "layered", "peplum", "ruched"],
        "avoid": ["straight cut", "boxy"],
        "description": "Shoulders, waist, and hips in similar width"
    },
    "Apple": {
        "best_silhouettes": ["empire waist", "wrap", "V-neck", "flowing tunic", "structured jacket open"],
        "avoid": ["clingy knits at midsection", "high thick belts at waist"],
        "description": "Fuller midsection with shoulders and hips often closer in width"
    },
    "Athletic": {
        "best_silhouettes": ["balanced separates", "slim-leg with soft top", "column dress", "open necklines"],
        "avoid": ["overly padded shoulders", "very tight sleeves if shoulders are broad"],
        "description": "Strong shoulders or upper body with a moderate V-shaped silhouette"
    },
}

# =============================================================================
# Clothing Categories
# =============================================================================
CATEGORIES: List[str] = [
    "top",
    "bottom", 
    "dress",
    "outerwear",
    "ethnic_top",
    "ethnic_bottom",
    "shoes",
    "accessory"
]

# Category display names
CATEGORY_DISPLAY: Dict[str, str] = {
    "top": "Top",
    "bottom": "Bottom",
    "dress": "Dress",
    "outerwear": "Outerwear",
    "ethnic_top": "Ethnic Top",
    "ethnic_bottom": "Ethnic Bottom",
    "shoes": "Shoes",
    "accessory": "Accessory"
}

# =============================================================================
# Clothing Styles
# =============================================================================
STYLES: List[str] = ["casual", "formal", "academic", "ethnic_eastern", "western"]

STYLE_DISPLAY: Dict[str, str] = {
    "casual": "Casual",
    "formal": "Formal",
    "academic": "Academic",
    "ethnic_eastern": "Eastern Traditional",
    "western": "Western"
}

# =============================================================================
# Occasions
# =============================================================================
OCCASIONS: List[str] = ["Casual", "Formal", "Academic"]

# =============================================================================
# Style Preferences
# =============================================================================
STYLE_PREFERENCES: List[str] = ["Eastern", "Western"]

# =============================================================================
# Fabric Weights
# =============================================================================
FABRIC_WEIGHTS: List[str] = ["light", "light-medium", "medium", "medium-heavy", "heavy"]

# =============================================================================
# Temperature Thresholds (Celsius)
# =============================================================================
TEMP_THRESHOLDS: Dict[str, float] = {
    "cold": 15.0,
    "cool": 22.0,
    "warm": 28.0,
    "hot": 35.0
}

# Temperature-based fabric recommendations
TEMP_FABRIC_MAP: Dict[str, List[str]] = {
    "heavy": ["wool", "tweed", "velvet", "heavy cotton", "corduroy"],
    "medium-heavy": ["cotton blend", "light wool", "denim"],
    "medium": ["cotton", "linen blend", "light denim"],
    "light-medium": ["cotton voile", "light linen", "chiffon"],
    "light": ["silk", "cotton", "linen", "chiffon", "organza"]
}

# =============================================================================
# Scoring Configuration
# =============================================================================
TOP_N_STOCHASTIC: int = 5

# Scoring weights (must sum to 100 base, with bonus making it up to 105)
SCORING_WEIGHTS: Dict[str, float] = {
    "color_harmony": 30.0,
    "skin_flattery": 20.0,
    "body_shape": 20.0,
    "weather": 20.0,
    "occasion": 10.0,
    "trending_bonus": 5.0
}

# =============================================================================
# Weather Conditions
# =============================================================================
RAIN_CONDITIONS: List[str] = [
    "rain", "drizzle", "thunderstorm", "showers", 
    "light rain", "moderate rain", "heavy rain"
]

# =============================================================================
# Color Families
# =============================================================================
COLOR_FAMILIES: Dict[str, List[str]] = {
    "red": ["crimson", "maroon", "burgundy", "scarlet", "ruby"],
    "pink": ["rose", "blush", "magenta", "fuchsia", "coral", "salmon"],
    "orange": ["tangerine", "coral", "peach", "apricot", "burnt orange"],
    "yellow": ["mustard", "gold", "lemon", "butter", "cream"],
    "green": ["sage", "emerald", "olive", "mint", "forest", "lime", "teal"],
    "blue": ["navy", "sky", "royal", "cobalt", "slate", "turquoise", "aqua"],
    "purple": ["lavender", "plum", "violet", "mauve", "lilac", "amethyst"],
    "neutral": ["black", "white", "gray", "grey", "beige", "cream", "ivory", "tan", "brown", "charcoal"]
}

NEUTRAL_COLORS: List[str] = ["black", "white", "gray", "grey", "beige", "cream", "ivory", "tan", "brown", "charcoal", "navy"]

# =============================================================================
# Data File Paths
# =============================================================================
COLOR_MAPPING_PATH: str = os.path.join(BASE_DIR, "backend", "data", "color_mapping.json")
SKIN_TONE_PALETTE_PATH: str = os.path.join(BASE_DIR, "backend", "data", "skin_tone_palette.json")
TRENDS_PATH: str = os.path.join(BASE_DIR, "backend", "data", "trends_2026.json")

# ✅ backend/config.py generated — Adorkable AI
