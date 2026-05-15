from __future__ import annotations

from collections import defaultdict

import streamlit as st

from components import render_header, render_error, similarity_pct
from constants import PRIMARY, ICONS
from image_utils import show_image_card, show_image_detail
from services import get_artwork_details
from state import get_cached_details, cache_details, get_artwork
from view_results import open_artwork


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
                _back_button()
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
        _render_info(art_id, details)

    st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)

    related = details.get("related_artworks", [])
    if related:
        st.markdown(
            f"<div class='section-label'>{ICONS.get('link','')} Related Artworks — Navigate the Graph</div>",
            unsafe_allow_html=True,
        )
        _render_related(related)
    else:
        st.markdown(
            "<div style='font-size:0.8rem;color:#444;padding:0.5rem 0;'>"
            "No related artworks found in the graph for this work.</div>",
            unsafe_allow_html=True,
        )


def _render_info(art_id: str, details: dict) -> None:
    title             = details.get("title", "Untitled")
    artist            = details.get("artist", "Unknown Artist")
    year              = details.get("year", "")
    medium            = details.get("medium", "")
    dimensions        = details.get("dimensions", "")
    department        = details.get("department", "")
    explanation_parts = details.get("explanation_parts", [])
    graph_sections    = details.get("graph_sections", [])
    neo4j_ok          = details.get("neo4j_ok", False)

    recs      = st.session_state.get("recommendations") or []
    matched   = next((r for r in recs if r["id"] == art_id), None) or get_artwork(art_id)
    sim_score = matched.get("similarity_score") if matched else None

    st.markdown(
        f"<h1 class='detail-title'>{title}</h1>"
        f"<p class='detail-artist'>{artist}</p>"
        f"<p class='detail-year'>{year}</p>",
        unsafe_allow_html=True,
    )

    meta_items = []
    if medium:
        meta_items.append(f"<div class='meta-item'><strong>Medium</strong>{medium}</div>")
    if dimensions:
        meta_items.append(f"<div class='meta-item'><strong>Dimensions</strong>{dimensions}</div>")
    if department:
        meta_items.append(f"<div class='meta-item'><strong>Department</strong>{department}</div>")
    if sim_score is not None:
        meta_items.append(
            f"<div class='meta-item'><strong>Style Match</strong>"
            f"<span style='color:{PRIMARY};font-weight:600;'>{similarity_pct(sim_score)}</span></div>"
        )
    if meta_items:
        st.markdown(f"<div class='detail-meta-row'>{''.join(meta_items)}</div>", unsafe_allow_html=True)

    if explanation_parts:
        source = "Via knowledge graph" if neo4j_ok else "From collection metadata"
        st.markdown(
            f"<div class='section-label'>About this work "
            f"<span style='font-size:0.6rem;color:#444;margin-left:0.5rem;'>{source}</span></div>",
            unsafe_allow_html=True,
        )
        for para in explanation_parts:
            st.markdown(f"<div class='explanation-text'>{para}</div>", unsafe_allow_html=True)

    if graph_sections:
        st.markdown("<div class='section-label' style='margin-top:1.2rem;'>Graph Context</div>", unsafe_allow_html=True)
        for section in graph_sections:
            items_html = "".join(
                f"<span style='display:inline-block;background:#1E1E1E;border:1px solid #333;"
                f"border-radius:3px;font-size:0.75rem;padding:0.2rem 0.6rem;"
                f"margin:0.15rem 0.2rem 0.15rem 0;color:#C8C4BF;'>{item}</span>"
                for item in section["items"]
            )
            st.markdown(
                f"<div style='margin-bottom:0.6rem;'>"
                f"<div style='font-size:0.68rem;text-transform:uppercase;letter-spacing:0.1em;"
                f"color:#555;margin-bottom:0.3rem;'>{section['label']}</div>"
                f"<div>{items_html}</div></div>",
                unsafe_allow_html=True,
            )


def _render_related(related: list[dict]) -> None:
    priority_order = ["Same Artist", "Same Movement", "Same Genre", "Same Technique", "Same Department", "Related"]
    groups = defaultdict(list)
    for artwork in related:
        groups[artwork.get("relation_type", "Related")].append(artwork)

    for group_name, artworks in sorted(
        groups.items(),
        key=lambda x: priority_order.index(x[0]) if x[0] in priority_order else 99,
    ):
        icon = ICONS.get("link", "")
        if "Movement"    in group_name: icon = ICONS.get("movement", "")
        elif "Genre"     in group_name: icon = ICONS.get("genre", "")
        elif "Artist"    in group_name: icon = ICONS.get("artist", "")
        elif "Technique" in group_name: icon = ICONS.get("technique", "")
        elif "Department"in group_name: icon = ICONS.get("department", "")

        st.markdown(
            f"<div class='section-label' style='margin-top:1.2rem;'>{icon} {group_name}</div>",
            unsafe_allow_html=True,
        )
        n = min(len(artworks), 3)
        for col, artwork in zip(st.columns(n, gap="small"), artworks[:n]):
            with col:
                thumb_url = artwork.get("thumbnail_url") or artwork.get("image_url", "")
                st.markdown(
                    "<div style='border:1px solid #222;border-radius:4px;overflow:hidden;background:#161616;'>",
                    unsafe_allow_html=True,
                )
                show_image_card(thumb_url, max_height=250)
                st.markdown(
                    f"<div style='padding:0.4rem 0.5rem 0.5rem;'>"
                    f"<div style='font-size:0.78rem;font-weight:500;line-height:1.3;color:#F0EDE8;'>"
                    f"{artwork.get('title','Untitled')[:35]}</div>"
                    f"<div style='font-size:0.68rem;color:#6a6460;'>{artwork.get('artist','')[:28]}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button("View →", key=f"rel_btn_{artwork['id']}_{group_name}"):
                    open_artwork(artwork)


def _back_button() -> None:
    if st.button("← Back to Results"):
        st.session_state["selected_artwork"] = None
        st.rerun()
