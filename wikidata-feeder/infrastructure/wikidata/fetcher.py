import time
import logging
from urllib.error import URLError, HTTPError

from SPARQLWrapper import SPARQLWrapper, JSON

from infrastructure.wikidata.queries import (
    SPARQL_ENDPOINT, USER_AGENT,
    REQUEST_DELAY, MAX_RETRIES,
    ARTIST_QUERY, ARTWORK_QUERY,
)
from domain.wikidata_id import extract_wikidata_id

logger = logging.getLogger(__name__)


def _build_sparql() -> SPARQLWrapper:
    sparql = SPARQLWrapper(SPARQL_ENDPOINT, agent=USER_AGENT)
    sparql.setReturnFormat(JSON)
    return sparql


def _run_query(query: str) -> list[dict]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            sparql = _build_sparql()
            sparql.setQuery(query)
            time.sleep(REQUEST_DELAY)
            results = sparql.query().convert()
            return results["results"]["bindings"]

        except HTTPError as e:
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

def fetch_artist_data(wikidata_id: str) -> dict:
    """
    Query Wikidata for contextual information about an artist.

    Returns a dict with keys:
        name              : str | None
        birthDate         : str | None   (YYYY-MM-DD)
        deathDate         : str | None   (YYYY-MM-DD)
        genderLabel       : str | None
        occupationLabel   : str | None
        nationalities     : list[str]
        movements         : list[{'label': str}]
        influenced_by     : list[{'id': str, 'label': str}]
        institutions      : list[str]
    """
    query = ARTIST_QUERY.format(wid=wikidata_id)
    rows  = _run_query(query)

    result: dict = {
        "name":            None,
        "birthDate":       None,
        "deathDate":       None,
        "genderLabel":     None,
        "occupationLabel": None,
        "nationalities":   [],
        "movements":       [],
        "influenced_by":   [],
        "institutions":    [],
    }

    seen_nationalities: set = set()
    seen_movements:     set = set()
    seen_influenced:    set = set()
    seen_institutions:  set = set()

    for row in rows:
        if result["name"] is None:
            result["name"] = row.get("name", {}).get("value")

        if result["birthDate"] is None and "birthDate" in row:
            result["birthDate"] = row["birthDate"]["value"][:10]

        if result["deathDate"] is None and "deathDate" in row:
            result["deathDate"] = row["deathDate"]["value"][:10]

        if result["genderLabel"] is None and "genderLabel" in row:
            result["genderLabel"] = row["genderLabel"]["value"]

        if result["occupationLabel"] is None and "occupationLabel" in row:
            result["occupationLabel"] = row["occupationLabel"]["value"]

        if "nationalityLabel" in row:
            label = row["nationalityLabel"]["value"]
            if label and label not in seen_nationalities:
                seen_nationalities.add(label)
                result["nationalities"].append(label)

        if "movement" in row:
            mlabel = row.get("movementLabel", {}).get("value", "")
            if mlabel and mlabel not in seen_movements:
                seen_movements.add(mlabel)
                result["movements"].append({"label": mlabel})

        if "influencedBy" in row:
            iid    = extract_wikidata_id(row["influencedBy"]["value"])
            ilabel = row.get("influencedByLabel", {}).get("value", "")
            if iid and iid not in seen_influenced:
                seen_influenced.add(iid)
                result["influenced_by"].append({"id": iid, "label": ilabel})

        if "studiedAt" in row:
            label = row.get("studiedAtLabel", {}).get("value", "")
            if label and label not in seen_institutions:
                seen_institutions.add(label)
                result["institutions"].append(label)

    return result

def fetch_artwork_data(wikidata_id: str) -> dict:
    """
    Query Wikidata for contextual information about an artwork.

    Returns a dict with keys:
        genres      : list[{'id': str, 'label': str}]
        movements   : list[{'label': str}]
        depicts     : list[{'id': str, 'label': str}]
        creators    : list[{'id': str, 'label': str}]
        inception   : str | None   (YYYY-MM-DD)
    """
    query = ARTWORK_QUERY.format(wid=wikidata_id)
    rows  = _run_query(query)

    result: dict = {
        "genres":    [],
        "movements": [],
        "depicts":   [],
        "creators":  [],
        "inception": None,
    }

    seen_genres:     set = set()
    seen_movements:  set = set()
    seen_depicts:    set = set()
    seen_creators:   set = set()

    for row in rows:
        if "genre" in row:
            gid    = extract_wikidata_id(row["genre"]["value"])
            glabel = row.get("genreLabel", {}).get("value", "")
            if gid and glabel and glabel not in seen_genres:
                seen_genres.add(glabel)
                result["genres"].append({"id": gid, "label": glabel})

        if "movement" in row:
            mlabel = row.get("movementLabel", {}).get("value", "")
            if mlabel and mlabel not in seen_movements:
                seen_movements.add(mlabel)
                result["movements"].append({"label": mlabel})

        if "depicts" in row:
            did    = extract_wikidata_id(row["depicts"]["value"])
            dlabel = row.get("depictsLabel", {}).get("value", "")
            if did and dlabel and did not in seen_depicts:
                seen_depicts.add(did)
                result["depicts"].append({"id": did, "label": dlabel})

        if "creator" in row:
            cid    = extract_wikidata_id(row["creator"]["value"])
            clabel = row.get("creatorLabel", {}).get("value", "")
            if cid and cid not in seen_creators:
                seen_creators.add(cid)
                result["creators"].append({"id": cid, "label": clabel})

        if "inception" in row and result["inception"] is None:
            result["inception"] = row["inception"]["value"][:10]

    return result