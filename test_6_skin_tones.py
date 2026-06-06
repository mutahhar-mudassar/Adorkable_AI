#!/usr/bin/env python3
"""Test 6 skin tone classifications with different brightness levels"""
import sys
sys.path.insert(0, 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai')

import cv2
import numpy as np
from backend.ml.skin_tone import analyze_skin_tone, classify_skin_tone_from_rgb
import os

test_dir = 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai/test_images'
os.makedirs(test_dir, exist_ok=True)

def create_face_image(skin_rgb, filename):
    """Create a test face image with given skin tone"""
    img = np.ones((400, 400, 3), dtype=np.uint8) * 240
    
    # Face oval with given skin tone
    cv2.ellipse(img, (200, 200), (100, 130), 0, 0, 360, skin_rgb, -1)
    
    # Eyes
    cv2.circle(img, (160, 170), 12, (40, 40, 40), -1)
    cv2.circle(img, (240, 170), 12, (40, 40, 40), -1)
    
    # Nose
    cv2.line(img, (200, 180), (200, 220), (skin_rgb[0]-20, skin_rgb[1]-20, skin_rgb[2]-20), 3)
    
    # Mouth
    cv2.ellipse(img, (200, 250), (30, 15), 0, 0, 180, (120, 60, 60), 3)
    
    # Add skin texture
    for i in range(100):
        x = np.random.randint(100, 300)
        y = np.random.randint(100, 320)
        if np.sqrt((x-200)**2 + (y-200)**2) < 100:
            variation = np.random.randint(-15, 15)
            color = (
                max(0, min(255, skin_rgb[0] + variation)),
                max(0, min(255, skin_rgb[1] + variation)),
                max(0, min(255, skin_rgb[2] + variation))
            )
            img[y, x] = color
    
    path = os.path.join(test_dir, filename)
    cv2.imwrite(path, img)
    return path

# Test all 6 skin tone brightness levels
print("="*70)
print("TESTING 6 SKIN TONE CLASSIFICATIONS")
print("="*70)

test_cases = [
    ("1. Very Fair", (235, 210, 195), 220, "Very Fair"),    # Brightness ~213
    ("2. Fair", (220, 190, 180), 197, "Fair"),              # Brightness ~197
    ("3. Light Medium", (200, 165, 150), 172, "Light Medium"), # Brightness ~172
    ("4. Medium", (170, 135, 120), 142, "Medium"),         # Brightness ~142
    ("5. Medium Dark", (140, 105, 90), 112, "Medium Dark"), # Brightness ~112
    ("6. Dark", (100, 75, 65), 80, "Dark"),                # Brightness ~80
]

results = []
for name, skin_rgb, expected_brightness, expected_tone in test_cases:
    path = create_face_image(skin_rgb, f"{name.replace(' ', '_').lower()}.jpg")
    result = analyze_skin_tone(path)
    
    actual_rgb = result['avg_rgb']
    actual_brightness = sum(actual_rgb) / 3
    actual_tone = result['skin_tone']
    
    results.append((name, expected_tone, actual_tone, actual_brightness))
    
    print(f"\n{name}:")
    print(f"  Expected: {expected_tone} (brightness ~{expected_brightness})")
    print(f"  Detected: {actual_tone} (brightness {actual_brightness:.1f})")
    print(f"  RGB: {actual_rgb}")
    print(f"  Face detected: {result['face_detected']}")
    print(f"  Confidence: {result['confidence']}")
    
    if actual_tone == expected_tone:
        print(f"  ✅ CORRECT")
    else:
        print(f"  ❌ WRONG (expected {expected_tone}, got {actual_tone})")

print("\n" + "="*70)
print("SUMMARY - All 6 skin tones should be different")
print("="*70)
print(f"{'Test':<20} {'Expected':<15} {'Detected':<15} {'Status':<10}")
print("-"*70)

all_correct = True
for name, expected, actual, brightness in results:
    status = "✅ PASS" if expected == actual else "❌ FAIL"
    if expected != actual:
        all_correct = False
    print(f"{name:<20} {expected:<15} {actual:<15} {status:<10}")

print("="*70)
tones = [r[2] for r in results]
unique_tones = len(set(tones))
print(f"\nUnique skin tones detected: {unique_tones}/6")

if all_correct and unique_tones == 6:
    print("\n🎉 SUCCESS! All 6 skin tones correctly classified!")
    sys.exit(0)
else:
    print(f"\n❌ Some classifications incorrect. Got: {tones}")
    sys.exit(1)
