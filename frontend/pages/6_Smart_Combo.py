"""
Adorkable AI - Smart Combo Page

Find matching garments that work with a selected item.
"""

import sys
from pathlib import Path

import streamlit as st
import httpx

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from ui_styles import inject_app_theme

st.set_page_config(page_title="Smart Combo - Adorkable AI", page_icon="🎯")

inject_app_theme()

API_BASE = "http://localhost:8006/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# =============================================================================
# Auth Check
# =============================================================================

def check_auth():
    if "user_token" not in st.session_state or not st.session_state.user_token:
        st.error("Please log in first")
        st.stop()


check_auth()


# =============================================================================
# API Functions
# =============================================================================

def get_wardrobe():
    """Fetch wardrobe."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/wardrobe/", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching wardrobe: {e}")
        return []


def get_combos(item_id, occasion, style_pref, weather_override=None):
    """Get outfit combos for selected item."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        
        params = {
            "occasion": occasion,
            "style_pref": style_pref
        }
        
        if weather_override is not None:
            params["weather_override"] = weather_override
        
        response = httpx.get(
            f"{API_BASE}/combo/{item_id}",
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Failed to get combos")}
    except Exception as e:
        return {"error": str(e)}


def resolve_image_path(path_str: str) -> str:
    if not path_str:
        return path_str
    p = Path(path_str)
    if p.is_absolute():
        return str(p)
    return str(PROJECT_ROOT / p)


def safe_image(image_path: str):
    resolved = resolve_image_path(image_path)
    if resolved and Path(resolved).exists():
        st.image(resolved, width="stretch")
    else:
        st.caption("Image missing")


# =============================================================================
# UI
# =============================================================================

def main():
    st.title("🎯 Smart Combo")
    st.subheader("Find the Perfect Match for Your Garment")
    
    # Fetch wardrobe
    wardrobe = get_wardrobe()
    
    if not wardrobe:
        st.info("Your wardrobe is empty. Upload some garments first!")
        if st.button("Go to My Wardrobe"):
            st.switch_page("pages/3_My_Wardrobe.py")
        return
    
    # Sidebar - Selection and filters
    with st.sidebar:
        st.header("Combo Settings")
        
        occasion = st.selectbox(
            "Occasion",
            ["Casual", "Formal", "Academic", "Business", "Party", "Date Night"]
        )
        
        style_pref = st.radio(
            "Style Preference",
            ["Western", "Eastern"]
        )
        
        use_weather = st.checkbox("Override Weather")
        weather_override = None
        if use_weather:
            weather_override = st.slider("Temperature (°C)", -10, 45, 22)
    
    # Main content
    st.markdown("### Select a Garment")
    st.caption("Click on a garment to find matching combinations")
    
    # Create garment grid
    cols = st.columns(4)
    
    selected_item = None
    
    for i, garment in enumerate(wardrobe):
        with cols[i % 4]:
            with st.container():
                # Show image
                try:
                    safe_image(garment.get("image_path"))
                except:
                    st.markdown(f"📷 {garment.get('category', 'Item')}")
                
                # Show details
                st.caption(f"{garment.get('dominant_color', 'Unknown')} {garment.get('category', 'Item')}")
                
                # Select button
                if st.button("Select", key=f"select_{garment['id']}", use_container_width=True):
                    st.session_state.selected_item_id = garment['id']
                    st.session_state.selected_item = garment
                    st.rerun()
    
    # Check if item selected
    if "selected_item_id" in st.session_state and st.session_state.selected_item_id:
        selected_item = st.session_state.get("selected_item")
        selected_id = st.session_state.selected_item_id
        
        st.markdown("---")
        st.header("Selected Item")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if selected_item:
                try:
                    safe_image(selected_item.get("image_path"))
                except:
                    st.markdown(f"📷 {selected_item.get('category', 'Item')}")
                
                st.markdown(f"**{selected_item.get('dominant_color', 'Unknown')} {selected_item.get('category', 'Item')}**")
        
        with col2:
            if st.button("🎯 Find Matches", type="primary", use_container_width=True):
                with st.spinner("Finding perfect matches..."):
                    result = get_combos(selected_id, occasion, style_pref, weather_override)
                
                if result.get("error"):
                    st.error(f"❌ {result['error']}")
                else:
                    st.success(f"✅ Found {result.get('total_combos', 0)} matching combinations!")
                    
                    combos = result.get("combos", [])
                    
                    if combos:
                        st.markdown("---")
                        st.markdown("### Matching Outfits")
                        
                        for i, combo in enumerate(combos[:5]):  # Show top 5
                            with st.expander(f"Outfit #{i+1} - Score: {combo.get('score', 0):.1f}", expanded=i==0):
                                
                                # Show hijab first if present (for female users)
                                if combo.get("hijab"):
                                    st.markdown("🧕 **Hijab:** " + combo["hijab"].get('dominant_color', 'Unknown'))
                                    try:
                                        safe_image(combo["hijab"].get("image_path"), width=100)
                                    except:
                                        pass
                                    st.markdown("---")
                                
                                # Show combo items
                                ccols = st.columns(4)
                                
                                items = [
                                    ("top", "👕 Top"),
                                    ("bottom", "👖 Bottom"),
                                    ("dress", "👗 Dress"),
                                    ("outerwear", "🧥 Outerwear")
                                ]
                                
                                for idx, (key, label) in enumerate(items):
                                    item = combo.get(key)
                                    with ccols[idx]:
                                        if item:
                                            try:
                                                safe_image(item.get("image_path"))
                                            except:
                                                st.markdown(f"📷 {label}")
                                            
                                            st.caption(f"{item.get('dominant_color', 'Unknown')}")
                                            st.caption(f"{item.get('category', 'Item')}")
                                        else:
                                            st.caption(f"No {label}")
                                
                                # Why this works
                                st.markdown("---")
                                st.markdown("**Why This Works:**")
                                st.write(combo.get("why_this_suits_you", ""))
                                
                                # Score breakdown
                                st.markdown("**Score Breakdown:**")
                                scol1, scol2, scol3 = st.columns(3)
                                
                                with scol1:
                                    st.caption(f"Color: {combo.get('color_harmony', 0):.0%}")
                                    st.caption(f"Skin: {combo.get('skin_flattery', 0):.0%}")
                                
                                with scol2:
                                    st.caption(f"Body: {combo.get('body_shape_score', 0):.0%}")
                                    st.caption(f"Weather: {combo.get('weather_score', 0):.0%}")
                                
                                with scol3:
                                    st.caption(f"Occasion: {combo.get('occasion_score', 0):.0%}")
                                    if combo.get("trending"):
                                        st.caption("🔥 Trending")
                    else:
                        st.info("No matching combinations found. Try adjusting your filters!")
        
        if st.button("🔄 Choose Different Garment"):
            st.session_state.selected_item_id = None
            st.session_state.selected_item = None
            st.rerun()


if __name__ == "__main__":
    main()


# ✅ frontend/pages/6_Smart_Combo.py generated — Adorkable AI
