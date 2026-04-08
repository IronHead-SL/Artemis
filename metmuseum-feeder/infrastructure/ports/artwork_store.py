from abc import ABC, abstractmethod

class ArtworkStore(ABC):
    @abstractmethod
    def init_indexes(self):
        pass

    @abstractmethod
    def get_last_processed_id(self) -> int:
        pass

    @abstractmethod
    def update_tracker(self, last_id: int):
        pass

    @abstractmethod
    def persist_batch(self, artworks: list, status_list: list):
        pass