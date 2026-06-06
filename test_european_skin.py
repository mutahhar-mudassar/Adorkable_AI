#!/usr/bin/env python3
"""Test European white skin tones with relaxed thresholds"""
import sys
sys.path.insert(0, 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai')

import cv2
import numpy as np
from backend.ml.skin_tone import analyze_skin_tone
import os

test_dir = 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai/test_images'
os.makedirs(test_dir, exist_ok=True)

def create_face_image(skin_rgb, filename):
    img = np.ones((400, 400, 3), dtype=np.uint8) * 240
    cv2.ellipse(img, (200, 200), (100, 130), 0, 0, 360, skin_rgb, -1)
    cv2.circle(img, (160, 170), 12, (40, 40, 40), -1)
    cv2.circle(img, (240, 170), 12, (40, 40, 40), -1)
    cv2.line(img, (200, 180), (200, 220), (skin_rgb[0]-20, skin_rgb[1]-20, skin_rgb[2]-20), 3)
    cv2.ellipse(img, (200, 250), (30, 15), 0, 0, 180, (120, 60, 60), 3)
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

# Test European white skin tones (various brightness levels)
test_cases = [
    ('Northern_European_Porcelain', (225, 200, 185), 203, 'Very Fair'),
    ('Central_European_Fair', (195, 175, 160), 177, 'Fair'),
    ('Southern_European_Light', (175, 155, 140), 157, 'Fair'),
    ('Mediterranean_Olive', (150, 135, 115), 133, 'Light Medium'),
    ('Mixed_European_Tan', (140, 120, 100), 120, 'Medium'),
    ('Dark_European', (100, 85, 75), 87, 'Medium Dark'),
]

print('='*70)
print('EUROPEAN SKIN TONE TEST - RELAXED THRESHOLDS')
print('='*70)

results = []
for name, skin_rgb, expected_brightness, expected_tone in test_cases:
    filename = 'euro_' + name.lower() + '.jpg'
    path = create_face_image(skin_rgb, filename)
    result = analyze_skin_tone(path)
    
    actual_rgb = result['avg_rgb']
    actual_brightness = sum(actual_rgb) / 3
    actual_tone = result['skin_tone']
    
    results.append((name, expected_tone, actual_tone, actual_brightness))
    
    status = 'OK' if actual_tone == expected_tone else 'WRONG'
    print('\n[' + status + '] ' + name.replace('_', ' '))
    print('   Expected: ' + expected_tone + ' (brightness ~' + str(expected_brightness) + ')')
    print('   Detected: ' + actual_tone + ' (brightness ' + str(round(actual_brightness, 1)) + ')')

print('\n' + '='*70)
print('SUMMARY')
print('='*70)
correct = sum(1 for _, exp, act, _ in results if exp == act)
print('Correct: ' + str(correct) + '/' + str(len(results)))

# Show what we got
tones = [r[2] for r in results]
print('\nDetected tones: ' + str(tones))

if correct == len(results):
    print('\nSUCCESS! All European skin tones classified correctly!')
else:
    print('\nSome classifications need adjustment.')
