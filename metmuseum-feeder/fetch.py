import requests
import time
from mongo_client_constants import BASE_URL


def fetch_artwork(object_id):
    time.sleep(0.5)
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