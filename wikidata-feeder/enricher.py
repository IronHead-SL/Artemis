import logging
from pymongo.collection import Collection

from wikidata_client import (
    fetch_artwork_data,
    fetch_artist_data,
    extract_wikidata_id,
)
from neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

STATUS_PENDING = "PENDING_WIKIPEDIA"
STATUS_ENRICHED = "ENRICHED"
STATUS_NO_WIKIDATA = "NO_WIKIDATA"
STATUS_ERROR = "ENRICHMENT_ERROR"


class Enricher:
    def __init__(
        self,
        artworks_collection: Collection,
        status_collection: Collection,
        neo4j: Neo4jClient,
    ):
        self.artworks = artworks_collection
        self.status = status_collection
        self.neo4j = neo4j

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, batch_size: int = 50):
        """
        Process all artworks with status PENDING_WIKIPEDIA.
        For each artwork:
          1. Query Wikidata for artwork context.
          2. Query Wikidata for each artist.
          3. Write everything to Neo4j.
          4. Update Mongo status.
        """
        pending = list(
            self.status.find({"status": STATUS_PENDING}).limit(batch_size)
        )

        if not pending:
            logger.info("No pending artworks to enrich.")
            return

        logger.info(f"Enriching {len(pending)} artworks...")

        for record in pending:
            object_id = record["objectId"]
            try:
                self._enrich_one(object_id)
            except Exception as e:
                logger.error(f"Unexpected error enriching {object_id}: {e}", exc_info=True)
                self._set_status(object_id, STATUS_ERROR)


    def _enrich_one(self, object_id: int):
        artwork_doc = self.artworks.find_one({"objectId": object_id})
        if not artwork_doc:
            logger.warning(f"Artwork {object_id} not found in artworks collection.")
            self._set_status(object_id, STATUS_ERROR)
            return

        artwork_wid = extract_wikidata_id(artwork_doc.get("objectWikidataUrl", ""))
        if not artwork_wid:
            logger.info(f"Artwork {object_id} has no Wikidata URL — skipping.")
            self._set_status(object_id, STATUS_NO_WIKIDATA)
            return

        logger.info(f"Enriching artwork {object_id} ({artwork_wid})...")

        artwork_wd = fetch_artwork_data(artwork_wid)

        with self.neo4j.driver.session() as session:
            self.neo4j.upsert_artwork(session, {
                "wikidataId":  artwork_wid,
                "objectId":    str(object_id),
                "title":       artwork_doc.get("title", ""),
                "department":  artwork_doc.get("department", ""),
                "medium":      artwork_doc.get("medium", ""),
                "objectDate":  artwork_doc.get("objectDate", ""),
                "objectUrl":   artwork_doc.get("objectUrl", ""),
            })

            for genre in artwork_wd["genres"]:
                self.neo4j.link_artwork_to_genre(session, artwork_wid, genre["label"])

            for movement in artwork_wd["movements"]:
                self.neo4j.link_artwork_to_movement(session, artwork_wid, movement["label"])

            for concept in artwork_wd["depicts"]:
                self.neo4j.link_artwork_to_concept(
                    session, artwork_wid, concept["id"], concept["label"]
                )

            for creator in artwork_wd["creators"]:
                self._enrich_artist(session, creator["id"], creator["label"])
                self.neo4j.link_artwork_to_artist(session, artwork_wid, creator["id"])

        artist_wid = extract_wikidata_id(artwork_doc.get("artistWikidataUrl", ""))
        if artist_wid:
            with self.neo4j.driver.session() as session:
                self._enrich_artist(session, artist_wid, artwork_doc.get("artistDisplayName", ""))
                self.neo4j.link_artwork_to_artist(session, artwork_wid, artist_wid)

        self._set_status(object_id, STATUS_ENRICHED)
        logger.info(f"✓ Artwork {object_id} enriched.")


    def _enrich_artist(self, session, artist_wid: str, fallback_name: str = ""):
        """
        Fetch and persist full artist context from Wikidata into Neo4j.
        Uses a single Neo4j session passed from the caller.
        """
        artist_wd = fetch_artist_data(artist_wid)

        self.neo4j.upsert_artist(session, {
            "wikidataId":       artist_wid,
            "name":             artist_wd["name"] or fallback_name,
            "birthDate":        artist_wd["birthDate"] or "",
            "deathDate":        artist_wd["deathDate"] or "",
            "genderLabel":      artist_wd["genderLabel"] or "",
            "occupationLabel":  artist_wd["occupationLabel"] or "",
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

    def _set_status(self, object_id: int, status: str):
        self.status.update_one(
            {"objectId": object_id},
            {"$set": {"status": status}},
        )