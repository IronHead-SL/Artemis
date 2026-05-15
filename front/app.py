from __future__ import annotations

import base64
import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import torch
import requests as _requests
import streamlit as st
from PIL import Image
import open_clip

from pymongo import MongoClient
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

from utils import (
    inject_css,
    init_session_state,
    render_header,
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
    ICONS,
)

_IMG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0 "
        "ArtemisBot/1.0"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.metmuseum.org/",
}
_IMG_TIMEOUT = 8
_IMG_CACHE_KEY = "_img_bytes_cache"


# ═══════════════════════════════════════════════════════════════
#  Connections
# ═══════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _load_clip_model():
    model, _, preprocess = open_clip.create_model_and_transforms(
        'ViT-B-32', pretrained='laion2b_s34b_b79k'
    )
    model.eval()
    return model, preprocess


@st.cache_resource(show_spinner=False)
def _mongo_db():
    uri = os.getenv("MONGO_URI", "mongodb://admin:password@mongodb:27017/")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[os.getenv("MONGO_DB", "artemis_db")]


@st.cache_resource(show_spinner=False)
def _qdrant_client() -> QdrantClient:
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )


@st.cache_resource(show_spinner=False)
def _neo4j_driver():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password")),
        max_connection_pool_size=10,
    )


# ═══════════════════════════════════════════════════════════════
#  Image helpers
# ═══════════════════════════════════════════════════════════════

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


def _prefetch_images_parallel(urls: list[str], max_workers: int = 8) -> None:
    """Fetch multiple images concurrently and store in session cache."""
    cache: dict = st.session_state.setdefault(_IMG_CACHE_KEY, {})
    missing = [u for u in urls if u and u not in cache]
    if not missing:
        return

    def _fetch(url: str) -> tuple[str, Optional[bytes]]:
        try:
            resp = _requests.get(url, headers=_IMG_HEADERS, timeout=_IMG_TIMEOUT)
            resp.raise_for_status()
            return url, resp.content
        except Exception:
            return url, None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch, u): u for u in missing}
        for future in as_completed(futures):
            url, data = future.result()
            cache[url] = data


def _show_image_card(url: str, max_height: int = 300) -> None:
    """Square-cropped card image via base64 — consistent sizing."""
    data = _fetch_image_bytes(url)
    if data:
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top  = (h - side) // 2
            img  = img.crop((left, top, left + side, top + side))
            img  = img.resize((400, 400), Image.LANCZOS)
            buf  = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64  = base64.b64encode(buf.getvalue()).decode()
            st.markdown(
                f"<img src='data:image/jpeg;base64,{b64}' "
                f"style='width:100%;aspect-ratio:1/1;object-fit:cover;"
                f"display:block;border-radius:4px 4px 0 0;max-height:{max_height}px;'>",
                unsafe_allow_html=True,
            )
            return
        except Exception:
            pass
    st.markdown(
        f"<div style='width:100%;aspect-ratio:1/1;max-height:{max_height}px;"
        "background:linear-gradient(135deg,#1a1a1a,#2a2a2a);"
        "border-radius:4px 4px 0 0;'></div>",
        unsafe_allow_html=True,
    )


def _show_image_detail(url: str) -> None:
    """Detail view — responsive with max width constraint."""
    data = _fetch_image_bytes(url)
    if data:
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            if w > 600:
                scale = 600 / w
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=88)
            st.image(buf.getvalue(), use_container_width=True)
            return
        except Exception:
            pass
    st.markdown(
        "<div style='width:100%;aspect-ratio:3/4;"
        "background:linear-gradient(135deg,#1a1a1a,#2a2a2a);"
        "border-radius:4px;'></div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════

def _store_artwork_data(artwork: dict) -> None:
    st.session_state.setdefault("artwork_data_cache", {})[artwork["id"]] = artwork


def _get_artwork_data(artwork_id: str) -> Optional[dict]:
    return st.session_state.get("artwork_data_cache", {}).get(artwork_id)


def _doc_to_card(doc: dict) -> dict:
    return {
        "id":            str(doc["objectId"]),
        "title":         doc.get("title", "Untitled"),
        "artist":        doc.get("artistDisplayName", "Unknown"),
        "year":          doc.get("objectEndDate", ""),
        "image_url":     doc.get("primaryImage") or doc.get("imageUrl", ""),
        "thumbnail_url": doc.get("primaryImageSmall") or doc.get("primaryImage") or doc.get("imageUrl", ""),
    }


def _build_fallback_explanation(doc: dict) -> list[str]:
    parts  = []
    title  = doc.get("title", "This artwork")
    artist = doc.get("artistDisplayName") or doc.get("artist") or "an unknown artist"
    year   = doc.get("objectEndDate") or doc.get("year", "")
    medium = doc.get("medium", "")
    dept   = doc.get("department", "")
    wiki   = doc.get("wikipediaSummary", "")

    header = f"<b>{title}</b> by <b>{artist}</b>"
    if year:
        header += f" ({year})"
    parts.append(header + ".")
    if medium:
        parts.append(f"Medium: {medium}.")
    if dept:
        parts.append(f"Department: {dept}.")
    if wiki:
        parts.append(wiki[:400] + ("…" if len(wiki) > 400 else ""))
    if len(parts) == 1:
        parts.append("Part of the collection based on its visual and metadata profile.")
    return parts


# ═══════════════════════════════════════════════════════════════
#  Neo4j queries — split to avoid cartesian explosions
# ═══════════════════════════════════════════════════════════════

def _neo4j_get_metadata(session, id_str: str) -> dict:
    r1 = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id LIMIT 1
        OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
        OPTIONAL MATCH (artist)-[:NATIONALITY]->(country:Country)
        OPTIONAL MATCH (artist)-[:STUDIED_AT]->(inst:Institution)
        RETURN
            coalesce(toString(artist.name), toString(artist.label), '') AS artist_name,
            collect(DISTINCT coalesce(toString(country.label), toString(country.name))) AS countries,
            collect(DISTINCT coalesce(toString(inst.label), toString(inst.name))) AS institutions
    """, id=id_str).single()

    r2 = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id LIMIT 1
        OPTIONAL MATCH (a)-[:PART_OF]->(mov:Movement)
        OPTIONAL MATCH (a)-[:HAS_GENRE]->(genre:Genre)
        OPTIONAL MATCH (a)-[:USES_TECHNIQUE]->(tech:Technique)
        OPTIONAL MATCH (a)-[:BELONGS_TO]->(dept:Department)
        RETURN
            collect(DISTINCT coalesce(toString(mov.label), toString(mov.name))) AS movements,
            collect(DISTINCT coalesce(toString(genre.label), toString(genre.name))) AS genres,
            collect(DISTINCT coalesce(toString(tech.label), toString(tech.name))) AS techniques,
            collect(DISTINCT coalesce(toString(dept.label), toString(dept.name))) AS departments
    """, id=id_str).single()

    r3 = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id LIMIT 1
        OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
        OPTIONAL MATCH (a)-[:INFLUENCED_BY]->(infl1:Artist)
        OPTIONAL MATCH (artist)-[:INFLUENCED_BY]->(infl2:Artist)
        WITH
            collect(DISTINCT coalesce(toString(infl1.name), toString(infl1.label))) AS i1,
            collect(DISTINCT coalesce(toString(infl2.name), toString(infl2.label))) AS i2
        RETURN [x IN (i1 + i2) WHERE x IS NOT NULL AND x <> ''] AS influences
    """, id=id_str).single()

    return {
        "artist_name":  (r1["artist_name"] if r1 else ""),
        "countries":    [x for x in (r1["countries"]    if r1 else []) if x],
        "institutions": [x for x in (r1["institutions"] if r1 else []) if x],
        "movements":    [x for x in (r2["movements"]    if r2 else []) if x],
        "genres":       [x for x in (r2["genres"]       if r2 else []) if x],
        "techniques":   [x for x in (r2["techniques"]   if r2 else []) if x],
        "departments":  [x for x in (r2["departments"]  if r2 else []) if x],
        "influences":   [x for x in (r3["influences"]   if r3 else []) if x],
    }


def _neo4j_get_related(session, id_str: str) -> list[tuple[int, str]]:
    result = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id

        CALL {
            WITH a
            MATCH (a)-[:CREATED_BY]->(artist:Artist)<-[:CREATED_BY]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Artist' AS rel_type, 3 AS priority
            LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:PART_OF]->(mov:Movement)<-[:PART_OF]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Movement' AS rel_type, 2 AS priority
            LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:HAS_GENRE]->(genre:Genre)<-[:HAS_GENRE]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Genre' AS rel_type, 4 AS priority
            LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:USES_TECHNIQUE]->(t:Technique)<-[:USES_TECHNIQUE]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Technique' AS rel_type, 1 AS priority
            LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:BELONGS_TO]->(d:Department)<-[:BELONGS_TO]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Department' AS rel_type, 0 AS priority
            LIMIT 3
        }

        RETURN DISTINCT toString(oid) AS oid, rel_type, priority
        ORDER BY priority DESC
        LIMIT 15
    """, id=id_str)

    seen    = set()
    related = []
    for row in result:
        try:
            oid_int = int(row["oid"])
        except (ValueError, TypeError):
            continue
        if oid_int not in seen:
            seen.add(oid_int)
            related.append((oid_int, row["rel_type"]))
    return related


# ═══════════════════════════════════════════════════════════════
#  Core data
# ═══════════════════════════════════════════════════════════════

def recommend_artworks(uploaded_image: bytes) -> list[dict]:
    """CLIP → Qdrant → MongoDB. Dedup by objectId only."""
    qdrant     = _qdrant_client()
    db         = _mongo_db()
    collection = os.getenv("QDRANT_COLLECTION", "artworks")
    vector     = _embed_image(uploaded_image)

    try:
        hits = qdrant.search(
            collection_name=collection,
            query_vector=vector,
            limit=12,
            with_payload=True,
        )
    except AttributeError:
        resp = qdrant.query_points(
            collection_name=collection,
            query=vector,
            limit=12,
            with_payload=True,
        )
        hits = resp.points

    results  = []
    seen_ids = set()

    for hit in hits:
        payload   = hit.payload or {}
        object_id = (
            payload.get("objectId") or payload.get("objectID")
            or payload.get("id")    or payload.get("mongo_id")
            or payload.get("title")
        )
        if object_id is None:
            continue
        try:
            object_id = int(object_id)
        except (ValueError, TypeError):
            pass

        if object_id in seen_ids:
            continue
        seen_ids.add(object_id)

        doc = db.artworks.find_one({"objectId": object_id})
        if not doc:
            continue

        results.append({
            "id":               str(doc["objectId"]),
            "title":            doc.get("title", "Untitled"),
            "artist":           doc.get("artistDisplayName", "Unknown"),
            "year":             doc.get("objectEndDate", ""),
            "image_url":        doc.get("primaryImage") or doc.get("imageUrl", ""),
            "thumbnail_url":    doc.get("primaryImageSmall") or doc.get("primaryImage") or doc.get("imageUrl", ""),
            "medium":           doc.get("medium", ""),
            "department":       doc.get("department", ""),
            "similarity_score": hit.score,
        })

    return results


def get_artwork_details(artwork_id: str) -> dict:
    driver = _neo4j_driver()
    db     = _mongo_db()

    try:
        query_id_int = int(artwork_id)
    except ValueError:
        query_id_int = artwork_id
    query_id_str = str(artwork_id)

    # ── MongoDB fetch ──
    doc = db.artworks.find_one({"objectId": query_id_int})
    if doc:
        base = {
            "id":            str(doc["objectId"]),
            "title":         doc.get("title", "Untitled"),
            "artist":        doc.get("artistDisplayName", "Unknown"),
            "year":          doc.get("objectEndDate", ""),
            "image_url":     doc.get("primaryImage") or doc.get("imageUrl", ""),
            "thumbnail_url": doc.get("primaryImageSmall") or doc.get("primaryImage") or doc.get("imageUrl", ""),
            "medium":        doc.get("medium", ""),
            "dimensions":    doc.get("dimensions", ""),
            "department":    doc.get("department", ""),
            "wiki_summary":  doc.get("wikipediaSummary", ""),
        }
    else:
        recs = st.session_state.get("recommendations") or []
        base = next((r for r in recs if r["id"] == artwork_id), {})
        for k in ("medium", "dimensions", "department", "wiki_summary"):
            base.setdefault(k, "")

    explanation_parts: list[str] = []
    graph_sections:    list[dict] = []
    related_artworks:  list[dict] = []
    neo4j_ok = False

    # ── Neo4j: split queries for performance ──
    try:
        with driver.session() as session:
            meta    = _neo4j_get_metadata(session, query_id_str)
            related = _neo4j_get_related(session, query_id_str)

        neo4j_ok    = True
        artist_name = meta["artist_name"] or base.get("artist", "Unknown")

        # Build explanation
        header = f"<b>{base.get('title','This work')}</b> created by <b>{artist_name}</b>"
        if base.get("year"):
            header += f" in {base['year']}"
        explanation_parts.append(header + ".")
        if base.get("medium"):
            explanation_parts.append(f"Medium: {base['medium']}.")
        if base.get("department"):
            explanation_parts.append(f"Department: {base['department']}.")
        wiki = base.get("wiki_summary", "")
        if wiki:
            explanation_parts.append(wiki[:400] + ("…" if len(wiki) > 400 else ""))

        # Graph sections
        def _add_section(label_key: str, label_text: str, items: list) -> None:
            if items:
                graph_sections.append({
                    "label": f"{ICONS.get(label_key, '')} {label_text}".strip(),
                    "items": items,
                })

        _add_section("movement",    "Art Movement",       meta["movements"])
        _add_section("genre",       "Genre",              meta["genres"])
        _add_section("technique",   "Technique",          meta["techniques"])
        _add_section("country",     "Artist Nationality", meta["countries"])
        _add_section("department",  "Department",         meta["departments"])
        _add_section("institution", "Studied At",         meta["institutions"])
        _add_section("influence",   "Influenced By",      meta["influences"])

        # Related artworks — single MongoDB batch query
        if related:
            rel_ids      = [oid for oid, _ in related]
            rel_type_map = {oid: rtype for oid, rtype in related}
            rel_order    = {oid: idx for idx, oid in enumerate(rel_ids)}

            docs = list(db.artworks.find({"objectId": {"$in": rel_ids}}).limit(15))
            docs.sort(key=lambda d: rel_order.get(d["objectId"], 999))

            for rel_doc in docs:
                card = _doc_to_card(rel_doc)
                card["relation_type"] = rel_type_map.get(rel_doc["objectId"], "Related")
                related_artworks.append(card)

    except Exception as exc:
        neo4j_ok = False
        print(f"Neo4j error: {exc}")

    if not explanation_parts:
        explanation_parts = _build_fallback_explanation(doc if doc else base)

    # Fallback: same artist via MongoDB
    if not related_artworks and base.get("artist") and base["artist"] not in ("Unknown", "Unknown Artist"):
        for rel_doc in db.artworks.find({
            "artistDisplayName": base["artist"],
            "objectId":          {"$ne": query_id_int},
        }).limit(6):
            card = _doc_to_card(rel_doc)
            card["relation_type"] = "Same Artist"
            related_artworks.append(card)

    # Prefetch related images in parallel
    urls_to_prefetch = [
        r.get("thumbnail_url") or r.get("image_url", "")
        for r in related_artworks
    ]
    if urls_to_prefetch:
        _prefetch_images_parallel(urls_to_prefetch)

    return {
        "title":             base.get("title", "Untitled"),
        "artist":            base.get("artist", "Unknown Artist"),
        "year":              base.get("year", ""),
        "medium":            base.get("medium", ""),
        "dimensions":        base.get("dimensions", ""),
        "department":        base.get("department", ""),
        "wiki_summary":      base.get("wiki_summary", ""),
        "image_url":         base.get("image_url", base.get("thumbnail_url", "")),
        "explanation_parts": explanation_parts,
        "graph_sections":    graph_sections,
        "related_artworks":  related_artworks,
        "neo4j_ok":          neo4j_ok,
    }


# ═══════════════════════════════════════════════════════════════
#  App config
# ═══════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════
#  Upload view
# ═══════════════════════════════════════════════════════════════

def view_upload() -> None:
    render_header(show_new_search=False)
    render_upload_prompt()

    try:
        logo = Image.open("artemis-logo.png")
        buf  = io.BytesIO()
        logo.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        st.markdown(
            f'<div style="display:flex;justify-content:center;margin-bottom:2rem;">'
            f'<img src="data:image/png;base64,{img_b64}" width="150px"></div>',
            unsafe_allow_html=True,
        )
    except Exception:
        pass

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
            img_bytes = pil_to_bytes(resize_image(img, 800))
            _run_recommendations(img_bytes)


def _run_recommendations(img_bytes: bytes) -> None:
    with st.spinner(random_spinner_msg()):
        try:
            results = recommend_artworks(img_bytes)
            if not results:
                render_error("No recommendations found. Try a different image.")
                return
            st.session_state["uploaded_image"]  = img_bytes
            st.session_state["recommendations"] = results
            for artwork in results:
                _store_artwork_data(artwork)
            urls = [a.get("thumbnail_url") or a.get("image_url", "") for a in results]
            _prefetch_images_parallel(urls)
            st.rerun()
        except Exception as e:
            render_error(f"Recommendation service unavailable: {e}")


# ═══════════════════════════════════════════════════════════════
#  Results view
# ═══════════════════════════════════════════════════════════════

def view_results() -> None:
    render_header(show_new_search=True)
    recommendations: list[dict] = st.session_state["recommendations"]

    col_img, col_txt = st.columns([2, 5], gap="large")
    with col_img:
        try:
            raw = st.session_state["uploaded_image"]
            img = Image.open(io.BytesIO(raw))
            img = resize_image(img, 500)
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

    year_txt = f" · {year}" if year else ""
    badge = ""
    if similarity is not None:
        pct = int(similarity * 100)
        badge = (
            f"<span style='display:inline-block;"
            f"background:rgba(255,49,49,0.12);color:{PRIMARY};"
            f"border:1px solid rgba(255,49,49,0.3);border-radius:20px;"
            f"font-size:0.68rem;letter-spacing:0.06em;"
            f"padding:0.15rem 0.55rem;margin-top:0.4rem;'>{pct}% match</span>"
        )

    st.markdown(
        "<div style='border:1px solid #2A2A2A;border-radius:4px;overflow:hidden;"
        "background:#161616;margin-bottom:0.25rem;'>",
        unsafe_allow_html=True,
    )
    _show_image_card(thumb_url)
    st.markdown(
        f"<div style='padding:0.65rem 0.75rem 0.5rem;'>"
        f"<p style='font-size:0.88rem;line-height:1.3;margin:0 0 0.2rem;"
        f"color:#F0EDE8;font-weight:500;'>{title[:55]}</p>"
        f"<p style='font-size:0.75rem;color:#8A8580;margin:0;'>{artist[:35]}{year_txt}</p>"
        f"{badge}"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("View →", key=f"card_btn_{artwork['id']}", help=f"{title} — {artist}"):
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
            push_history(art_id, artwork.get("title", "Artwork"))
            st.session_state["selected_artwork"] = art_id
            st.rerun()
        except Exception as e:
            render_error(f"Could not load artwork details: {e}")


# ═══════════════════════════════════════════════════════════════
#  Detail view
# ═══════════════════════════════════════════════════════════════

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
                _back_to_results_button()
                return

    # ── Back button only — breadcrumb removed ──
    col_back, _ = st.columns([1, 4])
    with col_back:
        if st.button("← Back to Results", key="back_btn"):
            st.session_state["selected_artwork"] = None
            st.rerun()

    st.write("")
    col_img, col_info = st.columns([1, 1], gap="medium")

    with col_img:
        _show_image_detail(details.get("image_url", ""))

    with col_info:
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
        matched   = next((r for r in recs if r["id"] == art_id), None) or _get_artwork_data(art_id)
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
            st.markdown(
                f"<div class='detail-meta-row'>{''.join(meta_items)}</div>",
                unsafe_allow_html=True,
            )

        if explanation_parts:
            source = "Via knowledge graph" if neo4j_ok else "From collection metadata"
            st.markdown(
                f"<div class='section-label'>About this work "
                f"<span style='font-size:0.6rem;color:#444;margin-left:0.5rem;'>{source}</span></div>",
                unsafe_allow_html=True,
            )
            for para in explanation_parts:
                st.markdown(
                    f"<div class='explanation-text'>{para}</div>",
                    unsafe_allow_html=True,
                )

        if graph_sections:
            st.markdown(
                "<div class='section-label' style='margin-top:1.2rem;'>Graph Context</div>",
                unsafe_allow_html=True,
            )
            for section in graph_sections:
                items_html = "".join(
                    f"<span style='display:inline-block;background:#1E1E1E;"
                    f"border:1px solid #333;border-radius:3px;font-size:0.75rem;"
                    f"padding:0.2rem 0.6rem;margin:0.15rem 0.2rem 0.15rem 0;"
                    f"color:#C8C4BF;'>{item}</span>"
                    for item in section["items"]
                )
                st.markdown(
                    f"<div style='margin-bottom:0.6rem;'>"
                    f"<div style='font-size:0.68rem;text-transform:uppercase;"
                    f"letter-spacing:0.1em;color:#555;margin-bottom:0.3rem;'>{section['label']}</div>"
                    f"<div>{items_html}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    related: list[dict] = details.get("related_artworks", [])
    st.markdown("<hr class='subtle-divider'>", unsafe_allow_html=True)

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


def _render_related(related: list[dict]) -> None:
    from collections import defaultdict
    groups = defaultdict(list)
    for artwork in related:
        groups[artwork.get("relation_type", "Related")].append(artwork)

    priority_order = [
        "Same Artist", "Same Movement", "Same Genre",
        "Same Technique", "Same Department", "Related"
    ]
    sorted_groups = sorted(
        groups.items(),
        key=lambda x: priority_order.index(x[0]) if x[0] in priority_order else 99
    )

    for group_name, artworks in sorted_groups:
        icon = ICONS.get("link", "")
        if "Movement"    in group_name: icon = ICONS.get("movement", "")
        elif "Genre"     in group_name: icon = ICONS.get("genre", "")
        elif "Artist"    in group_name: icon = ICONS.get("artist", "")
        elif "Technique" in group_name: icon = ICONS.get("technique", "")
        elif "Department"in group_name: icon = ICONS.get("department", "")

        st.markdown(
            f"<div class='section-label' style='margin-top:1.2rem;'>"
            f"{icon} {group_name}</div>",
            unsafe_allow_html=True,
        )
        n    = min(len(artworks), 3)
        cols = st.columns(n, gap="small")
        for col, artwork in zip(cols, artworks[:n]):
            with col:
                thumb_url = artwork.get("thumbnail_url") or artwork.get("image_url", "")
                title     = artwork.get("title", "Untitled")
                artist    = artwork.get("artist", "")
                st.markdown(
                    "<div style='border:1px solid #222;border-radius:4px;"
                    "overflow:hidden;background:#161616;'>",
                    unsafe_allow_html=True,
                )
                _show_image_card(thumb_url, max_height=250)
                st.markdown(
                    f"<div style='padding:0.4rem 0.5rem 0.5rem;'>"
                    f"<div style='font-size:0.78rem;font-weight:500;line-height:1.3;"
                    f"color:#F0EDE8;'>{title[:35]}</div>"
                    f"<div style='font-size:0.68rem;color:#6a6460;'>{artist[:28]}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                if st.button("View →", key=f"rel_btn_{artwork['id']}_{group_name}"):
                    _open_artwork(artwork)


def _back_to_results_button() -> None:
    if st.button("← Back to Results"):
        st.session_state["selected_artwork"] = None
        st.rerun()


# ═══════════════════════════════════════════════════════════════
#  Router
# ═══════════════════════════════════════════════════════════════

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