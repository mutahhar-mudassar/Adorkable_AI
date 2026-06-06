"""
Outfit structure rules: complete separates, cold-weather layering, formal polish.

Used by daily recommend, weekly planner, and smart combo.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from backend.database import GarmentItem, UserProfile
from backend.engine.outfit_scorer import score_outfit
from backend.engine.weather_rules import check_layering_needs
from backend.utils.weather_api import is_rainy_condition


FORMALISH_OCCASIONS = frozenset(
    x.lower()
    for x in (
        "Formal",
        "Business",
        "Party",
        "Wedding",
        "Date Night",
    )
)


def normalize_starter_gender(user_gender: Optional[str]) -> str:
    """
    Map account gender to starter catalog bucket.

    Returns one of: female, male, unisex (unknown / other uses full inclusive set).
    """
    if not user_gender:
        return "unisex"
    g = user_gender.strip().lower()
    if g in ("female", "woman", "women", "f"):
        return "female"
    if g in ("male", "man", "men", "m"):
        return "male"
    return "unisex"


def catalog_item_matches_user_gender(item: dict, bucket: str) -> bool:
    """Whether a preloaded catalog row is appropriate for this user."""
    target = (item.get("target_gender") or "unisex").strip().lower()
    if target == "unisex":
        return True
    if bucket == "unisex":
        return True
    return target == bucket


def should_include_outerwear_layer(weather: Dict, outerwear_count: int) -> bool:
    """True if we should try to add a coat/jacket when pieces exist."""
    if outerwear_count == 0:
        return False
    temp_c = float(weather.get("temp_c", 22))
    humidity = int(weather.get("humidity", 50))
    layering = check_layering_needs(temp_c, humidity)
    if layering["needs_outerwear"]:
        return True
    if is_rainy_condition(str(weather.get("condition", ""))):
        return True
    return False


def outfit_has_complete_separates_or_dress(scored: Dict) -> bool:
    """Valid: (top AND bottom) XOR dress; never dress + top/bottom mixed."""
    top = scored.get("top")
    bottom = scored.get("bottom")
    dress = scored.get("dress")
    if dress:
        if top is not None or bottom is not None:
            return False
        return True
    return top is not None and bottom is not None


def outfit_passes_weather_outerwear_rule(
    scored: Dict,
    weather: Dict,
    outerwear_available: bool,
) -> bool:
    """When cold/rain requires a layer and user owns outerwear, outfit must include it."""
    if not outerwear_available:
        return True
    if not should_include_outerwear_layer(weather, 1):
        return True
    return scored.get("outerwear") is not None


def outfit_passes_formal_rule(
    scored: Dict,
    occasion: str,
    outerwear_available: bool,
    dress_available: bool,
) -> bool:
    """
    Formal / business / party: prefer a dress OR a jacket/coat when wardrobe allows.

    If user has no dress and no outerwear, we still allow top + bottom.
    """
    occ = occasion.strip().lower()
    if occ not in FORMALISH_OCCASIONS:
        return True
    if scored.get("dress"):
        return True
    if scored.get("outerwear"):
        return True
    if not outerwear_available and not dress_available:
        return True
    return False


def filter_scored_outfits(
    candidates: List[Dict],
    weather: Dict,
    occasion: str,
    outerwear_available: bool,
    dress_available: bool,
) -> List[Dict]:
    """Drop structurally invalid or rule-breaking outfits."""
    out: List[Dict] = []
    for c in candidates:
        if not outfit_has_complete_separates_or_dress(c):
            continue
        if not outfit_passes_weather_outerwear_rule(c, weather, outerwear_available):
            continue
        if not outfit_passes_formal_rule(c, occasion, outerwear_available, dress_available):
            continue
        out.append(c)
    return out


def generate_wardrobe_outfit_candidates(
    wardrobe: List[GarmentItem],
    profile: Optional[UserProfile],
    weather: Dict,
    occasion: str,
    style_pref: str,
    min_score: float = 30.0,
) -> List[Dict]:
    """
    Build scored outfit candidates with correct pairing:

    - Every separate outfit is top + bottom (ethnic matched when Eastern).
    - Dress outfits are dress alone or dress + outerwear when weather demands a layer.
    - When layering requires outerwear and user has outerwear, only emit combos that include it.
    - When cool but not required, also emit optional outerwear variants.
    """
    temp_c = float(weather.get("temp_c", 22))
    humidity = int(weather.get("humidity", 50))
    layering = check_layering_needs(temp_c, humidity)
    need_ow = layering["needs_outerwear"]

    tops = [g for g in wardrobe if g.category in ["top", "traditional_top"]]
    bottoms = [g for g in wardrobe if g.category in ["bottom", "traditional_bottom"]]
    dresses = [g for g in wardrobe if g.category == "dress"]
    outerwear = [g for g in wardrobe if g.category == "outerwear"]
    ow_avail = len(outerwear) > 0
    dress_avail = len(dresses) > 0

    candidates: List[Dict] = []

    def add_result(garments: List[GarmentItem]) -> None:
        r = score_outfit(garments, profile, weather, occasion, style_pref)
        if r["score"] >= min_score:
            candidates.append(r)

    # --- Top + bottom (never incomplete) ---
    for top in tops:
        for bottom in bottoms:
            if style_pref == "Eastern":
                if not ("traditional" in top.category and "traditional" in bottom.category):
                    continue
            base = [top, bottom]

            if need_ow and ow_avail:
                for ow in outerwear:
                    add_result(base + [ow])
            elif need_ow and not ow_avail:
                add_result(base)
            else:
                add_result(base)
                if ow_avail and temp_c < 22:
                    for ow in outerwear:
                        add_result(base + [ow])

    # --- Dress ---
    for dress in dresses:
        base = [dress]
        if need_ow and ow_avail:
            for ow in outerwear:
                add_result(base + [ow])
        elif need_ow and not ow_avail:
            add_result(base)
        else:
            add_result(base)
            if ow_avail and temp_c < 22:
                for ow in outerwear:
                    add_result(base + [ow])

    filtered = filter_scored_outfits(
        candidates,
        weather,
        occasion,
        ow_avail,
        dress_avail,
    )
    return filtered if filtered else candidates
