from __future__ import annotations

from abc import ABC, abstractmethod


class VectorSearch(ABC):
    @abstractmethod
    def search(self, vector: list[float], limit: int = 12):
        pass
