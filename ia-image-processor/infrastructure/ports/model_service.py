from abc import ABC, abstractmethod

class ModelService(ABC):
    @abstractmethod
    def get_embedding(self, image_id, image_url):
        pass