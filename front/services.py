from __future__ import annotations

import io
import os
from typing import Optional

import torch
import streamlit as st
from PIL import Image

from constants import ICONS
from db import get_clip_model, get_mongo_db, get_qdrant, get_neo4j
from image_utils import prefetch_images_parallel
from queries import neo4j_metadata, neo4j_related


def embed_image(image_bytes: bytes) -> list[float]:
    model, preprocess = get_clip_model()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = preprocess(img).unsqueeze(0)
    with torch.no_grad():
        vector = model.encode_image(tensor)
    vector /= vector.norm(dim=-1, keepdim=True)
    return vector.cpu().numpy().tolist()[0]


def doc_to_card(doc: dict) -> dict:
    return {
        "id":            str(doc["objectId"]),
        "title":         doc.get("title", "Untitled"),
        "artist":        doc.get("artistDisplayName", "Unknown"),
        "year":          doc.get("objectEndDate", ""),
        "image_url":     doc.get("primaryImage") or doc.get("imageUrl", ""),
        "thumbnail_url": doc.get("primaryImageSmall") or doc.get("primaryImage") or doc.get("imageUrl", ""),
    }


def recommend_artworks(uploaded_image: bytes) -> list[dict]:
    qdrant     = get_qdrant()
    db         = get_mongo_db()
    collection = os.getenv("QDRANT_COLLECTION", "artworks")
    vector     = embed_image(uploaded_image)

    try:
        hits = qdrant.search(collection_name=collection, query_vector=vector, limit=12, with_payload=True)
    except AttributeError:
        hits = qdrant.query_points(collection_name=collection, query=vector, limit=12, with_payload=True).points

    results, seen_ids = [], set()
    for hit in hits:
        payload   = hit.payload or {}
        object_id = (
            payload.get("objectId") or payload.get("objectID")
            or payload.get("id") or payload.get("mongo_id") or payload.get("title")
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


def _fallback_explanation(doc: dict) -> list[str]:
    parts  = []
    artist = doc.get("artistDisplayName") or doc.get("artist") or "an unknown artist"
    title  = doc.get("title", "This artwork")
    year   = doc.get("objectEndDate") or doc.get("year", "")
    header = f"<b>{title}</b> by <b>{artist}</b>"
    if year:
        header += f" ({year})"
    parts.append(header + ".")
    if doc.get("medium"):
        parts.append(f"Medium: {doc['medium']}.")
    if doc.get("department"):
        parts.append(f"Department: {doc['department']}.")
    if doc.get("wikipediaSummary"):
        wiki = doc["wikipediaSummary"]
        parts.append(wiki[:400] + ("…" if len(wiki) > 400 else ""))
    if len(parts) == 1:
        parts.append("Part of the collection based on its visual and metadata profile.")
    return parts


def get_artwork_details(artwork_id: str) -> dict:
    driver = get_neo4j()
    db     = get_mongo_db()

    try:
        query_id_int = int(artwork_id)
    except ValueError:
        query_id_int = artwork_id
    query_id_str = str(artwork_id)

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

    try:
        with driver.session() as session:
            meta    = neo4j_metadata(session, query_id_str)
            related = neo4j_related(session, query_id_str)

        neo4j_ok    = True
        artist_name = meta["artist_name"] or base.get("artist", "Unknown")

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

        def _section(key: str, label: str, items: list) -> None:
            if items:
                graph_sections.append({"label": f"{ICONS.get(key,'')} {label}".strip(), "items": items})

        _section("movement",    "Art Movement",       meta["movements"])
        _section("genre",       "Genre",              meta["genres"])
        _section("technique",   "Technique",          meta["techniques"])
        _section("country",     "Artist Nationality", meta["countries"])
        _section("department",  "Department",         meta["departments"])
        _section("institution", "Studied At",         meta["institutions"])
        _section("influence",   "Influenced By",      meta["influences"])

        if related:
            rel_ids      = [oid for oid, _ in related]
            rel_type_map = {oid: rtype for oid, rtype in related}
            rel_order    = {oid: i for i, oid in enumerate(rel_ids)}
            docs = sorted(
                db.artworks.find({"objectId": {"$in": rel_ids}}).limit(15),
                key=lambda d: rel_order.get(d["objectId"], 999),
            )
            for rel_doc in docs:
                card = doc_to_card(rel_doc)
                card["relation_type"] = rel_type_map.get(rel_doc["objectId"], "Related")
                related_artworks.append(card)

    except Exception as exc:
        neo4j_ok = False
        print(f"Neo4j error: {exc}")

    if not explanation_parts:
        explanation_parts = _fallback_explanation(doc if doc else base)

    if not related_artworks and base.get("artist") and base["artist"] not in ("Unknown", "Unknown Artist"):
        for rel_doc in db.artworks.find({
            "artistDisplayName": base["artist"],
            "objectId": {"$ne": query_id_int},
        }).limit(6):
            card = doc_to_card(rel_doc)
            card["relation_type"] = "Same Artist"
            related_artworks.append(card)

    prefetch_images_parallel([r.get("thumbnail_url") or r.get("image_url", "") for r in related_artworks])

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
