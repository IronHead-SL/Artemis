import time
import logging
from urllib.error import URLError, HTTPError
from SPARQLWrapper import SPARQLWrapper, JSON
from .queries import SPARQL_ENDPOINT, USER_AGENT, REQUEST_DELAY, MAX_RETRIES

logger = logging.getLogger(__name__)

def execute_sparql_query(query: str) -> list[dict]:
    sparql = SPARQLWrapper(SPARQL_ENDPOINT, agent=USER_AGENT)
    sparql.setReturnFormat(JSON)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sparql.setQuery(query)
            time.sleep(REQUEST_DELAY)
            return sparql.query().convert()["results"]["bindings"]
            
        except HTTPError as e:
            if e.code in (429, 503):
                time.sleep(REQUEST_DELAY * (2 ** attempt))
            else:
                logger.error(f"Wikidata HTTP error {e.code}: {e}")
                return []
        except URLError:
            time.sleep(REQUEST_DELAY * (2 ** attempt))
        except Exception as e:
            logger.error(f"Unexpected SPARQL error: {e}")
            return []

    logger.error(f"Wikidata query failed after {MAX_RETRIES} attempts.")
    return []