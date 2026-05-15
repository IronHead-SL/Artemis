from __future__ import annotations

import base64
import io

import streamlit as st
from PIL import Image

from components import render_header, render_upload_prompt, render_logo_centered, render_error
from constants import PRIMARY
from image_utils import load_image_safe, resize_image, pil_to_bytes, prefetch_images_parallel
from services import recommend_artworks
from state import store_artwork


def view_upload() -> None:
    render_header(show_new_search=False)
    render_upload_prompt()
    render_logo_centered(150)

    uploaded_file = st.file_uploader(
        label="Drop an image to begin",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
    )

    if uploaded_file is None:
        return

    if uploaded_file.size > 10 * 1024 * 1024:
        render_error("Image must be smaller than 10 MB.")
        return

    img = load_image_safe(uploaded_file)
    if img is None:
        render_error("Could not load the image. Please upload a valid JPG or PNG.")
        return

    col_prev, col_info = st.columns([2, 3], gap="large")

    with col_prev:
        preview = resize_image(img, 600)
        buf = io.BytesIO()
        preview.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        st.markdown(
            f"<img src='data:image/jpeg;base64,{b64}' "
            f"style='width:100%;border-radius:4px;display:block;margin-top:-0.5rem;'>",
            unsafe_allow_html=True,
        )

    with col_info:
        st.markdown(
            f"""<div style='font-size:0.68rem;text-transform:uppercase;letter-spacing:0.14em;
                        color:{PRIMARY};margin-bottom:0.55rem;margin-top:0.15rem;'>Image loaded</div>
            <div style='font-size:1.35rem;font-weight:600;margin-bottom:0.35rem;
                        word-break:break-all;color:#F0EDE8;line-height:1.2;'>{uploaded_file.name}</div>
            <div style='font-size:0.78rem;color:#555;margin-bottom:1.6rem;letter-spacing:0.02em;'>
                {img.size[0]} × {img.size[1]} px &nbsp;·&nbsp; {uploaded_file.size // 1024} KB
            </div>
            <div style='font-size:0.85rem;color:#8A8580;line-height:1.7;
                        border-left:2px solid #2A2A2A;padding-left:0.9rem;margin-bottom:1.8rem;'>
                Artemis will analyze visual patterns, color relationships, and
                compositional structure to find historically and aesthetically
                related artworks in our database.
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("✦ Find Similar Artworks", type="primary", key="btn_find"):
            _run_recommendations(pil_to_bytes(resize_image(img, 800)))


def _run_recommendations(img_bytes: bytes) -> None:
    import random
    from constants import SPINNER_MESSAGES
    with st.spinner(random.choice(SPINNER_MESSAGES)):
        try:
            results = recommend_artworks(img_bytes)
            if not results:
                render_error("No recommendations found. Try a different image.")
                return
            st.session_state["uploaded_image"]  = img_bytes
            st.session_state["recommendations"] = results
            for artwork in results:
                store_artwork(artwork)
            prefetch_images_parallel([a.get("thumbnail_url") or a.get("image_url", "") for a in results])
            st.rerun()
        except Exception as e:
            render_error(f"Recommendation service unavailable: {e}")
