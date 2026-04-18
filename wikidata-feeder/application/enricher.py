import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo.collection import Collection

from infrastructure.adapters.wikidata.fetcher import fetch_artwork_data, fetch_artist_data
from domain.wikidata_id import extract_wikidata_id
from infrastructure.adapters.neo4j.client import Neo4jClient
from infrastructure.ports.graph_store import GraphStore

logger = logging.getLogger(__name__)

STATUS_PENDING     = "PENDING_WIKIPEDIA"
STATUS_ENRICHED    = "PENDING_IA"
STATUS_NO_WIKIDATA = "NO_WIKIDATA"
STATUS_ERROR       = "ENRICHMENT_ERROR"

class Enricher:
    def __init__(self, artworks_collection: Collection, status_collection: Collection, neo4j: GraphStore):
        self.artworks = artworks_collection
        self.status   = status_collection
        self.neo4j    = neo4j

    def _fetch_bundle(self, artwork_wid: str) -> dict:
        artwork_data = fetch_artwork_data(artwork_wid)
        for creator in artwork_data["creators"]:
            if not self.neo4j.cache.is_enriched(creator["id"]):
                artist_data = fetch_artist_data(creator["id"])
                creator.update(artist_data)
        return artwork_data

    def run(self, batch_size: int = 50) -> int:
        pending = list(self.status.find({"status": STATUS_PENDING}).limit(batch_size))
        if not pending:
            return 0

        object_ids = [doc["objectId"] for doc in pending]
        artworks_docs = {doc["objectId"]: doc for doc in self.artworks.find({"objectId": {"$in": object_ids}})}

        artist_wids = [extract_wikidata_id(d.get("artistWikidataUrl", "")) for d in artworks_docs.values()]
        self.neo4j.cache.prefetch([w for w in artist_wids if w])

        enriched_payloads, error_ids, no_wiki_ids = [], [], []

        logger.info(f"Enriching batch of {len(pending)} artworks in PARALLEL...")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for obj_id in object_ids:
                doc = artworks_docs.get(obj_id)
                wid = extract_wikidata_id(doc.get("objectWikidataUrl", "")) if doc else None
                
                if wid: futures[executor.submit(self._fetch_bundle, wid)] = (doc, wid)
                else: no_wiki_ids.append(obj_id)

            for future in as_completed(futures):
                doc, wid = futures[future]
                try:
                    wd_data = future.result()
                    if wd_data: enriched_payloads.append({"mongo": doc, "wiki": wd_data, "wid": wid})
                except Exception as e:
                    logger.error(f"Error objectId={doc['objectId']}: {e}")
                    error_ids.append(doc["objectId"])

        if enriched_payloads:
            try:
                self.neo4j.upsert_batch(enriched_payloads)
                success_ids = [item["mongo"]["objectId"] for item in enriched_payloads]
                self._set_status_batch(success_ids, STATUS_ENRICHED)
                logger.info(f"Batch complete: {len(success_ids)} enriched into Neo4j.")
            except Exception as e:
                logger.error(f"Neo4j Mass Insert Error: {e}")
                error_ids.extend([item["mongo"]["objectId"] for item in enriched_payloads])

        if error_ids: self._set_status_batch(error_ids, STATUS_ERROR)
        if no_wiki_ids: self._set_status_batch(no_wiki_ids, STATUS_NO_WIKIDATA)

        return len(enriched_payloads)

    def _set_status_batch(self, object_ids: list, new_status: str) -> None:
        if object_ids:
            self.status.update_many({"objectId": {"$in": object_ids}}, {"$set": {"status": new_status}})