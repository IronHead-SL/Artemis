import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from domain.wikidata_id import extract_wikidata_id

logger = logging.getLogger(__name__)

STATUS_PENDING     = "PENDING_WIKIPEDIA"
STATUS_ENRICHED    = "PENDING_IA"
STATUS_NO_WIKIDATA = "NO_WIKIDATA"
STATUS_ERROR       = "ENRICHMENT_ERROR"

class Enricher:
    def __init__(self, repository, graph_store, wikidata_adapter, wikipedia_adapter):
        self.repo = repository
        self.neo4j = graph_store
        self.wiki = wikidata_adapter
        self.wikipedia = wikipedia_adapter

    def _fetch_bundle(self, artwork_wid: str, title: str) -> dict:
        artwork_data = self.wiki.fetch_artwork_data(artwork_wid)
        for creator in artwork_data["creators"]:
            if not self.neo4j.is_artist_enriched(creator["id"]):
                artist_data = self.wiki.fetch_artist_data(creator["id"])
                creator.update(artist_data)

        extract = self.wikipedia.fetch_extract(title)
        
        return {"wikidata": artwork_data, "extract": extract}

    def run(self, batch_size: int = 50) -> int:
        batch = self.repo.get_pending_batch(STATUS_PENDING, batch_size)
        if not batch: return 0

        # Prefetch de artistas para optimizar Neo4j
        artist_wids = [extract_wikidata_id(doc.get("artistWikidataUrl", "")) for doc in batch]
        self.neo4j.prefetch_artists([w for w in artist_wids if w])

        enriched_payloads, error_ids, no_wiki_ids = [], [], []

        logger.info(f"Enriching batch of {len(batch)} artworks in PARALLEL...")

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for doc in batch:
                wid = extract_wikidata_id(doc.get("objectWikidataUrl", ""))
                title = doc.get("title", "")
                if wid: 
                    futures[executor.submit(self._fetch_bundle, wid, title)] = (doc, wid)
                else: 
                    no_wiki_ids.append(doc["objectId"])

            for future in as_completed(futures):
                doc, wid = futures[future]
                try:
                    bundle = future.result()
                    if bundle:
                        enriched_payloads.append({
                            "mongo_id": doc["objectId"],
                            "mongo": doc,
                            "wiki": bundle["wikidata"],
                            "extract": bundle["extract"],
                            "wid": wid
                        })
                except Exception as e:
                    logger.error(f"Error objectId={doc['objectId']}: {e}")
                    error_ids.append(doc["objectId"])

        if enriched_payloads:
            try:
                self.neo4j.upsert_batch(enriched_payloads)
                
                self.repo.save_enriched_batch(enriched_payloads, STATUS_ENRICHED)
                
                logger.info(f"Batch complete: {len(enriched_payloads)} enriched.")
            except Exception as e:
                logger.error(f"Persistence Error: {e}")
                error_ids.extend([item["mongo_id"] for item in enriched_payloads])

        if error_ids: self.repo.update_status_batch(error_ids, STATUS_ERROR)
        if no_wiki_ids: self.repo.update_status_batch(no_wiki_ids, STATUS_NO_WIKIDATA)

        return len(enriched_payloads)