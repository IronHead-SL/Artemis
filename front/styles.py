from __future__ import annotations

import streamlit as st
from constants import PRIMARY, ACCENT, BG_DARK, BG_CARD, BG_CARD2, TEXT_PRIMARY, TEXT_MUTED, BORDER

GLOBAL_CSS = f"""
<style>
:root {{
    --primary: {PRIMARY};
    --accent:  {ACCENT};
    --bg:      {BG_DARK};
    --card:    {BG_CARD};
    --card2:   {BG_CARD2};
    --text:    {TEXT_PRIMARY};
    --muted:   {TEXT_MUTED};
    --border:  {BORDER};
    --radius:  4px;
    --shadow:  0 4px 24px rgba(0,0,0,0.5);
}}

html, body, [data-testid="stAppViewContainer"] {{
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}}

[data-testid="stSidebar"]      {{ display: none; }}
[data-testid="stToolbar"]      {{ display: none; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
footer                         {{ display: none; }}
#MainMenu                      {{ display: none; }}

.main .block-container {{
    max-width: 1200px !important;
    padding: 2rem 2rem !important;
    margin: 0 auto;
}}

h1, h2, h3 {{ letter-spacing: -0.02em; }}

.stButton > button {{
    background: transparent !important;
    border: 1px solid var(--primary) !important;
    color: var(--primary) !important;
    border-radius: var(--radius) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    padding: 0.45rem 1.1rem !important;
    transition: all 0.2s ease !important;
}}
.stButton > button:hover {{
    background: var(--primary) !important;
    color: #fff !important;
}}
.stButton > button[kind="primary"] {{
    background: var(--primary) !important;
    color: #fff !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}}

[data-testid="stFileUploader"] {{
    border: 1px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--card) !important;
    transition: border-color 0.2s;
}}
[data-testid="stFileUploader"]:hover {{ border-color: var(--primary) !important; }}

.artwork-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    cursor: pointer;
    height: 100%;
}}
.artwork-card:hover {{
    transform: translateY(-3px);
    box-shadow: var(--shadow);
    border-color: var(--primary);
}}
.artwork-card img {{ width: 100%; aspect-ratio: 3/4; object-fit: cover; display: block; }}
.card-meta {{ padding: 0.75rem; }}
.card-title {{ font-size: 0.9rem; line-height: 1.3; margin: 0 0 0.2rem 0; color: var(--text); }}
.card-artist {{ font-size: 0.75rem; color: var(--muted); margin: 0; }}

.similarity-badge {{
    display: inline-block;
    background: rgba(46,134,171,0.15);
    color: var(--primary);
    border: 1px solid rgba(46,134,171,0.3);
    border-radius: 20px;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    padding: 0.15rem 0.55rem;
    margin-top: 0.4rem;
}}

.detail-title {{
    font-size: 1.9rem; font-weight: 700; line-height: 1.2;
    margin: 0 0 0.3rem 0; color: var(--text);
}}
.detail-artist {{ font-size: 1rem; color: var(--primary); margin: 0 0 0.15rem 0; }}
.detail-year   {{ font-size: 0.85rem; color: var(--muted); margin: 0 0 1rem 0; }}

.detail-meta-row {{ display: flex; gap: 1.5rem; margin-bottom: 1rem; flex-wrap: wrap; }}
.meta-item {{ font-size: 0.8rem; color: var(--muted); }}
.meta-item strong {{
    display: block; color: var(--text); font-weight: 500;
    font-size: 0.75rem; text-transform: uppercase;
    letter-spacing: 0.07em; margin-bottom: 0.15rem;
}}

.explanation-text {{
    font-size: 0.95rem; line-height: 1.75; color: var(--text);
    border-left: 2px solid var(--accent);
    padding-left: 1rem; margin: 1.2rem 0;
}}

.section-label {{
    font-size: 0.7rem; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--muted); margin-bottom: 0.75rem;
}}

.site-title {{
    font-size: 1.6rem; font-weight: 700;
    color: #ff3131; letter-spacing: -0.02em;
}}
.site-subtitle {{
    font-size: 0.78rem; color: var(--muted);
    letter-spacing: 0.1em; text-transform: uppercase; margin-top: 0.2rem;
}}

.upload-zone {{ max-width: 640px; margin: 0 auto; text-align: center; padding: 3rem 2rem; }}
.upload-eyebrow {{ font-size: 1.0rem; text-transform: uppercase; letter-spacing: 0.15em; color: var(--primary); margin-bottom: 0.75rem; }}
.upload-headline {{ font-size: 2.2rem; line-height: 1.2; margin-bottom: 0.75rem; }}
.upload-body {{ font-size: 0.9rem; color: var(--muted); margin-bottom: 2rem; line-height: 1.6; }}

.error-box {{
    background: rgba(162,59,114,0.1);
    border: 1px solid rgba(162,59,114,0.4);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    font-size: 0.85rem; color: #e08cbc;
}}

.subtle-divider {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}

[data-testid="stSpinner"] > div {{ color: var(--primary) !important; }}
[data-testid="stImage"] img {{ border-radius: var(--radius); }}
[data-testid="column"] {{ padding: 0 0.4rem; }}
</style>
"""


def inject_css() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
