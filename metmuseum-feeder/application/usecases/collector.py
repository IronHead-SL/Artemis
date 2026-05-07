import logging
from config import Config

logger = logging.getLogger(__name__)

class ArtworkCollector:
    def __init__(self, provider, store, builder):
        self.provider = provider
        self.store = store
        self.builder = builder

    def run(self, batch_size: int = Config.BATCH_SIZE):
        all_ids = self.provider.get_available_ids()
        last_id = self.store.get_last_processed_id()

        pending_ids = sorted([oid for oid in all_ids if oid > last_id])
        logger.info(f"Starting from ID {last_id}. Pending: {len(pending_ids)}")

        batch_artworks = []
        batch_status = []
        last_processed_oid = last_id

        for i, oid in enumerate(pending_ids):
            try:
                raw = self.provider.fetch_artwork_data(oid)
            except Exception as e:
                logger.warning(f"Error fetching {oid}: {e}")
                continue

            if not raw:
                continue

            obra = (
                self.builder
                .set_basic_info(raw.get("objectID"), raw.get("title"), raw.get("primaryImage") or raw.get("primaryImageSmall", ""))
                .set_metadata(raw.get("department", ""), raw.get("medium", ""), raw.get("objectDate", ""))
                .set_artist_info(raw.get("artistDisplayName", ""), raw.get("artistWikidata_URL", ""), raw.get("objectWikidata_URL", ""))
                .set_constituents(raw.get("constituents"))
                .build()
            )

            if not obra.image_url:
                logger.debug(f"Skipping {oid} — no image")
                continue

            batch_artworks.append(obra.to_dict())
            batch_status.append({"objectId": oid, "status": "PENDING_WIKIPEDIA"})
            last_processed_oid = oid

            if (i + 1) % batch_size == 0:
                self._save(batch_artworks, batch_status, last_processed_oid)
                batch_artworks, batch_status = [], []

        if batch_artworks:
            self._save(batch_artworks, batch_status, last_processed_oid)


    def _save(self, artworks, status_list, last_id):
        try:
            self.store.persist_batch(artworks, status_list)
            self.store.update_tracker(last_id)
        except Exception as e:
            raise