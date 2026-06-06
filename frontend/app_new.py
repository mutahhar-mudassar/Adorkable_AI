"""
Adorkable AI - Streamlit Frontend Main Entry
Fashion Intelligence Platform - Your Personal AI Stylist
"""

import streamlit as st
import httpx

from ui_styles import inject_app_theme

# Page config
st.set_page_config(
    page_title="Adorkable AI",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_app_theme("""
<style>
.hero-gradient {
  background: linear-gradient(135deg, #5b21b6 0%, #E91E8C 45%, #7c3aed 100%);
  padding: 52px 36px;
  border-radius: 22px;
  color: white;
  text-align: center;
  margin-bottom: 36px;
  box-shadow: 0 24px 64px rgba(91, 33, 182, 0.35);
  border: 1px solid rgba(255,255,255,0.12);
}
.hero-title { font-size: clamp(2rem, 4vw, 3.2rem) !important; font-weight: 700; margin-bottom: 16px; }
.hero-subtitle { font-size: 1.15rem; opacity: 0.95; margin-bottom: 24px; font-weight: 400; }
.feature-card {
  background: linear-gradient(145deg, #16182a 0%, #1e2138 100%);
  padding: 26px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.08);
  height: 100%;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 48px rgba(233, 30, 140, 0.15);
}
.feature-icon { font-size: 2.25rem; margin-bottom: 12px; display: block; }
.feature-title { font-size: 1.15rem; font-weight: 600; color: #f4f6fb; margin-bottom: 8px; }
.feature-desc { color: #9ca3b8; line-height: 1.65; font-size: 0.95rem; }
.metric-card {
  background: linear-gradient(145deg, rgba(233,30,140,0.12) 0%, rgba(124,58,237,0.1) 100%);
  padding: 22px;
  border-radius: 14px;
  text-align: center;
  border: 1px solid rgba(255,255,255,0.08);
  border-left: 4px solid #E91E8C;
}
.metric-value { font-size: 1.85rem; font-weight: 700; color: #f472b6; }
.metric-label { color: #9ca3b8; font-size: 0.88rem; margin-top: 6px; }
.sidebar-brand {
  background: linear-gradient(135deg, #5b21b6 0%, #E91E8C 100%);
  padding: 18px;
  border-radius: 14px;
  color: white;
  text-align: center;
  margin-bottom: 16px;
}
.status-active {
  background: linear-gradient(135deg, #0d9488 0%, #22c55e 100%);
  color: white; padding: 8px 16px; border-radius: 999px; font-weight: 600;
  display: inline-block;
}
.status-inactive {
  background: linear-gradient(135deg, #be123c 0%, #f97316 100%);
  color: white; padding: 8px 16px; border-radius: 999px; font-weight: 600;
  display: inline-block;
}
</style>
""")

# API base URL
API_BASE = "http://localhost:8000/api/v1"


# =============================================================================
# Session State Initialization
# =============================================================================

def init_session_state():
    """Initialize session state variables."""
    if "user_token" not in st.session_state:
        st.session_state.user_token = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_city" not in st.session_state:
        st.session_state.user_city = None


init_session_state()


# =============================================================================
# Authentication Check
# =============================================================================

def check_auth():
    """Check if user is authenticated."""
    return st.session_state.user_token is not None


# =============================================================================
# Sidebar Navigation
# =============================================================================

def render_sidebar():
    """Render navigation sidebar."""
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">
            <h2 style="margin: 0; font-size: 1.5em;">💜 Adorkable AI</h2>
            <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 0.85em;">Your Personal Stylist</p>
        </div>
        """, unsafe_allow_html=True)

        if check_auth():
            st.success(f"✨ Welcome, {st.session_state.user_email.split('@')[0]}")

            st.markdown("### 📍 Navigation")

            nav_items = [
                ("pages/1_Register_Login.py", "🔐 Account", "Account"),
                ("pages/2_My_Profile.py", "👤 My Profile", "Profile"),
                ("pages/3_My_Wardrobe.py", "👚 My Wardrobe", "Wardrobe"),
                ("pages/4_Daily_Outfit.py", "✨ Daily Outfit", "Daily Outfit"),
                ("pages/5_Weekly_Planner.py", "📅 Weekly Planner", "Weekly Planner"),
                ("pages/6_Smart_Combo.py", "🎯 Smart Combo", "Smart Combo"),
                ("pages/7_Analytics.py", "📊 Analytics", "Analytics"),
            ]

            for page, label, _ in nav_items:
                st.page_link(page, label=label)

            st.markdown("<div class='divider-fancy'></div>", unsafe_allow_html=True)

            if st.button("🚪 Logout", use_container_width=True, type="secondary"):
                st.session_state.user_token = None
                st.session_state.user_email = None
                st.session_state.user_city = None
                st.rerun()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 20px; background: #f8f9fa; border-radius: 12px; margin-bottom: 20px;">
                <span style="font-size: 3em;">👋</span>
                <p style="margin: 10px 0; color: #666;">Welcome! Please sign in to access your personal AI stylist.</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔐 Login / Register", use_container_width=True, type="primary"):
                st.switch_page("pages/1_Register_Login.py")


# =============================================================================
# Main Content
# =============================================================================

def render_hero():
    """Render beautiful hero section."""
    st.markdown("""
    <div class="hero-gradient">
        <h1 class="hero-title">💜 Adorkable AI</h1>
        <p class="hero-subtitle">Your Personal Fashion Intelligence Platform</p>
        <p style="font-size: 1em; opacity: 0.9; max-width: 600px; margin: 0 auto;">
            Eliminate outfit decision fatigue. Wear what already works, perfectly.
            Our AI analyzes your skin tone, body shape, and wardrobe to create
            stunning outfit combinations tailored just for you.
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_features():
    """Render beautiful feature cards."""
    st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>✨ What We Offer</h2>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    features = [
        {
            "icon": "🎨",
            "title": "Smart Color Harmony",
            "desc": "AI analyzes your skin tone to find colors that make you glow. Get personalized palettes with complementary shades."
        },
        {
            "icon": "🌤️",
            "title": "Weather Intelligence",
            "desc": "Real-time weather integration ensures you're dressed perfectly for any conditions. Smart layering recommendations."
        },
        {
            "icon": "🤖",
            "title": "AI-Powered Analysis",
            "desc": "MediaPipe face detection for skin tone, body shape analysis, and intelligent garment classification."
        }
    ]

    for i, (col, feature) in enumerate(zip([col1, col2, col3], features)):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <span class="feature-icon">{feature['icon']}</span>
                <div class="feature-title">{feature['title']}</div>
                <div class="feature-desc">{feature['desc']}</div>
            </div>
            """, unsafe_allow_html=True)


def render_how_it_works():
    """Render how it works section."""
    st.markdown("<div class='divider-fancy'></div>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>🚀 How It Works</h2>", unsafe_allow_html=True)

    steps = [
        ("1", "📸", "Create Your Profile", "Upload a selfie for skin tone analysis and a body photo for shape detection."),
        ("2", "👚", "Build Your Wardrobe", "Upload your clothes. The AI extracts colors while you specify the garment type."),
        ("3", "✨", "Get Recommendations", "Receive personalized outfit suggestions based on your profile, weather, and occasion."),
        ("4", "📊", "Track & Improve", "See analytics on your style preferences and get smarter suggestions over time.")
    ]

    cols = st.columns(4)
    for i, (num, icon, title, desc) in enumerate(steps):
        with cols[i]:
            st.markdown(f"""
            <div style="text-align: center; padding: 20px;">
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    width: 50px;
                    height: 50px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 15px auto;
                    font-weight: 700;
                    font-size: 1.2em;
                ">{num}</div>
                <span style="font-size: 2em; display: block; margin-bottom: 10px;">{icon}</span>
                <div style="font-weight: 600; margin-bottom: 8px; color: #333;">{title}</div>
                <div style="font-size: 0.9em; color: #666; line-height: 1.5;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


def render_logged_in_dashboard():
    """Render beautiful dashboard for logged-in users."""
    st.markdown("<div class='divider-fancy'></div>", unsafe_allow_html=True)

    user_name = st.session_state.user_email.split('@')[0] if st.session_state.user_email else "User"
    st.markdown(f"<h2 style='text-align: center;'>Welcome back, {user_name}! 👋</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666; margin-bottom: 30px;'>Here's your fashion dashboard</p>", unsafe_allow_html=True)

    # Fetch dashboard summary
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/analytics/dashboard-summary", headers=headers, timeout=5.0)

        if response.status_code == 200:
            data = response.json()

            # Display stats in beautiful cards
            col1, col2, col3, col4 = st.columns(4)

            metrics = [
                ("👚", "Wardrobe Items", str(data.get("total_items", 0))),
                ("🎨", "Favorite Color", data.get("favorite_color", "N/A")),
                ("⭐", "Last Outfit Score", f"{data.get('last_outfit_score', 0):.1f}" if data.get('last_outfit_score') else "N/A"),
                ("✅", "Status", "Active")
            ]

            for col, (icon, label, value) in zip([col1, col2, col3, col4], metrics):
                with col:
                    st.markdown(f"""
                    <div class="metric-card">
                        <span style="font-size: 1.5em;">{icon}</span>
                        <div class="metric-value">{value}</div>
                        <div class="metric-label">{label}</div>
                    </div>
                    """, unsafe_allow_html=True)

            # Quick actions
            st.markdown("<h3 style='margin-top: 40px; text-align: center;'>⚡ Quick Actions</h3>", unsafe_allow_html=True)

            qcol1, qcol2, qcol3 = st.columns(3)

            with qcol1:
                if st.button("✨ Get Today's Outfit", use_container_width=True, type="primary"):
                    st.switch_page("pages/4_Daily_Outfit.py")

            with qcol2:
                if st.button("👚 Manage Wardrobe", use_container_width=True):
                    st.switch_page("pages/3_My_Wardrobe.py")

            with qcol3:
                if st.button("📊 View Analytics", use_container_width=True):
                    st.switch_page("pages/7_Analytics.py")

        else:
            st.info("📊 Dashboard data will appear once you start using the app!")

    except Exception:
        st.info("📊 Connect to the backend to see your dashboard statistics.")


def render_login_prompt():
    """Render beautiful login prompt for guests."""
    st.markdown("<div class='divider-fancy'></div>", unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; padding: 40px; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); border-radius: 20px; margin-top: 20px;">
        <span style="font-size: 4em;">💜</span>
        <h2 style="margin: 20px 0 10px 0;">Ready to Transform Your Style?</h2>
        <p style="color: #666; max-width: 500px; margin: 0 auto 30px auto;">
            Join thousands of users who have discovered their perfect colors and built
            confidence in their wardrobe choices with AI-powered fashion intelligence.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Get Started - Login / Register", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Register_Login.py")


# =============================================================================
# Main
# =============================================================================

def main():
    """Main application entry."""
    render_sidebar()
    render_hero()
    render_features()
    render_how_it_works()

    if check_auth():
        render_logged_in_dashboard()
    else:
        render_login_prompt()

    # Footer
    st.markdown("<div class='divider-fancy'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 20px; color: #888; font-size: 0.85em;">
        <p>Made with 💜 by Adorkable AI | v1.0.0</p>
        <p>Your personal fashion intelligence platform</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
