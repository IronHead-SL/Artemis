from typing import List
from domain.image_to_process import ImageToProcess
from infrastructure.ports.image_repository import ImageRepository

class MongoImageRepository(ImageRepository):
    def __init__(self, db_instance):
        self.artworks = db_instance["artworks"]
        self.status = db_instance["status"]
    
    def get_unprocessed(self, limit):
        pending_docs = self.status.find({"status": "PENDING_IA"}).limit(limit)
        
        images_to_process = []
        for doc in pending_docs:
            oid = doc.get("objectId")
            artwork = self.artworks.find_one({"objectId": oid})
            
            if artwork and artwork.get("imageUrl"):
                images_to_process.append(ImageToProcess(str(oid), artwork["imageUrl"]))
        return images_to_process
    
    def mark_as_processed(self, image_id):
        self.status.update_one({"objectId": int(image_id)}, {"$set": {"status": "PROCESSED_IA"}})