from datetime import datetime
from typing import List
from domain.image_to_process import ImageToProcess
from infrastructure.ports.image_repository import ImageRepository

class MongoImageRepository(ImageRepository):
    def __init__(self, db_instance):
        self.artworks = db_instance["artworks"]
        self.status = db_instance["status"]
    
    def get_unprocessed(self, limit):
            pending_docs = self.status.find({"status": "PENDING_IA"}, {"objectId": 1, "_id": 0}).limit(limit)
            
            images_to_process = []
            object_ids = [doc["objectId"] for doc in pending_docs]
            
            if not object_ids:
                return []
            
            artworks_cursor = self.artworks.find({"objectId": {"$in": object_ids}},{"objectId": 1, "imageUrl": 1, "_id": 0})
            
            artwork_map = {a["objectId"]: a for a in artworks_cursor}

            missing = []
            for oid in object_ids:
                artwork = artwork_map.get(oid)
                if artwork and artwork.get("imageUrl"):
                    images_to_process.append(ImageToProcess(str(oid), artwork["imageUrl"]))
                else:
                    reason = "ARTWORK_NOT_FOUND" if artwork is None else "MISSING_IMAGE_URL"
                    missing.append((oid, reason))

            for oid, reason in missing:
                self.mark_as_failed(oid, reason)

            return images_to_process
    
    def mark_as_processed(self, image_id):
        self.status.update_one({"objectId": int(image_id)}, {"$set": {"status": "PROCESSED_IA"}})

    def mark_as_failed(self, image_id, reason: str | None = None):
        payload = {"status": "FAILED_IA", "updated_at": datetime.utcnow()}
        if reason:
            payload["error_reason"] = reason
        self.status.update_one({"objectId": int(image_id)}, {"$set": payload})