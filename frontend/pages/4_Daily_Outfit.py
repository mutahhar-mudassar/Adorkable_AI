"""
Adorkable AI - Daily Outfit Page

Generate daily outfit recommendations.
"""

import sys
from pathlib import Path

import streamlit as st
import httpx
import plotly.graph_objects as go

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from ui_styles import inject_app_theme

st.set_page_config(page_title="Daily Outfit - Adorkable AI", page_icon="💜", layout="wide")

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

def get_daily_outfit(occasion, style_pref, weather_override=None, reimagine_step=0):
    """Get daily outfit recommendation."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        
        data = {
            "occasion": occasion,
            "style_pref": style_pref,
            "weather_override": weather_override,
            "reimagine_step": reimagine_step,
        }
        
        response = httpx.post(
            f"{API_BASE}/recommend/daily",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Failed to generate outfit")}
    except Exception as e:
        return {"error": str(e)}


def resolve_image_path(path_str: str) -> str:
    if not path_str:
        return path_str
    p = Path(path_str)
    if p.is_absolute():
        return str(p)
    return str(PROJECT_ROOT / p)


# =============================================================================
# UI
# =============================================================================

def render_outfit_card(outfit):
    """Render outfit recommendation card."""
    st.markdown("---")
    
    # Score gauge
    score = outfit.get("score", 0)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Outfit Score", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [0, 105]},
            'bar': {'color': "#E91E8C"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 75], 'color': "yellow"},
                {'range': [75, 105], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    
    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)
    
    # Trending badge
    if outfit.get("trending"):
        st.success(f"🔥 {outfit.get('trending_reason', 'Trending now!')}")
    
    # Garment images
    st.markdown("### Your Outfit")
    if outfit.get("dress"):
        st.caption("Dress outfit selected: dress is treated as a complete top+bottom look.")
    
    # Show hijab first if present (for female users)
    if outfit.get("hijab"):
        st.markdown("🧕 **Hijab**")
        try:
            resolved = resolve_image_path(outfit["hijab"].get("image_path"))
            if Path(resolved).exists():
                st.image(resolved, width=150)
            else:
                st.caption("Hijab image missing")
        except:
            st.markdown("📷 Hijab")
        st.markdown(f"**{outfit['hijab'].get('dominant_color', 'Unknown')} Hijab**")
        st.caption(f"Hex: {outfit['hijab'].get('color_hex', 'N/A')}")
        st.markdown("---")
    
    cols = st.columns(4)
    
    items = [
        ("top", "👕 Top"),
        ("bottom", "👖 Bottom"),
        ("dress", "👗 Dress"),
        ("outerwear", "🧥 Outerwear")
    ]
    
    for idx, (key, label) in enumerate(items):
        item = outfit.get(key)
        with cols[idx]:
            if item:
                try:
                    resolved = resolve_image_path(item.get("image_path"))
                    if Path(resolved).exists():
                        st.image(resolved, width="stretch")
                    else:
                        st.caption("Image missing")
                except:
                    st.markdown(f"📷 {label}")
                
                st.markdown(f"**{item.get('dominant_color', 'Unknown')} {item.get('category', 'Item')}**")
                st.caption(f"Hex: {item.get('color_hex', 'N/A')}")
            else:
                # For dress outfits, top/bottom absence is expected.
                if not (outfit.get("dress") and key in ("top", "bottom")):
                    st.caption(f"No {label.lower()}")
    
    # Why this suits you
    st.markdown("---")
    st.markdown("### ✨ Why This Suits You")
    st.write(outfit.get("why_this_suits_you", "This outfit complements your style and preferences."))
    
    # Weather context
    st.markdown("### 🌤️ Weather Context")
    st.write(outfit.get("weather_explanation", ""))
    
    # Score breakdown
    st.markdown("### 📊 Score Breakdown")
    
    bcol1, bcol2, bcol3 = st.columns(3)
    
    with bcol1:
        st.metric("Color Harmony", f"{outfit.get('color_harmony', 0):.0%}")
        st.metric("Skin Flattery", f"{outfit.get('skin_flattery', 0):.0%}")
    
    with bcol2:
        st.metric("Body Shape", f"{outfit.get('body_shape_score', 0):.0%}")
        st.metric("Weather", f"{outfit.get('weather_score', 0):.0%}")
    
    with bcol3:
        st.metric("Occasion", f"{outfit.get('occasion_score', 0):.0%}")
        temp = outfit.get("weather", {}).get("temp_c", "N/A")
        st.metric("Temperature", f"{temp}°C" if temp != "N/A" else "N/A")
    
    # Style tags
    st.markdown("### 🏷️ Style Tags")
    tags = []
    if outfit.get("trending"):
        tags.append("🔥 Trending")
    if outfit.get("score", 0) > 80:
        tags.append("⭐ High Score")
    if outfit.get("color_harmony", 0) > 0.8:
        tags.append("🎨 Great Colors")
    
    if tags:
        st.write(" | ".join(tags))


def main():
    # Beautiful header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="margin-bottom: 10px;">✨ Daily Outfit</h1>
        <p style="color: #888; font-size: 1.1em;">Your AI-curated perfect look for today</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar inputs
    with st.sidebar:
        st.markdown("### ⚙️ Preferences")
        
        style_pref = st.radio(
            "Style Preference",
            ["Western", "Eastern"],
            help="Choose your preferred fashion style"
        )
        
        occasion = st.radio(
            "Occasion",
            ["Casual", "Formal", "Academic"],
            help="What's the occasion for this outfit?"
        )
        
        use_weather_override = st.checkbox("Override Weather")
        weather_override = None
        
        if use_weather_override:
            weather_override = st.slider(
                "Temperature (°C)",
                min_value=-10,
                max_value=45,
                value=22
            )
        
        st.markdown("---")
        
        if st.button("✨ Generate Outfit", type="primary", use_container_width=True):
            st.session_state.generate_outfit = True
            st.session_state.reimagine_step = 0
    
    # Main content
    if not st.session_state.get("generate_outfit"):
        st.info("👈 Set your preferences and click 'Generate Outfit' to get started!")
        
        st.markdown("""
        ### How It Works
        
        Adorkable AI generates outfit recommendations by considering:
        
        1. **🎨 Color Harmony** - Complementary and analogous color matching
        2. **👤 Your Profile** - Skin tone and body shape preferences
        3. **🌤️ Weather** - Temperature-appropriate fabrics and layering
        4. **📍 Occasion** - Style matching the event
        5. **🔥 Trends** - Current season's trending colors and styles
        
        Each outfit receives a score out of 100 (plus bonus points for trending items!)
        """)
    else:
        if "reimagine_step" not in st.session_state:
            st.session_state.reimagine_step = 0
        with st.spinner("🎨 Analyzing your wardrobe and generating the perfect outfit..."):
            outfit = get_daily_outfit(
                occasion,
                style_pref,
                weather_override,
                reimagine_step=st.session_state.reimagine_step,
            )
        
        if outfit.get("error"):
            st.error(f"❌ {outfit['error']}")
            st.info("💡 Tip: Make sure you have garments in your wardrobe that match your style preference!")
        else:
            render_outfit_card(outfit)
            
            # Re-imagine button (2nd best, then 3rd best, etc.)
            if st.button("🔄 Re-Imagine Outfit"):
                st.session_state.reimagine_step = st.session_state.get("reimagine_step", 0) + 1
                st.rerun()


if __name__ == "__main__":
    main()


# ✅ frontend/pages/4_Daily_Outfit.py generated — Adorkable AI
