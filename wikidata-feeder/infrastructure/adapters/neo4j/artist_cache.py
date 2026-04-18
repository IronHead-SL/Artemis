import logging
from neo4j import Driver

logger = logging.getLogger(__name__)

class ArtistCache:
    def __init__(self, driver: Driver):
        self._driver = driver
        self._in_mem: set[str] = set()

    def is_enriched(self, wid: str) -> bool:
        if wid in self._in_mem:
            return True

        with self._driver.session() as session:
            result = session.run(
                "MATCH (a:Artist {wikidataId: $wid}) RETURN a.enriched AS enriched",
                wid=wid,
            ).single()

        enriched = result is not None and result["enriched"] is True
        if enriched:
            self._in_mem.add(wid)
        return enriched

    def mark_enriched(self, wid: str) -> None:
        with self._driver.session() as session:
            session.run(
                "MERGE (a:Artist {wikidataId: $wid}) SET a.enriched = true",
                wid=wid,
            )
        self._in_mem.add(wid)
        logger.debug(f"Artist {wid} marked as enriched in Neo4j.")

    def prefetch(self, wids: list[str]) -> None:
        if not wids:
            return
        with self._driver.session() as session:
            result = session.run(
                "UNWIND $wids AS wid MATCH (a:Artist {wikidataId: wid, enriched: true}) RETURN a.wikidataId AS wid",
                wids=wids,
            )
            for record in result:
                self._in_mem.add(record["wid"])
        logger.debug(f"Prefetched artist cache: {len(self._in_mem)} already-enriched artists.")