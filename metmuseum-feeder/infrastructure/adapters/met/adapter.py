import requests
import time
import json
import os
from config import Config
from infrastructure.ports.artwork_provider import ArtworkProvider

class MetMuseumAdapter(ArtworkProvider):
    def __init__(self):
        self.base_url = Config.BASE_URL

    def get_available_ids(self) -> list[int]:
        if os.path.exists(Config.OBJECT_IDS_JSON):
            with open(Config.OBJECT_IDS_JSON, 'r') as f:
                return json.load(f)["objectIDs"]
        
        response = requests.get(f"{self.base_url}/objects")
        response.raise_for_status()
        data = response.json()
        with open(Config.OBJECT_IDS_JSON, 'w') as f:
            json.dump(data, f)
        return data["objectIDs"]

    def fetch_artwork_data(self, object_id: int) -> dict | None:
        time.sleep(0.5) 
        try:
            response = requests.get(f"{self.base_url}/objects/{object_id}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data if data.get("primaryImage") else None
        except Exception as e:
            print(f"Error en API MET (ID {object_id}): {e}")
        return None