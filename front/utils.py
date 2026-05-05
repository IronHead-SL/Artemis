from __future__ import annotations

import base64
import io
import random
from typing import Optional

import streamlit as st
from PIL import Image

PRIMARY      = "#ff3131"
ACCENT       = "#A23B72"
BG_DARK      = "#0D0D0D"
BG_CARD      = "#161616"
BG_CARD2     = "#1E1E1E"
TEXT_PRIMARY = "#F0EDE8"
TEXT_MUTED   = "#8A8580"
BORDER       = "#2A2A2A"

SPINNER_MESSAGES = [
    "Analyzing visual patterns…",
    "Traversing centuries of art…",
    "Consulting the museum archives…",
    "Matching brushstrokes and hues…",
    "Curating your personal exhibition…",
]


def random_spinner_msg() -> str:
    return random.choice(SPINNER_MESSAGES)


GLOBAL_CSS = f"""
<style>
/* ── Fonts ── */

/* ── Root variables ── */
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

/* ── Global reset ── */
html, body, [data-testid="stAppViewContainer"] {{
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}}

[data-testid="stSidebar"] {{ display: none; }}
[data-testid="stToolbar"]  {{ display: none; }}
footer                     {{ display: none; }}
#MainMenu                  {{ display: none; }}

/* ── Main container ── */
.main .block-container {{
    max-width: 1200px !important;
    padding: 2rem 2rem !important;
    margin: 0 auto;
}}

/* ── Typography ── */
h1, h2, h3 {{
    letter-spacing: -0.02em;
}}

/* ── Buttons ── */
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

/* ── File uploader ── */
[data-testid="stFileUploader"] {{
    border: 1px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--card) !important;
    transition: border-color 0.2s;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: var(--primary) !important;
}}

/* ── Artwork cards ── */
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
.artwork-card img {{
    width: 100%;
    aspect-ratio: 3/4;
    object-fit: cover;
    display: block;
}}
.card-meta {{
    padding: 0.75rem;
}}
.card-title {{
    font-size: 0.9rem;
    line-height: 1.3;
    margin: 0 0 0.2rem 0;
    color: var(--text);
}}
.card-artist {{
    font-size: 0.75rem;
    color: var(--muted);
    margin: 0;
}}
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

/* ── Detail view ── */
.detail-container {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem;
    margin-bottom: 2rem;
}}
.detail-title {{
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1.2;
    margin: 0 0 0.3rem 0;
    color: var(--text);
}}
.detail-artist {{
    font-size: 1rem;
    color: var(--primary);
    margin: 0 0 0.15rem 0;
}}
.detail-year {{
    font-size: 0.85rem;
    color: var(--muted);
    margin: 0 0 1rem 0;
}}
.detail-meta-row {{
    display: flex;
    gap: 1.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
}}
.meta-item {{
    font-size: 0.8rem;
    color: var(--muted);
}}
.meta-item strong {{
    display: block;
    color: var(--text);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.15rem;
}}
.explanation-text {{
    font-size: 0.95rem;
    line-height: 1.75;
    color: var(--text);
    border-left: 2px solid var(--accent);
    padding-left: 1rem;
    margin: 1.2rem 0;
}}
.section-label {{
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--muted);
    margin-bottom: 0.75rem;
}}

/* ── Breadcrumb ── */
.breadcrumb {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
}}
.breadcrumb-sep {{ color: var(--border); }}
.breadcrumb-current {{ color: var(--text); }}

/* ── Header ── */
.site-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 3rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}}
.site-title {{
    font-size: 1.6rem;
    font-weight: 700;
    color: #ff3131;
    letter-spacing: -0.02em;
}}

.site-subtitle {{
    font-size: 0.78rem;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 0.2rem;
}}

/* ── New Header Logo ── */
.header-logo {{
    display: flex;
    align-items: center;
    gap: 1rem; /* Space between logo and text */
}}

/* ── Upload zone ── */
.upload-zone {{
    max-width: 640px;
    margin: 0 auto;
    text-align: center;
    padding: 3rem 2rem;
}}
.upload-eyebrow {{
    font-size: 1.0rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--primary);
    margin-bottom: 0.75rem;
}}
.upload-headline {{
    font-size: 2.2rem;
    line-height: 1.2;
    margin-bottom: 0.75rem;
}}
.upload-body {{
    font-size: 0.9rem;
    color: var(--muted);
    margin-bottom: 2rem;
    line-height: 1.6;
}}

/* ── Error box ── */
.error-box {{
    background: rgba(162,59,114,0.1);
    border: 1px solid rgba(162,59,114,0.4);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    font-size: 0.85rem;
    color: #e08cbc;
}}

/* ── Related thumbnails ── */
.related-thumb {{
    background: var(--card2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    cursor: pointer;
    transition: border-color 0.15s, transform 0.15s;
}}
.related-thumb:hover {{
    border-color: var(--accent);
    transform: translateY(-2px);
}}

/* ── Divider ── */
.subtle-divider {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0;
}}

/* ── Spinner override ── */
[data-testid="stSpinner"] > div {{
    color: var(--primary) !important;
}}

/* ── Image display ── */
[data-testid="stImage"] img {{
    border-radius: var(--radius);
}}

/* ── Streamlit columns gap fix ── */
[data-testid="column"] {{ padding: 0 0.4rem; }}
</style>
"""


def inject_css() -> None:
    """Inject global CSS into the Streamlit page."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def pil_to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def image_to_base64(img_bytes: bytes) -> str:
    return base64.b64encode(img_bytes).decode()


def load_image_safe(uploaded_file) -> Optional[Image.Image]:
    """Load a PIL Image from an uploaded file, return None on failure."""
    try:
        img = Image.open(uploaded_file).convert("RGB")
        return img
    except Exception:
        return None


def resize_image(img: Image.Image, max_size: int = 600) -> Image.Image:
    """Resize image while preserving aspect ratio."""
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    scale = max_size / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def render_header(show_new_search: bool = False) -> None:
    """Render the site-wide header."""
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        # Load and process the logo for the header
        try:
            img = Image.open("artemis-logo.png")
            resized_logo_header = resize_image(img, 45)
            
            # Convert to base64 to embed in HTML
            img_base64 = image_to_base64(pil_to_bytes(resized_logo_header, fmt='PNG'))
            
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 12px;">
                    <img src="data:image/png;base64,{img_base64}" width="45px">
                    <div>
                        <div class="site-title">ARTEMIS</div>
                        <div class="site-subtitle">AI-Powered Art Discovery</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        except Exception:
            # Fallback if image fails to load
            st.markdown('<div class="site-title">ARTEMIS</div>', unsafe_allow_html=True)
    with col_btn:
        if show_new_search:
            if st.button("New Search", key="new_search_header"):
                _reset_state()
                st.rerun()
    st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)


def _reset_state() -> None:
    """Clear all session state to start fresh."""
    for key in ["uploaded_image", "recommendations", "selected_artwork",
                 "artwork_history", "artwork_details_cache"]:
        st.session_state.pop(key, None)


def render_breadcrumb() -> None:
    """Render navigation breadcrumb based on artwork_history."""
    history: list = st.session_state.get("artwork_history", [])
    if not history:
        return

    parts = ["<span>Recommendations</span>"]
    for i, item in enumerate(history):
        label = item.get("title", f"Artwork {i+1}")
        label = label[:30] + "…" if len(label) > 30 else label
        if i < len(history) - 1:
            parts.append(f"<span class='breadcrumb-sep'>›</span>")
            parts.append(f"<span>{label}</span>")
        else:
            parts.append(f"<span class='breadcrumb-sep'>›</span>")
            parts.append(f"<span class='breadcrumb-current'>{label}</span>")

    st.markdown(
        f"<div class='breadcrumb'>{''.join(parts)}</div>",
        unsafe_allow_html=True,
    )


def render_artwork_card_html(artwork: dict, idx: int) -> str:
    """Return HTML string for a single artwork card (display-only)."""
    title = artwork.get("title", "Untitled")[:60]
    artist = artwork.get("artist", "Unknown Artist")
    year = artwork.get("year", "")
    similarity = artwork.get("similarity_score", None)
    thumb_url = artwork.get("thumbnail_url") or artwork.get("image_url", "")

    badge_html = ""
    if similarity is not None:
        badge_html = f"<div class='similarity-badge'>{int(similarity * 100)}% match</div>"

    img_html = ""
    if thumb_url:
        img_html = f"<img src='{thumb_url}' alt='{title}' loading='lazy'>"
    else:
        img_html = "<div style='width:100%;aspect-ratio:3/4;background:linear-gradient(135deg,#1a1a1a,#2a2a2a);'></div>"

    year_txt = f" · {year}" if year else ""

    return f"""
    <div class="artwork-card" title="{title}">
        {img_html}
        <div class="card-meta">
            <p class="card-title">{title}</p>
            <p class="card-artist">{artist}{year_txt}</p>
            {badge_html}
        </div>
    </div>
    """


def render_error(msg: str) -> None:
    st.markdown(f"<div class='error-box'>⚠ {msg}</div>", unsafe_allow_html=True)


def render_upload_prompt() -> None:
    st.markdown(
        """
        <div class="upload-zone">
            <div class="upload-eyebrow">Discover Art</div>
            <h1 class="upload-headline">Find Art Inspired by You</h1>
            <p class="upload-body">
                Upload any image — a painting, photograph, or visual inspiration —
                and Artemis will surface artworks across centuries that share
                its visual DNA.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def similarity_pct(score: float) -> str:
    return f"{int(score * 100)}%"

def init_session_state() -> None:
    """Initialize all required session state keys."""
    defaults = {
        "uploaded_image":       None,
        "recommendations":      None,
        "selected_artwork":     None,
        "artwork_history":      [],
        "artwork_details_cache": {},
        "loading_states":       {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def push_history(artwork_id: str, title: str) -> None:
    hist: list = st.session_state.get("artwork_history", [])
    if not hist or hist[-1].get("id") != artwork_id:
        hist.append({"id": artwork_id, "title": title})
    st.session_state["artwork_history"] = hist


def get_cached_details(artwork_id: str) -> Optional[dict]:
    return st.session_state.get("artwork_details_cache", {}).get(artwork_id)


def cache_details(artwork_id: str, details: dict) -> None:
    cache = st.session_state.get("artwork_details_cache", {})
    cache[artwork_id] = details
    st.session_state["artwork_details_cache"] = cache