from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    def save_batch(self, results):
        pass