import logging
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from infrastructure.ports.artwork_store import ArtworkStore


class ArtworkRepository(ArtworkStore):
    def __init__(self, db_instance):
        self.db        = db_instance
        self.artworks  = self.db["artworks"]
        self.status    = self.db["status"]
        self.tracker   = self.db["procesados"]

    def init_indexes(self):
        self.artworks.create_index("objectId", unique=True, background=True)
        self.artworks.create_index("department", background=True)
        self.artworks.create_index("artistDisplayName", background=True)
        self.artworks.create_index("medium", background=True)
        self.artworks.create_index("objectWikidataUrl", background=True)

        self.status.create_index("objectId", unique=True, background=True)
        self.status.create_index("status", background=True)
        self.status.create_index([("status", 1), ("objectId", 1)], background=True)

    def get_last_processed_id(self):
        doc = self.tracker.find_one({"_id": "tracker"})
        return doc["last_id"] if doc else 0

    def update_tracker(self, last_id):
        self.tracker.update_one(
            {"_id": "tracker"},
            {"$set": {"last_id": last_id}},
            upsert=True
        )

    def persist_batch(self, artworks, status_list):
        if not artworks:
            return

        art_ops = [
            UpdateOne(
                {"objectId": a["objectId"]},
                {"$setOnInsert": a},
                upsert=True
            ) for a in artworks
        ]
        stat_ops = [
            UpdateOne(
                {"objectId": s["objectId"]},
                {"$setOnInsert": s},
                upsert=True
            ) for s in status_list
        ]

        try:
            self.artworks.bulk_write(art_ops, ordered=False)
            self.status.bulk_write(stat_ops, ordered=False)
        except BulkWriteError as bwe:
            errors = bwe.details.get('writeErrors', [])
