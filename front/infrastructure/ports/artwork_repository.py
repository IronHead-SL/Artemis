from __future__ import annotations

from abc import ABC, abstractmethod


class ArtworkRepository(ABC):
    @abstractmethod
    def find_by_object_id(self, object_id: int | str) -> dict | None:
        pass

    @abstractmethod
    def find_by_object_ids(self, object_ids: list[int], limit: int | None = None) -> list[dict]:
        pass

    @abstractmethod
    def find_by_artist(self, artist_name: str, exclude_object_id: int | str, limit: int = 6) -> list[dict]:
        pass
