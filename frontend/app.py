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
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_app_theme()

# API base URL
API_BASE = "http://localhost:8006/api/v1"


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
        st.title("👗 Adorkable AI")
        st.markdown("---")
        
        if check_auth():
            st.success(f"✅ Logged in as {st.session_state.user_email}")
            
            st.markdown("### Navigation")
            st.page_link("pages/1_Register_Login.py", label="Account", icon="🔐")
            st.page_link("pages/2_My_Profile.py", label="My Profile", icon="👤")
            st.page_link("pages/3_My_Wardrobe.py", label="My Wardrobe", icon="👚")
            st.page_link("pages/4_Daily_Outfit.py", label="Daily Outfit", icon="✨")
            st.page_link("pages/5_Weekly_Planner.py", label="Weekly Planner", icon="📅")
            st.page_link("pages/6_Smart_Combo.py", label="Smart Combo", icon="🎯")
            st.page_link("pages/7_Analytics.py", label="Analytics", icon="📊")
            
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user_token = None
                st.session_state.user_email = None
                st.session_state.user_city = None
                st.rerun()
        else:
            st.warning("⚠️ Not logged in")
            st.page_link("pages/1_Register_Login.py", label="🔐 Login / Register", icon="🔐")


# =============================================================================
# Main Content
# =============================================================================

def render_hero():
    """Render hero section."""
    st.title("👗 Adorkable AI")
    st.subheader("Your Personal Fashion Intelligence")
    
    st.markdown("""
    ### Eliminate outfit decision fatigue. Wear what already works, perfectly.
    
    Adorkable AI combines computer vision, color theory, and weather intelligence
to curate personalized outfit recommendations that match your style, flatter your
features, and suit the occasion.
    """)


def render_features():
    """Render feature highlights."""
    st.markdown("---")
    st.header("✨ Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        #### 🎨 Smart Color Matching
        - Complementary & analogous color harmony
        - Skin tone flattering recommendations
        - Trending color palettes
        """)
    
    with col2:
        st.markdown("""
        #### 🌤️ Weather-Aware
        - Live weather integration
        - Temperature-appropriate fabrics
        - Layering recommendations
        """)
    
    with col3:
        st.markdown("""
        #### 📊 AI-Powered
        - EfficientNet garment classification
        - MediaPipe body shape analysis
        - Stochastic outfit selection
        """)


def render_logged_in_dashboard():
    """Render dashboard for logged-in users."""
    st.markdown("---")
    st.header(f"Welcome back, {st.session_state.user_email}! 👋")
    
    # Fetch dashboard summary
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/analytics/dashboard-summary", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Display stats
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Wardrobe Items", data.get("total_items", 0))
            
            with col2:
                fav_color = data.get("favorite_color", "N/A")
                st.metric("Favorite Color", fav_color)
            
            with col3:
                last_score = data.get("last_outfit_score")
                if last_score:
                    st.metric("Last Outfit Score", f"{last_score:.1f}")
                else:
                    st.metric("Last Outfit Score", "N/A")
            
            with col4:
                st.metric("Status", "✅ Active")
            
            # Quick actions
            st.markdown("### Quick Actions")
            
            qcol1, qcol2, qcol3 = st.columns(3)
            
            with qcol1:
                if st.button("✨ Get Today's Outfit", use_container_width=True):
                    st.switch_page("pages/4_Daily_Outfit.py")
            
            with qcol2:
                if st.button("👚 Manage Wardrobe", use_container_width=True):
                    st.switch_page("pages/3_My_Wardrobe.py")
            
            with qcol3:
                if st.button("📊 View Analytics", use_container_width=True):
                    st.switch_page("pages/7_Analytics.py")
    except Exception as e:
        st.error(f"Could not load dashboard: {e}")


def render_login_prompt():
    """Render login prompt for guests."""
    st.markdown("---")
    st.info("👋 **Welcome!** Please log in or register to start using Adorkable AI.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔐 Login / Register", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Register_Login.py")


# =============================================================================
# Main
# =============================================================================

def main():
    """Main application entry."""
    render_sidebar()
    
    render_hero()
    render_features()
    
    if check_auth():
        render_logged_in_dashboard()
    else:
        render_login_prompt()
    
    # Footer
    st.markdown("---")
    st.caption("Made with 💕 by Adorkable AI | v1.0.0")


if __name__ == "__main__":
    main()


# ✅ frontend/app.py generated — Adorkable AI
