import os
from pymongo import MongoClient

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/")
OBJECT_IDS_JSON = 'object_ids.json'
BATCH_SIZE = 100


client = MongoClient(MONGO_URI)
db = client["artemis_db"]
artworks_collection = db["artworks"]
procesados_collection = db["procesados"]
status_collection = db["status"]