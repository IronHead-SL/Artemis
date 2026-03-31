from artwork import Artwork
from mongo_client_constants import BATCH_SIZE, status_collection, artworks_collection
from fetch import fetch_artwork
from database_processing import (
    setup_database,
    get_last_processed_id,
    update_last_processed_id,
    get_all_object_ids
)


def main():
    setup_database()
    all_ids = get_all_object_ids()

    print("Checking progress...")
    last_id = get_last_processed_id()

    ids_pendientes = [oid for oid in all_ids if oid > last_id]
    ids_pendientes.sort()

    total = len(ids_pendientes)
    print(f"Last processed ID: {last_id}")
    print(f"Remaining: {total}")

    if total == 0:
        print("All processed.")
        return

    batch_artworks = []
    batch_status = []
    guardados_hoy = 0

    for i, object_id in enumerate(ids_pendientes):

        raw_data = fetch_artwork(object_id)

        if raw_data:
            obra = Artwork(
                object_id=raw_data["objectID"],
                title=raw_data.get("title", "Unknown"),
                constituents=raw_data.get("constituents"),
                image_url=raw_data["primaryImage"],
                department=raw_data.get("department", ""),
                medium=raw_data.get("medium", ""),
                artist_display_name=raw_data.get("artistDisplayName", ""),
                object_wikidata_url=raw_data.get("objectWikidata_URL", ""),
                artist_wikidata_url=raw_data.get("artistWikidata_URL", ""),
                object_date=raw_data.get("objectDate", ""),
            )

            batch_artworks.append(obra.to_dict())
            batch_status.append({"objectId": object_id, "status": "PENDING_WIKIPEDIA"})
            guardados_hoy += 1

            print(f"[+] ({i+1}/{total}) Artwork {object_id} saved")
        else:
            print(f"[-] ({i+1}/{total}) Artwork {object_id} has no image")

        if (i + 1) % BATCH_SIZE == 0:

            if batch_artworks:
                artworks_collection.insert_many(batch_artworks, ordered=False)
                status_collection.insert_many(batch_status, ordered=False)

            update_last_processed_id(object_id)

            print(f">>> Progress saved. Artworks with image today: {guardados_hoy}")

            batch_artworks = []
            batch_status = []

    if batch_artworks:
        artworks_collection.insert_many(batch_artworks, ordered=False)
        status_collection.insert_many(batch_status, ordered=False)

    update_last_processed_id(ids_pendientes[-1])

    print(">>> Process completed")


if __name__ == "__main__":
    main()