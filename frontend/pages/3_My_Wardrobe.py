"""
Adorkable AI - My Wardrobe Page

Wardrobe management with garment upload and statistics.
"""

import sys
import json
import hashlib
from pathlib import Path

import streamlit as st
import httpx
import plotly.express as px

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from ui_styles import inject_app_theme

st.set_page_config(page_title="My Wardrobe - Adorkable AI", page_icon="👚")

inject_app_theme()

API_BASE = "http://localhost:8006/api/v1"
API_ORIGIN = API_BASE.replace("/api/v1", "").rstrip("/")
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ML analyze/upload can exceed httpx default (~5s)
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

def get_wardrobe():
    """Fetch wardrobe."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(
            f"{API_BASE}/wardrobe/", headers=headers, timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching wardrobe: {e}")
        return []


def get_wardrobe_stats():
    """Fetch wardrobe stats."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(
            f"{API_BASE}/wardrobe/stats", headers=headers, timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def upload_garment(file_bytes, category, tradition, dominant_color, color_hex, fabric_weight, occasion_tags):
    """Upload garment with user-specified category and tradition."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}

        # Derive style from tradition
        style = "traditional_eastern" if tradition == "Eastern" else "western"

        files = {"file": ("garment.jpg", file_bytes, "image/jpeg")}
        data = {
            "category": category,
            "style": style,
            "dominant_color": dominant_color,
            "color_hex": color_hex,
            "fabric_weight": fabric_weight,
            "occasion_tags": occasion_tags
        }

        response = httpx.post(
            f"{API_BASE}/wardrobe/upload",
            headers=headers,
            files=files,
            data=data,
            timeout=HTTP_TIMEOUT,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": response.json().get("detail", "Upload failed")}
    except Exception as e:
        return {"error": str(e)}


def analyze_garment(file_bytes):
    """Analyze garment image first (no save)."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        files = {"file": ("garment.jpg", file_bytes, "image/jpeg")}
        response = httpx.post(
            f"{API_BASE}/wardrobe/analyze-image",
            headers=headers,
            files=files,
            timeout=HTTP_TIMEOUT,
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Analysis failed")}
    except Exception as e:
        return {"error": str(e)}


def get_preloaded_catalog():
    """Fetch starter wardrobe catalog."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.get(f"{API_BASE}/wardrobe/preloaded/catalog", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []


def import_preloaded_items(items):
    """Import selected starter items."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.post(
            f"{API_BASE}/wardrobe/preloaded/import",
            headers=headers,
            json={"items": items}
        )
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Import failed")}
    except Exception as e:
        return {"error": str(e)}


def analyze_preloaded_items(ids):
    """Analyze selected starter items before import."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.post(
            f"{API_BASE}/wardrobe/preloaded/analyze",
            headers=headers,
            json={"ids": ids}
        )
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except Exception:
        return []


def clear_preloaded_items():
    """Remove imported preloaded items."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.delete(f"{API_BASE}/wardrobe/preloaded/clear", headers=headers)
        if response.status_code == 200:
            return response.json()
        return {"error": "Could not remove starter items"}
    except Exception as e:
        return {"error": str(e)}


def resolve_image_path(path_str: str) -> str:
    """Resolve DB-stored paths (relative to app root) for local display."""
    if not path_str:
        return path_str
    raw = path_str.replace("\\", "/")
    p = Path(raw)
    if p.is_absolute() and p.exists():
        return str(p)
    candidate = PROJECT_ROOT / raw
    if candidate.exists():
        return str(candidate)
    # Legacy rows: relpath from wrong cwd (e.g. ..\\uploads\\...)
    alt = (PROJECT_ROOT / Path(raw).name)
    if alt.exists():
        return str(alt)
    return str(candidate)


def safe_image(image_path: str, caption: str = ""):
    """Render image from disk or fall back to backend /uploads static URL."""
    resolved = resolve_image_path(image_path)
    if resolved and Path(resolved).exists():
        st.image(resolved, caption=caption, width="stretch")
        return
    norm = (image_path or "").replace("\\", "/").lstrip("/")
    if norm.startswith("uploads/"):
        url = f"{API_ORIGIN}/{norm}"
        st.image(url, caption=caption, width="stretch")
        return
    st.caption(f"Image missing: {Path(resolved).name if resolved else 'unknown'}")


def map_category_with_tradition(base_category: str, tradition: str) -> str:
    """Map category to eastern/western taxonomy."""
    cat = (base_category or "").lower()
    tradition = (tradition or "Western").lower()
    if tradition == "eastern":
        if cat == "top":
            return "traditional_top"
        if cat == "bottom":
            return "traditional_bottom"
    return cat


def infer_tradition_from_analysis(analysis: dict) -> str:
    """Infer Eastern/Western from analyzed category."""
    category = (analysis.get("category") or "").lower()
    if "traditional" in category:
        return "Eastern"
    return "Western"


def mark_as_worn(item_id):
    """Mark garment as worn."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.patch(f"{API_BASE}/wardrobe/{item_id}/wear", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def delete_garment(item_id):
    """Delete garment."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.user_token}"}
        response = httpx.delete(f"{API_BASE}/wardrobe/{item_id}", headers=headers)
        
        if response.status_code == 200:
            return True
        return False
    except Exception:
        return False


# =============================================================================
# UI
# =============================================================================

def main():
    st.title("👚 My Wardrobe")
    st.subheader("Manage Your Clothing Collection")
    
    # Tab switching via query params - side by side buttons
    query_tab = st.query_params.get("tab", "wardrobe")
    
    tab_options = {
        "wardrobe": "👕 My Garments",
        "upload": "⬆️ Upload New",
        "starter": "📦 Starter Wardrobe",
        "stats": "📊 Statistics"
    }
    
    # Use columns for side-by-side buttons
    cols = st.columns(4)
    selected_tab = query_tab if query_tab in tab_options else "wardrobe"
    
    for idx, (tab_key, tab_label) in enumerate(tab_options.items()):
        with cols[idx]:
            button_type = "primary" if selected_tab == tab_key else "secondary"
            if st.button(tab_label, key=f"tab_{tab_key}", type=button_type, use_container_width=True):
                st.query_params["tab"] = tab_key
                st.rerun()
    
    # Content based on selected tab
    if selected_tab == "wardrobe":
        st.header("Your Garments")
        
        wardrobe = get_wardrobe()
        
        if not wardrobe:
            st.info("Your wardrobe is empty. Upload some garments to get started!")
        else:
            # Filter by category
            categories = list(set(g.get("category", "Unknown") for g in wardrobe))
            selected_category = st.selectbox(
                "Filter by category",
                ["All"] + categories
            )
            
            # Filter wardrobe
            if selected_category != "All":
                filtered = [g for g in wardrobe if g.get("category") == selected_category]
            else:
                filtered = wardrobe
            
            # Display in grid
            cols = st.columns(3)
            
            for i, garment in enumerate(filtered):
                with cols[i % 3]:
                    with st.container():
                        # Image
                        try:
                            safe_image(garment.get("image_path"))
                        except:
                            st.markdown(f"📷 {garment.get('category', 'Item')}")
                        
                        # Details
                        st.markdown(f"**{garment.get('dominant_color', 'Unknown')} {garment.get('category', 'Item')}**")
                        st.caption(f"Style: {garment.get('style', 'Unknown')}")
                        st.caption(f"Fabric: {garment.get('fabric_weight', 'Unknown')}")
                        st.caption(f"Worn: {garment.get('wear_count', 0)} times")
                        
                        # Actions
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✓ Worn", key=f"wear_{garment['id']}"):
                                result = mark_as_worn(garment['id'])
                                if result:
                                    st.success("Marked!")
                                    st.rerun()
                        
                        with c2:
                            if st.button("🗑️", key=f"del_{garment['id']}"):
                                if delete_garment(garment['id']):
                                    st.success("Deleted!")
                                    st.rerun()
                        
                        st.markdown("---")
    
    elif selected_tab == "upload":
        st.header("Upload New Garment")
        
        st.markdown("AI analyzes first, then you can correct category/style/color before saving.")

        uploaded_file = st.file_uploader(
            "Choose garment image",
            type=["jpg", "jpeg", "png"]
        )

        if uploaded_file:
            st.image(uploaded_file, caption="Preview", width="stretch")

        if "upload_analysis" not in st.session_state:
            st.session_state.upload_analysis = None
        if "upload_analysis_sig" not in st.session_state:
            st.session_state.upload_analysis_sig = None

        if uploaded_file and st.button("🔍 Analyze with AI", type="secondary"):
            with st.spinner("Analyzing garment..."):
                file_bytes = uploaded_file.getvalue()
                st.session_state.upload_analysis = analyze_garment(file_bytes)
                st.session_state.upload_analysis_sig = hashlib.sha256(file_bytes).hexdigest()

        analysis = st.session_state.upload_analysis or {}
        if analysis.get("error"):
            st.error(analysis["error"])
        elif analysis and not analysis.get("error") and uploaded_file:
            st.markdown("#### Analysis Results")
            ar1, ar2 = st.columns(2)
            with ar1:
                inferred_tradition = infer_tradition_from_analysis(analysis)
                st.markdown(
                    f"**Category:** {analysis.get('category', '—').replace('_', ' ').title()}  \n"
                    f"**Style:** {analysis.get('style', '—').replace('_', ' ').title()}  \n"
                    f"**Tradition:** {inferred_tradition}  \n"
                    f"**Fabric Weight:** {analysis.get('fabric_weight', '—')}"
                )
            with ar2:
                st.markdown("**Dominant Color:**")
                cname = analysis.get("dominant_color", "—")
                st.markdown(
                    f'<p style="word-wrap:break-word;">{cname}</p>',
                    unsafe_allow_html=True,
                )
                ch = analysis.get("color_hex", "#808080")
                st.markdown(
                    f'<div style="width:100%;max-width:120px;height:36px;background-color:{ch};border:1px solid #666;border-radius:6px;"></div>',
                    unsafe_allow_html=True,
                )
                st.image(uploaded_file.getvalue(), caption="Your photo", width="stretch")

        st.markdown("#### Review / Correct AI Result")

        col1, col2 = st.columns(2)

        with col1:
            detected_tradition = infer_tradition_from_analysis(analysis) if analysis else "Western"
            tradition = st.selectbox(
                "Clothing Type",
                ["Western", "Eastern"],
                index=0 if detected_tradition == "Western" else 1,
                help="Tell AI if this garment is western or eastern."
            )
            category = st.selectbox(
                "Category *",
                ["Top", "Bottom", "Dress", "Outerwear", "Shoes", "Accessory", "Hijab"],
                index=["top", "bottom", "dress", "outerwear", "shoes", "accessory", "hijab"].index(
                    analysis.get("category", "top")
                ) if analysis.get("category", "top") in ["top", "bottom", "dress", "outerwear", "shoes", "accessory"] else 0,
                help="What type of clothing is this?"
            )

            fabric_weight = st.selectbox(
                "Fabric Weight",
                ["light", "light-medium", "medium", "medium-heavy", "heavy"],
                help="How heavy/thick is the fabric?"
            )

        with col2:
            dominant_color = st.text_input("Dominant Color", value=analysis.get("dominant_color", ""))
            default_hex = analysis.get("color_hex", "#808080")
            color_hex = st.color_picker("Color Hex Wheel", value=default_hex)

            occasions = st.multiselect(
                "Occasions",
                ["Casual", "Formal", "Academic", "Business", "Party", "Wedding", "Sports"],
                default=["Casual"]
            )

        st.caption("Upload flow: Analyze first -> correct fields -> Save to database.")
        st.caption("Only analyzed garments are allowed to be saved.")

        if uploaded_file and st.button("Upload & Save Garment", type="primary"):
            current_sig = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
            if not analysis or analysis.get("error"):
                st.error("Please run garment analysis first.")
                st.stop()
            if st.session_state.upload_analysis_sig != current_sig:
                st.error("Image changed after analysis. Please analyze again before saving.")
                st.stop()
            with st.spinner("Analyzing color and saving garment..."):
                occasion_str = json.dumps(occasions)

                result = upload_garment(
                    uploaded_file.getvalue(),
                    map_category_with_tradition(category.lower(), tradition),
                    tradition,
                    dominant_color,
                    color_hex,
                    fabric_weight,
                    occasion_str
                )
                
                if result.get("error"):
                    st.error(f"❌ {result['error']}")
                else:
                    st.success("✅ Garment uploaded successfully!")

                    # Show results in a nice card
                    st.markdown("### 📊 Analysis Results")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"""
                        **Category:** {result.get('category', 'Unknown').replace('_', ' ').title()}  
                        **Style:** {result.get('style', 'Unknown').replace('_', ' ').title()}  
                        **Fabric Weight:** {result.get('fabric_weight', 'Unknown')}
                        """)
                    with col2:
                        hex_color = color_hex or result.get('color_hex', '#808080')
                        color_label = dominant_color or result.get("dominant_color", "Unknown")
                        st.markdown("**Dominant Color:**")
                        st.markdown(
                            f'<p style="word-wrap:break-word;">{color_label}</p>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div style="width:100%;max-width:120px;height:36px;background-color:{hex_color};border:1px solid #666;border-radius:6px;"></div>',
                            unsafe_allow_html=True,
                        )
                        if uploaded_file:
                            st.image(
                                uploaded_file.getvalue(),
                                caption="Saved garment",
                                width="stretch",
                            )

    elif selected_tab == "starter":
        st.header("Starter Wardrobe")
        st.caption("Import preloaded items, review AI analysis, then save.")

        catalog = get_preloaded_catalog()
        if not catalog:
            st.info("No starter items available.")
        else:
            query = st.text_input("Search starter items", value="").strip().lower()
            tradition_filter = st.selectbox("Tradition", ["All", "Western", "Eastern"])
            filtered_catalog = []
            for item in catalog:
                if tradition_filter != "All" and item.get("tradition") != tradition_filter:
                    continue
                if query:
                    hay = " ".join(
                        [
                            str(item.get("title", "")),
                            str(item.get("category", "")),
                            str(item.get("tradition", "")),
                            " ".join(item.get("search_tags", [])),
                        ]
                    ).lower()
                    if query not in hay:
                        continue
                filtered_catalog.append(item)

            cols = st.columns(3)
            for idx, item in enumerate(filtered_catalog):
                with cols[idx % 3]:
                    safe_image(item.get("image_path"))
                    st.caption(
                        f"{item.get('tradition', 'Western')} • {item.get('category', 'top').replace('_', ' ').title()}"
                    )
                    
                    # Quick Add button for one-click import
                    if st.button(f"➕ Quick Add", key=f"quick_add_{item.get('id')}", type="secondary"):
                        # Import with default values from catalog
                        quick_payload = [{
                            "id": item.get("id"),
                            "category": item.get("category", "top"),
                            "style": "traditional_eastern" if item.get("tradition") == "Eastern" else "western",
                            "dominant_color": item.get("dominant_color", "Unknown"),
                            "color_hex": item.get("color_hex", "#808080"),
                            "fabric_weight": item.get("fabric_weight", "medium"),
                            "occasion_tags": item.get("occasion_tags", ["Casual"])
                        }]
                        result = import_preloaded_items(quick_payload)
                        if result.get("error"):
                            st.error(result["error"])
                        else:
                            st.success(f"✅ Added {item.get('title')}")
                            st.rerun()

            if st.button("🧹 Remove Imported Starter Items"):
                result = clear_preloaded_items()
                if result.get("error"):
                    st.error(result["error"])
                else:
                    st.success(f"Removed {result.get('removed_count', 0)} preloaded items.")
                    st.rerun()
    
    elif selected_tab == "stats":
        st.header("Wardrobe Statistics")
        
        stats = get_wardrobe_stats()
        
        if stats:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Items", stats.get("total_items", 0))
            
            with col2:
                by_cat = stats.get("items_by_category", {})
                if by_cat:
                    top_cat = max(by_cat, key=by_cat.get)
                    st.metric("Most Common", f"{top_cat} ({by_cat[top_cat]})")
            
            with col3:
                by_color = stats.get("items_by_color", {})
                if by_color:
                    top_color = max(by_color, key=by_color.get)
                    st.metric("Top Color", f"{top_color} ({by_color[top_color]})")
            
            # Category breakdown chart
            if by_cat:
                st.markdown("### Items by Category")
                fig = px.pie(
                    values=list(by_cat.values()),
                    names=list(by_cat.keys()),
                    hole=0.4
                )
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            
            # Least worn items
            least_worn = stats.get("least_worn", [])
            if least_worn:
                st.markdown("### Give These Some Love 💕")
                st.caption("Your least worn items:")
                
                for item in least_worn:
                    st.markdown(f"- {item.get('color', 'Unknown')} {item.get('category', 'Item')} "
                              f"(worn {item.get('wear_count', 0)} times)")
        else:
            st.info("Upload garments to see statistics")


if __name__ == "__main__":
    main()


# ✅ frontend/pages/3_My_Wardrobe.py generated — Adorkable AI
