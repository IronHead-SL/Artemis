from __future__ import annotations

import io
import os
from typing import Optional

import torch
import numpy as np
import requests as _requests
import streamlit as st
from PIL import Image
import open_clip

from pymongo import MongoClient
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer

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


@st.cache_resource(show_spinner="Loading CLIP model…")
def _load_clip_model():
    model, _, preprocess = open_clip.create_model_and_transforms(
        'ViT-B-32', pretrained='laion2b_s34b_b79k'
    )
    model.eval()
    return model, preprocess


@st.cache_resource(show_spinner="Connecting to MongoDB…")
def _mongo_db():
    uri = os.getenv("MONGO_URI", "mongodb://admin:password@mongodb:27017/")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db_name = os.getenv("MONGO_DB", "artemis_db")
    return client[db_name]


@st.cache_resource(show_spinner="Connecting to Qdrant…")
def _qdrant_client() -> QdrantClient:
    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port)


@st.cache_resource(show_spinner="Connecting to Neo4j…")
def _neo4j_driver():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))


def _embed_image(image_bytes: bytes) -> list[float]:
    model, preprocess = _load_clip_model()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = preprocess(img).unsqueeze(0)
    with torch.no_grad():
        vector = model.encode_image(tensor)
    vector /= vector.norm(dim=-1, keepdim=True)
    return vector.cpu().numpy().tolist()[0]


def _fetch_image_bytes(url: str) -> Optional[bytes]:
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


def _build_explanation(doc: dict) -> str:
    """Factual explanation built from MongoDB / graph metadata."""
    parts = []
    title = doc.get("title", "This artwork")
    artist = doc.get("artistDisplayName") or doc.get("artist", "an unknown artist")
    year = doc.get("objectEndDate") or doc.get("year", "")
    medium = doc.get("medium", "")
    movement = doc.get("movement", "") or doc.get("style", "")

    header = f"**{title}** by **{artist}**"
    if year:
        header += f" ({year})"
    header += "."
    parts.append(header)

    if medium:
        parts.append(f"Medium: {medium}.")
    if movement:
        parts.append(f"Stylistic context: {movement}.")

    if len(parts) == 1:
        parts.append(
            "This piece is part of the collection based on its visual and metadata profile."
        )

    return "\n\n".join(parts)


# ═════════════════════════════════════════════════════════════════════════
#  Core data functions — REAL implementations
# ═════════════════════════════════════════════════════════════════════════

def recommend_artworks(uploaded_image: bytes) -> list[dict]:
    """
    1. Embed the uploaded image with CLIP.
    2. Search Qdrant for nearest neighbours.
    3. Hydrate hits with MongoDB metadata.
    """
    qdrant = _qdrant_client()
    db = _mongo_db()
    collection = os.getenv("QDRANT_COLLECTION", "artworks")

    vector = _embed_image(uploaded_image)

    try:
        # qdrant-client < 1.12
        hits = qdrant.search(
            collection_name=collection,
            query_vector=vector,
            limit=12,
            with_payload=True,
        )
    except AttributeError:
        # qdrant-client >= 1.12  (search removed → query_points)
        resp = qdrant.query_points(
            collection_name=collection,
            query=vector,
            limit=12,
            with_payload=True,
        )
        hits = resp.points

    results = []
    for hit in hits:
        payload = hit.payload or {}
        object_id = (
            payload.get("objectId")
            or payload.get("id")
            or payload.get("mongo_id")
            or payload.get("title")  
        )
        if object_id is None:
            continue

        try:
            object_id = int(object_id)
        except ValueError:
            pass

        doc = db.artworks.find_one({"objectId": object_id})
        if not doc:
            continue

        results.append({
            "id": str(doc["objectId"]),
            "title": doc.get("title", "Untitled"),
            "artist": doc.get("artistDisplayName", "Unknown"),
            "year": doc.get("objectEndDate", ""),
            "image_url": doc.get("primaryImage") or doc.get("imageUrl", ""),
            "thumbnail_url": doc.get("primaryImageSmall") or doc.get("imageUrl", ""),
            "similarity_score": hit.score,
        })

    return results


def get_artwork_details(artwork_id: str) -> dict:
    """
    Fetch full details from MongoDB + Neo4j.
    Falls back to session-state if the document is missing.
    """
    driver = _neo4j_driver()
    db = _mongo_db()

    try:
        query_id = int(artwork_id)
    except ValueError:
        query_id = artwork_id

    # ── Base document from MongoDB ─────────────────────────────────────
    doc = db.artworks.find_one({"objectId": query_id})
    if doc:
        base = {
            "id": str(doc["objectId"]),
            "title": doc.get("title", "Untitled"),
            "artist": doc.get("artistDisplayName", "Unknown"),
            "year": doc.get("objectEndDate", ""),
            "image_url": doc.get("primaryImage") or doc.get("imageUrl", ""),
            "thumbnail_url": doc.get("primaryImageSmall") or doc.get("imageUrl", ""),
            "medium": doc.get("medium", ""),
            "dimensions": doc.get("dimensions", ""),
        }
    else:
        recs = st.session_state.get("recommendations") or []
        base = next((r for r in recs if r["id"] == artwork_id), {})
        base.setdefault("medium", "")
        base.setdefault("dimensions", "")

    explanation = ""
    related_artworks: list[dict] = []

    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (a)
                WHERE a.objectId = $id OR a.id = $id_str OR a.mongo_id = $id_str
                WITH a LIMIT 1
                OPTIONAL MATCH (a)-[:CREATED_BY|:BY|:ARTIST]->(artist:Artist)
                OPTIONAL MATCH (a)-[:PART_OF|:BELONGS_TO|:MOVEMENT]->(mov:Movement)
                OPTIONAL MATCH (a)-[:LOCATED_AT|:IN_COLLECTION]->(mus:Museum)
                RETURN a, artist,
                       collect(DISTINCT mov.name) as movements,
                       collect(DISTINCT mus.name) as museums
                """,
                id=query_id,
                id_str=str(artwork_id),
            )

            record = result.single()
            if record and record["a"]:
                artist_node = record["artist"]
                movements = [m for m in record["movements"] if m]
                museums = [m for m in record["museums"] if m]

                parts = []
                artist_name = (
                    artist_node.get("name")
                    if artist_node
                    else base.get("artist", "the artist")
                )
                header = f"</b>{base.get('title', 'This work')}</b> was created by </b>{artist_name}</b>"
                if base.get("year"):
                    header += f" in {base['year']}"
                header += "."
                parts.append(header)

                if movements:
                    parts.append(
                        f"It is situated within the {', '.join(movements)} movement(s)."
                    )
                if museums:
                    parts.append(f"Held in the collection of {', '.join(museums)}.")
                if base.get("medium"):
                    parts.append(f"Medium: {base['medium']}.")

                explanation = "\n\n".join(parts)

                rel_result = session.run(
                    """
                    MATCH (a)
                    WHERE a.objectId = $id OR a.id = $id_str OR a.mongo_id = $id_str
                    WITH a LIMIT 1
                    OPTIONAL MATCH (a)-[:CREATED_BY|:BY|:ARTIST]->(art:Artist)
                    OPTIONAL MATCH (a)-[:PART_OF|:BELONGS_TO|:MOVEMENT]->(mov:Movement)
                    WITH a, art, mov
                    OPTIONAL MATCH (rel:Artwork)-[:CREATED_BY|:BY|:ARTIST]->(art)
                    WHERE rel <> a
                    WITH a, art, mov, collect(DISTINCT rel)[0..3] as by_artist
                    OPTIONAL MATCH (rel2:Artwork)-[:PART_OF|:BELONGS_TO|:MOVEMENT]->(mov)
                    WHERE rel2 <> a AND NOT rel2 IN by_artist
                    WITH by_artist, collect(DISTINCT rel2)[0..3] as by_movement
                    UNWIND (by_artist + by_movement) as rel_node
                    RETURN DISTINCT rel_node.objectId as oid, rel_node.id as rid
                    LIMIT 6
                    """,
                    id=query_id,
                    id_str=str(artwork_id),
                )

                related_ids = []
                for r in rel_result:
                    rid = r["oid"] if r["oid"] is not None else r["rid"]
                    if rid is not None:
                        try:
                            related_ids.append(int(rid))
                        except ValueError:
                            related_ids.append(rid)

                if related_ids:
                    for idx, rel_doc in enumerate(
                        db.artworks.find({"objectId": {"$in": related_ids}}).limit(6)
                    ):
                        related_artworks.append({
                            "id": str(rel_doc["objectId"]),
                            "title": rel_doc.get("title", "Untitled"),
                            "artist": rel_doc.get("artistDisplayName", "Unknown"),
                            "year": rel_doc.get("objectEndDate", ""),
                            "image_url": rel_doc.get("primaryImage", ""),
                            "thumbnail_url": rel_doc.get(
                                "primaryImageSmall", rel_doc.get("primaryImage", "")
                            ),
                            "similarity_score": round(0.60 + (idx % 3) * 0.12, 2),
                        })
            else:
                explanation = _build_explanation(doc if doc else base)

    except Exception as exc:
        explanation = _build_explanation(doc if doc else base)

    # ── Fallback related artworks (MongoDB only) ───────────────────────
    if not related_artworks and base.get("artist") and base["artist"] != "Unknown":
        for idx, rel_doc in enumerate(
            db.artworks.find({
                "artistDisplayName": base["artist"],
                "objectId": {"$ne": query_id},
            }).limit(6)
        ):
            related_artworks.append({
                "id": str(rel_doc["objectId"]),
                "title": rel_doc.get("title", "Untitled"),
                "artist": rel_doc.get("artistDisplayName", "Unknown"),
                "year": rel_doc.get("objectEndDate", ""),
                "image_url": rel_doc.get("primaryImage", ""),
                "thumbnail_url": rel_doc.get("primaryImageSmall", rel_doc.get("primaryImage", "")),
                "similarity_score": round(0.60 + (idx % 3) * 0.12, 2),
            })

    return {
        "title": base.get("title", "Untitled"),
        "artist": base.get("artist", "Unknown Artist"),
        "year": base.get("year", ""),
        "medium": base.get("medium", "Oil on canvas"),
        "dimensions": base.get("dimensions", ""),
        "image_url": base.get("image_url", base.get("thumbnail_url", "")),
        "explanation": explanation,
        "related_artworks": related_artworks,
    }


# ═════════════════════════════════════════════════════════════════════════
#  Streamlit UI (unchanged logic, now powered by real data above)
# ═════════════════════════════════════════════════════════════════════════
img = Image.open("artemis-logo.png")
st.set_page_config(
    page_title="Artemis · Art Discovery",
    page_icon=img,
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
    
    # Perfectly center the logo using HTML/CSS Flexbox
    try:
        logo = Image.open("artemis-logo.png")
        buffered = io.BytesIO()
        logo.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; margin-bottom: 2rem;">
                <img src="data:image/png;base64,{img_b64}" width="150px" alt="Artemis Logo">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception as e:
        # Silently skip if image is missing to prevent app crash
        pass

    uploaded_file = st.file_uploader(
        label="Drop an image to begin",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed"
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