from __future__ import annotations

import io
import time
from typing import Optional

import requests as _requests
import streamlit as st
from PIL import Image

from utils import (
    inject_css,
    init_session_state,
    render_header,
    render_breadcrumb,
    render_error,
    render_upload_prompt,
    load_image_safe,
    resize_image,
    pil_to_bytes,
    push_history,
    get_cached_details,
    cache_details,
    similarity_pct,
    random_spinner_msg,
    _reset_state,
    PRIMARY,
)

_IMG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0 "
        "ArtemisBot/1.0"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.metmuseum.org/",
}
_IMG_TIMEOUT = 10
_IMG_CACHE_KEY = "_img_bytes_cache"


def _fetch_image_bytes(url: str) -> Optional[bytes]:
    """
    Fetch image bytes SERVER-SIDE with proper headers.

    Cached in session state (URL → bytes | None) so each URL is only
    downloaded once per Streamlit session.  Returns None on any error.
    """
    if not url:
        return None
    cache: dict = st.session_state.setdefault(_IMG_CACHE_KEY, {})
    if url in cache:
        return cache[url]
    try:
        resp = _requests.get(url, headers=_IMG_HEADERS, timeout=_IMG_TIMEOUT)
        resp.raise_for_status()
        data = resp.content
        cache[url] = data
        return data
    except Exception:
        cache[url] = None
        return None


def _show_image(url: str, *, use_container_width: bool = True,
                placeholder_ratio: str = "3/4") -> None:
    """Fetch *url* server-side and render with st.image(), or show placeholder."""
    data = _fetch_image_bytes(url)
    if data:
        try:
            st.image(data, use_container_width=use_container_width)
            return
        except Exception:
            pass
    st.markdown(
        f"<div style='width:100%;aspect-ratio:{placeholder_ratio};"
        "background:linear-gradient(135deg,#1a1a1a,#2a2a2a);"
        "border-radius:4px;'></div>",
        unsafe_allow_html=True,
    )

def _store_artwork_data(artwork: dict) -> None:
    st.session_state.setdefault("artwork_data_cache", {})[artwork["id"]] = artwork


def _get_artwork_data(artwork_id: str) -> Optional[dict]:
    return st.session_state.get("artwork_data_cache", {}).get(artwork_id)

def recommend_artworks(uploaded_image: bytes) -> list[dict]:
    """
    Return artwork recommendations for *uploaded_image*.

    MongoDB field mapping (Met feeder schema):
        objectID            → id
        title               → title
        artistDisplayName   → artist
        objectEndDate       → year
        primaryImage        → image_url
        primaryImageSmall   → thumbnail_url

    ── STUB: replace with real Qdrant search + Mongo lookup ─────────────────
    Example skeleton:

        from qdrant_client import QdrantClient
        from pymongo import MongoClient
        import os

        qdrant = QdrantClient(host=os.getenv("QDRANT_HOST", "qdrant"), port=6333)
        mongo  = MongoClient(os.getenv("MONGO_URI"))["artemis_db"]

        embedding = embed_image(uploaded_image)   # your CLIP embed fn
        hits = qdrant.search("artworks", embedding, limit=10)

        results = []
        for hit in hits:
            doc = mongo.artworks.find_one({"objectID": hit.id})
            if doc:
                results.append({
                    "id":              str(doc["objectID"]),
                    "title":           doc.get("title", "Untitled"),
                    "artist":          doc.get("artistDisplayName", "Unknown"),
                    "year":            doc.get("objectEndDate", ""),
                    "image_url":       doc.get("primaryImage", ""),
                    "thumbnail_url":   doc.get("primaryImageSmall", ""),
                    "similarity_score": hit.score,
                })
        return results
    """
    import random
    time.sleep(0.8)

    ARTWORKS = [
        {
            "id": "art_0",
            "title": "The Persistence of Memory",
            "artist": "Salvador Dalí", "year": 1931,
            "image_url":     "https://upload.wikimedia.org/wikipedia/en/d/dd/The_Persistence_of_Memory.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/en/d/dd/The_Persistence_of_Memory.jpg",
        },
        {
            "id": "art_1",
            "title": "The Starry Night",
            "artist": "Vincent van Gogh", "year": 1889,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/1280px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg/640px-Van_Gogh_-_Starry_Night_-_Google_Art_Project.jpg",
        },
        {
            "id": "art_2",
            "title": "Girl with a Pearl Earring",
            "artist": "Johannes Vermeer", "year": 1665,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/800px-1665_Girl_with_a_Pearl_Earring.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/1665_Girl_with_a_Pearl_Earring.jpg/400px-1665_Girl_with_a_Pearl_Earring.jpg",
        },
        {
            "id": "art_3",
            "title": "The Birth of Venus",
            "artist": "Sandro Botticelli", "year": 1485,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg/1280px-Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg/640px-Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg",
        },
        {
            "id": "art_4",
            "title": "Water Lilies",
            "artist": "Claude Monet", "year": 1906,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg/1280px-Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/aa/Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg/640px-Claude_Monet_-_Water_Lilies_-_1906%2C_Ryerson.jpg",
        },
        {
            "id": "art_5",
            "title": "The Great Wave off Kanagawa",
            "artist": "Katsushika Hokusai", "year": 1831,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/1280px-Tsunami_by_hokusai_19th_century.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Tsunami_by_hokusai_19th_century.jpg/640px-Tsunami_by_hokusai_19th_century.jpg",
        },
        {
            "id": "art_6",
            "title": "Las Meninas",
            "artist": "Diego Velázquez", "year": 1656,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Las_Meninas_01.jpg/800px-Las_Meninas_01.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Las_Meninas_01.jpg/400px-Las_Meninas_01.jpg",
        },
        {
            "id": "art_7",
            "title": "A Sunday on La Grande Jatte",
            "artist": "Georges Seurat", "year": 1886,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg/1280px-A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7d/A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg/640px-A_Sunday_on_La_Grande_Jatte%2C_Georges_Seurat%2C_1884.jpg",
        },
    ]
    picks = random.sample(ARTWORKS, 7)
    for p in picks:
        p["similarity_score"] = round(random.uniform(0.65, 0.98), 2)
    return picks


def get_artwork_details(artwork_id: str) -> dict:
    """
    Fetch full details for *artwork_id*.

    ── STUB: replace with real MongoDB + Neo4j call ──────────────────────────
    """
    time.sleep(0.4)

    recs = st.session_state.get("recommendations") or []
    base = next((r for r in recs if r["id"] == artwork_id), None)
    if base is None:
        base = _get_artwork_data(artwork_id) or {}

    RELATED_POOL = [
        {
            "id": "rel_scream",
            "title": "The Scream", "artist": "Edvard Munch", "year": 1893,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg/800px-Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg/400px-Edvard_Munch%2C_1893%2C_The_Scream%2C_oil%2C_tempera_and_pastel_on_cardboard%2C_91_x_73_cm%2C_National_Gallery_of_Norway.jpg",
        },
        {
            "id": "rel_kandinsky",
            "title": "Composition VIII", "artist": "Wassily Kandinsky", "year": 1923,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg/1280px-Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg/640px-Vassily_Kandinsky%2C_1923_-_Composition_8%2C_huile_sur_toile%2C_140_cm_x_201_cm%2C_Mus%C3%A9e_Guggenheim%2C_New_York.jpg",
        },
        {
            "id": "rel_nightwatch",
            "title": "The Night Watch", "artist": "Rembrandt", "year": 1642,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Rembrandt_van_Rijn_-_De_Nachtwacht.jpg/1280px-Rembrandt_van_Rijn_-_De_Nachtwacht.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Rembrandt_van_Rijn_-_De_Nachtwacht.jpg/640px-Rembrandt_van_Rijn_-_De_Nachtwacht.jpg",
        },
        {
            "id": "rel_gothic",
            "title": "American Gothic", "artist": "Grant Wood", "year": 1930,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg/800px-Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg/400px-Grant_Wood_-_American_Gothic_-_Google_Art_Project.jpg",
        },
        {
            "id": "rel_guernica",
            "title": "Guernica", "artist": "Pablo Picasso", "year": 1937,
            "image_url":     "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/en/7/74/PicassoGuernica.jpg",
        },
        {
            "id": "rel_arnolfini",
            "title": "The Arnolfini Portrait", "artist": "Jan van Eyck", "year": 1434,
            "image_url":     "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Van_Eyck_-_Arnolfini_Portrait.jpg/800px-Van_Eyck_-_Arnolfini_Portrait.jpg",
            "thumbnail_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Van_Eyck_-_Arnolfini_Portrait.jpg/400px-Van_Eyck_-_Arnolfini_Portrait.jpg",
        },
    ]

    related_with_scores = []
    for j, item in enumerate(RELATED_POOL):
        enriched = {**item, "similarity_score": round(0.55 + j * 0.06, 2)}
        _store_artwork_data(enriched)
        related_with_scores.append(enriched)

    return {
        "title":       base.get("title", "Untitled"),
        "artist":      base.get("artist", "Unknown Artist"),
        "year":        base.get("year", ""),
        "medium":      "Oil on canvas",
        "dimensions":  "73.7 × 92.1 cm",
        "image_url":   base.get("image_url", ""),
        "explanation": (
            "This work resonates with your uploaded image through its masterful use of "
            "color temperature and compositional weight. The artist's brushwork creates a "
            "visual rhythm that echoes the tonal distribution in your image — specifically "
            "the interplay between warm highlights and cool shadow regions."
            "\n\n"
            "The spatial organization mirrors your image's underlying geometric structure, "
            "where primary masses anchor the composition while secondary elements provide "
            "a dynamic counterpoint. The chromatic palette — particularly the relationship "
            "between the dominant hues — shares a calculated harmony with your source material."
            "\n\n"
            "Art historians often situate this piece at a pivotal moment in the artist's "
            "development, where technical mastery began to serve pure expression. "
            "The visible tension between representation and abstraction creates the emotional "
            "charge that connects it so strongly to contemporary visual sensibilities."
        ),
        "related_artworks": related_with_scores,
    }


st.set_page_config(
    page_title="Artemis · Art Discovery",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()
init_session_state()
st.session_state.setdefault("artwork_data_cache", {})
st.session_state.setdefault(_IMG_CACHE_KEY, {})


def view_upload() -> None:
    render_header(show_new_search=False)
    render_upload_prompt()

    uploaded_file = st.file_uploader(
        label="Drop an image to begin",
        type=["jpg", "jpeg", "png", "webp"],
        help="Maximum 10 MB. Supports JPG, PNG, WebP.",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        if uploaded_file.size > 10 * 1024 * 1024:
            render_error("Image must be smaller than 10 MB.")
            return

        img = load_image_safe(uploaded_file)
        if img is None:
            render_error("Could not load the image. Please upload a valid JPG or PNG.")
            return

        col_prev, col_info = st.columns([1, 2], gap="large")
        with col_prev:
            st.image(resize_image(img, 400), use_container_width=True)

        with col_info:
            st.markdown(
                f"""
                <div style='padding-top:1rem;'>
                    <div style='font-size:0.7rem;text-transform:uppercase;letter-spacing:0.12em;
                                color:{PRIMARY};margin-bottom:0.5rem;'>Image loaded</div>
                    <div style='font-family:"Playfair Display",serif;font-size:1.4rem;
                                margin-bottom:0.5rem;'>{uploaded_file.name}</div>
                    <div style='font-size:0.82rem;color:#6a6460;margin-bottom:1.5rem;'>
                        {img.size[0]} × {img.size[1]} px · {uploaded_file.size // 1024} KB
                    </div>
                    <div style='font-size:0.85rem;color:#8A8580;line-height:1.6;'>
                        Artemis will analyze visual patterns, color relationships, and
                        compositional structure to find historically and aesthetically
                        related artworks in our database.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.write("")
            if st.button("✦ Find Similar Artworks", type="primary", key="btn_find"):
                img_bytes = pil_to_bytes(resize_image(img, 800))
                _run_recommendations(img_bytes)


def _run_recommendations(img_bytes: bytes) -> None:
    with st.spinner(random_spinner_msg()):
        try:
            results = recommend_artworks(img_bytes)
            if not results:
                render_error("No recommendations found. Try a different image.")
                return
            st.session_state["uploaded_image"] = img_bytes
            st.session_state["recommendations"] = results
            for artwork in results:
                _store_artwork_data(artwork)
                url = artwork.get("thumbnail_url") or artwork.get("image_url", "")
                if url:
                    _fetch_image_bytes(url)
            st.rerun()
        except Exception as e:
            render_error(f"Recommendation service unavailable: {e}")


def view_results() -> None:
    render_header(show_new_search=True)
    recommendations: list[dict] = st.session_state["recommendations"]

    col_img, col_txt = st.columns([1, 3], gap="large")
    with col_img:
        try:
            img = Image.open(io.BytesIO(st.session_state["uploaded_image"]))
            st.image(resize_image(img, 300), use_container_width=True)
        except Exception:
            pass

    with col_txt:
        st.markdown(
            f"""
            <div style='padding-top:0.5rem;'>
                <div style='font-size:0.68rem;text-transform:uppercase;
                            letter-spacing:0.12em;color:{PRIMARY};margin-bottom:0.4rem;'>
                    Your Image · {len(recommendations)} Artworks Found
                </div>
                <h2 style='font-family:"Playfair Display",serif;font-size:1.6rem;
                           margin:0 0 0.5rem 0;'>Recommended Works</h2>
                <p style='font-size:0.85rem;color:#8A8580;line-height:1.6;margin:0;'>
                    These artworks share visual, compositional, or stylistic affinity
                    with your uploaded image. Click any work to explore it in depth.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)

    n_cols = 4
    rows = [recommendations[i:i+n_cols] for i in range(0, len(recommendations), n_cols)]
    for row in rows:
        cols = st.columns(n_cols, gap="small")
        for col, artwork in zip(cols, row):
            with col:
                _render_artwork_card(artwork)


def _render_artwork_card(artwork: dict) -> None:
    title      = artwork.get("title", "Untitled")
    artist     = artwork.get("artist", "Unknown Artist")
    year       = artwork.get("year", "")
    similarity = artwork.get("similarity_score")
    thumb_url  = artwork.get("thumbnail_url") or artwork.get("image_url", "")

    st.markdown(
        "<div style='border:1px solid #2A2A2A;border-radius:4px;overflow:hidden;"
        "background:#161616;margin-bottom:0.25rem;'>",
        unsafe_allow_html=True,
    )

    _show_image(thumb_url, use_container_width=True, placeholder_ratio="3/4")

    year_txt = f" · {year}" if year else ""
    badge = (
        f"<span style='display:inline-block;background:rgba(46,134,171,0.15);"
        f"color:#2E86AB;border:1px solid rgba(46,134,171,0.3);border-radius:20px;"
        f"font-size:0.68rem;letter-spacing:0.06em;padding:0.15rem 0.55rem;"
        f"margin-top:0.4rem;'>{int(similarity * 100)}% match</span>"
        if similarity is not None else ""
    )
    st.markdown(
        f"""
        <div style='padding:0.65rem 0.75rem 0.5rem 0.75rem;'>
            <p style='font-family:"Playfair Display",serif;font-size:0.88rem;
                      line-height:1.3;margin:0 0 0.2rem 0;color:#F0EDE8;'>{title[:55]}</p>
            <p style='font-size:0.75rem;color:#8A8580;margin:0;'>{artist}{year_txt}</p>
            {badge}
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("View →", key=f"card_btn_{artwork['id']}",
                 help=f"{title} — {artist}"):
        _open_artwork(artwork)


def _open_artwork(artwork: dict) -> None:
    art_id = artwork["id"]
    _store_artwork_data(artwork)
    with st.spinner(random_spinner_msg()):
        try:
            details = get_cached_details(art_id)
            if details is None:
                details = get_artwork_details(art_id)
                cache_details(art_id, details)
                # Pre-fetch related images while spinner is visible
                for rel in details.get("related_artworks", []):
                    url = rel.get("thumbnail_url") or rel.get("image_url", "")
                    if url:
                        _fetch_image_bytes(url)
            push_history(art_id, artwork.get("title", "Artwork"))
            st.session_state["selected_artwork"] = art_id
            st.rerun()
        except Exception as e:
            render_error(f"Could not load artwork details: {e}")


def view_detail() -> None:
    render_header(show_new_search=True)
    render_breadcrumb()

    art_id: str = st.session_state["selected_artwork"]
    details: Optional[dict] = get_cached_details(art_id)

    if details is None:
        with st.spinner("Loading artwork details…"):
            try:
                details = get_artwork_details(art_id)
                cache_details(art_id, details)
            except Exception as e:
                render_error(f"Could not load artwork details: {e}")
                _back_to_results_button()
                return

    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Back to Results", key="back_btn"):
            st.session_state["selected_artwork"] = None
            st.rerun()

    st.write("")

    col_img, col_info = st.columns([5, 7], gap="large")

    with col_img:
        _show_image(details.get("image_url", ""), placeholder_ratio="3/4")

    with col_info:
        title       = details.get("title", "Untitled")
        artist      = details.get("artist", "Unknown Artist")
        year        = details.get("year", "")
        medium      = details.get("medium", "")
        dimensions  = details.get("dimensions", "")
        explanation = details.get("explanation", "")

        recs = st.session_state.get("recommendations") or []
        matched = next((r for r in recs if r["id"] == art_id), None)
        if matched is None:
            matched = _get_artwork_data(art_id)
        sim_score = matched.get("similarity_score") if matched else None

        st.markdown(
            f"""
            <div style='padding-bottom:0.5rem;'>
                <h1 class="detail-title">{title}</h1>
                <p class="detail-artist">{artist}</p>
                <p class="detail-year">{year}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        meta_items = []
        if medium:
            meta_items.append(f"<div class='meta-item'><strong>Medium</strong>{medium}</div>")
        if dimensions:
            meta_items.append(f"<div class='meta-item'><strong>Dimensions</strong>{dimensions}</div>")
        if sim_score is not None:
            meta_items.append(
                f"<div class='meta-item'><strong>Style Match</strong>"
                f"<span style='color:{PRIMARY};font-weight:600;'>{similarity_pct(sim_score)}</span></div>"
            )
        if meta_items:
            st.markdown(
                f"<div class='detail-meta-row'>{''.join(meta_items)}</div>",
                unsafe_allow_html=True,
            )

        if explanation:
            st.markdown("<div class='section-label'>Why This Artwork</div>", unsafe_allow_html=True)
            for para in [p.strip() for p in explanation.split("\n\n") if p.strip()]:
                st.markdown(
                    f"<div class='explanation-text'>{para}</div>",
                    unsafe_allow_html=True,
                )

        st.write("")
        if st.button("✦ Find Similar to This Artwork", key="find_similar_btn", type="primary"):
            _find_similar_to_current(details, art_id)

    related: list[dict] = details.get("related_artworks", [])
    if related:
        st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)
        st.markdown("<div class='section-label'>Related Artworks</div>", unsafe_allow_html=True)
        _render_related(related)


def _render_related(related: list[dict]) -> None:
    n_cols = min(len(related), 6)
    cols = st.columns(n_cols, gap="small")
    for col, artwork in zip(cols, related[:n_cols]):
        with col:
            thumb_url = artwork.get("thumbnail_url") or artwork.get("image_url", "")
            title  = artwork.get("title", "Untitled")
            artist = artwork.get("artist", "")
            _show_image(thumb_url, placeholder_ratio="1/1")
            st.markdown(
                f"""
                <div style='padding:0.3rem 0 0.5rem 0;'>
                    <div style='font-size:0.75rem;font-family:"Playfair Display",serif;
                                line-height:1.3;'>{title[:35]}</div>
                    <div style='font-size:0.68rem;color:#6a6460;margin-top:0.1rem;'>{artist[:25]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("View →", key=f"rel_btn_{artwork['id']}"):
                _open_artwork(artwork)


def _find_similar_to_current(details: dict, art_id: str) -> None:
    img_url = details.get("image_url", "")
    if not img_url:
        render_error("No image URL available for this artwork.")
        return
    with st.spinner("Fetching artwork image…"):
        img_bytes = _fetch_image_bytes(img_url)
        if not img_bytes:
            render_error("Could not fetch artwork image.")
            return
    _reset_state()
    with st.spinner("Finding similar artworks…"):
        try:
            results = recommend_artworks(img_bytes)
            if not results:
                render_error("No similar artworks found.")
                return
            st.session_state["uploaded_image"] = img_bytes
            st.session_state["recommendations"] = results
            for artwork in results:
                _store_artwork_data(artwork)
                url = artwork.get("thumbnail_url") or artwork.get("image_url", "")
                if url:
                    _fetch_image_bytes(url)
            st.rerun()
        except Exception as e:
            render_error(f"Recommendation service error: {e}")


def _back_to_results_button() -> None:
    if st.button("← Back to Results"):
        st.session_state["selected_artwork"] = None
        st.rerun()

def main() -> None:
    uploaded = st.session_state.get("uploaded_image")
    recs     = st.session_state.get("recommendations")
    selected = st.session_state.get("selected_artwork")

    if uploaded is None or recs is None:
        view_upload()
    elif selected is not None:
        view_detail()
    else:
        view_results()


if __name__ == "__main__":
    main()