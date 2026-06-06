"""
Starter wardrobe helpers.

Provides safe fallback import of starter garments when user's wardrobe is empty.
"""

from __future__ import annotations

import json
import os
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import GarmentItem, get_user_wardrobe, get_user_by_id
from backend.engine.outfit_constraints import (
    catalog_item_matches_user_gender,
    normalize_starter_gender,
)
from backend.utils.image_utils import save_uploaded_image


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOG_PATH = os.path.join(BASE_DIR, "backend", "data", "preloaded_wardrobe.json")


def _load_catalog() -> List[dict]:
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("items", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _resolve_abs_path(image_path: str) -> str:
    normalized = image_path.replace("/", os.sep)
    if os.path.isabs(normalized):
        return normalized
    return os.path.join(BASE_DIR, normalized)


async def ensure_user_has_wardrobe(db: AsyncSession, user_id: int) -> List[GarmentItem]:
    """
    Return user's wardrobe, importing starter garments if empty.
    """
    wardrobe = await get_user_wardrobe(db, user_id)
    if wardrobe:
        return wardrobe

    catalog = _load_catalog()
    user = await get_user_by_id(db, user_id)
    bucket = normalize_starter_gender(user.gender if user else None)
    rows = [i for i in catalog if catalog_item_matches_user_gender(i, bucket)]
    if not rows:
        rows = [
            i
            for i in catalog
            if (i.get("target_gender") or "unisex").strip().lower() == "unisex"
        ]
    if not rows:
        rows = catalog

    for item in rows:
        source_path = _resolve_abs_path(item.get("image_path", ""))
        if not os.path.exists(source_path):
            continue

        with open(source_path, "rb") as f:
            image_bytes = f.read()

        saved_path = save_uploaded_image(
            image_bytes,
            user_id,
            filename=f"starter_{item.get('id', 'item')}.png"
        )

        title = (item.get("title") or "").lower()
        is_eastern = any(word in title for word in ["kurta", "salwar", "traditional", "saree"])
        category = item.get("category", "top")
        if category == "top" and is_eastern:
            category = "traditional_top"
        elif category == "bottom" and is_eastern:
            category = "traditional_bottom"

        # Derive style from tradition field (since style is removed from JSON)
        tradition = item.get("tradition", "Western")
        style = "traditional_eastern" if tradition == "Eastern" else "western"
        gender_fit = (item.get("target_gender") or "unisex").strip().lower()
        garment = GarmentItem(
            user_id=user_id,
            image_path=saved_path,
            category=category,
            style=style,
            dominant_color=item.get("dominant_color", "Unknown"),
            color_hex=item.get("color_hex", "#808080"),
            fabric_weight=item.get("fabric_weight", "medium"),
            occasion_tags=json.dumps(item.get("occasion_tags", ["Casual"])),
            gender_fit=gender_fit,
        )
        db.add(garment)

    await db.commit()
    return await get_user_wardrobe(db, user_id)

