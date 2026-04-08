from abc import ABC, abstractmethod

class ArtworkProvider(ABC):
    @abstractmethod
    def get_available_ids(self):
        pass

    @abstractmethod
    def fetch_artwork_data(self, object_id):
        pass