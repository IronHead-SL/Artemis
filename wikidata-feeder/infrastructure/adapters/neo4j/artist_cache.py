import logging
from neo4j import Driver

logger = logging.getLogger(__name__)

class ArtistCache:
    def __init__(self, driver: Driver):
        self._driver = driver
        self._in_mem: set[str] = set()

    def is_enriched(self, wid: str) -> bool:
        return wid in self._in_mem

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
    
    def mark_batch_enriched(self, wids: set[str]) -> None:
        self._in_mem.update(wids)
        logger.debug(f"Marked {len(wids)} artists as enriched in memory cache.")