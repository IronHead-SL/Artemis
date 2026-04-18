import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from infrastructure.ports.graph_store import GraphStore
from infrastructure.adapters.neo4j.constraints import setup_constraints
from infrastructure.adapters.neo4j.queries import BATCH_UPSERT_QUERY
from infrastructure.adapters.neo4j.artist_cache import ArtistCache

logger = logging.getLogger(__name__)

class Neo4jClient(GraphStore):
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.cache = ArtistCache(self.driver)

    def close(self):
        self.driver.close()

    def verify_connection(self):
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j connection verified.")
        except ServiceUnavailable as e:
            logger.error(f"Cannot connect to Neo4j: {e}")
            raise

    def setup_constraints(self):
        setup_constraints(self.driver)

    def upsert_batch(self, batch_payloads: list) -> None:
        unwind_data = []
        for item in batch_payloads:
            for creator in item["wiki"].get("creators", []):
                self.cache.mark_enriched(creator["id"])

            unwind_data.append({
                "wid": item["wid"],
                "objectId": str(item["mongo"].get("objectId", "")),
                "title": item["mongo"].get("title", ""),
                "department": item["mongo"].get("department", ""),
                "medium": item["mongo"].get("medium", ""),
                "objectDate": item["mongo"].get("objectDate", ""),
                "objectUrl": item["mongo"].get("objectURL", item["mongo"].get("objectUrl", "")),
                "genres": item["wiki"].get("genres", []),
                "movements": item["wiki"].get("movements", []),
                "creators": item["wiki"].get("creators", []),
                "depicts": item["wiki"].get("depicts", [])
            })

        with self.driver.session() as session:
            session.run(BATCH_UPSERT_QUERY, batch=unwind_data)