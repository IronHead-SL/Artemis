from qdrant_client import QdrantClient
from qdrant_client.http import models
from domain.embedding_result import EmbeddingResult
from infrastructure.ports.vector_store import VectorStore

class QdrantStore(VectorStore):
    def __init__(self, url="http://qdrant:6333"):
        self.client = QdrantClient(url)
        self.collection_name = "artworks"
        
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=512, distance=models.Distance.COSINE))

    def save_batch(self, results):
        points = [
            models.PointStruct(
                id=int(r.image_id), 
                vector=r.vector,
                payload={
                    "image_url": r.image_url,
                    "title": r.title,
                    "processed_at": r.processed_at
                }
            ) for r in results
        ]

        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as e:
            print(f"Error guardando en Qdrant: {e}")
            raise