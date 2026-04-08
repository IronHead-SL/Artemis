import logging
from pymongo.collection import Collection

from utils.fetch_data import *
from utils.extractor import extract_wikidata_id
from neo4j_client import Neo4jClient
from cache.ArtistCache import ArtistCache

logger = logging.getLogger(__name__)

STATUS_PENDING     = "PENDING_WIKIPEDIA"
STATUS_ENRICHED    = "ENRICHED"
STATUS_NO_WIKIDATA = "NO_WIKIDATA"
STATUS_ERROR       = "ENRICHMENT_ERROR"


class Enricher:
    def __init__(
        self,
        artworks_collection: Collection,
        status_collection: Collection,
        neo4j: Neo4jClient,
    ):
        self.artworks = artworks_collection
        self.status   = status_collection
        self.neo4j    = neo4j
        self._cache   = ArtistCache(neo4j.driver)

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, batch_size: int = 50) -> int:
        """
        Process artworks with status PENDING_WIKIPEDIA.
        Returns the count of artworks successfully enriched.
        """
        pending = list(
            self.status.find({"status": STATUS_PENDING}).limit(batch_size)
        )
        if not pending:
            logger.info("No pending artworks to enrich.")
            return 0

        logger.info(f"Enriching batch of {len(pending)} artworks...")

        # Prefetch artist cache for the whole batch in one Neo4j round-trip
        object_ids  = [r["objectId"] for r in pending]
        artist_wids = self._collect_artist_wids(object_ids)
        self._cache.prefetch(artist_wids)

        enriched = 0
        for record in pending:
            object_id = record["objectId"]
            try:
                self._enrich_one(object_id)
                enriched += 1
            except Exception as e:
                logger.error(
                    f"Unexpected error enriching objectId={object_id}: {e}",
                    exc_info=True,
                )
                self._set_status(object_id, STATUS_ERROR)

        logger.info(f"Batch complete: {enriched}/{len(pending)} enriched.")
        return enriched

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _collect_artist_wids(self, object_ids: list) -> list[str]:
        """Pull all artistWikidataUrl values for the batch from MongoDB."""
        docs = self.artworks.find(
            {"objectId": {"$in": object_ids}},
            {"artistWikidataUrl": 1, "_id": 0},
        )
        wids = []
        for doc in docs:
            wid = extract_wikidata_id(doc.get("artistWikidataUrl", ""))
            if wid:
                wids.append(wid)
        return wids

    # ── Per-artwork logic ─────────────────────────────────────────────────────

    def _enrich_one(self, object_id: int) -> None:
        # 1. Fetch MongoDB document
        artwork_doc = self.artworks.find_one({"objectId": object_id})
        if not artwork_doc:
            logger.warning(f"objectId={object_id} not found in artworks collection.")
            self._set_status(object_id, STATUS_ERROR)
            return

        artwork_wid = extract_wikidata_id(artwork_doc.get("objectWikidataUrl", ""))
        if not artwork_wid:
            logger.info(f"objectId={object_id} has no valid Wikidata URL — skipping.")
            self._set_status(object_id, STATUS_NO_WIKIDATA)
            return

        logger.info(f"Enriching objectId={object_id} ({artwork_wid})...")

        # 2. Fetch artwork context from Wikidata
        artwork_wd = fetch_artwork_data(artwork_wid)

        # 3. Write everything inside ONE Neo4j session
        with self.neo4j.driver.session() as session:

            self.neo4j.upsert_artwork(session, {
                "wikidataId": artwork_wid,
                "objectId":   str(object_id),
                "title":      artwork_doc.get("title", ""),
                "department": artwork_doc.get("department", ""),
                "medium":     artwork_doc.get("medium", ""),
                "objectDate": artwork_doc.get("objectDate", ""),
                "objectUrl":  artwork_doc.get("objectURL", artwork_doc.get("objectUrl", "")),
            })

            for genre in artwork_wd["genres"]:
                self.neo4j.link_artwork_to_genre(session, artwork_wid, genre["label"])

            for movement in artwork_wd["movements"]:
                self.neo4j.link_artwork_to_movement(session, artwork_wid, movement["label"])

            for concept in artwork_wd["depicts"]:
                self.neo4j.link_artwork_to_concept(
                    session, artwork_wid, concept["id"], concept["label"]
                )

            # Creators from Wikidata (P170)
            for creator in artwork_wd["creators"]:
                self._enrich_artist(session, creator["id"], creator["label"])
                self.neo4j.link_artwork_to_artist(session, artwork_wid, creator["id"])

            # Main artist from MET metadata in MongoDB
            artist_wid = extract_wikidata_id(artwork_doc.get("artistWikidataUrl", ""))
            if artist_wid:
                fallback = artwork_doc.get("artistDisplayName", "")
                self._enrich_artist(session, artist_wid, fallback)
                self.neo4j.link_artwork_to_artist(session, artwork_wid, artist_wid)

        # 4. Mark done in MongoDB
        self._set_status(object_id, STATUS_ENRICHED)
        logger.info(f"OK objectId={object_id} ({artwork_wid}) enriched.")

    # ── Artist enrichment ─────────────────────────────────────────────────────

    def _enrich_artist(self, session, artist_wid: str, fallback_name: str = "") -> None:
        """
        Fetch full artist context from Wikidata and persist to Neo4j.
        Skips the Wikidata fetch entirely if the artist is already flagged
        as enriched in the persistent ArtistCache (survives process restarts).
        """
        if self._cache.is_enriched(artist_wid):
            logger.debug(f"Artist {artist_wid} already enriched — skipping Wikidata fetch.")
            return

        artist_wd = fetch_artist_data(artist_wid)

        self.neo4j.upsert_artist(session, {
            "wikidataId":      artist_wid,
            "name":            artist_wd["name"]            or fallback_name,
            "birthDate":       artist_wd["birthDate"]       or "",
            "deathDate":       artist_wd["deathDate"]       or "",
            "genderLabel":     artist_wd["genderLabel"]     or "",
            "occupationLabel": artist_wd["occupationLabel"] or "",
        })

        for country in artist_wd["nationalities"]:
            self.neo4j.link_artist_to_country(session, artist_wid, country)

        for movement in artist_wd["movements"]:
            self.neo4j.link_artist_to_movement(session, artist_wid, movement["label"])

        for inf in artist_wd["influenced_by"]:
            self.neo4j.link_artist_influenced_by(
                session, artist_wid, inf["id"], inf["label"]
            )

        for institution in artist_wd["institutions"]:
            self.neo4j.link_artist_to_institution(session, artist_wid, institution)

        self._cache.mark_enriched(artist_wid)

    # ── Status helpers ─────────────────────────────────────────────────────────

    def _set_status(self, object_id: int, status: str) -> None:
        self.status.update_one(
            {"objectId": object_id},
            {"$set": {"status": status}},
            upsert=True,
        )