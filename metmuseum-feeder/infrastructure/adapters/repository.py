from infrastructure.adapters.database import MongoConnection
from infrastructure.ports.artwork_store import ArtworkStore

class ArtworkRepository(ArtworkStore):
    def __init__(self, db_instance):
        self.db = db_instance
        self.artworks = self.db["artworks"]
        self.status = self.db["status"]
        self.tracker = self.db["procesados"]

    def init_indexes(self):
        self.artworks.create_index("objectId", unique=True)
        self.status.create_index([("status", 1), ("objectId", 1)])

    def get_last_processed_id(self):
        doc = self.tracker.find_one({"_id": "tracker"})
        return doc["last_id"] if doc else 0

    def update_tracker(self, last_id):
        self.tracker.update_one({"_id": "tracker"}, {"$set": {"last_id": last_id}}, upsert=True)

    def persist_batch(self, artworks, status_list):
        if artworks:
            self.artworks.insert_many(artworks, ordered=False)
            self.status.insert_many(status_list, ordered=False)