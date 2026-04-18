import logging
import argparse
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from pymongo import MongoClient

from infrastructure.adapters.mongo.repository import ArtworkRepository
from infrastructure.adapters.neo4j.client import Neo4jClient
import infrastructure.adapters.wikidata.fetcher as wikidata_adapter
import infrastructure.adapters.wikipedia.fetcher as wikipedia_adapter # <-- 1. IMPORTAR

from application.usecases.enricher import Enricher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27018/")
MONGO_DB  = os.getenv("MONGO_DB",  "artemis_db")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wikidata → Neo4j enrichment pipeline")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--setup-only", action="store_true")
    parser.add_argument("--loop", action="store_true")
    return parser.parse_args()

def main() -> None:
    args = parse_args()

    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB]
    mongo_repo = ArtworkRepository(db)
    logger.info(f"Connected to MongoDB ({MONGO_DB}).")

    neo4j = Neo4jClient(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password")
    )
    neo4j.verify_connection()
    neo4j.setup_constraints()

    if args.setup_only:
        logger.info("Setup complete. Exiting.")
        neo4j.close()
        mongo_client.close()
        return

    enricher = Enricher(repository=mongo_repo, graph_store=neo4j, wikidata_adapter=wikidata_adapter,wikipedia_adapter=wikipedia_adapter)

    if args.loop:
        logger.info("Loop mode activated. The feeder will listen indefinitely...")
        total = 0
        while True:
            procesados = enricher.run(batch_size=args.batch_size)
                
            if procesados == 0:
                logger.info(f"Queue is empty (Total processed: {total}). Waiting 15 seconds...")
                time.sleep(15)
                continue
                
            total += procesados
            logger.info(f"Batch finished. Total accumulated this session: {total}")
                
    else:
        procesados = enricher.run(batch_size=args.batch_size)
        logger.info(f"Single run completed. Total processed: {procesados}")

    neo4j.close()
    mongo_client.close()
    logger.info("Done.")

if __name__ == "__main__":
    main()