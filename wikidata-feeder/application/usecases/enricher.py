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
        for creator in artwork_data.get("creators", []):
            if not self.neo4j.is_artist_enriched(creator["id"]):
                artist_data = self.wiki.fetch_artist_data(creator["id"])
                creator.update(artist_data)

        extract = self.wikipedia.fetch_extract(title)
        
        return {"wikidata": artwork_data, "extract": extract}

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

        if not enriched_payloads:
            if error_ids:
                self.repo.update_status_batch(error_ids, STATUS_ERROR)
            if no_wiki_ids:
                self.repo.update_status_batch(no_wiki_ids, STATUS_NO_WIKIDATA)
            return 0

        neo4j_success_ids = []
        neo4j_failed_ids = []
        
        neo4j_batch_size = 10
        for i in range(0, len(enriched_payloads), neo4j_batch_size):
            micro_batch = enriched_payloads[i:i + neo4j_batch_size]
            try:
                self.neo4j.upsert_batch(micro_batch)
                neo4j_success_ids.extend([item["mongo_id"] for item in micro_batch])
            except Exception as e:
                logger.error(f"Neo4j micro-batch failed: {e}")
                neo4j_failed_ids.extend([item["mongo_id"] for item in micro_batch])

        if not neo4j_success_ids:
            error_ids.extend(neo4j_failed_ids)
            self.repo.update_status_batch(error_ids, STATUS_ERROR)
            return 0

        try:
            success_payloads = [p for p in enriched_payloads if p["mongo_id"] in neo4j_success_ids]
            self.repo.save_enriched_batch(success_payloads, STATUS_ENRICHED)
            logger.info(f"Batch complete: {len(success_payloads)} enriched.")
        except Exception as e:
            logger.error(f"MongoDB write failed! Rolling back Neo4j... Error: {e}")
            self.neo4j.delete_artworks(neo4j_success_ids)
            error_ids.extend(neo4j_success_ids)
            self.repo.update_status_batch(error_ids, STATUS_ERROR)
            return 0

        if neo4j_failed_ids:
            error_ids.extend(neo4j_failed_ids)
        if error_ids:
            self.repo.update_status_batch(error_ids, STATUS_ERROR)
        if no_wiki_ids:
            self.repo.update_status_batch(no_wiki_ids, STATUS_NO_WIKIDATA)

        return len(neo4j_success_ids)