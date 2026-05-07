from pymongo import MongoClient
from config import Config

class MongoConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = MongoClient(Config.MONGO_URI, w=1, journal=False, connectTimeoutMS=5000,
                socketTimeoutMS=30000, maxPoolSize=50, minPoolSize=10, serverSelectionTimeoutMS=5000)
            cls._instance._db = cls._instance.client["artemis_db"]
        return cls._instance

    @property
    def db(self):
        return self._db