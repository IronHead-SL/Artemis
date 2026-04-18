class ArtworkRepository:
    def __init__(self, db_instance):
        self.db = db_instance
        self.artworks = self.db["artworks"]
        self.status_col = self.db["status"]

    def get_pending_batch(self, status: str, limit: int) -> list:
        pending_docs = list(self.status_col.find({"status": status}).limit(limit))
        if not pending_docs:
            return []
            
        object_ids = [doc["objectId"] for doc in pending_docs]
        return list(self.artworks.find({"objectId": {"$in": object_ids}}))

    def update_status_batch(self, object_ids: list, new_status: str) -> None:
        if not object_ids:
            return
            
        self.status_col.update_many(
            {"objectId": {"$in": object_ids}},
            {"$set": {"status": new_status}}
        )