import time
from infrastructure.adapters.mongo.database import MongoConnection
from infrastructure.adapters.mongo.mongo_image_adapter import MongoImageRepository
from infrastructure.adapters.qdrant.qdrant_store import QdrantStore
from infrastructure.adapters.clip.clip_service import CLIPService
from application.usecases.processor_usecase import ImageProcessorUseCase

def main():
    print("Iniciando Artemis AI Processor...")
    db = MongoConnection().db
    
    repo = MongoImageRepository(db)
    model = CLIPService() 
    vector_db = QdrantStore()
    
    processor = ImageProcessorUseCase(repo, model, vector_db)
    
    while True:
        try:
            batch_count = processor.run(batch_size=50)
            if batch_count == 0:
                print("Todo procesado. Esperando 15s...")
                time.sleep(15)
            else:
                print(f"Procesado lote de {batch_count} imágenes.")
                time.sleep(1)
        except Exception as e:
            print(f"Error en el proceso: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()