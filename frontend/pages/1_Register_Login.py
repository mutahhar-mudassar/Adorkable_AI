"""
Adorkable AI - Register/Login Page

User authentication with JWT token management.
"""

import sys
from pathlib import Path

import streamlit as st
import httpx

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from ui_styles import inject_app_theme

st.set_page_config(page_title="Login - Adorkable AI", page_icon="🔐", layout="centered")

inject_app_theme("""
<style>
.auth-container { max-width: 480px; margin: 0 auto; padding: 12px 8px 32px; }
.brand-header { text-align: center; margin-bottom: 28px; }
.brand-logo { font-size: 3.5rem; margin-bottom: 8px; line-height: 1; }
.brand-title { font-size: 2.35rem; font-weight: 700; margin-bottom: 8px; }
.brand-tagline { font-size: 1.05rem; font-weight: 400; }
</style>
""")

API_BASE = "http://localhost:8006/api/v1"


# =============================================================================
# Session State
# =============================================================================

def init_session():
    if "user_token" not in st.session_state:
        st.session_state.user_token = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None


init_session()


# =============================================================================
# API Functions
# =============================================================================

def register_user(email: str, password: str, gender: str, city: str):
    """Register new user."""
    try:
        response = httpx.post(
            f"{API_BASE}/auth/register",
            json={
                "email": email,
                "password": password,
                "gender": gender,
                "city": city
            }
        )
        
        if response.status_code == 201:
            data = response.json()
            return True, data
        else:
            error = response.json().get("detail", "Registration failed")
            return False, error
    except Exception as e:
        return False, str(e)


def login_user(email: str, password: str):
    """Login user."""
    try:
        response = httpx.post(
            f"{API_BASE}/auth/login",
            json={
                "email": email,
                "password": password
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            error = response.json().get("detail", "Login failed")
            return False, error
    except Exception as e:
        return False, str(e)


# =============================================================================
# UI
# =============================================================================

def main():
    st.markdown("""
    <div class="auth-container">
        <div class="brand-header">
            <div class="brand-logo">💜</div>
            <h1 class="brand-title">Adorkable AI</h1>
            <p class="brand-tagline">Your Personal Fashion Intelligence Platform</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Check if already logged in
    if st.session_state.user_token:
        st.success(f"✅ Welcome back, {st.session_state.user_email.split('@')[0]}!")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("✨ Go to Dashboard", use_container_width=True, type="primary"):
                st.switch_page("app.py")
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.user_token = None
                st.session_state.user_email = None
                st.rerun()

        return

    # Tabs for login and register
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Register"])
    
    with tab1:
        st.markdown("<div class='auth-form'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; margin-bottom: 25px;'>Welcome Back! 👋</h2>", unsafe_allow_html=True)

        login_email = st.text_input("📧 Email Address", key="login_email", placeholder="your@email.com")
        login_password = st.text_input("🔒 Password", type="password", key="login_password",
                                       placeholder="Enter your password")

        col1, col2 = st.columns([2, 1])
        with col1:
            remember_me = st.checkbox("Remember me", value=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🔐 Sign In", use_container_width=True, type="primary"):
            if not login_email or not login_password:
                st.error("Please enter both email and password")
            else:
                with st.spinner("Authenticating..."):
                    success, result = login_user(login_email, login_password)

                    if success:
                        st.session_state.user_token = result["access_token"]
                        st.session_state.user_email = result["user"]["email"]
                        st.session_state.user_city = result["user"].get("city")
                        st.success("✅ Login successful! Welcome back!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")

        st.markdown("</div>", unsafe_allow_html=True)
    
    with tab2:
        st.markdown("<div class='auth-form'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; margin-bottom: 25px;'>Create Account ✨</h2>", unsafe_allow_html=True)

        reg_email = st.text_input("📧 Email Address", key="reg_email", placeholder="your@email.com")
        reg_password = st.text_input("🔒 Password", type="password", key="reg_password",
                                     help="Minimum 8 characters required", placeholder="Create a password")

        col1, col2 = st.columns(2)
        with col1:
            reg_gender = st.selectbox("👤 Gender", ["Female", "Male", "Other", "Prefer not to say"],
                                     key="reg_gender")
        with col2:
            reg_city = st.text_input("🌍 City", key="reg_city",
                                    help="For weather-based recommendations", placeholder="e.g., London")

        st.markdown("""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; font-size: 0.9em; color: #666;">
            <strong>💡 Tip:</strong> Adding your city helps us suggest weather-appropriate outfits!
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("✨ Create Free Account", use_container_width=True, type="primary"):
            if not reg_email or not reg_password:
                st.error("Please fill in all required fields")
            elif len(reg_password) < 8:
                st.error("Password must be at least 8 characters")
            else:
                with st.spinner("Creating your account..."):
                    success, result = register_user(reg_email, reg_password,
                                                   reg_gender, reg_city)

                    if success:
                        st.session_state.user_token = result["access_token"]
                        st.session_state.user_email = result["user"]["email"]
                        st.session_state.user_city = result["user"].get("city")
                        st.success("✅ Welcome to Adorkable AI! Let's find your perfect style!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {result}")

        st.markdown("</div>", unsafe_allow_html=True)
    
    # Info section
    st.markdown("<div class='divider-fancy'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
        <h3 style="margin-top: 0; color: #333;">💜 Why Choose Adorkable AI?</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 20px;">
            <div>
                <span style="font-size: 1.5em;">🎨</span>
                <strong>Color Harmony</strong><br>
                <span style="font-size: 0.9em; color: #666;">AI finds colors that complement your skin tone</span>
            </div>
            <div>
                <span style="font-size: 1.5em;">🌤️</span>
                <strong>Smart Weather</strong><br>
                <span style="font-size: 0.9em; color: #666;">Outfits matched to current conditions</span>
            </div>
            <div>
                <span style="font-size: 1.5em;">👤</span>
                <strong>Body Analysis</strong><br>
                <span style="font-size: 0.9em; color: #666;">Personalized style recommendations</span>
            </div>
            <div>
                <span style="font-size: 1.5em;">📅</span>
                <strong>Weekly Planning</strong><br>
                <span style="font-size: 0.9em; color: #666;">Plan your entire week in advance</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()


# ✅ frontend/pages/1_Register_Login.py generated — Adorkable AI
