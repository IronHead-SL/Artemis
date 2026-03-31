from mongo_client_constants import BASE_URL,OBJECT_IDS_JSON, artworks_collection, status_collection, procesados_collection
import os
import requests
import json

def get_all_object_ids():
    if os.path.exists(OBJECT_IDS_JSON):
        with open(OBJECT_IDS_JSON, 'r') as f:
            data = json.load(f)
            print(f"IDs cargados desde {OBJECT_IDS_JSON}")
            return data["objectIDs"]
    
    print(f"{OBJECT_IDS_JSON} no encontrado. Descargando desde la API...")
    response = requests.get(f"{BASE_URL}/objects")
    response.raise_for_status()
    data = response.json()

    with open(OBJECT_IDS_JSON, 'w') as f:
        json.dump(data, f)
    
    print(f"Encontradas {data['total']} obras posibles.")
    return data["objectIDs"]

def setup_database():
    artworks_collection.create_index("objectId", unique=True)
    status_collection.create_index([("status", 1), ("objectId", 1)])

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
