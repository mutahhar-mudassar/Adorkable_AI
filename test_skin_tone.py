#!/usr/bin/env python3
"""Test skin tone analysis with different skin colors"""
import sys
sys.path.insert(0, 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai')

import cv2
import numpy as np
from backend.ml.skin_tone import analyze_skin_tone
import os

test_dir = 'c:/Users/dell/Downloads/AI LAB PROJECT/adorkable_ai/test_images'

# Test the 3 images we created earlier
results = []
for name, filename in [('FAIR', 'fair_face.jpg'), ('MEDIUM', 'medium_face.jpg'), ('DARK', 'dark_face.jpg')]:
    path = os.path.join(test_dir, filename)
    print(f'\n--- Testing {name} ---')
    result = analyze_skin_tone(path)
    results.append((name, result))
    print(f"RGB: {result['avg_rgb']}")
    print(f"Skin Tone: {result['skin_tone']}")
    print(f"Undertone: {result['undertone']}")
    print(f"Face Detected: {result['face_detected']}")
    print(f"Confidence: {result['confidence']}")

print()
print('='*60)
print('SUMMARY - All 3 skin tones should be DIFFERENT')
print('='*60)
print(f"{'Type':<15} {'Skin Tone':<12} {'Undertone':<12} {'Status':<15}")
print('-'*60)
all_different = True
for name, result in results:
    tone = result.get('skin_tone', 'N/A')
    undertone = result.get('undertone', 'N/A')
    status = 'OK' if result.get('face_detected') else 'FAIL'
    print(f"{name:<15} {tone:<12} {undertone:<12} {status:<15}")

# Check if we got 3 different tones
tones = [r[1].get('skin_tone') for r in results]
print(f'\nDetected tones: {tones}')
if len(set(tones)) == 3:
    print('SUCCESS: All 3 skin tones detected as different!')
    sys.exit(0)
else:
    print('FAIL: Some skin tones are the same')
    sys.exit(1)
