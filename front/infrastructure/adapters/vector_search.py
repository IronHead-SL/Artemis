from __future__ import annotations

import os

from infrastructure.adapters.db import get_qdrant
from infrastructure.ports.vector_search import VectorSearch


class QdrantVectorSearch(VectorSearch):
    def __init__(self, client=None, collection: str | None = None):
        self._client = client or get_qdrant()
        self._collection = collection or os.getenv("QDRANT_COLLECTION", "artworks")

    def search(self, vector: list[float], limit: int = 12):
        try:
            return self._client.search(
                collection_name=self._collection,
                query_vector=vector,
                limit=limit,
                with_payload=True,
            )
        except AttributeError:
            return self._client.query_points(
                collection_name=self._collection,
                query=vector,
                limit=limit,
                with_payload=True,
            ).points
