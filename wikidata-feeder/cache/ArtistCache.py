"""
Persistent artist enrichment cache backed by Neo4j.

An artist is considered "already enriched" when its Artist node carries the
`enriched: true` property.  This survives process restarts — unlike the
previous in-memory set which reset on every run.

Usage
-----
    cache = ArtistCache(neo4j_driver)
    if not cache.is_enriched(artist_wid):
        # ... fetch from Wikidata, write to Neo4j ...
        cache.mark_enriched(artist_wid)
"""

import logging
from neo4j import Driver

logger = logging.getLogger(__name__)


class ArtistCache:
    """
    Two-level cache:
      1. In-memory set  — O(1) look-up for the current process run.
      2. Neo4j property — persists across restarts; consulted on first miss.
    """

    def __init__(self, driver: Driver):
        self._driver  = driver
        self._in_mem: set[str] = set()

    def is_enriched(self, wid: str) -> bool:
        """Return True if this artist has already been fully enriched."""
        if wid in self._in_mem:
            return True

        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (a:Artist {wikidataId: $wid})
                RETURN a.enriched AS enriched
                """,
                wid=wid,
            ).single()

        enriched = result is not None and result["enriched"] is True
        if enriched:
            self._in_mem.add(wid)   # warm the in-memory layer
        return enriched

    def mark_enriched(self, wid: str) -> None:
        """Stamp the Artist node with enriched:true and update the in-memory set."""
        with self._driver.session() as session:
            session.run(
                """
                MERGE (a:Artist {wikidataId: $wid})
                SET a.enriched = true
                """,
                wid=wid,
            )
        self._in_mem.add(wid)
        logger.debug(f"Artist {wid} marked as enriched in Neo4j.")

    def prefetch(self, wids: list[str]) -> None:
        """
        Bulk-load enrichment flags for a list of QIDs into the in-memory cache.
        Call this at the start of a batch to minimise individual round-trips.
        """
        if not wids:
            return
        with self._driver.session() as session:
            result = session.run(
                """
                UNWIND $wids AS wid
                MATCH (a:Artist {wikidataId: wid, enriched: true})
                RETURN a.wikidataId AS wid
                """,
                wids=wids,
            )
            for record in result:
                self._in_mem.add(record["wid"])
        logger.debug(
            f"Prefetched artist cache: {len(self._in_mem)} already-enriched artists."
        )