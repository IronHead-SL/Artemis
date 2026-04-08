from neo4j import Session
 
 
def upsert_artwork(session: Session, artwork_data: dict) -> None:
    """
    Merge an Artwork node into Neo4j.
 
    artwork_data expected keys:
        wikidataId, objectId, title, department, medium, objectDate, objectUrl
    """
    session.run(
        """
        MERGE (a:Artwork {wikidataId: $wikidataId})
        SET
            a.objectId   = $objectId,
            a.title      = $title,
            a.department = $department,
            a.medium     = $medium,
            a.objectDate = $objectDate,
            a.objectUrl  = $objectUrl
        """,
        **artwork_data,
    )
 
 
def upsert_artist(session: Session, artist_data: dict) -> None:
    """
    Merge an Artist node into Neo4j.
 
    artist_data expected keys:
        wikidataId, name, birthDate, deathDate, genderLabel, occupationLabel
    """
    session.run(
        """
        MERGE (a:Artist {wikidataId: $wikidataId})
        SET
            a.name            = $name,
            a.birthDate       = $birthDate,
            a.deathDate       = $deathDate,
            a.genderLabel     = $genderLabel,
            a.occupationLabel = $occupationLabel
        """,
        **artist_data,
    )