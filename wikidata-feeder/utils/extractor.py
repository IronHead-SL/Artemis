import logging
from utils.queries_constants import *

logger = logging.getLogger(__name__)

def extract_wikidata_id(url: str) -> str | None:
    if not url:
        return None
    return url.rstrip("/").split("/")[-1]