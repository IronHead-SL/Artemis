import time
import requests
import logging
from .queries import SPARQL_ENDPOINT, USER_AGENT, REQUEST_DELAY, MAX_RETRIES

logger = logging.getLogger(__name__)

def execute_sparql_query(query: str) -> list[dict]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/sparql-results+json"
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                SPARQL_ENDPOINT, 
                params={"query": query, "format": "json"}, 
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()["results"]["bindings"]

            if response.status_code in (429, 503):
                wait = REQUEST_DELAY * (2 ** attempt)
                time.sleep(wait)
                continue
            
            logger.error(f"Wikidata HTTP error {response.status_code}")
            return []

        except requests.exceptions.RequestException as e:
            wait = REQUEST_DELAY * (2 ** attempt)
            time.sleep(wait)
            
    return []