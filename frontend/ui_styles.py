"""
Shared Streamlit UI theme for Adorkable AI.

Inject once per page after st.set_page_config() for consistent dark styling,
readable contrast on tips/cards, and polished tabs/buttons.
"""

from __future__ import annotations

import streamlit as st

_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,400;600;700&display=swap');

:root {
  --ado-accent: #E91E8C;
  --ado-accent-soft: rgba(233, 30, 140, 0.18);
  --ado-accent-glow: rgba(233, 30, 140, 0.35);
  --ado-surface: #16182a;
  --ado-surface-2: #1e2138;
  --ado-border: rgba(255, 255, 255, 0.08);
  --ado-text: #f4f6fb;
  --ado-muted: #9ca3b8;
  --ado-violet: #8b5cf6;
}

html, body, [class*="css"] {
  font-family: 'Instrument Sans', 'Inter', system-ui, sans-serif !important;
}

h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: 'Fraunces', 'Playfair Display', Georgia, serif !important;
  letter-spacing: -0.02em;
  font-weight: 600 !important;
}

/* Main column breathing room */
.block-container {
  padding-top: 2rem !important;
  padding-bottom: 3rem !important;
  max-width: 1100px !important;
}

/* Sidebar polish */
[data-testid="stSidebar"] {
  border-right: 1px solid var(--ado-border);
  background: linear-gradient(180deg, #12131f 0%, #0f1018 100%) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  color: var(--ado-muted);
  font-size: 0.9rem;
}
[data-testid="stSidebar"] hr {
  border-color: var(--ado-border);
  margin: 1rem 0;
}

/* Tabs: dark-selected, accent underline */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px;
  background: transparent !important;
  padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
  height: auto !important;
  min-height: 44px;
  padding: 10px 16px !important;
  border-radius: 10px 10px 0 0 !important;
  color: var(--ado-muted) !important;
  background: transparent !important;
}
.stTabs [data-baseweb="tab"] p {
  color: inherit !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(180deg, var(--ado-accent-soft) 0%, transparent 100%) !important;
  border-bottom: 3px solid var(--ado-accent) !important;
  color: var(--ado-text) !important;
  font-weight: 600 !important;
}
.stTabs [aria-selected="false"] {
  border-bottom: 3px solid transparent !important;
}

/* Primary buttons */
.stButton button[kind="primary"] {
  background: linear-gradient(135deg, #E91E8C 0%, #c026d3 50%, #7c3aed 100%) !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 20px rgba(233, 30, 140, 0.25);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.stButton button[kind="primary"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(233, 30, 140, 0.35);
}

/* Inputs */
.stTextInput input, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"],
.stRadio div[role="radiogroup"] label {
  border-radius: 10px !important;
}
div[data-baseweb="input"] > div {
  border-radius: 10px !important;
  border-color: var(--ado-border) !important;
}

/* File uploader */
[data-testid="stFileUploader"] section {
  border: 1px dashed var(--ado-accent-glow) !important;
  border-radius: 14px !important;
  background: var(--ado-surface) !important;
}

/* Metrics */
[data-testid="stMetricValue"] {
  font-variant-numeric: tabular-nums;
}

/* ---- Legacy class overrides (pages use these in HTML markdown) ---- */
.profile-card,
.auth-form {
  background: linear-gradient(145deg, var(--ado-surface) 0%, var(--ado-surface-2) 100%) !important;
  border: 1px solid var(--ado-border) !important;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.35) !important;
  color: var(--ado-text) !important;
}
.profile-card p, .auth-form p, .profile-card h3, .auth-form h3 {
  color: var(--ado-text) !important;
}

.status-pending {
  background: rgba(255,255,255,0.08) !important;
  color: var(--ado-muted) !important;
}

.upload-section {
  background: linear-gradient(145deg, #1a1d2f 0%, #222642 100%) !important;
  border: 1px solid var(--ado-border) !important;
  border-left: 4px solid var(--ado-accent) !important;
  box-shadow: 0 4px 28px rgba(0, 0, 0, 0.28);
  padding: 25px !important;
  border-radius: 14px !important;
  margin-bottom: 1rem !important;
  color: var(--ado-text) !important;
}
.upload-section h4 {
  color: var(--ado-text) !important;
}
.upload-section p {
  color: var(--ado-muted) !important;
}

.ado-tip-panel {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--ado-border);
  padding: 16px !important;
  border-radius: 12px !important;
  font-size: 0.92rem !important;
  color: var(--ado-text) !important;
}
.ado-tip-panel strong {
  color: var(--ado-text) !important;
}
.ado-tip-panel ul, .ado-tip-panel li {
  color: var(--ado-muted) !important;
}

.analysis-result {
  background: linear-gradient(135deg, #5b21b6 0%, var(--ado-accent) 55%, #c026d3 100%) !important;
  color: #ffffff !important;
  padding: 22px !important;
  border-radius: 14px !important;
  margin: 16px 0 !important;
  box-shadow: 0 12px 40px rgba(91, 33, 182, 0.25);
}

.brand-tagline {
  color: var(--ado-muted) !important;
}

.brand-title {
  background: linear-gradient(135deg, #fbcfe8 0%, var(--ado-accent) 45%, var(--ado-violet) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.auth-form .stTabs [aria-selected="true"] p {
  color: var(--ado-text) !important;
}

.info-box {
  background: linear-gradient(145deg, var(--ado-surface) 0%, #252845 100%) !important;
  border: 1px solid var(--ado-border) !important;
  border-left: 4px solid var(--ado-violet) !important;
  border-radius: 16px !important;
  padding: 24px !important;
  color: var(--ado-text) !important;
}
.info-box h3 {
  color: var(--ado-text) !important;
}
.info-box span {
  color: var(--ado-muted) !important;
}

.divider-fancy {
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--ado-accent), var(--ado-violet), transparent);
  margin: 2rem 0;
  border: none;
  opacity: 0.85;
}

/* Daily outfit decorative classes (when used later) */
.outfit-card {
  background: linear-gradient(145deg, var(--ado-surface) 0%, var(--ado-surface-2) 100%) !important;
  border: 1px solid var(--ado-border);
  border-radius: 16px;
  overflow: hidden;
}
.garment-item {
  background: rgba(255,255,255,0.04) !important;
  border-left: 4px solid var(--ado-accent);
  border-radius: 12px;
}
.weather-card {
  background: linear-gradient(145deg, rgba(233,30,140,0.08) 0%, rgba(124,58,237,0.08) 100%) !important;
  border: 1px solid var(--ado-border);
  border-radius: 12px;
  color: var(--ado-text) !important;
}
.explanation-box {
  background: linear-gradient(135deg, rgba(253,224,71,0.12) 0%, rgba(233,30,140,0.08) 100%) !important;
  border-left: 4px solid #fbbf24 !important;
  color: var(--ado-text) !important;
}

/* Alerts: slightly tighter */
[data-testid="stAlert"] {
  border-radius: 12px !important;
}

/* Anchored header strip for centered pages */
.ado-brand-stack {
  text-align: center;
  margin-bottom: 1.5rem;
}

</style>
"""


def inject_app_theme(extra_css: str = "") -> None:
    """Apply global CSS. Optional page-specific snippet appended."""
    st.markdown(_THEME_CSS + (extra_css or ""), unsafe_allow_html=True)

