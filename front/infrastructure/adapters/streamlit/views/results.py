from __future__ import annotations

import base64
import io
import random

import streamlit as st
from PIL import Image

from domain.constants import PRIMARY, SPINNER_MESSAGES
from application.usecases.services import get_artwork_details
from ..components import render_header, render_error
from ..state import store_artwork, get_cached_details, cache_details, push_history
from ...media.image_utils import resize_image, show_image_card


def view_results() -> None:
    render_header(show_new_search=True)
    recommendations: list[dict] = st.session_state["recommendations"]

    col_img, col_txt = st.columns([2, 5], gap="large")
    with col_img:
        try:
            raw = st.session_state["uploaded_image"]
            img = resize_image(Image.open(io.BytesIO(raw)), 500)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode()
            st.markdown(
                f"<img src='data:image/jpeg;base64,{b64}' style='width:100%;border-radius:4px;'>",
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    with col_txt:
        st.markdown(
            f"""<div style='padding-top:0.5rem;'>
                <div style='font-size:0.68rem;text-transform:uppercase;
                            letter-spacing:0.12em;color:{PRIMARY};margin-bottom:0.4rem;'>
                    Your Image · {len(recommendations)} Artworks Found
                </div>
                <h2 style='font-size:1.6rem;margin:0 0 0.5rem 0;'>Recommended Works</h2>
                <p style='font-size:0.85rem;color:#8A8580;line-height:1.6;margin:0;'>
                    These artworks share visual, compositional, or stylistic affinity
                    with your uploaded image. Click any work to explore it in depth
                    and navigate the collection through the knowledge graph.
                </p>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)

    n_cols = 4
    for row in [recommendations[i:i+n_cols] for i in range(0, len(recommendations), n_cols)]:
        cols = st.columns(n_cols, gap="small")
        for col, artwork in zip(cols, row):
            with col:
                _render_card(artwork)


def _render_card(artwork: dict) -> None:
    title      = artwork.get("title", "Untitled")
    artist     = artwork.get("artist", "Unknown Artist")
    year       = artwork.get("year", "")
    similarity = artwork.get("similarity_score")
    thumb_url  = artwork.get("thumbnail_url") or artwork.get("image_url", "")
    year_txt   = f" · {year}" if year else ""

    badge = ""
    if similarity is not None:
        badge = (
            f"<span style='display:inline-block;background:rgba(255,49,49,0.12);color:{PRIMARY};"
            f"border:1px solid rgba(255,49,49,0.3);border-radius:20px;font-size:0.68rem;"
            f"letter-spacing:0.06em;padding:0.15rem 0.55rem;margin-top:0.4rem;'>"
            f"{int(similarity * 100)}% match</span>"
        )

    st.markdown(
        "<div style='border:1px solid #2A2A2A;border-radius:4px;overflow:hidden;"
        "background:#161616;margin-bottom:0.25rem;'>",
        unsafe_allow_html=True,
    )
    show_image_card(thumb_url)
    st.markdown(
        f"<div style='padding:0.65rem 0.75rem 0.5rem;'>"
        f"<p style='font-size:0.88rem;line-height:1.3;margin:0 0 0.2rem;"
        f"color:#F0EDE8;font-weight:500;'>{title[:55]}</p>"
        f"<p style='font-size:0.75rem;color:#8A8580;margin:0;'>{artist[:35]}{year_txt}</p>"
        f"{badge}</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("View →", key=f"card_btn_{artwork['id']}", help=f"{title} — {artist}"):
        open_artwork(artwork)


def open_artwork(artwork: dict) -> None:
    art_id = artwork["id"]
    store_artwork(artwork)
    with st.spinner(random.choice(SPINNER_MESSAGES)):
        try:
            details = get_cached_details(art_id)
            if details is None:
                details = get_artwork_details(art_id)
                cache_details(art_id, details)
            push_history(art_id, artwork.get("title", "Artwork"))
            st.session_state["selected_artwork"] = art_id
            st.rerun()
        except Exception as e:
            render_error(f"Could not load artwork details: {e}")
