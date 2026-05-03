from domain.wikidata_id import extract_wikidata_id
from .queries import ARTIST_QUERY, ARTWORK_QUERY
from .query_runner import execute_sparql_query

_artist_cache: dict[str, dict] = {}
_artwork_cache: dict[str, dict] = {}

def fetch_artist_data(wikidata_id: str) -> dict:
    if wikidata_id in _artist_cache:
        return _artist_cache[wikidata_id]
    
    rows = execute_sparql_query(ARTIST_QUERY.format(wid=wikidata_id))
    
    result = {
        "name": None, "birthDate": None, "deathDate": None, "genderLabel": None,
        "occupationLabel": None, "nationalities": [], "movements": [],
        "influenced_by": [], "institutions": []
    }
    seen_nat, seen_mov, seen_inf, seen_inst = set(), set(), set(), set()

    for row in rows:
        if not result["name"]: result["name"] = row.get("name", {}).get("value")
        if not result["birthDate"] and "birthDate" in row: result["birthDate"] = row["birthDate"]["value"][:10]
        if not result["deathDate"] and "deathDate" in row: result["deathDate"] = row["deathDate"]["value"][:10]
        if not result["genderLabel"] and "genderLabel" in row: result["genderLabel"] = row["genderLabel"]["value"]
        if not result["occupationLabel"] and "occupationLabel" in row: result["occupationLabel"] = row["occupationLabel"]["value"]

        if "nationalityLabel" in row:
            label = row["nationalityLabel"]["value"]
            if label not in seen_nat: seen_nat.add(label); result["nationalities"].append(label)

        if "movement" in row:
            mlabel = row.get("movementLabel", {}).get("value", "")
            if mlabel and mlabel not in seen_mov: seen_mov.add(mlabel); result["movements"].append({"label": mlabel})

        if "influencedBy" in row:
            iid = extract_wikidata_id(row["influencedBy"]["value"])
            ilabel = row.get("influencedByLabel", {}).get("value", "")
            if iid and iid not in seen_inf: seen_inf.add(iid); result["influenced_by"].append({"id": iid, "label": ilabel})

        if "studiedAt" in row:
            label = row.get("studiedAtLabel", {}).get("value", "")
            if label and label not in seen_inst: seen_inst.add(label); result["institutions"].append(label)

    _artist_cache[wikidata_id] = result
    return result

def fetch_artwork_data(wikidata_id: str) -> dict:
    if wikidata_id in _artwork_cache:
        return _artwork_cache[wikidata_id]
    
    rows = execute_sparql_query(ARTWORK_QUERY.format(wid=wikidata_id))
    
    result = {
        "genres": [], "movements": [], "depicts": [], 
        "creators": [], "inception": None
    }
    seen_gen, seen_mov, seen_dep, seen_cre = set(), set(), set(), set()

    for row in rows:
        if "genreLabel" in row:
            label = row["genreLabel"]["value"]
            if label not in seen_gen:
                seen_gen.add(label)
                result["genres"].append({"label": label})

        if "movementLabel" in row:
            label = row["movementLabel"]["value"]
            if label not in seen_mov:
                seen_mov.add(label)
                result["movements"].append({"label": label})

        if "creator" in row:
            cid = extract_wikidata_id(row["creator"]["value"])
            if cid and cid not in seen_cre:
                seen_cre.add(cid)
                result["creators"].append({
                    "id": cid,
                    "name": row.get("creatorLabel", {}).get("value"),
                    "birthDate": row.get("birthDate", {}).get("value", "")[:10],
                    "deathDate": row.get("deathDate", {}).get("value", "")[:10],
                    "genderLabel": row.get("genderLabel", {}).get("value"),
                    "occupationLabel": row.get("occLabel", {}).get("value"),
                    "nationalities": [],
                    "movements": [],
                    "institutions": [],
                    "influenced_by": []
                })

        if "inception" in row and result["inception"] is None:
            result["inception"] = row["inception"]["value"][:10]

    _artwork_cache[wikidata_id] = result
    return result