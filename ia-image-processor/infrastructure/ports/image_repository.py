from abc import ABC, abstractmethod

class ImageRepository(ABC):
    @abstractmethod
    def get_unprocessed(self, limit):
        pass
    
    @abstractmethod
    def mark_as_processed(self, image_id):
        pass

    @abstractmethod
    def mark_as_failed(self, image_id, reason: str | None = None):
        pass