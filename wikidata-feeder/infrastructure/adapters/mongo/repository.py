from pymongo import UpdateOne

class ArtworkRepository:
    def __init__(self, db_instance):
        self.db = db_instance
        self.artworks = self.db["artworks"]
        self.status_col = self.db["status"]

    def get_pending_batch(self, status: str, limit: int) -> list:
        pending_docs = list(self.status_col.find({"status": status}).limit(limit))
        if not pending_docs: return []
        
        object_ids = [doc["objectId"] for doc in pending_docs]
        return list(self.artworks.find({"objectId": {"$in": object_ids}}))

    def update_status_batch(self, object_ids: list, new_status: str) -> None:
            if not object_ids:
                return
                
            self.status_col.update_many(
                {"objectId": {"$in": object_ids}},
                {"$set": {"status": new_status}}
            )

    def save_enriched_batch(self, enriched_payloads: list, new_status: str) -> None:
        if not enriched_payloads: return
            
        art_ops = []
        stat_ops = []
        
        for item in enriched_payloads:
            obj_id = item["mongo_id"]
            stat_ops.append(UpdateOne({"objectId": obj_id}, {"$set": {"status": new_status}}))
            
            if item.get("extract"):
                art_ops.append(UpdateOne(
                    {"objectId": obj_id}, 
                    {"$set": {"wikipediaSummary": item["extract"]}}
                ))
                
        if stat_ops: self.status_col.bulk_write(stat_ops)
        if art_ops: self.artworks.bulk_write(art_ops)