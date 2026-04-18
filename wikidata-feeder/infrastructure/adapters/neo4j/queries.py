BATCH_UPSERT_QUERY = """
UNWIND $batch AS row

// 1. Obra
MERGE (a:Artwork {wikidataId: row.wid})
SET a.objectId = row.objectId, a.title = row.title, a.department = row.department, a.medium = row.medium, a.objectDate = row.objectDate, a.objectUrl = row.objectUrl

// 2. Relaciones Obra (Con FOREACH no se corta si no hay datos)
FOREACH (genre IN row.genres | MERGE (g:Genre {label: genre.label}) MERGE (a)-[:HAS_GENRE]->(g))
FOREACH (movement IN row.movements | MERGE (m:Movement {label: movement.label}) MERGE (a)-[:PART_OF]->(m))
FOREACH (concept IN row.depicts | MERGE (c:Concept {wikidataId: concept.id}) SET c.label = concept.label MERGE (a)-[:DEPICTS]->(c))

// 3. Artistas y sus relaciones anidadas
FOREACH (creator IN row.creators | 
    MERGE (p:Artist {wikidataId: creator.id}) 
    SET p.name = creator.name, p.birthDate = creator.birthDate, p.deathDate = creator.deathDate, p.genderLabel = creator.genderLabel, p.occupationLabel = creator.occupationLabel 
    MERGE (a)-[:CREATED_BY]->(p)

    // Relaciones propias del artista
    FOREACH (country IN creator.nationalities | MERGE (ctry:Country {label: country}) MERGE (p)-[:NATIONALITY]->(ctry))
    FOREACH (amovement IN creator.movements | MERGE (am:Movement {label: amovement.label}) MERGE (p)-[:PART_OF]->(am))
    FOREACH (inst IN creator.institutions | MERGE (i:Institution {label: inst}) MERGE (p)-[:STUDIED_AT]->(i))
    FOREACH (influence IN creator.influenced_by | MERGE (inf_p:Artist {wikidataId: influence.id}) ON CREATE SET inf_p.name = influence.label MERGE (p)-[:INFLUENCED_BY]->(inf_p))
)
"""