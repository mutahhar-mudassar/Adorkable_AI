"""
Shared helper utilities for routers.

Centralises hijab selection and garment serialisation so they are
not duplicated across recommendations, planner and combo routers.
"""

import random
from typing import List, Optional

from backend.database import GarmentItem


def select_hijab_for_female(
    user_gender: str,
    all_items: List[GarmentItem],
    day_idx: int = 0,
    rotate: bool = False,
) -> Optional[GarmentItem]:
    """
    Return a hijab for female users.

    Args:
        user_gender: Raw gender string from user profile.
        all_items:   Full wardrobe list to search for hijabs.
        day_idx:     Day index (0-6) used for rotation in weekly planner.
        rotate:      If True, rotate by day_idx; otherwise pick randomly.
    """
    if not user_gender or user_gender.strip().lower() not in (
        "female", "woman", "women", "f"
    ):
        return None

    hijabs = [g for g in all_items if g.category == "hijab"]
    if not hijabs:
        return None

    if rotate and len(hijabs) > 1:
        return hijabs[day_idx % len(hijabs)]

    return random.choice(hijabs)


def garment_to_dict(g: Optional[GarmentItem]) -> Optional[dict]:
    """Convert a GarmentItem to a plain dict suitable for API responses."""
    if not g:
        return None
    return {
        "id": g.id,
        "category": g.category,
        "dominant_color": g.dominant_color,
        "color_hex": g.color_hex,
        "image_path": g.image_path,
    }
