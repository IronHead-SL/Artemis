import os
import requests
from dotenv import load_dotenv

load_dotenv()

USER_AGENT = f"ArtemisProject/1.0 ({os.getenv('WIKIDATA_EMAIL')})"

def fetch_extract(title: str) -> str | None:
    if not title:
        return None
    
    safe_title = title.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
    
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("extract")
            
        return None
    except Exception as e:
        print(f"Error en Wikipedia para '{title}': {e}")
        return None