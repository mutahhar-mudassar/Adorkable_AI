"""
Adorkable AI Smart Combo Generator

Finds matching garments that create harmonious outfits with a selected item.
"""

from typing import List, Dict, Optional

from backend.database import GarmentItem, UserProfile
from backend.engine.outfit_scorer import score_outfit
from backend.engine.outfit_constraints import (
    filter_scored_outfits,
    should_include_outerwear_layer,
)


def _weather_dict(weather: Optional[Dict]) -> Dict:
    w = dict(weather or {})
    w.setdefault("temp_c", 22)
    w.setdefault("condition", "Clear")
    w.setdefault("humidity", 50)
    return w


def _append_scored_with_outerwear(
    base: List[GarmentItem],
    outerwear: List[GarmentItem],
    combos: List[Dict],
    user_profile: Optional[UserProfile],
    weather: Dict,
    occasion: str,
    style_pref: str,
    min_score: float,
) -> None:
    """Score base garments with mandatory or optional outerwear (aligned with daily engine)."""
    temp_c = float(weather.get("temp_c", 22))
    need_ow = should_include_outerwear_layer(weather, len(outerwear))
    if need_ow and outerwear:
        for ow in outerwear:
            r = score_outfit(
                base + [ow], user_profile, weather, occasion, style_pref
            )
            if r["score"] >= min_score:
                combos.append(r)
    elif need_ow and not outerwear:
        r = score_outfit(base, user_profile, weather, occasion, style_pref)
        if r["score"] >= min_score:
            combos.append(r)
    else:
        r = score_outfit(base, user_profile, weather, occasion, style_pref)
        if r["score"] >= min_score:
            combos.append(r)
        if outerwear and temp_c < 22:
            for ow in outerwear:
                r2 = score_outfit(
                    base + [ow], user_profile, weather, occasion, style_pref
                )
                if r2["score"] >= min_score:
                    combos.append(r2)


def generate_combos(
    selected_item: GarmentItem,
    all_wardrobe: List[GarmentItem],
    user_profile: Optional[UserProfile],
    occasion: str,
    style_pref: str = "Western",
    weather: Optional[Dict] = None
) -> List[Dict]:
    """
    Generate outfit combinations featuring the selected garment.
    
    Separates are always top + bottom (no top + dress). Dress outfits are dress ± outerwear.
    Cold / rain and formal rules match the main recommendation engine.
    """
    combos: List[Dict] = []
    w = _weather_dict(weather)

    other_garments = [g for g in all_wardrobe if g.id != selected_item.id]
    outerwear = [g for g in other_garments if g.category == "outerwear"]
    ow_avail = len(outerwear) > 0
    dress_avail = any(g.category == "dress" for g in all_wardrobe)

    min_score = 40.0

    if selected_item.category in ["top", "ethnic_top"]:
        partners = [
            g for g in other_garments
            if g.category in ["bottom", "ethnic_bottom"]
        ]
        for partner in partners:
            if style_pref == "Eastern":
                if not (
                    "ethnic" in selected_item.category
                    and "ethnic" in partner.category
                ):
                    continue
            elif ("ethnic" in selected_item.category) != (
                "ethnic" in partner.category
            ):
                continue
            _append_scored_with_outerwear(
                [selected_item, partner],
                outerwear,
                combos,
                user_profile,
                w,
                occasion,
                style_pref,
                min_score,
            )

    elif selected_item.category in ["bottom", "ethnic_bottom"]:
        partners = [g for g in other_garments if g.category in ["top", "ethnic_top"]]
        for partner in partners:
            if style_pref == "Eastern":
                if not (
                    "ethnic" in partner.category
                    and "ethnic" in selected_item.category
                ):
                    continue
            elif ("ethnic" in partner.category) != (
                "ethnic" in selected_item.category
            ):
                continue
            _append_scored_with_outerwear(
                [partner, selected_item],
                outerwear,
                combos,
                user_profile,
                w,
                occasion,
                style_pref,
                min_score,
            )

    elif selected_item.category == "dress":
        _append_scored_with_outerwear(
            [selected_item],
            outerwear,
            combos,
            user_profile,
            w,
            occasion,
            style_pref,
            min_score,
        )

    elif selected_item.category == "outerwear":
        tops = [g for g in other_garments if g.category in ["top", "ethnic_top"]]
        bottoms = [
            g for g in other_garments if g.category in ["bottom", "ethnic_bottom"]
        ]
        dresses = [g for g in other_garments if g.category == "dress"]

        for top in tops:
            for bottom in bottoms:
                if style_pref == "Eastern":
                    if not (
                        "ethnic" in top.category and "ethnic" in bottom.category
                    ):
                        continue
                elif ("ethnic" in top.category) != ("ethnic" in bottom.category):
                    continue
                r = score_outfit(
                    [top, bottom, selected_item],
                    user_profile,
                    w,
                    occasion,
                    style_pref,
                )
                if r["score"] >= min_score:
                    combos.append(r)

        for dress in dresses:
            r = score_outfit(
                [dress, selected_item],
                user_profile,
                w,
                occasion,
                style_pref,
            )
            if r["score"] >= min_score:
                combos.append(r)

    filtered = filter_scored_outfits(combos, w, occasion, ow_avail, dress_avail)
    use = filtered if filtered else combos
    use.sort(key=lambda x: x["score"], reverse=True)
    return use


def find_alternatives(
    outfit: Dict,
    all_wardrobe: List[GarmentItem],
    user_profile: Optional[UserProfile],
    occasion: str,
    weather: Optional[Dict] = None
) -> Dict[str, List[Dict]]:
    """
    Find alternative garments for each piece in an outfit.
    
    Args:
        outfit: Current outfit
        all_wardrobe: All garments
        user_profile: User profile
        occasion: Occasion
        weather: Weather info
        
    Returns:
        Dictionary mapping garment categories to alternative options
    """
    alternatives = {}
    w = _weather_dict(weather)

    for key in ["top", "bottom", "dress", "outerwear"]:
        current = outfit.get(key)
        if not current:
            continue

        same_category = [
            g for g in all_wardrobe
            if g.category == current.category and g.id != current.id
        ]

        scored_alternatives = []

        for alt in same_category[:10]:
            test_garments = []
            for k in ["top", "bottom", "dress", "outerwear"]:
                if k == key:
                    test_garments.append(alt)
                elif outfit.get(k):
                    test_garments.append(outfit[k])

            score_result = score_outfit(
                test_garments,
                user_profile,
                w,
                occasion,
                "Eastern" if "ethnic" in alt.category else "Western"
            )

            if score_result["score"] >= 40:
                scored_alternatives.append({
                    "garment": alt,
                    "score": score_result["score"]
                })

        scored_alternatives.sort(key=lambda x: x["score"], reverse=True)
        alternatives[key] = scored_alternatives[:3]

    return alternatives


# ✅ backend/engine/combo_generator.py generated — Adorkable AI
