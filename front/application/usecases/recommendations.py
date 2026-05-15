from __future__ import annotations

from infrastructure.adapters.embedding import ClipImageEmbedder
from infrastructure.adapters.mongo.artwork_repository import MongoArtworkRepository
from infrastructure.adapters.vector_search import QdrantVectorSearch
from infrastructure.ports.artwork_repository import ArtworkRepository
from infrastructure.ports.image_embedder import ImageEmbedder
from infrastructure.ports.vector_search import VectorSearch


def recommend_artworks(
    uploaded_image: bytes,
    embedder: ImageEmbedder | None = None,
    vector_search: VectorSearch | None = None,
    repo: ArtworkRepository | None = None,
) -> list[dict]:
    embedder = embedder or ClipImageEmbedder()
    vector_search = vector_search or QdrantVectorSearch()
    repo = repo or MongoArtworkRepository()

    vector = embedder.embed(uploaded_image)
    hits = vector_search.search(vector, limit=12)

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

        doc = repo.find_by_object_id(object_id)
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
