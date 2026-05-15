from __future__ import annotations

from infrastructure.adapters.db import get_mongo_db
from infrastructure.ports.artwork_repository import ArtworkRepository


class MongoArtworkRepository(ArtworkRepository):
    def __init__(self, db=None):
        self._db = db or get_mongo_db()
        self._artworks = self._db["artworks"]

    def find_by_object_id(self, object_id: int | str) -> dict | None:
        return self._artworks.find_one({"objectId": object_id})

    def find_by_object_ids(self, object_ids: list[int], limit: int | None = None) -> list[dict]:
        cursor = self._artworks.find({"objectId": {"$in": object_ids}})
        if limit is not None:
            cursor = cursor.limit(limit)
        return list(cursor)

    def find_by_artist(self, artist_name: str, exclude_object_id: int | str, limit: int = 6) -> list[dict]:
        cursor = self._artworks.find({
            "artistDisplayName": artist_name,
            "objectId": {"$ne": exclude_object_id},
        }).limit(limit)
        return list(cursor)
