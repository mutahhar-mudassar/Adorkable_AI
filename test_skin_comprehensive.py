#!/usr/bin/env python3
"""Comprehensive skin tone test with synthetic images"""
import sys
sys.path.insert(0, 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai')

import cv2
import numpy as np
from backend.ml.skin_tone import analyze_skin_tone
import os

test_dir = 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai/test_images'
os.makedirs(test_dir, exist_ok=True)

def create_face_image(skin_rgb, filename):
    """Create a realistic face image with given skin tone"""
    img = np.ones((400, 400, 3), dtype=np.uint8) * 240
    
    # Face oval with given skin tone
    cv2.ellipse(img, (200, 200), (100, 130), 0, 0, 360, skin_rgb, -1)
    
    # Eyes
    cv2.circle(img, (160, 170), 12, (40, 40, 40), -1)
    cv2.circle(img, (240, 170), 12, (40, 40, 40), -1)
    
    # Eye highlights
    cv2.circle(img, (163, 167), 4, (255, 255, 255), -1)
    cv2.circle(img, (243, 167), 4, (255, 255, 255), -1)
    
    # Nose
    cv2.line(img, (200, 180), (200, 220), (skin_rgb[0]-15, skin_rgb[1]-15, skin_rgb[2]-15), 3)
    
    # Mouth
    cv2.ellipse(img, (200, 250), (30, 15), 0, 0, 180, (180, 80, 80), 3)
    
    # Add realistic skin texture and variation
    for i in range(200):
        x = np.random.randint(100, 300)
        y = np.random.randint(100, 320)
        dist = np.sqrt((x-200)**2 + (y-200)**2)
        if dist < 95:  # Within face
            variation = np.random.randint(-20, 20)
            color = (
                max(0, min(255, skin_rgb[0] + variation)),
                max(0, min(255, skin_rgb[1] + variation)),
                max(0, min(255, skin_rgb[2] + variation))
            )
            img[y, x] = color
    
    path = os.path.join(test_dir, filename)
    cv2.imwrite(path, img)
    return path

# Create test images for all 6 skin tones
test_cases = [
    ('very_fair_porcelain', (230, 210, 195), 'Very Fair'),      # Brightness ~212
    ('very_fair_ivory', (210, 190, 175), 'Very Fair'),          # Brightness ~192
    ('fair_light', (190, 170, 155), 'Fair'),                    # Brightness ~172
    ('fair_peach', (175, 155, 140), 'Fair'),                    # Brightness ~157
    ('light_medium_olive', (155, 135, 120), 'Light Medium'),    # Brightness ~137
    ('light_medium_tan', (140, 120, 105), 'Light Medium'),      # Brightness ~122
    ('medium_golden', (125, 105, 90), 'Medium'),                # Brightness ~107
    ('medium_brown', (110, 90, 75), 'Medium'),                   # Brightness ~92
    ('medium_dark_caramel', (95, 75, 60), 'Medium Dark'),       # Brightness ~77
    ('medium_dark_rich', (80, 60, 50), 'Medium Dark'),          # Brightness ~63
    ('dark_deep', (65, 45, 35), 'Dark'),                        # Brightness ~48
    ('dark_rich', (50, 35, 25), 'Dark'),                       # Brightness ~37
]

print('='*80)
print('COMPREHENSIVE SKIN TONE TEST - ALL 6 TYPES')
print('='*80)

results = []
for name, skin_rgb, expected_tone in test_cases:
    path = create_face_image(skin_rgb, f'{name}.jpg')
    result = analyze_skin_tone(path)
    
    actual_rgb = result['avg_rgb']
    actual_brightness = sum(actual_rgb) / 3
    actual_tone = result['skin_tone']
    face_detected = result['face_detected']
    
    results.append((name, expected_tone, actual_tone, actual_brightness, face_detected))
    
    status = '✅' if actual_tone == expected_tone else '❌'
    print(f'\n{status} {name.replace("_", " ").title()}')
    print(f'   Expected: {expected_tone} (RGB: {skin_rgb}, brightness: {sum(skin_rgb)/3:.0f})')
    print(f'   Detected: {actual_tone} (RGB: {actual_rgb}, brightness: {actual_brightness:.1f})')
    print(f'   Face detected: {face_detected}')

print('\n' + '='*80)
print('SUMMARY')
print('='*80)
correct = sum(1 for _, exp, act, _, _ in results if exp == act)
print(f'Correct: {correct}/{len(results)}')

print('\nBreakdown by expected type:')
for expected in ['Very Fair', 'Fair', 'Light Medium', 'Medium', 'Medium Dark', 'Dark']:
    type_results = [(n, e, a, b, f) for n, e, a, b, f in results if e == expected]
    if type_results:
        correct_for_type = sum(1 for _, e, a, _, _ in type_results if e == a)
        print(f'  {expected}: {correct_for_type}/{len(type_results)} correct')
        for name, _, actual, brightness, _ in type_results:
            if actual != expected:
                print(f'    ❌ {name}: got {actual} at brightness {brightness:.1f}')

print('\nDetected tones:')
for name, expected, actual, brightness, _ in results:
    print(f'  {name:<25} -> {actual:<12} (brightness: {brightness:>6.1f})')
