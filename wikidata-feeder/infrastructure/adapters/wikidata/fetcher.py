from domain.wikidata_id import extract_wikidata_id
from .queries import ARTIST_QUERY, ARTWORK_QUERY
from .query_runner import execute_sparql_query

def fetch_artist_data(wikidata_id: str) -> dict:
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

    return result

def fetch_artwork_data(wikidata_id: str) -> dict:
    rows = execute_sparql_query(ARTWORK_QUERY.format(wid=wikidata_id))
    
    result = {"genres": [], "movements": [], "depicts": [], "creators": [], "inception": None}
    seen_gen, seen_mov, seen_dep, seen_cre = set(), set(), set(), set()

    for row in rows:
        if "genre" in row:
            gid = extract_wikidata_id(row["genre"]["value"])
            glabel = row.get("genreLabel", {}).get("value", "")
            if gid and glabel and glabel not in seen_gen: seen_gen.add(glabel); result["genres"].append({"id": gid, "label": glabel})

        if "movement" in row:
            mlabel = row.get("movementLabel", {}).get("value", "")
            if mlabel and mlabel not in seen_mov: seen_mov.add(mlabel); result["movements"].append({"label": mlabel})

        if "depicts" in row:
            did = extract_wikidata_id(row["depicts"]["value"])
            dlabel = row.get("depictsLabel", {}).get("value", "")
            if did and dlabel and did not in seen_dep: seen_dep.add(did); result["depicts"].append({"id": did, "label": dlabel})

        if "creator" in row:
            cid = extract_wikidata_id(row["creator"]["value"])
            clabel = row.get("creatorLabel", {}).get("value", "")
            if cid and cid not in seen_cre: seen_cre.add(cid); result["creators"].append({"id": cid, "label": clabel})

        if "inception" in row and result["inception"] is None:
            result["inception"] = row["inception"]["value"][:10]

    return result