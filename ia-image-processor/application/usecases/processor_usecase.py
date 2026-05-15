from infrastructure.ports.image_repository import ImageRepository
from infrastructure.ports.model_service import ModelService
from infrastructure.ports.vector_store import VectorStore

class ImageProcessorUseCase:
    def __init__(self, repo, model, vector_db):
        self.repo = repo
        self.model = model
        self.vector_db = vector_db

    def run(self, batch_size):
        images = self.repo.get_unprocessed(batch_size)
        if not images: 
            return 0
        
        results = []
        processed_ids = []
        
        if hasattr(self.model, "get_embeddings"):
            embeddings_map = self.model.get_embeddings(images)
            for img in images:
                embedding = embeddings_map.get(img.id)
                if embedding is None:
                    print(f"Saltando imagen {img.id}: error en embedding")
                    self.repo.mark_as_failed(img.id, "EMBEDDING_ERROR")
                    continue
                results.append(embedding)
                processed_ids.append(img.id)
        else:
            for img in images:
                embedding = self.model.get_embedding(img.id, img.url)

                if embedding is None:
                    print(f"Saltando imagen {img.id}: error en embedding")
                    self.repo.mark_as_failed(img.id, "EMBEDDING_ERROR")
                    continue

                results.append(embedding)
                processed_ids.append(img.id)
        
        if results:
            self.vector_db.save_batch(results)
        
        for img_id in processed_ids:
            self.repo.mark_as_processed(img_id)
            
        return len(processed_ids)