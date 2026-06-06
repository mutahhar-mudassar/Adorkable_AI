"""
Adorkable AI Skin Tone Analysis Module

MediaPipe-based face detection and skin tone classification using
cheek region color analysis for undertone detection.
"""

import json
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

import cv2
import numpy as np

from backend.utils.image_utils import resolve_stored_image_path

# MediaPipe import - Tasks API for version 0.10+
MEDIAPIPE_AVAILABLE = False
FACE_DETECTOR = None

try:
    import mediapipe as mp
    from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions
    from mediapipe import Image, ImageFormat
    import os
    
    # Model path
    model_path = os.path.join(os.path.dirname(__file__), "models", "blaze_face_short_range.tflite")
    
    # Download model if not exists
    if not os.path.exists(model_path):
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        print(f"Downloading face detection model...")
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
        urllib.request.urlretrieve(url, model_path)
        print("✅ Model downloaded!")
    
    # Create detector with model
    base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
    options = FaceDetectorOptions(
        base_options=base_options,
        min_detection_confidence=0.5
    )
    FACE_DETECTOR = FaceDetector.create_from_options(options)
    MEDIAPIPE_AVAILABLE = True
    print("✅ MediaPipe FaceDetector initialized!")
    
except Exception as e:
    print(f"MediaPipe FaceDetector not available: {e}")
    FACE_DETECTOR = None
    MEDIAPIPE_AVAILABLE = False

from backend.config import SKIN_TONE_LABELS, SKIN_TONE_UNDERTONES, SKIN_TONE_PALETTE_PATH


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SkinToneResult:
    """Result of skin tone analysis."""
    skin_tone: str  # Fair, Medium, Dark
    undertone: str  # Warm, Cool, Neutral
    avg_rgb: Tuple[int, int, int]
    confidence: float
    face_detected: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "skin_tone": self.skin_tone,
            "undertone": self.undertone,
            "avg_rgb": list(self.avg_rgb),
            "confidence": self.confidence,
            "face_detected": self.face_detected,
            "error": self.error
        }


# =============================================================================
# Color Analysis Functions
# =============================================================================

def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert RGB to HSV color space.
    
    Args:
        r, g, b: RGB values (0-255)
        
    Returns:
        HSV tuple (hue 0-360, saturation 0-1, value 0-1)
    """
    rgb = np.uint8([[[r, g, b]]])
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    return float(hsv[0][0][0]) * 2, float(hsv[0][0][1]) / 255.0, float(hsv[0][0][2]) / 255.0


def classify_skin_tone_from_rgb(r: int, g: int, b: int) -> Tuple[str, float]:
    """
    Classify skin tone (6 types) from RGB values.
    
    Uses brightness and red channel values to determine skin tone category.
    
    6 Skin Tone Types (Relaxed for European skin):
    - Very Fair (Porcelain): brightness > 160
    - Fair: brightness 120-160
    - Light Medium (Olive): brightness 95-120
    - Medium: brightness 70-95
    - Medium Dark: brightness 50-70
    - Dark: brightness < 50
    
    Args:
        r, g, b: Average RGB values from skin sample
        
    Returns:
        Tuple of (skin_tone_label, confidence)
    """
    brightness = (r + g + b) / 3.0
    # Perceived luminance is more robust than plain mean for darker tones.
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # Guard against dark skin being over-lifted into medium by highlights.
    if luminance < 90 and max(r, g, b) < 145:
        if luminance < 70:
            return "Dark", 0.91
        return "Medium Dark", 0.89

    # Balanced thresholds across six tones.
    if luminance > 175:
        return "Very Fair", 0.92
    elif 145 <= luminance <= 175:
        return "Fair", 0.90
    elif 118 <= luminance < 145:
        return "Light Medium", 0.88
    elif 92 <= luminance < 118:
        return "Medium", 0.85
    elif 70 <= luminance < 92:
        return "Medium Dark", 0.88
    else:
        return "Dark", 0.90


def classify_undertone_from_rgb(r: int, g: int, b: int) -> Tuple[str, float]:
    """
    Classify undertone (Warm, Cool, Neutral) from RGB values.
    
    Uses hue analysis to detect warm (yellow/orange/red) vs cool (pink/blue) tones.
    
    Args:
        r, g, b: Average RGB values from skin sample
        
    Returns:
        Tuple of (undertone_label, confidence)
    """
    # Convert to HSV for better hue analysis
    h, s, v = rgb_to_hsv(r, g, b)
    
    # Warm undertones: yellow (60°), orange (30°), red (0-15°)
    # Cool undertones: pink (340-360°), blue (200-260°)
    
    warm_score = 0
    cool_score = 0
    
    # Check red/yellow dominance (warm)
    if r > b and g > b:
        warm_score += 1
    
    # Check for pink tones (more blue in red) - cool
    if r > 150 and abs(r - b) < 50:
        cool_score += 1
    
    # Hue-based analysis
    if 0 <= h <= 60 or 330 <= h <= 360:  # Red-orange-yellow range
        warm_score += 2
    elif 180 <= h <= 280:  # Blue-cyan range
        cool_score += 2
    
    # Yellow vs pink undertone detection
    # More yellow (high G relative to B) = warm
    # More pink (balanced R and B) = cool
    yellow_indicator = g - b
    if yellow_indicator > 20:
        warm_score += 1
    elif abs(r - g) < 15 and b > g:  # Pinkish
        cool_score += 1
    
    # Determine undertone
    if warm_score > cool_score + 1:
        confidence = min(0.95, 0.6 + (warm_score - cool_score) * 0.1)
        return "Warm", confidence
    elif cool_score > warm_score + 1:
        confidence = min(0.95, 0.6 + (cool_score - warm_score) * 0.1)
        return "Cool", confidence
    else:
        return "Neutral", 0.75


def extract_cheek_regions(
    image: np.ndarray,
    face_detection_result
) -> List[np.ndarray]:
    """
    Extract cheek regions from detected face.
    
    Uses face detection bounding box to estimate cheek positions.
    
    Args:
        image: Input image array
        face_detection_result: MediaPipe face detection result
        
    Returns:
        List of cheek region image patches
    """
    h, w = image.shape[:2]
    cheek_regions = []
    
    if not face_detection_result.detections:
        return cheek_regions
    
    for detection in face_detection_result.detections:
        # Get bounding box
        bbox = detection.location_data.relative_bounding_box
        
        # Convert to pixel coordinates
        x_min = int(bbox.xmin * w)
        y_min = int(bbox.ymin * h)
        x_max = int((bbox.xmin + bbox.width) * w)
        y_max = int((bbox.ymin + bbox.height) * h)
        
        face_width = x_max - x_min
        face_height = y_max - y_min
        
        # Define cheek regions (approximately 20-30% of face width/height)
        # Left cheek (face left, image right)
        left_cheek_x1 = x_min + int(face_width * 0.10)
        left_cheek_x2 = x_min + int(face_width * 0.35)
        left_cheek_y1 = y_min + int(face_height * 0.45)
        left_cheek_y2 = y_min + int(face_height * 0.75)
        
        # Right cheek
        right_cheek_x1 = x_min + int(face_width * 0.65)
        right_cheek_x2 = x_min + int(face_width * 0.90)
        right_cheek_y1 = y_min + int(face_height * 0.45)
        right_cheek_y2 = y_min + int(face_height * 0.75)
        
        # Extract regions
        left_cheek = image[left_cheek_y1:left_cheek_y2, left_cheek_x1:left_cheek_x2]
        right_cheek = image[right_cheek_y1:right_cheek_y2, right_cheek_x1:right_cheek_x2]
        
        if left_cheek.size > 0:
            cheek_regions.append(left_cheek)
        if right_cheek.size > 0:
            cheek_regions.append(right_cheek)
    
    return cheek_regions


def _is_skin_pixel(r: int, g: int, b: int) -> bool:
    """Check if pixel is likely skin colored."""
    # Skin tones typically have R > G > B pattern with specific ranges
    rg_diff = r - g
    rb_diff = r - b
    # Skin: reddish, not too dark, not too saturated
    return (60 < r < 250 and 40 < g < 220 and 20 < b < 170 and
            10 < rg_diff < 100 and rb_diff > 10)


def _fallback_skin_tone_from_image(image_rgb: np.ndarray) -> Dict:
    """
    Improved fallback skin tone estimation using skin pixel detection.

    Samples multiple regions and finds skin-like pixels for better accuracy.
    """
    h, w = image_rgb.shape[:2]

    # Define multiple sampling regions (upper face area, center, sides)
    regions = [
        (0.2, 0.5, 0.2, 0.8),   # Upper center (forehead area)
        (0.3, 0.6, 0.3, 0.7),   # Center
        (0.2, 0.5, 0.1, 0.4),   # Left upper
        (0.2, 0.5, 0.6, 0.9),   # Right upper
    ]

    all_skin_pixels = []

    for y_start_pct, y_end_pct, x_start_pct, x_end_pct in regions:
        y1, y2 = int(h * y_start_pct), int(h * y_end_pct)
        x1, x2 = int(w * x_start_pct), int(w * x_end_pct)
        region = image_rgb[y1:y2, x1:x2]

        if region.size == 0:
            continue

        pixels = region.reshape(-1, 3)
        # Filter for skin-like pixels
        for pixel in pixels:
            r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
            if _is_skin_pixel(r, g, b):
                all_skin_pixels.append([r, g, b])

    # Check if at least 30% of image pixels are skin-colored (prevent false positives on non-human images)
    total_pixels = h * w
    skin_percentage = len(all_skin_pixels) / total_pixels if total_pixels > 0 else 0
    
    if skin_percentage < 0.30:
        return SkinToneResult(
            skin_tone="Unknown",
            undertone="Unknown",
            avg_rgb=(0, 0, 0),
            confidence=0.0,
            face_detected=False,
            error="No face detected. Image does not contain sufficient skin tones."
        ).to_dict()

    # If we found skin pixels, use the brighter ones (likely actual skin, not shadows)
    if len(all_skin_pixels) > 10:
        # Sort by brightness and take top 50%
        skin_pixels = np.array(all_skin_pixels)
        brightness = skin_pixels[:, 0] + skin_pixels[:, 1] + skin_pixels[:, 2]
        bright_threshold = np.percentile(brightness, 50)
        bright_skin = skin_pixels[brightness >= bright_threshold]

        avg_rgb = tuple(map(int, np.mean(bright_skin, axis=0)))
        confidence_boost = min(0.85, 0.6 + len(all_skin_pixels) / 1000)
    else:
        # Very few skin pixels found - fall back to center region
        y1, y2 = int(h * 0.3), int(h * 0.7)
        x1, x2 = int(w * 0.3), int(w * 0.7)
        region = image_rgb[y1:y2, x1:x2]
        pixels = region.reshape(-1, 3)

        # Use brighter pixels from center (but keep all bright pixels for fair skin)
        brightness = pixels[:, 0] + pixels[:, 1] + pixels[:, 2]
        bright_threshold = np.percentile(brightness, 60)  # Lower threshold to include more pixels
        bright_pixels = pixels[brightness >= bright_threshold]

        avg_rgb = tuple(map(int, np.mean(bright_pixels, axis=0)))
        confidence_boost = 0.5

    r, g, b = avg_rgb
    skin_tone, tone_conf = classify_skin_tone_from_rgb(r, g, b)
    undertone, undertone_conf = classify_undertone_from_rgb(r, g, b)

    return SkinToneResult(
        skin_tone=skin_tone,
        undertone=undertone,
        avg_rgb=avg_rgb,
        confidence=max(confidence_boost, (tone_conf + undertone_conf) / 2),
        face_detected=False,
        error=None
    ).to_dict()


# =============================================================================
# Main Analysis
# =============================================================================

def analyze_skin_tone(selfie_path: str) -> Dict:
    """
    Analyze skin tone from a selfie image using REAL MediaPipe face detection.
    
    Process:
        1. Load image with OpenCV
        2. Run MediaPipe FaceDetector (NEW Tasks API)
        3. Extract cheek regions from detected face bounding boxes
        4. Average RGB pixel values from cheek regions
        5. Classify skin tone and undertone
    
    Args:
        selfie_path: Path to selfie image
        
    Returns:
        Dictionary with skin tone analysis results:
        {
            "skin_tone": "Fair|Medium|Dark",
            "undertone": "Warm|Cool|Neutral",
            "avg_rgb": [r, g, b],
            "confidence": float,
            "face_detected": bool,
            "error": str or None
        }
    """
    # Load image
    image = cv2.imread(resolve_stored_image_path(selfie_path))
    if image is None:
        return SkinToneResult(
            skin_tone="Unknown",
            undertone="Unknown",
            avg_rgb=(0, 0, 0),
            confidence=0.0,
            face_detected=False,
            error="Could not load image"
        ).to_dict()

    # Convert to RGB for MediaPipe
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    h, w = image_rgb.shape[:2]

    # Check if MediaPipe FaceDetector is available
    if not MEDIAPIPE_AVAILABLE or FACE_DETECTOR is None:
        print("MediaPipe FaceDetector not available, using fallback")
        return _fallback_skin_tone_from_image(image_rgb)
    
    try:
        # Create MediaPipe Image from numpy array (Tasks API)
        mp_image = Image(image_format=ImageFormat.SRGB, data=image_rgb)
        
        # Run face detection with Tasks API
        detection_result = FACE_DETECTOR.detect(mp_image)
        
        # Check if any faces were detected
        if not detection_result.detections:
            print("No face detected, using fallback skin analysis")
            return _fallback_skin_tone_from_image(image_rgb)
        
        print(f"✅ Face detected! Found {len(detection_result.detections)} face(s)")
        
        # Extract cheek regions from detections (Tasks API format)
        cheek_regions = []
        
        for detection in detection_result.detections:
            # Get bounding box from detection (Tasks API format)
            bbox = detection.bounding_box
            
            # Convert to pixel coordinates
            x_min = int(bbox.origin_x)
            y_min = int(bbox.origin_y)
            x_max = int(bbox.origin_x + bbox.width)
            y_max = int(bbox.origin_y + bbox.height)
            
            face_width = x_max - x_min
            face_height = y_max - y_min
            
            # Define cheek regions
            left_cheek_x1 = max(0, x_min + int(face_width * 0.10))
            left_cheek_x2 = max(0, x_min + int(face_width * 0.35))
            left_cheek_y1 = max(0, y_min + int(face_height * 0.45))
            left_cheek_y2 = max(0, y_min + int(face_height * 0.75))
            
            right_cheek_x1 = max(0, x_min + int(face_width * 0.65))
            right_cheek_x2 = max(0, x_min + int(face_width * 0.90))
            right_cheek_y1 = max(0, y_min + int(face_height * 0.45))
            right_cheek_y2 = max(0, y_min + int(face_height * 0.75))
            
            # Extract cheek regions
            left_cheek = image_rgb[left_cheek_y1:left_cheek_y2, left_cheek_x1:left_cheek_x2]
            right_cheek = image_rgb[right_cheek_y1:right_cheek_y2, right_cheek_x1:right_cheek_x2]
            
            if left_cheek.size > 0:
                cheek_regions.append(left_cheek)
            if right_cheek.size > 0:
                cheek_regions.append(right_cheek)
        
        if not cheek_regions:
            return _fallback_skin_tone_from_image(image_rgb)
        
        # Calculate average RGB from all cheek regions
        all_pixels = []
        for region in cheek_regions:
            pixels = region.reshape(-1, 3)
            all_pixels.extend(pixels)
        
        all_pixels = np.array(all_pixels)
        
        # Remove very dark pixels (shadows) but keep bright pixels for fair skin detection
        brightness = np.mean(all_pixels, axis=1)
        valid_mask = brightness > 30  # Only remove very dark pixels
        valid_pixels = all_pixels[valid_mask]
        
        if len(valid_pixels) < 10:
            valid_pixels = all_pixels
        
        # Calculate average
        avg_rgb = tuple(map(int, np.mean(valid_pixels, axis=0)))
        r, g, b = avg_rgb
        
        # Classify skin tone
        skin_tone, tone_conf = classify_skin_tone_from_rgb(r, g, b)
        
        # Classify undertone
        undertone, undertone_conf = classify_undertone_from_rgb(r, g, b)
        
        # Combined confidence
        confidence = (tone_conf + undertone_conf) / 2
        
        return SkinToneResult(
            skin_tone=skin_tone,
            undertone=undertone,
            avg_rgb=avg_rgb,
            confidence=confidence,
            face_detected=True,
            error=None
        ).to_dict()
        
    except Exception as e:
        print(f"❌ MediaPipe face detection error: {e}")
        import traceback
        traceback.print_exc()
        # Fall back to image-based analysis
        return _fallback_skin_tone_from_image(image_rgb)


def load_skin_tone_recommendations(skin_tone: str, undertone: str) -> Dict:
    """
    Load color recommendations for a skin tone + undertone combination.
    
    Args:
        skin_tone: "Fair", "Medium", or "Dark"
        undertone: "Warm", "Cool", or "Neutral"
        
    Returns:
        Dictionary with best colors, colors to avoid, and metal recommendations
    """
    key = f"{skin_tone}_{undertone}"
    
    try:
        with open(SKIN_TONE_PALETTE_PATH, 'r') as f:
            palettes = json.load(f)
            return palettes.get(key, {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "best_colors": [],
            "avoid": [],
            "metal": [],
            "description": "No recommendations available"
        }


def get_full_profile_recommendations(skin_tone: str, undertone: str) -> Dict:
    """
    Get comprehensive recommendations for skin tone profile.
    
    Args:
        skin_tone: Skin tone label
        undertone: Undertone label
        
    Returns:
        Complete recommendations dictionary
    """
    recommendations = load_skin_tone_recommendations(skin_tone, undertone)
    
    return {
        "skin_tone": skin_tone,
        "undertone": undertone,
        "profile_name": f"{skin_tone}-{undertone}",
        "best_colors": recommendations.get("best_colors", []),
        "colors_to_avoid": recommendations.get("avoid", []),
        "recommended_metals": recommendations.get("metal", []),
        "description": recommendations.get("description", "")
    }


# ✅ backend/ml/skin_tone.py generated — Adorkable AI
