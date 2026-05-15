from __future__ import annotations

from abc import ABC, abstractmethod


class ImageEmbedder(ABC):
    @abstractmethod
    def embed(self, image_bytes: bytes) -> list[float]:
        pass
