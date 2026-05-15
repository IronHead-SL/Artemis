from __future__ import annotations

from abc import ABC, abstractmethod


class GraphQuery(ABC):
    @abstractmethod
    def get_metadata_and_related(self, id_str: str) -> tuple[dict, list[tuple[int, str]]]:
        pass
