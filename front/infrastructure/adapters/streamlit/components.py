from __future__ import annotations

import base64
import io

import streamlit as st
from PIL import Image

from domain.constants import PRIMARY
from ..media.image_utils import resize_image, pil_to_bytes, image_to_base64
from .state import reset_state


def render_header(show_new_search: bool = False) -> None:
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        try:
            img    = Image.open("artemis-logo.png")
            logo   = resize_image(img, 45)
            b64    = image_to_base64(pil_to_bytes(logo, fmt="PNG"))
            st.markdown(
                f"""<div style="display:flex;align-items:center;gap:12px;">
                    <img src="data:image/png;base64,{b64}" width="45px">
                    <div>
                        <div class="site-title">ARTEMIS</div>
                        <div class="site-subtitle">AI-Powered Art Discovery</div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
        except Exception:
            st.markdown('<div class="site-title">ARTEMIS</div>', unsafe_allow_html=True)
    with col_btn:
        if show_new_search and st.button("New Search", key="new_search_header"):
            reset_state()
            st.rerun()
    st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)


def render_upload_prompt() -> None:
    st.markdown(
        """<div class="upload-zone">
            <div class="upload-eyebrow">Discover Art</div>
            <h1 class="upload-headline">Find Art Inspired by You</h1>
            <p class="upload-body">
                Upload any image — a painting, photograph, or visual inspiration —
                and Artemis will surface artworks across centuries that share its visual DNA.
            </p>
        </div>""",
        unsafe_allow_html=True,
    )


def render_logo_centered(width: int = 150) -> None:
    try:
        logo = Image.open("artemis-logo.png")
        buf  = io.BytesIO()
        logo.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        st.markdown(
            f'<div style="display:flex;justify-content:center;margin-bottom:2rem;">'
            f'<img src="data:image/png;base64,{b64}" width="{width}px"></div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass


def render_error(msg: str) -> None:
    st.markdown(f"<div class='error-box'>⚠ {msg}</div>", unsafe_allow_html=True)


def similarity_pct(score: float) -> str:
    return f"{int(score * 100)}%"
