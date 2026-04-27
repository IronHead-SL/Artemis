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
        for img in images:
            embedding = self.model.get_embedding(img.id, img.url)
            results.append(embedding)
        
        self.vector_db.save_batch(results)
        
        for img in images:
            self.repo.mark_as_processed(img.id)
            
        return len(images)