import logging
from config import Config
from domain.artwork import ArtworkBuilder
from infrastructure.adapters.met.adapter import MetMuseumAdapter
from infrastructure.adapters.mongo.database import MongoConnection
from infrastructure.adapters.mongo.repository import ArtworkRepository
from application.usecases.collector import ArtworkCollector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

def main():
    db_instance = MongoConnection().db
    repo = ArtworkRepository(db_instance)
    api = MetMuseumAdapter()

    builder = ArtworkBuilder()
    
    repo.init_indexes()
    collector = ArtworkCollector(provider=api, store=repo, builder=builder)

    collector.run()

if __name__ == "__main__":
    main()