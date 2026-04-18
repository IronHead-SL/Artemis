from abc import ABC, abstractmethod

class GraphStore(ABC):
    @abstractmethod
    def setup_constraints(self):
        pass

    @abstractmethod
    def upsert_batch(self, batch_payloads):
        pass