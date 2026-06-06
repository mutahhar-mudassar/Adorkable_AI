"""
Adorkable AI Stochastic Selector

Weighted random outfit selection using softmax for variety while
maintaining quality through top-N filtering.
"""

import random
from typing import List, Dict, Optional
import math

from backend.config import TOP_N_STOCHASTIC


def softmax(weights: List[float]) -> List[float]:
    """
    Calculate softmax probabilities from scores.
    
    Args:
        weights: List of scores
        
    Returns:
        List of softmax probabilities summing to 1
    """
    # Subtract max for numerical stability
    max_weight = max(weights)
    exp_weights = [math.exp(w - max_weight) for w in weights]
    sum_exp = sum(exp_weights)
    
    return [e / sum_exp for e in exp_weights]


def weighted_random_select(
    scored_outfits: List[Dict],
    top_n: int = TOP_N_STOCHASTIC
) -> Dict:
    """
    Select an outfit using weighted random sampling from top-N candidates.
    
    Process:
        1. Sort outfits by score descending
        2. Take top-N candidates
        3. Calculate softmax weights from scores
        4. Randomly select based on weights
    
    This ensures:
        - Quality: Only top-N candidates considered
        - Variety: Weighted random prevents always picking #1
    
    Args:
        scored_outfits: List of outfit dictionaries with "score" key
        top_n: Number of top candidates to consider
        
    Returns:
        Selected outfit dictionary
        
    Example:
        >>> outfits = [
        ...     {"id": 1, "score": 85},
        ...     {"id": 2, "score": 82},
        ...     {"id": 3, "score": 78}
        ... ]
        >>> selected = weighted_random_select(outfits, top_n=2)
        >>> # Selected from top 2, with 85 having higher probability
    """
    if not scored_outfits:
        raise ValueError("No outfits provided")
    
    if len(scored_outfits) == 1:
        return scored_outfits[0]
    
    # Sort by score descending
    sorted_outfits = sorted(
        scored_outfits,
        key=lambda x: x.get("score", 0),
        reverse=True
    )
    
    # Take top-N (or all if fewer)
    candidates = sorted_outfits[:min(top_n, len(sorted_outfits))]
    
    # Get scores
    scores = [outfit.get("score", 0) for outfit in candidates]
    
    # Calculate softmax weights
    weights = softmax(scores)
    
    # Weighted random selection
    selected = random.choices(candidates, weights=weights, k=1)[0]
    
    return selected


def select_with_exclusion(
    scored_outfits: List[Dict],
    used_item_ids: List[int],
    top_n: int = TOP_N_STOCHASTIC
) -> Optional[Dict]:
    """
    Select an outfit excluding garments that have been used.
    
    Args:
        scored_outfits: List of scored outfit dictionaries
        used_item_ids: List of garment IDs to exclude
        top_n: Number of top candidates
        
    Returns:
        Selected outfit or None if all excluded
    """
    # Filter out outfits with used garments
    available_outfits = []
    
    for outfit in scored_outfits:
        # Check all garment IDs in the outfit
        garment_ids = set()
        
        for key in ["top", "bottom", "dress", "outerwear"]:
            if key in outfit and outfit[key]:
                garment_ids.add(outfit[key].id)
        
        if not garment_ids.intersection(set(used_item_ids)):
            available_outfits.append(outfit)
    
    if not available_outfits:
        return None
    
    return weighted_random_select(available_outfits, top_n)


def get_selection_confidence(outfit: Dict) -> float:
    """
    Calculate confidence level for a selection.
    
    Args:
        outfit: Selected outfit dictionary
        
    Returns:
        Confidence score (0-1)
    """
    score = outfit.get("score", 0)
    
    if score >= 90:
        return 0.95
    elif score >= 80:
        return 0.85
    elif score >= 70:
        return 0.70
    elif score >= 60:
        return 0.55
    else:
        return 0.40


# ✅ backend/engine/stochastic_selector.py generated — Adorkable AI
