"""
Adorkable AI - Outfit Scorer Tests

Unit tests for outfit scoring functionality.
"""

import pytest
from datetime import date
from backend.engine.outfit_scorer import score_outfit, check_trending
from backend.database import GarmentItem, UserProfile


class MockGarment:
    """Mock garment for testing."""
    
    def __init__(self, id, category, color_hex, color_name, style, 
                 fabric_weight="medium", occasion_tags=None):
        self.id = id
        self.category = category
        self.color_hex = color_hex
        self.dominant_color = color_name
        self.style = style
        self.fabric_weight = fabric_weight
        self._occasion_tags = occasion_tags or ["Casual"]
        self.wear_count = 0
        self.last_worn = None
        self.image_path = f"test_{id}.jpg"
    
    def get_occasion_tags_list(self):
        return self._occasion_tags


class MockProfile:
    """Mock user profile for testing."""
    
    def __init__(self, skin_tone="Medium", undertone="Warm", body_shape="Hourglass"):
        self.skin_tone = skin_tone
        self.undertone = undertone
        self.body_shape = body_shape


class TestOutfitScoring:
    """Test outfit scoring functions."""
    
    def test_score_outfit_returns_dict(self):
        """Test that score_outfit returns a dictionary with required keys."""
        # Create mock garments
        top = MockGarment(1, "top", "#FF0000", "Red", "casual")
        bottom = MockGarment(2, "bottom", "#0000FF", "Blue", "casual")
        
        # Create mock profile
        profile = MockProfile()
        
        # Weather
        weather = {"temp_c": 22, "condition": "Clear"}
        
        # Score outfit
        result = score_outfit(
            [top, bottom],
            profile,
            weather,
            "Casual",
            "Western"
        )
        
        # Check result structure
        assert isinstance(result, dict)
        assert "score" in result
        assert "color_harmony" in result
        assert "skin_flattery" in result
        assert "body_shape_score" in result
        assert "weather_score" in result
        assert "occasion_score" in result
        assert "trending" in result
        assert "why_this_suits_you" in result
    
    def test_score_range(self):
        """Test that score is within valid range."""
        top = MockGarment(1, "top", "#FF0000", "Red", "casual")
        bottom = MockGarment(2, "bottom", "#0000FF", "Blue", "casual")
        profile = MockProfile()
        weather = {"temp_c": 22, "condition": "Clear"}
        
        result = score_outfit([top, bottom], profile, weather, "Casual", "Western")
        
        assert 0 <= result["score"] <= 105
    
    def test_complementary_colors_high_harmony(self):
        """Test that complementary colors get high harmony score."""
        # Navy and orange are complementary
        top = MockGarment(1, "top", "#000080", "Navy Blue", "formal")
        bottom = MockGarment(2, "bottom", "#FFA500", "Orange", "formal")
        profile = MockProfile()
        weather = {"temp_c": 22, "condition": "Clear"}
        
        result = score_outfit([top, bottom], profile, weather, "Formal", "Western")
        
        # Should have good color harmony
        assert result["color_harmony"] >= 0.5
    
    def test_occasion_matching(self):
        """Test that occasion matching affects score."""
        # Casual outfit for casual occasion - should score well
        top = MockGarment(1, "top", "#0000FF", "Blue", "casual", occasion_tags=["Casual"])
        bottom = MockGarment(2, "bottom", "#FFFFFF", "White", "casual", occasion_tags=["Casual"])
        profile = MockProfile()
        weather = {"temp_c": 22, "condition": "Clear"}
        
        result = score_outfit([top, bottom], profile, weather, "Casual", "Western")
        
        assert result["occasion_score"] >= 0.5


class TestTrending:
    """Test trending detection."""
    
    def test_check_trending_returns_tuple(self):
        """Test that check_trending returns a tuple."""
        result = check_trending(["Sage Green", "Navy"], "casual", ["top", "bottom"])
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


class TestWeatherScoring:
    """Test weather-based scoring."""
    
    def test_cold_weather_prefers_heavy_fabrics(self):
        """Test that cold weather prefers heavy fabrics."""
        # Light fabric in cold weather should score lower
        top = MockGarment(1, "top", "#0000FF", "Blue", "casual", fabric_weight="light")
        bottom = MockGarment(2, "bottom", "#FFFFFF", "White", "casual", fabric_weight="light")
        profile = MockProfile()
        cold_weather = {"temp_c": 5, "condition": "Clear"}  # Cold
        
        result = score_outfit([top, bottom], profile, cold_weather, "Casual", "Western")
        
        # Weather score should be lower for light fabrics in cold
        assert result["weather_score"] < 0.5
    
    def test_warm_weather_prefers_light_fabrics(self):
        """Test that warm weather prefers light fabrics."""
        # Light fabric in warm weather should score well
        top = MockGarment(1, "top", "#0000FF", "Blue", "casual", fabric_weight="light")
        bottom = MockGarment(2, "bottom", "#FFFFFF", "White", "casual", fabric_weight="light")
        profile = MockProfile()
        warm_weather = {"temp_c": 30, "condition": "Clear"}  # Warm
        
        result = score_outfit([top, bottom], profile, warm_weather, "Casual", "Western")
        
        # Weather score should be good for light fabrics in warm weather
        assert result["weather_score"] >= 0.5


# ✅ tests/test_outfit_scorer.py generated — Adorkable AI
