from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

class ArtworkRepository:
    def __init__(self, db_instance):
        self.db = db_instance
        self.artworks = self.db["artworks"]
        self.status_col = self.db["status"]

    def get_pending_batch(self, status: str, limit: int) -> list:
        pending_docs = list(self.status_col.find({"status": status}, {"objectId": 1, "_id": 0})
                            .limit(limit))
        
        if not pending_docs: 
            return []
        
        object_ids = [doc["objectId"] for doc in pending_docs]
        return list(self.artworks.find(
            {"objectId": {"$in": object_ids}},
            {
                "objectId": 1, "title": 1, "objectWikidataUrl": 1,
                "artistWikidataUrl": 1, "department": 1, "medium": 1,
                "objectDate": 1, "objectUrl": 1, "objectURL": 1,
                "artistDisplayName": 1
            }
        ))

    def update_status_batch(self, object_ids: list, new_status: str) -> None:
        if not object_ids:
            return
            
        self.status_col.update_many({"objectId": {"$in": object_ids}}, {"$set": {"status": new_status}})

    def save_enriched_batch(self, enriched_payloads: list, new_status: str) -> None:
        if not enriched_payloads: 
            return
            
        art_ops = []
        stat_ops = []
        
        for item in enriched_payloads:
            obj_id = item["mongo_id"]
            stat_ops.append(UpdateOne(
                {"objectId": obj_id}, 
                {"$set": {"status": new_status}}
            ))
            
            if item.get("extract"):
                art_ops.append(UpdateOne(
                    {"objectId": obj_id}, 
                    {"$set": {"wikipediaSummary": item["extract"]}}
                ))
        
        try:
            if stat_ops: 
                self.status_col.bulk_write(stat_ops, ordered=False)
            if art_ops: 
                self.artworks.bulk_write(art_ops, ordered=False)
        except BulkWriteError as bwe:
            errors = bwe.details.get('writeErrors', [])
            if len(errors) == len(stat_ops):
                raise
            print(f"Partial bulk write: {len(errors)} errors of {len(stat_ops)}")