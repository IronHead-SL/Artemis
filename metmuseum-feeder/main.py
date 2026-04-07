from met_adapter import MetMuseumAdapter
from repository import ArtworkRepository
from artwork import ArtworkBuilder
from config import Config

def main():
    repo = ArtworkRepository()
    api = MetMuseumAdapter()
    builder = ArtworkBuilder()
    repo.init_indexes()

    all_ids = api.get_available_ids()
    last_id = repo.get_last_processed_id()
    
    pending_ids = sorted([oid for oid in all_ids if oid > last_id])
    print(f"Procesando desde {last_id}. Pendientes: {len(pending_ids)}")

    batch_artworks = []
    batch_status = []

    for i, oid in enumerate(pending_ids):
        raw = api.fetch_artwork_data(oid)
        
        if raw:
            obra = (builder
                    .set_basic_info(raw["objectID"], raw.get("title"), raw["primaryImage"])
                    .set_metadata(raw.get("department"), raw.get("medium"), raw.get("objectDate"))
                    .set_artist_info(raw.get("artistDisplayName"), 
                                     raw.get("artistWikidata_URL"), 
                                     raw.get("objectWikidata_URL"))
                    .set_constituents(raw.get("constituents"))
                    .build())

            batch_artworks.append(obra.to_dict())
            batch_status.append({"objectId": oid, "status": "PENDING_WIKIPEDIA"})
            print(f"[+] {oid} ok")

        if (i + 1) % Config.BATCH_SIZE == 0:
            repo.persist_batch(batch_artworks, batch_status)
            repo.update_tracker(oid)
            print(f"Batch guardado en ID: {oid}")
            batch_artworks, batch_status = [], []

    if batch_artworks:
        repo.persist_batch(batch_artworks, batch_status)
        repo.update_tracker(pending_ids[-1])

    print("Proceso finalizado con éxito.")

if __name__ == "__main__":
    main()