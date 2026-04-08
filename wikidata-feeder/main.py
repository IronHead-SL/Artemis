import logging
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pymongo import MongoClient
from neo4j_client import Neo4jClient
from enricher import Enricher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:password@localhost:27017/")
MONGO_DB  = os.getenv("MONGO_DB",  "artemis_db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Wikidata → Neo4j enrichment pipeline"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of artworks to process per run (default: 50)",
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Only create Neo4j constraints and exit",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep running until no pending artworks remain",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # ── MongoDB ──────────────────────────────────────────────────────────────
    mongo_client       = MongoClient(MONGO_URI)
    db                 = mongo_client[MONGO_DB]
    artworks_col       = db["artworks"]
    status_col         = db["status"]
    logger.info(f"Connected to MongoDB ({MONGO_DB}).")

    # ── Neo4j ────────────────────────────────────────────────────────────────
    neo4j = Neo4jClient()
    neo4j.verify_connection()
    neo4j.setup_constraints()

    if args.setup_only:
        logger.info("Setup complete. Exiting.")
        neo4j.close()
        mongo_client.close()
        return

    # ── Enricher ─────────────────────────────────────────────────────────────
    enricher = Enricher(
        artworks_collection=artworks_col,
        status_collection=status_col,
        neo4j=neo4j,
    )

    if args.loop:
        logger.info("Loop mode — running until all pending artworks are enriched…")
        total = 0
        while True:
            pending_count = status_col.count_documents({"status": "PENDING_WIKIPEDIA"})
            if pending_count == 0:
                logger.info(f"All artworks enriched (total this run: {total}). Exiting.")
                break
            logger.info(f"{pending_count} artworks still pending.")
            enriched = enricher.run(batch_size=args.batch_size)
            total += enriched
    else:
        enricher.run(batch_size=args.batch_size)

    neo4j.close()
    mongo_client.close()
    logger.info("Done.")


if __name__ == "__main__":
    main()