"""
Adorkable AI - Color Theory Tests

Unit tests for color harmony and conversion functions.
"""

import pytest
from backend.engine.color_theory import (
    hex_to_rgb,
    rgb_to_hex,
    hex_to_hsl,
    hsl_to_hex,
    get_complementary_colors,
    get_analogous_colors,
    get_monochromatic_colors,
    color_harmony_score,
    is_complementary,
    is_analogous,
    is_monochromatic
)


class TestColorConversions:
    """Test color conversion functions."""
    
    def test_hex_to_rgb_red(self):
        """Test hex to RGB for pure red."""
        result = hex_to_rgb("#FF0000")
        assert result == (255, 0, 0)
    
    def test_hex_to_rgb_green(self):
        """Test hex to RGB for pure green."""
        result = hex_to_rgb("#00FF00")
        assert result == (0, 255, 0)
    
    def test_hex_to_rgb_blue(self):
        """Test hex to RGB for pure blue."""
        result = hex_to_rgb("#0000FF")
        assert result == (0, 0, 255)
    
    def test_hex_to_rgb_without_hash(self):
        """Test hex to RGB without # prefix."""
        result = hex_to_rgb("FF0000")
        assert result == (255, 0, 0)
    
    def test_rgb_to_hex_red(self):
        """Test RGB to hex for pure red."""
        result = rgb_to_hex(255, 0, 0)
        assert result == "#ff0000"
    
    def test_hex_to_hsl_red(self):
        """Test HSL conversion for red."""
        h, s, l = hex_to_hsl("#FF0000")
        assert 0 <= h <= 10 or 350 <= h <= 360  # Red is at 0°
        assert s > 90  # High saturation
        assert 45 <= l <= 55  # Medium lightness


class TestColorHarmony:
    """Test color harmony functions."""
    
    def test_complementary_red_cyan(self):
        """Test that red and cyan are complementary."""
        score = color_harmony_score("#FF0000", "#00FFFF")
        assert score >= 0.95
    
    def test_complementary_blue_orange(self):
        """Test that blue and orange are complementary."""
        score = color_harmony_score("#0000FF", "#FFA500")
        assert score >= 0.85
    
    def test_analogous_colors(self):
        """Test analogous color harmony."""
        # Red and red-orange should be analogous
        score = color_harmony_score("#FF0000", "#FF4500")
        assert score >= 0.70
    
    def test_monochromatic_colors(self):
        """Test monochromatic color harmony."""
        # Different shades of blue
        score = color_harmony_score("#0000FF", "#4169E1")
        assert score >= 0.70
    
    def test_neutral_plus_any(self):
        """Test that neutral colors harmonize with anything."""
        score = color_harmony_score("#000000", "#FF0000", 
                                     color1_name="Black", color2_name="Red")
        assert score >= 0.85
    
    def test_clashing_colors_low_score(self):
        """Test that clashing colors get low scores."""
        # Similar hue but different saturation/lightness
        score = color_harmony_score("#FF0000", "#FF3333")
        assert score < 0.5


class TestHarmonyDetection:
    """Test harmony detection functions."""
    
    def test_is_complementary_true(self):
        """Test complementary detection - true case."""
        assert is_complementary("#FF0000", "#00FFFF") == True
    
    def test_is_complementary_false(self):
        """Test complementary detection - false case."""
        assert is_complementary("#FF0000", "#00FF00") == False
    
    def test_is_analogous_true(self):
        """Test analogous detection - true case."""
        assert is_analogous("#FF0000", "#FF4500") == True
    
    def test_is_analogous_false(self):
        """Test analogous detection - false case."""
        assert is_analogous("#FF0000", "#0000FF") == False
    
    def test_is_monochromatic_true(self):
        """Test monochromatic detection - true case."""
        assert is_monochromatic("#0000FF", "#4169E1") == True
    
    def test_is_monochromatic_false(self):
        """Test monochromatic detection - false case."""
        assert is_monochromatic("#FF0000", "#00FF00") == False


class TestColorGeneration:
    """Test color generation functions."""
    
    def test_complementary_generation(self):
        """Test that complementary colors are generated correctly."""
        colors = get_complementary_colors("#FF0000")
        assert len(colors) == 3
        # First color should be roughly cyan
        h, s, l = hex_to_hsl(colors[0])
        assert 170 <= h <= 190
    
    def test_analogous_generation(self):
        """Test that analogous colors are generated correctly."""
        colors = get_analogous_colors("#FF0000")
        assert len(colors) == 4
        # All should be in the red-orange-yellow range
        for color in colors:
            h, s, l = hex_to_hsl(color)
            assert 0 <= h <= 90 or 330 <= h <= 360
    
    def test_monochromatic_generation(self):
        """Test that monochromatic colors are generated correctly."""
        colors = get_monochromatic_colors("#0000FF")
        assert len(colors) == 4
        # All should have similar hue
        base_h, _, _ = hex_to_hsl("#0000FF")
        for color in colors:
            h, _, _ = hex_to_hsl(color)
            hue_diff = abs(h - base_h)
            assert hue_diff < 15 or hue_diff > 345


# ✅ tests/test_color_theory.py generated — Adorkable AI
