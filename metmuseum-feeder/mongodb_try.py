import requests
import time
from pymongo import MongoClient
from artwork import Artwork

BASE_URL = "https://collectionapi.metmuseum.org/public/collection/v1"
MONGO_URI = "mongodb://localhost:27017/"

client = MongoClient(MONGO_URI)
db = client["artemis_db"]
artworks_collection = db["artworks"]
procesados_collection = db["procesados"]


def get_all_object_ids():
    print("Obteniendo la lista de obras del museo...")
    response = requests.get(f"{BASE_URL}/objects")
    response.raise_for_status()
    data = response.json()
    print(f"Encontradas {data['total']} obras posibles.")
    return data["objectIDs"]


def fetch_artwork(object_id):
    time.sleep(1.2)
    try:
        response = requests.get(f"{BASE_URL}/objects/{object_id}", timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("primaryImage"):
            return None

        return data

    except Exception as e:
        print(f"Error en ID {object_id}: {e}")
        return None


def get_last_processed_id():
    tracker = procesados_collection.find_one({"_id": "tracker"})
    if tracker:
        return tracker["last_id"]
    return 0


def update_last_processed_id(last_id):
    procesados_collection.update_one(
        {"_id": "tracker"},
        {"$set": {"last_id": last_id}},
        upsert=True
    )


def main():
    all_ids = get_all_object_ids()

    print("Consultando progreso...")
    last_id = get_last_processed_id()

    ids_pendientes = [oid for oid in all_ids if oid > last_id]
    ids_pendientes.sort()

    total = len(ids_pendientes)
    print(f"Último ID procesado: {last_id}")
    print(f"Faltan {total} por revisar")

    if total == 0:
        print("Todo procesado.")
        return

    batch_artworks = []
    guardados_hoy = 0

    for i, object_id in enumerate(ids_pendientes):

        raw_data = fetch_artwork(object_id)

        if raw_data:
            obra = Artwork(
                object_id=raw_data["objectID"],
                title=raw_data.get("title", "Unknown"),
                constituents=raw_data.get("constituents"),
                image_url=raw_data["primaryImage"]
            )

            batch_artworks.append(obra.to_dict())
            guardados_hoy += 1

            print(f"[+] ({i+1}/{total}) Cuadro {object_id} guardado")
        else:
            print(f"[-] ({i+1}/{total}) Cuadro {object_id} sin imagen")

        if (i + 1) % 50 == 0:

            if batch_artworks:
                artworks_collection.insert_many(batch_artworks)

            update_last_processed_id(object_id)

            print(f">>> Progreso guardado. Obras con imagen hoy: {guardados_hoy}")

            batch_artworks = []

    if batch_artworks:
        artworks_collection.insert_many(batch_artworks)

    update_last_processed_id(ids_pendientes[-1])

    print(">>> Proceso terminado")


if __name__ == "__main__":
    main()