from infrastructure.adapters.mongo.database import MongoConnection
from pymongo.errors import BulkWriteError
from infrastructure.ports.artwork_store import ArtworkStore

class ArtworkRepository(ArtworkStore):
    def __init__(self, db_instance):
        self.db = db_instance
        self.artworks = self.db["artworks"]
        self.status = self.db["status"]
        self.tracker = self.db["procesados"]

    def init_indexes(self):
        self.artworks.create_index("objectId", unique=True, background=True)
        self.status.create_index("status", background=True)
        self.status.create_index("objectId", unique=True, background=True)

    def get_last_processed_id(self):
        doc = self.tracker.find_one({"_id": "tracker"})
        return doc["last_id"] if doc else 0

    def update_tracker(self, last_id):
        self.tracker.update_one({"_id": "tracker"}, {"$set": {"last_id": last_id}}, upsert=True)

    def persist_batch(self, artworks, status_list):
        if not artworks:
            return
        try:
            self.artworks.insert_many(artworks, ordered=True)
            self.status.insert_many(status_list, ordered=True)
        except BulkWriteError:
            self.artworks.insert_many(artworks, ordered=False)
            self.status.insert_many(status_list, ordered=False)