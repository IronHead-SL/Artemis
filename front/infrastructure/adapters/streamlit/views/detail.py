from __future__ import annotations

import streamlit as st

from domain.constants import ICONS
from application.usecases.services import get_artwork_details
from ..components import render_header, render_error
from ..state import get_cached_details, cache_details
from ...media.image_utils import show_image_detail
from .detail_renderers import render_info, render_related, render_back_button


def view_detail() -> None:
    render_header(show_new_search=True)
    art_id: str = st.session_state["selected_artwork"]

    details = get_cached_details(art_id)
    if details is None:
        with st.spinner("Loading artwork details…"):
            try:
                details = get_artwork_details(art_id)
                cache_details(art_id, details)
            except Exception as e:
                render_error(f"Could not load artwork details: {e}")
                render_back_button()
                return

    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Back to Results", key="back_btn"):
            st.session_state["selected_artwork"] = None
            st.rerun()

    st.write("")
    col_img, col_info = st.columns([1, 1], gap="medium")

    with col_img:
        show_image_detail(details.get("image_url", ""))

    with col_info:
        render_info(art_id, details)

    st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)

    related = details.get("related_artworks", [])
    if related:
        st.markdown(
            f"<div class='section-label'>{ICONS.get('link','')} Related Artworks — Navigate the Graph</div>",
            unsafe_allow_html=True,
        )
        render_related(related)
    else:
        st.markdown(
            "<div style='font-size:0.8rem;color:#444;padding:0.5rem 0;'>"
            "No related artworks found in the graph for this work.</div>",
            unsafe_allow_html=True,
        )


