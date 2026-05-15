from __future__ import annotations


def neo4j_metadata(session, id_str: str) -> dict:
    r1 = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id LIMIT 1
        OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
        OPTIONAL MATCH (artist)-[:NATIONALITY]->(country:Country)
        OPTIONAL MATCH (artist)-[:STUDIED_AT]->(inst:Institution)
        RETURN
            coalesce(toString(artist.name), toString(artist.label), '') AS artist_name,
            collect(DISTINCT coalesce(toString(country.label), toString(country.name))) AS countries,
            collect(DISTINCT coalesce(toString(inst.label), toString(inst.name))) AS institutions
    """, id=id_str).single()

    r2 = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id LIMIT 1
        OPTIONAL MATCH (a)-[:PART_OF]->(mov:Movement)
        OPTIONAL MATCH (a)-[:HAS_GENRE]->(genre:Genre)
        OPTIONAL MATCH (a)-[:USES_TECHNIQUE]->(tech:Technique)
        OPTIONAL MATCH (a)-[:BELONGS_TO]->(dept:Department)
        RETURN
            collect(DISTINCT coalesce(toString(mov.label), toString(mov.name))) AS movements,
            collect(DISTINCT coalesce(toString(genre.label), toString(genre.name))) AS genres,
            collect(DISTINCT coalesce(toString(tech.label), toString(tech.name))) AS techniques,
            collect(DISTINCT coalesce(toString(dept.label), toString(dept.name))) AS departments
    """, id=id_str).single()

    r3 = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id LIMIT 1
        OPTIONAL MATCH (a)-[:CREATED_BY]->(artist:Artist)
        OPTIONAL MATCH (a)-[:INFLUENCED_BY]->(infl1:Artist)
        OPTIONAL MATCH (artist)-[:INFLUENCED_BY]->(infl2:Artist)
        WITH
            collect(DISTINCT coalesce(toString(infl1.name), toString(infl1.label))) AS i1,
            collect(DISTINCT coalesce(toString(infl2.name), toString(infl2.label))) AS i2
        RETURN [x IN (i1 + i2) WHERE x IS NOT NULL AND x <> ''] AS influences
    """, id=id_str).single()

    return {
        "artist_name":  (r1["artist_name"] if r1 else ""),
        "countries":    [x for x in (r1["countries"]    if r1 else []) if x],
        "institutions": [x for x in (r1["institutions"] if r1 else []) if x],
        "movements":    [x for x in (r2["movements"]    if r2 else []) if x],
        "genres":       [x for x in (r2["genres"]       if r2 else []) if x],
        "techniques":   [x for x in (r2["techniques"]   if r2 else []) if x],
        "departments":  [x for x in (r2["departments"]  if r2 else []) if x],
        "influences":   [x for x in (r3["influences"]   if r3 else []) if x],
    }


def neo4j_related(session, id_str: str) -> list[tuple[int, str]]:
    result = session.run("""
        MATCH (a:Artwork) WHERE toString(a.objectId) = $id
        CALL {
            WITH a
            MATCH (a)-[:CREATED_BY]->(artist:Artist)<-[:CREATED_BY]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Artist' AS rel_type, 3 AS priority LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:PART_OF]->(mov:Movement)<-[:PART_OF]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Movement' AS rel_type, 2 AS priority LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:HAS_GENRE]->(genre:Genre)<-[:HAS_GENRE]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Genre' AS rel_type, 4 AS priority LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:USES_TECHNIQUE]->(t:Technique)<-[:USES_TECHNIQUE]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Technique' AS rel_type, 1 AS priority LIMIT 4
        UNION ALL
            WITH a
            MATCH (a)-[:BELONGS_TO]->(d:Department)<-[:BELONGS_TO]-(r:Artwork)
            WHERE r <> a AND r.objectId IS NOT NULL
            RETURN r.objectId AS oid, 'Same Department' AS rel_type, 0 AS priority LIMIT 3
        }
        RETURN DISTINCT toString(oid) AS oid, rel_type, priority
        ORDER BY priority DESC LIMIT 15
    """, id=id_str)

    seen, related = set(), []
    for row in result:
        try:
            oid = int(row["oid"])
        except (ValueError, TypeError):
            continue
        if oid not in seen:
            seen.add(oid)
            related.append((oid, row["rel_type"]))
    return related
