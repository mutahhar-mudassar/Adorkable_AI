
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import math

import cv2
import numpy as np

# MediaPipe import - Tasks API for version 0.10+
MEDIAPIPE_AVAILABLE = False
POSE_LANDMARKER = None

try:
    import mediapipe as mp
    from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions
    from mediapipe import Image, ImageFormat
    import os
    
    # Model path
    model_path = os.path.join(os.path.dirname(__file__), "models", "pose_landmarker_full.task")
    
    # Download model if not exists
    if not os.path.exists(model_path):
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        print(f"Downloading pose landmarker model...")
        import urllib.request
        url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
        urllib.request.urlretrieve(url, model_path)
        print("✅ Model downloaded!")
    
    # Create landmarker with model
    base_options = mp.tasks.BaseOptions(model_asset_path=model_path)
    options = PoseLandmarkerOptions(
        base_options=base_options,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        num_poses=1
    )
    POSE_LANDMARKER = PoseLandmarker.create_from_options(options)
    MEDIAPIPE_AVAILABLE = True
    print("✅ MediaPipe PoseLandmarker initialized!")
    
except Exception as e:
    print(f"MediaPipe PoseLandmarker not available: {e}")
    POSE_LANDMARKER = None
    MEDIAPIPE_AVAILABLE = False

# Landmark indices (MediaPipe Pose standard indices)
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
NOSE = 0

from backend.config import BODY_SHAPES, BODY_SHAPE_RULES
from backend.utils.image_utils import resolve_stored_image_path


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BodyShapeResult:
    """Result of body shape analysis."""
    body_shape: str
    shoulder_width: float
    hip_width: float
    waist_width: Optional[float]
    ratio: float
    confidence: float
    pose_detected: bool
    landmarks: Optional[List[Dict]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "body_shape": self.body_shape,
            "shoulder_width": self.shoulder_width,
            "hip_width": self.hip_width,
            "waist_width": self.waist_width,
            "ratio": self.ratio,
            "confidence": self.confidence,
            "pose_detected": self.pose_detected,
            "error": self.error
        }


# =============================================================================
# Landmark Extraction
# =============================================================================

def get_landmark_coordinates(
    landmarks: List,
    landmark_idx: int,
    image_width: int,
    image_height: int
) -> Optional[Tuple[float, float, float]]:
    """
    Get x, y, z coordinates for a landmark.
    
    Args:
        landmarks: List of MediaPipe NormalizedLandmark (Tasks API)
        landmark_idx: Landmark index
        image_width: Image width in pixels
        image_height: Image height in pixels
        
    Returns:
        Tuple of (x, y, z) in pixel coordinates, or None if not visible
    """
    # Tasks API: landmarks is a list of landmark objects
    if landmark_idx >= len(landmarks):
        return None
    
    landmark = landmarks[landmark_idx]
    
    # Check visibility (MediaPipe provides visibility score)
    if hasattr(landmark, 'visibility') and landmark.visibility < 0.5:
        return None
    
    x = landmark.x * image_width
    y = landmark.y * image_height
    z = landmark.z if hasattr(landmark, 'z') else 0.0  # Relative depth
    
    return (x, y, z)


def calculate_distance_2d(p1: Tuple[float, ...], p2: Tuple[float, ...]) -> float:
    """
    Calculate 2D Euclidean distance between two points.
    
    Args:
        p1, p2: Points with at least x, y coordinates
        
    Returns:
        Euclidean distance
    """
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def calculate_width_at_y(
    landmarks,
    target_y: float,
    image_width: int,
    image_height: int
) -> Optional[float]:
    """
    Estimate width at a specific Y level using pose landmarks.
    
    Args:
        landmarks: MediaPipe landmarks
        target_y: Target Y coordinate
        image_width: Image width
        image_height: Image height
        
    Returns:
        Estimated width, or None if cannot calculate
    """
    # Get all visible body landmarks
    body_landmarks = [
        LEFT_SHOULDER, RIGHT_SHOULDER,
        LEFT_HIP, RIGHT_HIP,
        LEFT_ELBOW, RIGHT_ELBOW,
        LEFT_WRIST, RIGHT_WRIST
    ]
    
    points_at_y = []
    
    for idx in body_landmarks:
        coords = get_landmark_coordinates(landmarks, idx, image_width, image_height)
        if coords:
            # Check if near target Y (within 10% of body height tolerance)
            if abs(coords[1] - target_y) < image_height * 0.1:
                points_at_y.append(coords)
    
    if len(points_at_y) < 2:
        return None
    
    # Calculate width as max horizontal distance
    xs = [p[0] for p in points_at_y]
    return max(xs) - min(xs)


# =============================================================================
# Body Shape Classification
# =============================================================================

def classify_body_shape(
    shoulder_width: float,
    hip_width: float,
    waist_width: Optional[float] = None,
    torso_height: Optional[float] = None
) -> Tuple[str, float]:
    """
    Classify body shape from pose-derived widths.

    Shoulders are often over-estimated vs hips in 2D photos; we calibrate
    slightly before ratios. Strong V-shape vs moderate V-shape is split into
    Inverted Triangle vs Athletic. Apple uses waist-to-hip cues when balanced.
    """
    if hip_width <= 0:
        hip_width = max(shoulder_width, 1.0)

    eff_shoulder = shoulder_width * 0.93
    ratio = eff_shoulder / hip_width

    waist_ratio = None
    if waist_width is not None and eff_shoulder > 0:
        waist_ratio = waist_width / eff_shoulder
    waist_to_hip = None
    if waist_width is not None and hip_width > 0:
        waist_to_hip = waist_width / hip_width

    WIDE_STRONG = 1.22
    WIDE_MOD = 1.10
    NARROW = 0.88
    BAL_MIN = 0.90
    BAL_MAX = 1.10
    DEFINED_WAIST = 0.76

    if (
        waist_width is not None
        and waist_to_hip is not None
        and 0.90 <= ratio <= 1.08
        and waist_to_hip >= 0.97
        and (waist_ratio is None or waist_ratio >= 0.78)
    ):
        conf = min(0.9, 0.72 + max(0.0, waist_to_hip - 0.97) * 2.0)
        return "Apple", conf

    if ratio >= WIDE_STRONG:
        return "Inverted Triangle", min(
            0.95, 0.7 + (ratio - WIDE_STRONG) * 0.45
        )
    if ratio >= WIDE_MOD:
        return "Athletic", min(0.9, 0.65 + (ratio - WIDE_MOD) * 0.55)

    if ratio <= NARROW:
        return "Pear", min(0.95, 0.7 + (NARROW - ratio) * 0.5)

    if BAL_MIN <= ratio <= BAL_MAX:
        if waist_ratio is not None and waist_ratio < DEFINED_WAIST:
            return "Hourglass", 0.85
        return "Rectangle", 0.80

    if ratio > 1.0:
        return "Athletic", 0.58
    return "Pear", 0.58


# =============================================================================
# Main Analysis
# =============================================================================

def analyze_body_shape(body_photo_path: str) -> Dict:
    """
    Analyze body shape from a full-body photo.
    
    Process:
        1. Load image with OpenCV
        2. Run MediaPipe Pose detection
        3. Extract key landmarks (shoulders, hips)
        4. Calculate width measurements
        5. Classify body shape based on ratios
    
    Args:
        body_photo_path: Path to full-body photo
        
    Returns:
        Dictionary with body shape analysis results:
        {
            "body_shape": "Hourglass|Pear|Inverted Triangle|Rectangle|Apple|Athletic",
            "shoulder_width": float,
            "hip_width": float,
            "waist_width": float or null,
            "ratio": float,
            "confidence": float,
            "pose_detected": bool,
            "error": str or null
        }
        
    Example:
        >>> result = analyze_body_shape("fullbody.jpg")
        >>> print(f"Body shape: {result['body_shape']}")
        Body shape: Hourglass
    """
    # Load image
    image = cv2.imread(resolve_stored_image_path(body_photo_path))
    if image is None:
        return BodyShapeResult(
            body_shape="Unknown",
            shoulder_width=0.0,
            hip_width=0.0,
            waist_width=None,
            ratio=1.0,
            confidence=0.0,
            pose_detected=False,
            error="Could not load image"
        ).to_dict()

    if not MEDIAPIPE_AVAILABLE or POSE_LANDMARKER is None:
        return BodyShapeResult(
            body_shape="Unknown",
            shoulder_width=0.0,
            hip_width=0.0,
            waist_width=None,
            ratio=1.0,
            confidence=0.0,
            pose_detected=False,
            error="MediaPipe not available for pose detection"
        ).to_dict()
    
    height, width = image.shape[:2]
    
    # Convert to RGB for MediaPipe
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    try:
        # Create MediaPipe Image (Tasks API)
        mp_image = Image(image_format=ImageFormat.SRGB, data=image_rgb)
        
        # Run pose detection with Tasks API
        detection_result = POSE_LANDMARKER.detect(mp_image)
        
        # Check if any poses were detected
        if not detection_result.pose_landmarks:
            return BodyShapeResult(
                body_shape="Unknown",
                shoulder_width=0.0,
                hip_width=0.0,
                waist_width=None,
                ratio=1.0,
                confidence=0.0,
                pose_detected=False,
                error="No pose detected - ensure full body is visible"
            ).to_dict()
        
        print(f"✅ Pose detected! Found {len(detection_result.pose_landmarks)} pose(s)")
        
        # Get the first detected pose landmarks
        landmarks = detection_result.pose_landmarks[0]  # List of 33 landmarks
        
        # Get shoulder coordinates
        left_shoulder = get_landmark_coordinates(landmarks, LEFT_SHOULDER, width, height)
        right_shoulder = get_landmark_coordinates(landmarks, RIGHT_SHOULDER, width, height)
        
        # Get hip coordinates
        left_hip = get_landmark_coordinates(landmarks, LEFT_HIP, width, height)
        right_hip = get_landmark_coordinates(landmarks, RIGHT_HIP, width, height)
        
        # Check if all key landmarks are detected
        if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
            return BodyShapeResult(
                body_shape="Unknown",
                shoulder_width=0.0,
                hip_width=0.0,
                waist_width=None,
                ratio=1.0,
                confidence=0.0,
                pose_detected=True,
                error="Could not detect all required body landmarks"
            ).to_dict()
        
        # Calculate widths
        shoulder_width = calculate_distance_2d(left_shoulder, right_shoulder)
        hip_width = calculate_distance_2d(left_hip, right_hip)
        
        # Estimate waist position (midpoint between shoulders and hips)
        shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
        hip_y = (left_hip[1] + right_hip[1]) / 2
        estimated_waist_y = (shoulder_y + hip_y) / 2
        
        # Try to calculate waist width
        waist_width = calculate_width_at_y(landmarks, estimated_waist_y, width, height)
        
        # Calculate torso height for scale
        torso_height = abs(hip_y - shoulder_y)
        
        # Classify body shape
        body_shape, confidence = classify_body_shape(
            shoulder_width,
            hip_width,
            waist_width,
            torso_height
        )
        
        # Calculate ratio
        ratio = shoulder_width / hip_width if hip_width > 0 else 1.0
        
        return BodyShapeResult(
            body_shape=body_shape,
            shoulder_width=float(shoulder_width),
            hip_width=float(hip_width),
            waist_width=float(waist_width) if waist_width else None,
            ratio=float(ratio),
            confidence=float(confidence),
            pose_detected=True,
            error=None
        ).to_dict()
        
    except Exception as e:
        print(f"❌ MediaPipe pose detection error: {e}")
        import traceback
        traceback.print_exc()
        return BodyShapeResult(
            body_shape="Unknown",
            shoulder_width=0.0,
            hip_width=0.0,
            waist_width=None,
            ratio=1.0,
            confidence=0.0,
            pose_detected=False,
            error=f"Pose detection failed: {str(e)}"
        ).to_dict()


def get_body_shape_recommendations(body_shape: str) -> Dict:
    """
    Get style recommendations for a body shape.
    
    Args:
        body_shape: Body shape label
        
    Returns:
        Dictionary with style recommendations
    """
    if body_shape not in BODY_SHAPE_RULES:
        return {
            "best_silhouettes": [],
            "avoid": [],
            "description": "No recommendations available"
        }
    
    return BODY_SHAPE_RULES[body_shape]


def get_full_body_profile(body_shape: str) -> Dict:
    """
    Get comprehensive body shape profile.
    
    Args:
        body_shape: Body shape label
        
    Returns:
        Complete profile dictionary
    """
    recommendations = get_body_shape_recommendations(body_shape)
    
    return {
        "body_shape": body_shape,
        "best_silhouettes": recommendations.get("best_silhouettes", []),
        "avoid": recommendations.get("avoid", []),
        "description": recommendations.get("description", "")
    }


# =============================================================================
# Utilities
# =============================================================================

def visualize_body_analysis(
    image_path: str,
    output_path: Optional[str] = None
) -> np.ndarray:
    """
    Create visualization of body analysis with landmarks drawn.
    
    Args:
        image_path: Path to input image
        output_path: Optional path to save visualization
        
    Returns:
        Annotated image array
    """
    image = cv2.imread(resolve_stored_image_path(image_path))
    if image is None:
        return None

    if not MEDIAPIPE_AVAILABLE:
        return image
    
    height, width = image.shape[:2]
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        min_detection_confidence=0.5
    ) as pose:
        
        results = pose.process(image_rgb)
        
        if results.pose_landmarks:
            # Draw pose landmarks
            mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing.DrawingSpec(
                    color=(0, 255, 0),
                    thickness=2,
                    circle_radius=3
                ),
                connection_drawing_spec=mp_drawing.DrawingSpec(
                    color=(255, 0, 0),
                    thickness=2
                )
            )
    
    if output_path:
        cv2.imwrite(output_path, image)
    
    return image


# ✅ backend/ml/body_shape.py generated — Adorkable AI
