"""
Adorkable AI - Weekly Planner Page

Plan your outfits for the entire week.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import httpx

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from ui_styles import inject_app_theme

st.set_page_config(page_title="Weekly Planner - Adorkable AI", page_icon="📅")

inject_app_theme()

API_BASE = "http://localhost:8006/api/v1"


def resolve_image_path(path_str: str) -> str:
    """Resolve DB-stored paths (relative to app root) for local display."""
    if not path_str:
        return path_str
    p = Path(path_str)
    if p.is_absolute():
        return str(p)
    # Assume relative to project root (adorkable_ai folder)
    project_root = Path(__file__).resolve().parent.parent.parent
    abs_path = project_root / p
    if abs_path.exists():
        return str(abs_path)
    return path_str


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

def get_weekly_plan(occasions, style_pref):
    """Get weekly outfit plan."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        
        data = {
            "occasions": occasions,
            "style_pref": style_pref
        }
        
        response = httpx.post(
            f"{API_BASE}/plan/weekly",
            headers=headers,
            json=data,
            timeout=90
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get("detail", f"HTTP {response.status_code}")
            return {"error": f"Failed to generate plan: {error_detail}"}
    except httpx.TimeoutException:
        return {"error": "Request timed out. The plan is taking too long to generate. Please try again or use Quick Plan."}
    except Exception as e:
        return {"error": str(e)}


def get_quick_plan():
    """Get quick weekly plan."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/plan/quick", headers=headers, timeout=60)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get("detail", f"HTTP {response.status_code}")
            return {"error": f"Failed to load quick plan: {error_detail}"}
    except httpx.TimeoutException:
        return {"error": "Request timed out. Please try again."}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# UI
# =============================================================================

def safe_image(image_path, width=80):
    """Safely display an image with fallback.""" 
    try:
        resolved = resolve_image_path(image_path)
        if Path(resolved).exists():
            st.image(resolved, width=width)
            return True
        else:
            st.caption("📷 No image")
            return False
    except:
        st.caption("📷 Error")
        return False


def render_day_outfit(day_plan, day_num):
    """Render a single day outfit card with images.""" 
    with st.container():
        # Day header
        st.markdown(f"### {day_plan.get('day_name', f'Day {day_num}')} - {day_plan.get('date', '')}")
        
        cols = st.columns([2, 3])
        
        with cols[0]:
            # Day info
            st.markdown(f"📍 **{day_plan.get('occasion', 'Casual')}**")
            
            score = day_plan.get('score', 0)
            if score > 80:
                st.success(f"⭐ Score: {score:.0f}")
            elif score > 60:
                st.info(f"Score: {score:.0f}")
            else:
                st.warning(f"Score: {score:.0f}")
            
            # Show actual weather from forecast
            weather = day_plan.get("weather", {})
            if weather:
                temp = weather.get("temp_c", "N/A")
                condition = weather.get("condition", "")
                feels_like = weather.get("feels_like_c", temp)
                humidity = weather.get("humidity", "N/A")
                
                # Weather icon based on condition
                weather_icon = "🌤️"
                if "rain" in condition.lower() or "drizzle" in condition.lower():
                    weather_icon = "🌧️"
                elif "snow" in condition.lower():
                    weather_icon = "❄️"
                elif "cloud" in condition.lower():
                    weather_icon = "☁️"
                elif "clear" in condition.lower() or "sun" in condition.lower():
                    weather_icon = "☀️"
                elif "storm" in condition.lower() or "thunder" in condition.lower():
                    weather_icon = "⛈️"
                
                st.markdown(f"{weather_icon} **{temp}°C** | {condition}")
                st.caption(f"Feels like {feels_like}°C | Humidity: {humidity}%")
            
            # Trending badge
            if day_plan.get("trending"):
                st.markdown("🔥 **Trending**")
        
        with cols[1]:
            # Show garments with images
            garments_to_show = []
            
            # Hijab first
            if day_plan.get("hijab"):
                garments_to_show.append(("hijab", "🧕 Hijab", day_plan["hijab"]))
            
            # Other garments
            for key in ["dress", "top", "bottom", "outerwear"]:
                item = day_plan.get(key)
                if item:
                    label = key.capitalize()
                    emoji = {"dress": "👗", "top": "👕", "bottom": "👖", "outerwear": "🧥"}.get(key, "👔")
                    garments_to_show.append((key, f"{emoji} {label}", item))
            
            # Display garments in columns
            if garments_to_show:
                garment_cols = st.columns(len(garments_to_show))
                for idx, (key, label, item) in enumerate(garments_to_show):
                    with garment_cols[idx]:
                        st.markdown(f"**{label}**")
                        safe_image(item.get("image_path"), width=100)
                        st.markdown(f"*{item.get('dominant_color', 'Unknown')}*")
                        st.caption(f"{item.get('category', 'Item')}")
            else:
                st.caption("No outfit generated")
        
        # Reason why this outfit
        why = day_plan.get('why_this_suits_you', '')
        if why:
            st.info(f"� {why}")


def main():
    st.title("📅 Weekly Planner")
    st.subheader("Plan Your Outfits for the Week")
    
    # Tabs
    tab1, tab2 = st.tabs(["Custom Plan", "Quick Plan"])
    
    with tab1:
        st.header("Create Custom Weekly Plan")
        
        # Occasion inputs for each day
        st.markdown("### Set Occasions for Each Day")
        
        occasions = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        cols = st.columns(4)
        for i, day in enumerate(days):
            with cols[i % 4]:
                occasion = st.selectbox(
                    day,
                    ["Casual", "Formal", "Academic", "Business", "Party", "Wedding", "Date Night"],
                    key=f"occasion_{i}"
                )
                occasions.append(occasion)
        
        style_pref = st.radio(
            "Style Preference",
            ["Western", "Eastern"],
            horizontal=True
        )
        
        if st.button("📅 Plan My Week", type="primary", use_container_width=True):
            with st.spinner("🎨 Generating your weekly plan... This may take a moment."):
                plan_data = get_weekly_plan(occasions, style_pref)
            
            if plan_data.get("error"):
                st.error(f"❌ {plan_data['error']}")
            else:
                st.success("✅ Weekly plan generated!")
                
                # Show stats
                stats = plan_data.get("stats", {})
                
                scol1, scol2, scol3, scol4 = st.columns(4)
                
                with scol1:
                    st.metric("Avg Score", f"{stats.get('average_score', 0):.1f}")
                with scol2:
                    st.metric("Trending Days", stats.get('trending_days', 0))
                with scol3:
                    st.metric("Unique Items", stats.get('unique_garments_used', 0))
                with scol4:
                    st.metric("Coverage", f"{stats.get('coverage_percentage', 0):.0f}%")
                
                # Show plan
                st.markdown("---")
                st.header("Your Weekly Plan")
                
                plan = plan_data.get("plan", [])
                
                for i, day_plan in enumerate(plan):
                    with st.expander(f"📅 {day_plan.get('day_name', f'Day {i+1}')} - {day_plan.get('occasion', 'Casual')}", expanded=i==0):
                        render_day_outfit(day_plan, i+1)
                        
                        st.markdown("---")
                        st.markdown("### ✨ Why This Works")
                        st.write(day_plan.get("why_this_suits_you", ""))
                        
                        if day_plan.get("weather_explanation"):
                            st.markdown("### 🌤️ Weather Context")
                            st.write(day_plan.get("weather_explanation"))
                
                # Download option
                st.markdown("---")
                plan_text = (
                    f"Adorkable AI - Weekly Outfit Plan\n"
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"Stats:\n"
                    f"- Average Score: {stats.get('average_score', 0):.1f}/105\n"
                    f"- Trending Days: {stats.get('trending_days', 0)}\n"
                    f"- Unique Items Used: {stats.get('unique_garments_used', 0)}\n\n"
                    f"Daily Outfits:\n"
                )
                
                for day_plan in plan:
                    day_name = day_plan.get('day_name', 'Day')
                    date_str = day_plan.get('date', '')
                    occasion = day_plan.get('occasion', 'Casual')
                    score = day_plan.get('score', 0)
                    
                    plan_text += f"\n{day_name} ({date_str}) - {occasion}\n"
                    plan_text += f"Score: {score:.1f}\n"
                    
                    items = []
                    # Add hijab first if present
                    if day_plan.get("hijab"):
                        hijab_color = day_plan["hijab"].get('dominant_color', 'Unknown')
                        items.append(f"{hijab_color} Hijab")
                    
                    for key in ["top", "bottom", "dress", "outerwear"]:
                        item = day_plan.get(key)
                        if item:
                            color = item.get('dominant_color', 'Unknown')
                            cat = item.get('category', 'Item')
                            items.append(f"{color} {cat}")
                    
                    if items:
                        plan_text += f"Outfit: {' + '.join(items)}\n\n"
                
                st.download_button(
                    "📥 Download Plan (Text)",
                    plan_text,
                    file_name="weekly_plan.txt",
                    mime="text/plain"
                )
    
    with tab2:
        st.header("Quick Plan")
        st.info("Generate a quick 7-day plan with default occasion pattern (alternating casual/formal)")
        
        if st.button("⚡ Generate Quick Plan", type="primary", use_container_width=True):
            with st.spinner("Generating quick plan..."):
                plan_data = get_quick_plan()
            
            if plan_data.get("error"):
                st.error(f"❌ {plan_data['error']}")
            else:
                st.success("✅ Quick plan generated!")
                
                stats = plan_data.get("stats", {})
                
                scol1, scol2 = st.columns(2)
                with scol1:
                    st.metric("Average Score", f"{stats.get('average_score', 0):.1f}")
                with scol2:
                    st.metric("Trending Days", stats.get('trending_days', 0))
                
                plan = plan_data.get("plan", [])
                
                for i, day_plan in enumerate(plan):
                    with st.expander(f"{day_plan.get('day_name', f'Day {i+1}')}", expanded=i==0):
                        render_day_outfit(day_plan, i+1)


if __name__ == "__main__":
    main()


# ✅ frontend/pages/5_Weekly_Planner.py generated — Adorkable AI
