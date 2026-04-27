import os

class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/")
