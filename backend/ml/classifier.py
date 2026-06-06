"""
Adorkable AI Clothing Classifier Module

TensorFlow/Keras-based clothing classification using EfficientNetB0
with dual output heads for category and style classification.
"""

import os
from typing import Dict, Optional, Tuple
from pathlib import Path
import hashlib

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.preprocessing import image

from backend.config import MODEL_PATH, CATEGORIES, STYLES, IMAGE_SIZE
from backend.utils.image_utils import load_and_preprocess, resolve_stored_image_path


# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


# =============================================================================
# Model Architecture
# =============================================================================

def build_model(
    num_categories: int = len(CATEGORIES),
    num_styles: int = len(STYLES)
) -> Model:
    """
    Build a multi-output clothing classification model.
    
    Architecture:
        - EfficientNetB0 base (frozen) with ImageNet weights
        - Global Average Pooling
        - Dense(256) + Dropout(0.3)
        - Two output heads:
            - Category: softmax over clothing categories
            - Style: softmax over style types
    
    Args:
        num_categories: Number of clothing categories
        num_styles: Number of style categories
        
    Returns:
        Compiled Keras Model
    """
    # Load EfficientNetB0 base for stronger feature extraction.
    base_model = EfficientNetB0(
        weights='imagenet',
        include_top=False,
        input_shape=(*IMAGE_SIZE, 3)
    )
    
    # Freeze base layers
    base_model.trainable = False
    
    # Input
    inputs = keras.Input(shape=(*IMAGE_SIZE, 3))
    
    # Base model
    x = base_model(inputs, training=False)
    
    # Global pooling
    x = layers.GlobalAveragePooling2D()(x)
    
    # Dense layer
    x = layers.Dense(256, activation='relu')(x)
    x = layers.Dropout(0.3)(x)
    
    # Output heads
    category_output = layers.Dense(
        num_categories,
        activation='softmax',
        name='category'
    )(x)
    
    style_output = layers.Dense(
        num_styles,
        activation='softmax',
        name='style'
    )(x)
    
    # Create model
    model = Model(
        inputs=inputs,
        outputs=[category_output, style_output],
        name='clothing_classifier'
    )
    
    # Compile
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss={
            'category': 'sparse_categorical_crossentropy',
            'style': 'sparse_categorical_crossentropy'
        },
        metrics={
            'category': ['accuracy'],
            'style': ['accuracy']
        }
    )
    
    return model


# =============================================================================
# Model Persistence
# =============================================================================

def save_model(model: Model, path: str = MODEL_PATH) -> None:
    """
    Save trained model to disk.
    
    Args:
        model: Trained Keras model
        path: Directory path to save model
    """
    os.makedirs(path, exist_ok=True)
    model.save(os.path.join(path, 'model.h5'))
    print(f"✅ Model saved to {path}")


def load_model(path: str = MODEL_PATH) -> Optional[Model]:
    """
    Load trained model from disk.
    
    Args:
        path: Directory path to load model from
        
    Returns:
        Loaded Keras model, or None if not found
    """
    model_file = os.path.join(path, 'model.h5')
    
    if not os.path.exists(model_file):
        return None
    
    try:
        model = keras.models.load_model(model_file)
        print(f"✅ Model loaded from {path}")
        return model
    except Exception as e:
        print(f"⚠️ Error loading model: {e}")
        return None


# =============================================================================
# Classification
# =============================================================================

# Global model cache
_model: Optional[Model] = None

def get_model() -> Optional[Model]:
    """Get or load the classification model."""
    global _model
    if _model is None:
        _model = load_model()
    return _model


def classify_garment(image_path: str) -> Dict:
    """
    Classify a garment image into category and style.
    
    If no trained model exists, returns mock predictions for development.
    
    Args:
        image_path: Path to garment image
        
    Returns:
        Dictionary with classification results:
        {
            "category": str,
            "category_confidence": float,
            "style": str,
            "style_confidence": float
        }
    """
    model = get_model()
    
    # If no model exists, use rule-based mock classification
    if model is None:
        return mock_classify(image_path)
    
    # Preprocess image
    img_array = load_and_preprocess(image_path, target_size=IMAGE_SIZE)
    img_batch = np.expand_dims(img_array, axis=0)
    
    # Predict
    predictions = model.predict(img_batch, verbose=0)
    
    # Category prediction
    category_probs = predictions[0][0]
    category_idx = np.argmax(category_probs)
    category = CATEGORIES[category_idx]
    category_confidence = float(category_probs[category_idx])
    
    # Style prediction
    style_probs = predictions[1][0]
    style_idx = np.argmax(style_probs)
    style = STYLES[style_idx]
    style_confidence = float(style_probs[style_idx])
    
    return {
        "category": category,
        "category_confidence": category_confidence,
        "style": style,
        "style_confidence": style_confidence
    }


def _analyze_image_features(image_path: str) -> Dict:
    """
    Analyze image features (aspect ratio, color distribution, edges).
    
    Returns features that help distinguish clothing types.
    """
    import cv2
    from backend.ml.color_extractor import extract_dominant_color
    
    img = cv2.imread(resolve_stored_image_path(image_path))
    if img is None:
        return {"aspect_ratio": 1.0, "area": 0, "dominant_color": "#000000", 
                "brightness": 128, "edge_density": 0.5}
    
    h, w = img.shape[:2]
    aspect_ratio = w / h if h > 0 else 1.0
    area = h * w
    
    # Convert to RGB for color analysis
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Get dominant color
    try:
        dom_color_hex, color_name = extract_dominant_color(image_path)
        # Convert hex to RGB for brightness calc
        r = int(dom_color_hex[1:3], 16)
        g = int(dom_color_hex[3:5], 16)
        b = int(dom_color_hex[5:7], 16)
        brightness = (r + g + b) / 3
    except:
        brightness = 128
        color_name = "Unknown"
    
    # Edge density (simple Canny edge detection)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    edge_density = np.sum(edges > 0) / (h * w)
    
    return {
        "aspect_ratio": aspect_ratio,
        "area": area,
        "dominant_color": color_name,
        "brightness": brightness,
        "edge_density": edge_density
    }


def mock_classify(image_path: str) -> Dict:
    """
    Smart classification using image features and filename hints.
    
    Analyzes actual image content (aspect ratio, colors, edges) to determine
    clothing category rather than just using filename.
    
    Args:
        image_path: Path to garment image
        
    Returns:
        Classification results based on image analysis
    """
    filename = Path(image_path).stem.lower()
    
    # Analyze image features
    features = _analyze_image_features(image_path)
    aspect = features["aspect_ratio"]
    brightness = features["brightness"]
    edge_density = features["edge_density"]
    
    # First try filename keywords (strong signal if present)
    category_keywords = {
        "top": ["top", "shirt", "blouse", "tshirt", "t-shirt", "tee"],
        "bottom": ["bottom", "pant", "trouser", "jean", "skirt", "short", "cargo", "chino", "corduroy", "trackpant", "jogger", "sweatpant", "legging", "wide leg", "straight leg", "pinstripe", "navy pant", "black pant", "trousers"],
        "dress": ["dress", "gown", "frock"],
        "outerwear": ["jacket", "coat", "blazer", "cardigan", "sweater"],
        "ethnic_top": ["kurta", "kameez", "sherwani", "ethnic", "saree_blouse", "lehenga_choli_top"],
        "ethnic_bottom": ["salwar", "pajama", "dhoti", "churidar", "lehenga", "ghagra", "lungi"],
        "shoes": ["shoe", "sandal", "heel", "boot", "slipper"],
        "accessory": ["bag", "belt", "scarf", "jewelry", "watch", "hat", "tie"]
    }
    
    category = None
    category_conf = 0.7
    
    for cat, keywords in category_keywords.items():
        if any(kw in filename for kw in keywords):
            category = cat
            category_conf = 0.85  # Higher confidence when filename matches
            break
    
    # If no filename match, use image features
    if category is None:
        # Aspect ratio based classification
        if aspect < 0.7:  # Tall/slim - likely shoes or pants (was 0.6, increased to 0.7)
            if edge_density > 0.06:  # High detail = shoes (was 0.05, increased threshold)
                category = "shoes"
            else:
                category = "bottom"
        elif aspect > 1.5:  # Wide - likely top or accessory
            if edge_density > 0.08:  # Complex = accessory (bag, etc.)
                category = "accessory"
            else:
                category = "top"
        elif 0.8 <= aspect <= 1.2:  # Square-ish - dress or outerwear
            if brightness < 100:  # Dark = outerwear
                category = "outerwear"
            else:
                category = "dress"
        else:  # Medium aspect - could be ethnic or other
            if brightness > 200:  # Very bright = ethnic often colorful
                category = "ethnic_top"
            else:
                category = "top"
        
        category_conf = 0.65
    
    # Style classification based on colors and features
    style_keywords = {
        "casual": ["casual", "everyday", "relaxed", "tshirt", "jean"],
        "formal": ["formal", "business", "office", "suit", "blazer"],
        "academic": ["academic", "university", "college", "study"],
        "ethnic_eastern": ["ethnic", "traditional", "kurta", "saree", "salwar", "lehenga", "anarkali", "churidar"],
        "western": ["western", "modern", "dress", "skirt"]
    }
    
    style = None
    style_conf = 0.65
    
    for stl, keywords in style_keywords.items():
        if any(kw in filename for kw in keywords):
            style = stl
            style_conf = 0.80
            break
    
    # If no filename match for style, infer from features
    if style is None:
        if "ethnic" in category or category in ["ethnic_top", "ethnic_bottom"]:
            style = "ethnic_eastern"
        elif category in ["dress"] and edge_density < 0.08:
            style = "western"
        elif brightness < 100:  # Dark colors often formal
            style = "formal"
        elif edge_density > 0.1:  # Complex patterns often ethnic
            style = "ethnic_eastern"
        elif category in ["dress", "skirt", "top"]:
            style = "western"
        elif category in ["bottom"]:
            style = "casual"
        else:
            style = "casual"
    
    return {
        "category": category,
        "category_confidence": round(category_conf, 2),
        "style": style,
        "style_confidence": round(style_conf, 2),
        "features": {  # Include for debugging
            "aspect_ratio": round(aspect, 2),
            "brightness": round(brightness, 1),
            "edge_density": round(edge_density, 3)
        }
    }


def classify_batch(image_paths: list) -> list:
    """
    Classify multiple garment images.
    
    Args:
        image_paths: List of image paths
        
    Returns:
        List of classification dictionaries
    """
    return [classify_garment(path) for path in image_paths]


# =============================================================================
# Inference Helpers
# =============================================================================

def get_category_from_prediction(prediction_array: np.ndarray) -> Tuple[str, float]:
    """
    Get category name and confidence from prediction array.
    
    Args:
        prediction_array: Softmax output array
        
    Returns:
        Tuple of (category_name, confidence)
    """
    idx = np.argmax(prediction_array)
    confidence = float(prediction_array[idx])
    category = CATEGORIES[idx] if idx < len(CATEGORIES) else "unknown"
    return category, confidence


def get_style_from_prediction(prediction_array: np.ndarray) -> Tuple[str, float]:
    """
    Get style name and confidence from prediction array.
    
    Args:
        prediction_array: Softmax output array
        
    Returns:
        Tuple of (style_name, confidence)
    """
    idx = np.argmax(prediction_array)
    confidence = float(prediction_array[idx])
    style = STYLES[idx] if idx < len(STYLES) else "unknown"
    return style, confidence


# =============================================================================
# Model Info
# =============================================================================

def get_model_info() -> Dict:
    """
    Get information about the current model.
    
    Returns:
        Dictionary with model status and info
    """
    model = get_model()
    model_path = os.path.join(MODEL_PATH, 'model.h5')
    
    info = {
        "model_loaded": model is not None,
        "model_path": MODEL_PATH,
        "model_exists": os.path.exists(model_path),
        "categories": CATEGORIES,
        "styles": STYLES,
        "image_size": IMAGE_SIZE
    }
    
    if model:
        info["model_summary"] = str(model.summary())
    
    return info


def is_model_available() -> bool:
    """Check if a trained model is available."""
    model_file = os.path.join(MODEL_PATH, 'model.h5')
    return os.path.exists(model_file)


# ✅ backend/ml/classifier.py generated — Adorkable AI
