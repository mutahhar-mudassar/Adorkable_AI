"""
Adorkable AI - Analytics Page

Wardrobe analytics and visualizations.
"""

import sys
from collections import Counter
from pathlib import Path

import streamlit as st
import httpx
import plotly.express as px
import plotly.graph_objects as go

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from ui_styles import inject_app_theme

st.set_page_config(page_title="Analytics - Adorkable AI", page_icon="📊", layout="wide")

inject_app_theme()

API_BASE = "http://localhost:8006/api/v1"


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

def get_analytics(endpoint):
    """Fetch analytics data."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/analytics/{endpoint}", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching {endpoint}: {e}")
        return None


def get_dashboard_summary():
    """Fetch dashboard summary."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/analytics/dashboard-summary", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


# =============================================================================
# UI
# =============================================================================

def render_color_distribution():
    """Render color distribution donut chart."""
    st.subheader("🎨 Wardrobe Color Distribution")
    
    data = get_analytics("wardrobe-colors")
    
    if data and len(data) > 0:
        colors = [d.get("color") for d in data]
        counts = [d.get("count") for d in data]
        
        # Create color mapping for the chart
        color_map = {d.get("color"): d.get("hex", "#808080") for d in data}
        
        fig = px.pie(
            names=colors,
            values=counts,
            hole=0.4,
            color=colors,
            color_discrete_map=color_map
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No color data available. Upload garments to see your color palette!")


def render_garment_usage():
    """Render garment usage heatmap/bar chart."""
    st.subheader("👚 Garment Usage Tracker")
    
    data = get_analytics("garment-usage")
    
    if data and len(data) > 0:
        # Create DataFrame-like structure
        labels = [f"{d.get('color', 'Unknown')} {d.get('category', 'Item')}" for d in data]
        wear_counts = [d.get("wear_count", 0) for d in data]
        
        fig = px.bar(
            x=labels,
            y=wear_counts,
            color=wear_counts,
            color_continuous_scale="Viridis",
            labels={"x": "Garment", "y": "Times Worn"}
        )
        
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        
        # Show least worn
        st.caption("💡 Tip: Try wearing your least-worn items this week!")
    else:
        st.info("No usage data available yet. Start wearing your outfits!")


def render_combinability():
    """Render combinability counter."""
    st.subheader("🔗 Wardrobe Combinability")
    
    data = get_analytics("combinability")
    
    if data:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Combos", f"{data.get('total_combinations', 0):,}")
        
        with col2:
            st.metric("Tops", data.get('tops', 0))
        
        with col3:
            st.metric("Bottoms", data.get('bottoms', 0))
        
        with col4:
            st.metric("Dresses", data.get('dresses', 0))
        
        # Explanation
        st.markdown("""
        **How it's calculated:**
        - Top + Bottom combinations: Each top can pair with each bottom
        - Dresses can be standalone or with outerwear
        - Total = (Top×Bottom + Dresses) × Outerwear options
        """)
    else:
        st.info("Upload more garments to see combinability stats!")


def render_outfit_history():
    """Render outfit score history line chart."""
    st.subheader("📈 Outfit Score History")
    
    data = get_analytics("outfit-history")
    
    if data and len(data) > 0:
        dates = [d.get("date") for d in data]
        scores = [d.get("score", 0) for d in data]
        trending = [d.get("trending_badge", False) for d in data]
        
        # Create line chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=scores,
            mode='lines+markers',
            name='Outfit Score',
            line=dict(color='#E91E8C', width=2),
            marker=dict(size=8)
        ))
        
        # Add trending markers
        trending_dates = [d for d, t in zip(dates, trending) if t]
        trending_scores = [s for s, t in zip(scores, trending) if t]
        
        if trending_dates:
            fig.add_trace(go.Scatter(
                x=trending_dates,
                y=trending_scores,
                mode='markers',
                name='Trending Outfits',
                marker=dict(color='gold', size=12, symbol='star')
            ))
        
        fig.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="Score",
            yaxis_range=[0, 105]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No outfit history yet. Generate some daily outfits!")


def render_success_gauge():
    """Render success probability gauge."""
    st.subheader("🎯 Success Probability")
    
    summary = get_dashboard_summary()
    
    if summary:
        last_score = summary.get("last_outfit_score")
        
        if last_score:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=last_score,
                title={'text': "Last Outfit Score"},
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
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No outfit scores yet. Generate your first daily outfit!")


def main():
    st.title("📊 Analytics Dashboard")
    st.subheader("Insights Into Your Wardrobe")
    
    # Dashboard summary at top
    summary = get_dashboard_summary()
    
    if summary:
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", summary.get("total_items", 0))
        
        with col2:
            st.metric("Favorite Color", summary.get("favorite_color", "N/A"))
        
        with col3:
            most_worn = summary.get("most_worn")
            if most_worn:
                st.metric("Most Worn", f"{most_worn['category']} ({most_worn['wear_count']}x)")
            else:
                st.metric("Most Worn", "N/A")
        
        with col4:
            least_worn = summary.get("least_worn")
            if least_worn:
                st.metric("Needs Love", f"{least_worn['category']} ({least_worn['wear_count']}x)")
            else:
                st.metric("Needs Love", "N/A")
    
    st.markdown("---")
    
    # Charts grid
    col1, col2 = st.columns(2)
    
    with col1:
        render_color_distribution()
    
    with col2:
        render_garment_usage()
    
    st.markdown("---")
    
    col3, col4 = st.columns(2)
    
    with col3:
        render_combinability()
    
    with col4:
        render_success_gauge()
    
    st.markdown("---")
    
    # Full width chart
    render_outfit_history()


if __name__ == "__main__":
    main()


# ✅ frontend/pages/7_Analytics.py generated — Adorkable AI
