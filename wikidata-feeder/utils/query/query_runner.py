import time
import logging
from urllib.error import URLError, HTTPError
from utils.query.queries_constants import *
from utils.builder import _build_sparql

logger = logging.getLogger(__name__)


def _run_query(query: str) -> list[dict]:
    """
    Execute a SPARQL query against Wikidata and return bindings.
    Retries up to MAX_RETRIES times on transient errors (rate-limit, network).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sparql = _build_sparql()
            sparql.setQuery(query)
            time.sleep(REQUEST_DELAY)
            results = sparql.query().convert()
            return results["results"]["bindings"]

        except HTTPError as e:
            # 429 = rate limited; 503 = Wikidata overloaded
            if e.code in (429, 503):
                wait = REQUEST_DELAY * (2 ** attempt)
                logger.warning(
                    f"Wikidata HTTP {e.code} — backing off {wait:.1f}s "
                    f"(attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(wait)
            else:
                logger.error(f"Wikidata HTTP error {e.code}: {e}")
                return []

        except URLError as e:
            wait = REQUEST_DELAY * (2 ** attempt)
            logger.warning(
                f"Network error querying Wikidata: {e} — "
                f"retrying in {wait:.1f}s (attempt {attempt}/{MAX_RETRIES})"
            )
            time.sleep(wait)

        except Exception as e:
            logger.error(f"Unexpected SPARQL error: {e}")
            return []

    logger.error(f"Wikidata query failed after {MAX_RETRIES} attempts.")
    return []