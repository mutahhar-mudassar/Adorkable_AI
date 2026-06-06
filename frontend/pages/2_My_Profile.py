"""
Adorkable AI - My Profile Page

User profile management with skin tone and body shape analysis.
"""

import sys
from pathlib import Path

import streamlit as st
import httpx
from PIL import Image
import io

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from ui_styles import inject_app_theme

st.set_page_config(page_title="My Profile - Adorkable AI", page_icon="👤", layout="wide")

inject_app_theme("""
<style>
.profile-card {
  padding: 28px !important;
  border-radius: 18px !important;
  margin-bottom: 22px !important;
}
.status-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.85em;
  font-weight: 600;
}
.status-complete {
  background: linear-gradient(135deg, #0d9488 0%, #22c55e 100%) !important;
  color: #fff !important;
}
</style>
""")

API_BASE = "http://localhost:8006/api/v1"
HTTP_TIMEOUT = httpx.Timeout(120.0, connect=30.0)


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

def get_profile():
    """Fetch user profile."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/profile/", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching profile: {e}")
        return None


def get_wardrobe_count():
    """Fetch wardrobe item count."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/wardrobe/stats", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("total_items", 0)
        return 0
    except Exception:
        return 0


def upload_selfie(file_bytes):
    """Upload selfie for skin tone analysis."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        files = {"file": ("selfie.jpg", file_bytes, "image/jpeg")}
        
        response = httpx.post(
            f"{API_BASE}/profile/selfie",
            headers=headers,
            files=files,
            timeout=HTTP_TIMEOUT,
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Upload failed")}
    except Exception as e:
        return {"error": str(e)}


def upload_body_photo(file_bytes):
    """Upload body photo for body shape analysis."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        files = {"file": ("body.jpg", file_bytes, "image/jpeg")}
        
        response = httpx.post(
            f"{API_BASE}/profile/body",
            headers=headers,
            files=files,
            timeout=HTTP_TIMEOUT,
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Upload failed")}
    except Exception as e:
        return {"error": str(e)}


def get_color_palette():
    """Get recommended color palette."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/profile/color-palette", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to fetch palette")}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# UI
# =============================================================================

def render_color_swatches(colors, title):
    """Render color swatches with neutral background."""
    if not colors:
        return
    
    st.markdown(f"**{title}**")
    
    # Color name to hex mapping
    color_map = {
        "Peach": "#FFDAB9", "Coral": "#FF7F50", "Warm Beige": "#F5DEB3",
        "Camel": "#C19A6B", "Rust": "#B7410E", "Burnt Orange": "#CC5500",
        "Terracotta": "#E2725B", "Cream": "#FFFDD0", "Ivory": "#FFFFF0",
        "Warm White": "#F5F5DC", "Gold": "#FFD700", "Butter Yellow": "#F0E68C",
        "Apricot": "#FBCEB1", "Salmon": "#FA8072", "Blush Pink": "#DE5D83",
        "Dusty Rose": "#DCAE96", "Mint": "#98FF98", "Sage Green": "#9DC183",
        "Stark White": "#FFFFFF", "Cool Gray": "#909090", "Slate Blue": "#6A5ACD",
        "Navy Blue": "#000080", "Deep Burgundy": "#800020", "Black": "#000000",
        "Charcoal": "#36454F", "Ice Blue": "#D6EAF8", "Lavender": "#E6E6FA",
        "Rose": "#FF007F", "Plum": "#8E4585", "Royal Blue": "#4169E1",
        "Cobalt Blue": "#0047AB", "Pastel Pink": "#FFD1DC", "Orchid": "#DA70D6",
        "Amethyst": "#9966CC", "Mauve": "#E0B0FF", "Violet": "#8F00FF",
        "Berry": "#8B0000", "Fuchsia": "#FF00FF", "Orange": "#FFA500",
        "Mustard": "#FFDB58", "Olive": "#808000", "Forest Green": "#228B22",
        "Brick Red": "#CB4154", "Chocolate": "#7B3F00", "Coffee": "#6F4E37",
        "Emerald": "#50C878", "Teal": "#008080", "Jade": "#00A86B",
        "Taupe": "#483C32", "Soft Pink": "#FFB6C1", "Soft White": "#FAF9F6",
        "Neon colors": "#CCFF00", "Silver": "#C0C0C0", "White": "#FFFFFF",
        "White Gold": "#F0F0F0", "Platinum": "#E5E4E2", "Bronze": "#CD7F32",
        "Copper": "#B87333", "Rose Gold": "#B76E79", "Warm Red": "#E34234",
        "Caramel": "#FFD59A", "Kelly Green": "#4CBB17", "Electric Purple": "#BF00FF",
        "Crimson": "#DC143C", "Sapphire Blue": "#0F52BA", "Turquoise": "#40E0D0",
        "Magenta": "#FF00FF", "Purple": "#800080", "Dark Brown": "#5C4033",
        "Dark Navy": "#000022", "Very dark brown": "#3D2B1F", "Muddy colors": "#8B7355",
        "Washed out pastels": "#E8E8E8", "Extreme pastels": "#F8F8FF",
        "Neon yellows": "#CCFF00", "Overly bright oranges": "#FF8C00",
        "Overly bright yellows": "#FFFF00", "Overly saturated oranges": "#FF4500",
        "Gray": "#808080", "Blue": "#0000FF", "Red": "#FF0000",
        "Green": "#008000", "Yellow": "#FFFF00", "Pink": "#FFC0CB",
    }
    
    # Display in rows of 5 with neutral background
    for i in range(0, len(colors), 5):
        cols = st.columns(5)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(colors):
                color_name = colors[idx]
                hex_color = color_map.get(color_name, "#CCCCCC")
                
                col.markdown(f"""
                <div style="
                    background-color: rgba(255,255,255,0.05);
                    padding: 10px;
                    border-radius: 10px;
                    text-align: center;
                    margin: 5px 0;
                    border: 1px solid rgba(255,255,255,0.1);
                ">
                    <div style="
                        background-color: {hex_color};
                        width: 100%;
                        height: 50px;
                        border-radius: 6px;
                        margin-bottom: 8px;
                        border: 1px solid rgba(0,0,0,0.25);
                    "></div>
                    <span style="color: #c8cdd8; font-size: 12px; font-weight: 500;">
                        {color_name}
                    </span>
                </div>
                """, unsafe_allow_html=True)


def render_hex_swatches(hex_colors, title):
    """Render hex-based swatches for harmony suggestions."""
    if not hex_colors:
        return

    st.markdown(f"**{title}**")
    for i in range(0, len(hex_colors), 5):
        cols = st.columns(5)
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(hex_colors):
                hex_color = hex_colors[idx]
                col.markdown(
                    f"""
                    <div style="
                        background-color: rgba(255,255,255,0.05);
                        padding: 10px;
                        border-radius: 10px;
                        text-align: center;
                        margin: 5px 0;
                        border: 1px solid rgba(255,255,255,0.1);
                    ">
                        <div style="
                            background-color: {hex_color};
                            width: 100%;
                            height: 50px;
                            border-radius: 6px;
                            margin-bottom: 8px;
                            border: 1px solid rgba(0,0,0,0.25);
                        "></div>
                        <span style="color: #c8cdd8; font-size: 12px; font-weight: 500;">
                            {hex_color.upper()}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


def render_palette_details(palette):
    """Render complete palette details including harmony."""
    # Best colors grid
    st.markdown("<h4 style='margin-bottom: 15px;'>✨ Best Colors For You</h4>", unsafe_allow_html=True)
    best_colors = palette.get("best_colors", [])
    if best_colors:
        render_color_swatches(best_colors, "Your Flattering Colors")

    # Avoid colors
    avoid_colors = palette.get("colors_to_avoid", [])
    if avoid_colors:
        st.markdown("<h4 style='margin-top: 25px; margin-bottom: 15px;'>⚠️ Use With Care</h4>", unsafe_allow_html=True)
        render_color_swatches(avoid_colors, "Colors to Be Cautious With")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<h4>💎 Recommended Metals</h4>", unsafe_allow_html=True)
        metals = palette.get("recommended_metals", [])
        if metals:
            for metal in metals:
                st.markdown(
                    f"<span style='background: rgba(233,30,140,0.15); color: #f4f6fb; padding: 6px 14px; border-radius: 999px; margin: 4px; display: inline-block; border: 1px solid rgba(255,255,255,0.1);'>{metal}</span>",
                    unsafe_allow_html=True
                )

    with col2:
        st.markdown("<h4>📝 Description</h4>", unsafe_allow_html=True)
        st.markdown(
            f"<p style='color: #9ca3b8; font-style: italic; line-height: 1.6;'>{palette.get('description', 'Your personalized color recommendations')}</p>",
            unsafe_allow_html=True
        )

    harmony_sets = palette.get("color_harmony_sets", [])
    if harmony_sets:
        st.markdown("---")
        st.markdown("<h4 style='margin-bottom: 12px;'>🧩 Color Harmony Sets</h4>", unsafe_allow_html=True)
        st.caption("Mix and match these combinations with your best colors.")

        for harmony in harmony_sets:
            base_color = harmony.get("base_color", "Base Color")
            base_hex = harmony.get("base_hex", "#CCCCCC")
            suggestions = harmony.get("suggestions", {})
            st.markdown(f"**Base: {base_color} ({base_hex.upper()})**")
            for harmony_type, hex_list in suggestions.items():
                nice_type = harmony_type.replace("_", " ").title()
                render_hex_swatches(hex_list, nice_type)


def main():
    # Header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="margin-bottom: 10px;">👤 Your Fashion Profile</h1>
        <p style="color: #9ca3b8; font-size: 1.08em;">Set up your profile for personalized AI recommendations</p>
    </div>
    """, unsafe_allow_html=True)

    # Fetch profile data
    profile_data = get_profile()
    wardrobe_count = get_wardrobe_count()

    if not profile_data:
        st.error("Could not load profile data. Please try again later.")
        return

    profile = profile_data.get("profile", {})

    # Profile Status Card
    st.markdown("<div class='profile-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin-top: 0;'>📊 Profile Completion</h3>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if profile.get("skin_tone"):
            st.markdown(f"""
            <div style="text-align: center;">
                <span class="status-badge status-complete">✅ Complete</span>
                <p style="margin: 10px 0; font-weight: 600;">🎨 Skin Tone</p>
                <p style="color: #f472b6; font-size: 1.2em; font-weight: 600;">{profile['skin_tone']}-{profile.get('skin_undertone', 'Unknown')}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center;">
                <span class="status-badge status-pending">⏳ Pending</span>
                <p style="margin: 10px 0; font-weight: 600;">🎨 Skin Tone</p>
                <p style="color: #9ca3b8; font-size: 0.92em;">Upload a selfie to analyze</p>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        if profile.get("body_shape"):
            st.markdown(f"""
            <div style="text-align: center;">
                <span class="status-badge status-complete">✅ Complete</span>
                <p style="margin: 10px 0; font-weight: 600;">👔 Body Shape</p>
                <p style="color: #f472b6; font-size: 1.2em; font-weight: 600;">{profile['body_shape']}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align: center;">
                <span class="status-badge status-pending">⏳ Pending</span>
                <p style="margin: 10px 0; font-weight: 600;">⏳ Body Shape</p>
                <p style="color: #9ca3b8; font-size: 0.92em;">Upload body photo</p>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        # Show wardrobe count - green if items present, pink if empty
        if wardrobe_count > 0:
            badge_class = "status-complete"
            badge_text = "✅ Active"
            count_color = "#f472b6"
        else:
            badge_class = "status-pending"
            badge_text = "⏳ Empty"
            count_color = "#9ca3b8"
        
        st.markdown(f"""
        <div style="text-align: center;">
            <span class="status-badge {badge_class}">{badge_text}</span>
            <p style="margin: 10px 0; font-weight: 600;">👚 Wardrobe</p>
            <p style="color: {count_color}; font-size: 1.2em; font-weight: 600;">{wardrobe_count} items</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Upload sections
    st.header("📸 Profile Photos")
    
    tab1, tab2 = st.tabs(["📸 Skin Tone Analysis", "⏳ Body Shape Analysis"])

    with tab1:
        st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
        st.markdown("""
        <h4 style='margin-top: 0;'>🎨 Upload a Clear Selfie</h4>
        <p style='color: #9ca3b8; margin-bottom: 15px;'>Our AI will analyze your skin tone to find your most flattering colors.</p>
        <div class='ado-tip-panel'>
        <strong>💡 Tips for best results</strong>
        <ul style='margin: 10px 0;'>
        <li>Face the camera directly</li>
        <li>Good natural lighting</li>
        <li>No heavy makeup or filters</li>
        <li>Clear view of your face</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        selfie_file = st.file_uploader(
            "Choose a selfie image",
            type=["jpg", "jpeg", "png"],
            key="selfie_uploader"
        )

        if selfie_file:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(selfie_file, caption="Preview", width="stretch")
            with col2:
                if st.button("🔬 Analyze Skin Tone", type="primary", use_container_width=True):
                    with st.spinner("Analyzing your unique skin tone..."):
                        result = upload_selfie(selfie_file.getvalue())

                        if result.get("error"):
                            st.error(f"❌ {result['error']}")
                        else:
                            analysis = result.get("result", {})
                            skin_tone = analysis.get("skin_tone")
                            undertone = analysis.get("undertone")
                            avg_rgb = analysis.get("avg_rgb", [0, 0, 0])

                            st.markdown(f"""
                            <div class='analysis-result'>
                            <h4 style='margin-top: 0;'>✨ Analysis Complete!</h4>
                            <p><strong>Skin Tone:</strong> {skin_tone}</p>
                            <p><strong>Undertone:</strong> {undertone}</p>
                            <p><strong>Confidence:</strong> {analysis.get('confidence', 0):.0%}</p>
                            <p><strong>Detected RGB:</strong> {avg_rgb}</p>
                            </div>
                            """, unsafe_allow_html=True)

                            # Show color palette
                            palette = get_color_palette()
                            if palette and not palette.get("error"):
                                st.success("🎨 Your personalized color palette is ready!")
                                st.markdown("### 🎨 Color Palette Preview")
                                render_palette_details(palette)
                            elif palette and palette.get("error"):
                                st.error(f"Palette error: {palette['error']}")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with tab2:
        st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
        st.markdown("""
        <h4 style='margin-top: 0;'>⏳ Upload a Full-Body Photo</h4>
        <p style='color: #9ca3b8; margin-bottom: 15px;'>Our AI analyzes your body proportions to suggest the most flattering silhouettes.</p>
        <div class='ado-tip-panel'>
        <strong>💡 Tips for best results</strong>
        <ul style='margin: 10px 0;'>
        <li>Stand straight, facing camera</li>
        <li>Arms slightly away from body</li>
        <li>Full body visible from head to toe</li>
        <li>Fitted clothing (not baggy)</li>
        <li>Side angle or front view works</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        body_file = st.file_uploader(
            "Choose a full-body image",
            type=["jpg", "jpeg", "png"],
            key="body_uploader"
        )

        if body_file:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(body_file, caption="Preview", width="stretch")
            with col2:
                if st.button("🔬 Analyze Body Shape", type="primary", use_container_width=True):
                    with st.spinner("Analyzing your body proportions..."):
                        result = upload_body_photo(body_file.getvalue())

                        if result.get("error"):
                            st.error(f"❌ {result['error']}")
                        else:
                            analysis = result.get("result", {})
                            body_shape = analysis.get("body_shape")

                            st.markdown(f"""
                            <div class='analysis-result'>
                            <h4 style='margin-top: 0;'>✨ Body Analysis Complete!</h4>
                            <p><strong>Body Shape:</strong> {body_shape}</p>
                            <p><strong>Shoulder Width:</strong> {analysis.get('shoulder_width', 0):.0f}px</p>
                            <p><strong>Hip Width:</strong> {analysis.get('hip_width', 0):.0f}px</p>
                            <p><strong>Ratio:</strong> {analysis.get('ratio', 0):.2f}</p>
                            </div>
                            """, unsafe_allow_html=True)

                            # Show body shape recommendations
                            body_recs = profile_data.get("body_recommendations", {})
                            if body_recs:
                                st.success("👗 Body shape recommendations loaded!")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Color palette section if profile complete
    if profile.get("skin_tone"):
        st.markdown("<div class='profile-card' style='margin-top: 30px;'>", unsafe_allow_html=True)
        st.markdown("""
        <h2 style='text-align: center; margin-bottom: 5px;'>🎨 Your Personalized Color Palette</h2>
        <p style='text-align: center; color: #888; margin-bottom: 25px;'>Colors that make you glow</p>
        """, unsafe_allow_html=True)

        palette = get_color_palette()
        if isinstance(palette, dict) and palette.get("error"):
            # Fallback to bundled profile recommendations when API call fails.
            fallback = profile_data.get("skin_recommendations", {})
            if fallback:
                palette = fallback
                st.warning("Using cached profile recommendations. Refresh after backend restart for full harmony sets.")

        if palette:
            render_palette_details(palette)

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()


# ✅ frontend/pages/2_My_Profile.py generated — Adorkable AI
