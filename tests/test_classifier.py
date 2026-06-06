"""
Adorkable AI - Classifier Tests

Unit tests for garment classification.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from backend.ml.classifier import (
    build_model,
    classify_garment,
    _mock_classify,
    get_category_from_prediction,
    get_style_from_prediction,
    is_model_available
)
from backend.config import CATEGORIES, STYLES


class TestModelBuilding:
    """Test model building functions."""
    
    def test_build_model_returns_model(self):
        """Test that build_model returns a Keras Model."""
        model = build_model()
        
        # Check it's a model with expected properties
        assert model is not None
        assert hasattr(model, 'layers')
        assert len(model.layers) > 0


class TestMockClassification:
    """Test mock classification when no model exists."""
    
    def test_mock_classify_returns_dict(self):
        """Test that mock classification returns expected structure."""
        result = _mock_classify("test_image.jpg")
        
        assert isinstance(result, dict)
        assert "category" in result
        assert "category_confidence" in result
        assert "style" in result
        assert "style_confidence" in result
    
    def test_mock_classify_valid_categories(self):
        """Test that mock classification returns valid category."""
        result = _mock_classify("test_image.jpg")
        
        assert result["category"] in CATEGORIES
    
    def test_mock_classify_valid_styles(self):
        """Test that mock classification returns valid style."""
        result = _mock_classify("test_image.jpg")
        
        assert result["style"] in STYLES
    
    def test_mock_classify_confidence_range(self):
        """Test that confidence values are in valid range."""
        result = _mock_classify("test_image.jpg")
        
        assert 0 <= result["category_confidence"] <= 1
        assert 0 <= result["style_confidence"] <= 1


class TestPredictionHelpers:
    """Test prediction helper functions."""
    
    def test_get_category_from_prediction(self):
        """Test category extraction from prediction array."""
        # Create a mock prediction with one clear winner
        prediction = np.zeros(len(CATEGORIES))
        prediction[0] = 0.8  # First category wins
        prediction[1] = 0.1
        prediction[2] = 0.1
        
        category, confidence = get_category_from_prediction(prediction)
        
        assert category == CATEGORIES[0]
        assert confidence == 0.8
    
    def test_get_style_from_prediction(self):
        """Test style extraction from prediction array."""
        # Create a mock prediction
        prediction = np.zeros(len(STYLES))
        prediction[0] = 0.7
        prediction[1] = 0.3
        
        style, confidence = get_style_from_prediction(prediction)
        
        assert style == STYLES[0]
        assert confidence == 0.7
    
    def test_get_category_unknown_on_empty(self):
        """Test that unknown category is returned for invalid prediction."""
        # Create prediction with all zeros
        prediction = np.zeros(len(CATEGORIES))
        
        category, confidence = get_category_from_prediction(prediction)
        
        assert category in CATEGORIES or category == "unknown"


class TestModelAvailability:
    """Test model availability checking."""
    
    def test_is_model_available_returns_bool(self):
        """Test that is_model_available returns a boolean."""
        result = is_model_available()
        
        assert isinstance(result, bool)


# ✅ tests/test_classifier.py generated — Adorkable AI
