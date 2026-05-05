import time
import requests
import logging
from .queries import SPARQL_ENDPOINT, USER_AGENT, REQUEST_DELAY, MAX_RETRIES

logger = logging.getLogger(__name__)

_session = requests.Session()
_session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "application/sparql-results+json"
})

def execute_sparql_query(query: str) -> list[dict]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = _session.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"}, timeout=30)
            
            if response.status_code == 429:
                wait = 5 * attempt
                logger.warning(f"Wikidata 429. Waiting {wait}s...")
                time.sleep(wait)
                continue
            
            if response.status_code == 200:
                time.sleep(REQUEST_DELAY)
                return response.json()["results"]["bindings"]
            
            logger.error(f"Wikidata error {response.status_code}")
            return []
            
        except requests.RequestException as e:
            logger.error(f"Wikidata exception: {e}")
            time.sleep(2 * attempt)
    
    return []