"""
Script to add target_gender field to preloaded wardrobe items
Run this after manually categorizing your items as male/female/unisex
"""

import json

# Load the current wardrobe
with open('backend/data/preloaded_wardrobe.json', 'r') as f:
    data = json.load(f)

items = data.get('items', [])

print(f"Total items: {len(items)}")
print("\nCurrent items without target_gender:")
for i, item in enumerate(items):
    gender = item.get('target_gender', 'NOT SET')
    print(f"{i+1}. {item.get('title', 'Unknown')} - {gender}")

print("\n" + "="*60)
print("INSTRUCTIONS:")
print("="*60)
print("""
You need to add 'target_gender' field to each item in the JSON file.

Valid values:
- "male"      - For men's clothing
- "female"    - For women's clothing  
- "unisex"    - For clothing that works for both

Example edit in preloaded_wardrobe.json:
{
  "id": "starter_white_shirt",
  "title": "White Shirt",
  "target_gender": "male",     <-- ADD THIS LINE
  "category": "top",
  ...
}

Quick categorization guide:
- Dresses, skirts, blouses → "female"
- Men's suits, ties, dress shirts → "male"
- T-shirts, jeans, sneakers → "unisex"
- Hijabs, abayas → "female"
""")

# Let user input gender for each item
print("\n" + "="*60)
print("QUICK SETUP MODE")
print("="*60)
print("I'll help you set target_gender for each item.\n")

updated_items = []
for item in items:
    title = item.get('title', 'Unknown')
    current = item.get('target_gender', 'NOT SET')
    
    print(f"\nItem: {title}")
    print(f"Category: {item.get('category', 'unknown')}")
    print(f"Current gender: {current}")
    
    # Auto-suggest based on category
    category = item.get('category', '').lower()
    tradition = item.get('tradition', '').lower()
    
    suggested = 'unisex'  # default
    if category in ['dress']:
        suggested = 'female'
    elif category in ['hijab', 'abaya', 'salwar', 'kameez']:
        suggested = 'female'
    elif 'men' in title.lower() or 'mens' in title.lower():
        suggested = 'male'
    elif 'women' in title.lower() or 'womens' in title.lower():
        suggested = 'female'
    
    print(f"Suggested: {suggested}")
    
    # For now, auto-assign based on suggestions
    # In real use, you would manually edit the JSON
    item['target_gender'] = suggested
    updated_items.append(item)
    print(f"✓ Set to: {suggested}")

# Save updated file
with open('backend/data/preloaded_wardrobe.json', 'w') as f:
    json.dump({'items': updated_items}, f, indent=2)

print("\n" + "="*60)
print("✅ COMPLETE!")
print("="*60)
print(f"\nUpdated {len(updated_items)} items with target_gender field.")
print("File saved: backend/data/preloaded_wardrobe.json")
print("\nSummary:")
male_count = sum(1 for i in updated_items if i.get('target_gender') == 'male')
female_count = sum(1 for i in updated_items if i.get('target_gender') == 'female')
unisex_count = sum(1 for i in updated_items if i.get('target_gender') == 'unisex')
print(f"  Male: {male_count}")
print(f"  Female: {female_count}")
print(f"  Unisex: {unisex_count}")
