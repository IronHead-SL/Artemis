import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from domain.wikidata_id import extract_wikidata_id

logger = logging.getLogger(__name__)

STATUS_PENDING     = "PENDING_WIKIPEDIA"
STATUS_ENRICHED    = "PENDING_IA"
STATUS_NO_WIKIDATA = "NO_WIKIDATA"
STATUS_ERROR       = "ENRICHMENT_ERROR"

class Enricher:
    def __init__(self, repository, graph_store, wikidata_adapter):
        self.repo = repository
        self.neo4j = graph_store
        self.wiki = wikidata_adapter

    def _fetch_bundle(self, artwork_wid: str) -> dict:
        artwork_data = self.wiki.fetch_artwork_data(artwork_wid)
        for creator in artwork_data["creators"]:
            if not self.neo4j.is_artist_enriched(creator["id"]):
                artist_data = self.wiki.fetch_artist_data(creator["id"])
                creator.update(artist_data)
        return artwork_data

    def run(self, batch_size: int = 50) -> int:
        batch = self.repo.get_pending_batch(STATUS_PENDING, batch_size)
        if not batch:
            return 0

        artist_wids = [extract_wikidata_id(doc.get("artistWikidataUrl", "")) for doc in batch]
        self.neo4j.prefetch_artists([w for w in artist_wids if w])

        enriched_payloads, error_ids, no_wiki_ids = [], [], []

        logger.info(f"Enriching batch of {len(batch)} artworks in PARALLEL...")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for doc in batch:
                wid = extract_wikidata_id(doc.get("objectWikidataUrl", ""))
                if wid: 
                    futures[executor.submit(self._fetch_bundle, wid)] = (doc, wid)
                else: 
                    no_wiki_ids.append(doc["objectId"])

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
                # 4. ACTUALIZACIÓN A TRAVÉS DEL REPOSITORIO
                self.repo.update_status_batch(success_ids, STATUS_ENRICHED)
                logger.info(f"Batch complete: {len(success_ids)} enriched into Neo4j.")
            except Exception as e:
                logger.error(f"Neo4j Mass Insert Error: {e}")
                error_ids.extend([item["mongo"]["objectId"] for item in enriched_payloads])

        if error_ids: self.repo.update_status_batch(error_ids, STATUS_ERROR)
        if no_wiki_ids: self.repo.update_status_batch(no_wiki_ids, STATUS_NO_WIKIDATA)

        return len(enriched_payloads)