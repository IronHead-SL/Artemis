from config import Config

class ArtworkCollector:
    def __init__(self, provider, store, builder):
        self.provider = provider
        self.store = store
        self.builder = builder

    def run(self, batch_size: int = Config.BATCH_SIZE):
        all_ids = self.provider.get_available_ids()
        last_id = self.store.get_last_processed_id()
        
        pending_ids = sorted([oid for oid in all_ids if oid > last_id])
        print(f"Starting from ID {last_id}. Pending artworks: {len(pending_ids)}")

        batch_artworks = []
        batch_status = []

        for i, oid in enumerate(pending_ids):
            raw = self.provider.fetch_artwork_data(oid)
            
            if raw:
                obra = (self.builder
                        .set_basic_info(raw["objectID"], raw.get("title"), raw.get("primaryImage"))
                        .set_metadata(raw.get("department"), raw.get("medium"), raw.get("objectDate"))
                        .set_artist_info(raw.get("artistDisplayName"), 
                                         raw.get("artistWikidata_URL"), 
                                         raw.get("objectWikidata_URL"))
                        .set_constituents(raw.get("constituents"))
                        .build())

                batch_artworks.append(obra.to_dict())
                batch_status.append({"objectId": oid, "status": "PENDING_WIKIPEDIA"})
                print(f"[+] {oid} ok")

            if (i + 1) % batch_size == 0:
                self._save(batch_artworks, batch_status, oid)
                batch_artworks, batch_status = [], []

        if batch_artworks:
            self._save(batch_artworks, batch_status, pending_ids[-1])

    def _save(self, artworks, status_list, last_id):
        self.store.persist_batch(artworks, status_list)
        self.store.update_tracker(last_id)
        print(f"Batch guardado en ID: {last_id}")