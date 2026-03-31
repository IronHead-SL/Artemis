from queries_constants import REQUEST_DELAY
import time
import logging
from utils.queries_constants import *
from builder import _build_sparql


logger = logging.getLogger(__name__)

def _run_query(query: str) -> list[dict]:
    """Execute a SPARQL query and return the rows as list of dicts."""
    sparql = _build_sparql()
    sparql.setQuery(query)
    time.sleep(REQUEST_DELAY)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        logger.error(f"SPARQL query failed: {e}")
        return []