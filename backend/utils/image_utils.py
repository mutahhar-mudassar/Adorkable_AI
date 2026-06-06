"""
Adorkable AI Image Preprocessing Utilities

OpenCV and Pillow-based image processing helpers for garment classification,
background removal, and image storage.
"""

import os
import io
import uuid
from typing import Tuple, Optional
from datetime import datetime

import cv2
import numpy as np
from PIL import Image

from backend.config import UPLOAD_DIR, IMAGE_SIZE, BASE_DIR


# =============================================================================
# Path resolution (stored paths are relative to project / BASE_DIR)
# =============================================================================

def resolve_stored_image_path(image_path: str) -> str:
    """
    Turn DB-stored paths into an absolute path on disk.

    Saves use relpath from BASE_DIR so they work regardless of backend CWD.
    """
    if not image_path:
        return image_path
    normalized = image_path.replace("/", os.sep)
    if os.path.isabs(normalized) and os.path.exists(normalized):
        return normalized
    from_base = os.path.normpath(os.path.join(BASE_DIR, normalized))
    if os.path.exists(from_base):
        return from_base
    if os.path.exists(normalized):
        return os.path.normpath(normalized)
    return from_base


# =============================================================================
# Image Loading & Preprocessing
# =============================================================================

def load_and_preprocess(image_path: str, target_size: Tuple[int, int] = IMAGE_SIZE) -> np.ndarray:
    """
    Load an image and preprocess it for model inference.
    
    Steps:
        1. Read image from disk
        2. Convert BGR (OpenCV default) to RGB
        3. Resize to target dimensions
        4. Normalize pixel values to [0, 1]
    
    Args:
        image_path: Path to the image file
        target_size: Target dimensions (width, height), default (224, 224)
        
    Returns:
        Preprocessed image as numpy array with shape (H, W, 3) and dtype float32
        
    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If image cannot be loaded
    """
    # Load image
    img = cv2.imread(resolve_stored_image_path(image_path))
    if img is None:
        raise ValueError(f"Could not load image from {image_path}")
    
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Resize to target size
    img_resized = cv2.resize(img_rgb, target_size, interpolation=cv2.INTER_LINEAR)
    
    # Normalize to [0, 1]
    img_normalized = img_resized.astype(np.float32) / 255.0
    
    return img_normalized


def load_image_pil(image_path: str) -> Image.Image:
    """
    Load an image using PIL.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        PIL Image object
    """
    return Image.open(resolve_stored_image_path(image_path)).convert("RGB")


def preprocess_for_model(image: np.ndarray) -> np.ndarray:
    """
    Add batch dimension for model inference.
    
    Args:
        image: Preprocessed image array of shape (H, W, 3)
        
    Returns:
        Image array with batch dimension (1, H, W, 3)
    """
    return np.expand_dims(image, axis=0)


# =============================================================================
# Background Removal (GrabCut)
# =============================================================================

def remove_background_simple(image: np.ndarray) -> np.ndarray:
    """
    Remove background from an image using OpenCV GrabCut algorithm.
    
    This is a simplified approach that assumes the foreground (garment) is
    in the center of the image.
    
    Args:
        image: Input image as numpy array (H, W, 3), BGR or RGB
        
    Returns:
        Image with background removed (alpha channel or black background)
    """
    # Ensure image is in correct format
    if len(image.shape) == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    height, width = image.shape[:2]
    
    # Initialize mask
    mask = np.zeros((height, width), np.uint8)
    
    # Define rectangle for GrabCut (center 70% of image)
    rect = (
        int(width * 0.15), 
        int(height * 0.15), 
        int(width * 0.7), 
        int(height * 0.7)
    )
    
    # Background and foreground models
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    
    # Run GrabCut
    try:
        cv2.grabCut(
            image, 
            mask, 
            rect, 
            bgd_model, 
            fgd_model, 
            5,  # iterations
            cv2.GC_INIT_WITH_RECT
        )
        
        # Create mask: 0 and 2 are background, 1 and 3 are foreground
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # Apply mask to image
        result = image * mask2[:, :, np.newaxis]
        
        return result
    except Exception:
        # If GrabCut fails, return original image
        return image


def remove_background_advanced(image_path: str) -> np.ndarray:
    """
    Advanced background removal with better edge handling.
    
    Args:
        image_path: Path to the image
        
    Returns:
        Image with background removed
    """
    img = cv2.imread(resolve_stored_image_path(image_path))
    if img is None:
        raise ValueError(f"Could not load image: {image_path}")
    
    height, width = img.shape[:2]
    
    # Create initial mask
    mask = np.zeros((height, width), np.uint8)
    
    # Define foreground and background rectangles
    # Foreground: center area
    fg_rect = (
        int(width * 0.2),
        int(height * 0.2),
        int(width * 0.6),
        int(height * 0.6)
    )
    
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    
    # First pass with rectangle
    cv2.grabCut(img, mask, fg_rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
    
    # Create foreground mask
    mask_fg = np.where((mask == 1) | (mask == 3), 255, 0).astype('uint8')
    
    # Apply morphological operations to clean up
    kernel = np.ones((5, 5), np.uint8)
    mask_fg = cv2.morphologyEx(mask_fg, cv2.MORPH_CLOSE, kernel)
    mask_fg = cv2.morphologyEx(mask_fg, cv2.MORPH_OPEN, kernel)
    
    # Apply mask
    result = cv2.bitwise_and(img, img, mask=mask_fg)
    
    return result


# =============================================================================
# Image Storage
# =============================================================================

def ensure_directory(path: str) -> None:
    """
    Ensure a directory exists, create if not.
    
    Args:
        path: Directory path
    """
    os.makedirs(path, exist_ok=True)


def generate_unique_filename(extension: str = "jpg") -> str:
    """
    Generate a unique filename with timestamp and UUID.
    
    Args:
        extension: File extension without dot
        
    Returns:
        Unique filename string
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"{timestamp}_{unique_id}.{extension}"


def save_uploaded_image(
    file_bytes: bytes, 
    user_id: int, 
    filename: Optional[str] = None,
    category: str = "garment"
) -> str:
    """
    Save an uploaded image file to the user's garment directory.
    
    Args:
        file_bytes: Raw file bytes from upload
        user_id: User ID for directory organization
        filename: Optional custom filename (original name preserved for reference only)
        category: Subdirectory category (default: "garment")
        
    Returns:
        Relative path to saved image
    """
    # Create directory structure: uploads/{user_id}/garments/
    user_dir = os.path.join(UPLOAD_DIR, str(user_id), "garments")
    ensure_directory(user_dir)
    
    # Always generate unique filename to prevent overwrites
    # Try to determine extension from bytes first, then from filename
    ext = "jpg"  # default
    if file_bytes[:4] == b'\x89PNG':
        ext = "png"
    elif file_bytes[:2] == b'\xff\xd8':
        ext = "jpg"
    elif filename:
        # Extract extension from provided filename
        _, provided_ext = os.path.splitext(filename.lower())
        if provided_ext in ['.png', '.jpg', '.jpeg']:
            ext = provided_ext.lstrip('.')
            if ext == 'jpeg':
                ext = 'jpg'
    
    # Generate unique filename with timestamp and UUID
    unique_filename = generate_unique_filename(ext)
    
    # Full path
    file_path = os.path.join(user_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Stable path relative to app root (not process CWD)
    return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")


def save_profile_image(
    file_bytes: bytes,
    user_id: int,
    photo_type: str
) -> str:
    """
    Save a profile image (selfie or body photo).
    
    Args:
        file_bytes: Raw file bytes from upload
        user_id: User ID for directory organization
        photo_type: Either "selfie" or "body"
        
    Returns:
        Relative path to saved image
        
    Raises:
        ValueError: If photo_type is invalid
    """
    if photo_type not in ["selfie", "body"]:
        raise ValueError(f"Invalid photo_type: {photo_type}. Must be 'selfie' or 'body'")
    
    # Create directory: uploads/{user_id}/profile/
    profile_dir = os.path.join(UPLOAD_DIR, str(user_id), "profile")
    ensure_directory(profile_dir)
    
    # Determine extension
    ext = "jpg"
    if file_bytes[:4] == b'\x89PNG':
        ext = "png"
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{photo_type}_{timestamp}.{ext}"
    
    # Full path
    file_path = os.path.join(profile_dir, filename)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return os.path.relpath(file_path, BASE_DIR).replace("\\", "/")


def delete_image_file(image_path: str) -> bool:
    """
    Delete an image file from disk.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        abs_path = resolve_stored_image_path(image_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            return True
        return False
    except Exception:
        return False


# =============================================================================
# Image Analysis Helpers
# =============================================================================

def get_dominant_colors(image_path: str, n_colors: int = 5) -> list:
    """
    Get dominant colors from an image using k-means clustering.
    
    Args:
        image_path: Path to image
        n_colors: Number of dominant colors to extract
        
    Returns:
        List of RGB tuples
    """
    img = cv2.imread(resolve_stored_image_path(image_path))
    if img is None:
        return []
    
    # Convert to RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Reshape for clustering
    pixels = img.reshape((-1, 3))
    pixels = np.float32(pixels)
    
    # K-means clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Count occurrences
    _, counts = np.unique(labels, return_counts=True)
    
    # Sort by frequency
    sorted_indices = np.argsort(-counts)
    sorted_colors = centers[sorted_indices].astype(int)
    
    return [tuple(color) for color in sorted_colors]


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """
    Convert RGB tuple to hex color string.
    
    Args:
        rgb: RGB tuple (r, g, b)
        
    Returns:
        Hex color string (e.g., "#FF5733")
    """
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


# =============================================================================
# Validation
# =============================================================================

def is_valid_image(file_bytes: bytes) -> bool:
    """
    Check if bytes represent a valid image.
    
    Args:
        file_bytes: Raw bytes to check
        
    Returns:
        True if valid image, False otherwise
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
        return True
    except Exception:
        return False


def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """
    Get image dimensions without loading full image.
    
    Args:
        image_path: Path to image
        
    Returns:
        Tuple of (width, height)
    """
    with Image.open(resolve_stored_image_path(image_path)) as img:
        return img.size


# ✅ backend/utils/image_utils.py generated — Adorkable AI
