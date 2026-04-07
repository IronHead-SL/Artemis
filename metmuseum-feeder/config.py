import os

class Config:
    BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/")
    OBJECT_IDS_JSON = 'object_ids.json'
    BATCH_SIZE = 100