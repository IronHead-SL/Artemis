from abc import ABC, abstractmethod

class GraphStore(ABC):
    @abstractmethod
    def setup_constraints(self):
        pass

    @abstractmethod
    def upsert_batch(self, batch_payloads):
        pass

    @abstractmethod
    def is_artist_enriched(self, wid: str) -> bool:
        pass

    @abstractmethod
    def prefetch_artists(self, wids: list):
        pass

    @abstractmethod
    def delete_artworks(self, object_ids: list):
        pass