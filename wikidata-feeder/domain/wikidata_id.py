import logging

logger = logging.getLogger(__name__)

def extract_wikidata_id(url: str) -> str | None:
    if not url:
        return None
    qid = url.rstrip("/").split("/")[-1]
    if qid.startswith("Q") and qid[1:].isdigit():
        return qid
    return None