def upsert_artwork(self, session, artwork_data: dict):
    """
    Merge an Artwork node. artwork_data keys:
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

def upsert_artist(self, session, artist_data: dict):
    """
    Merge an Artist node. artist_data keys:
    wikidataId, name, birthDate, deathDate, genderLabel, occupationLabel
    """
    session.run(
        """
        MERGE (a:Artist {wikidataId: $wikidataId})
        SET
            a.name             = $name,
            a.birthDate        = $birthDate,
            a.deathDate        = $deathDate,
            a.genderLabel      = $genderLabel,
            a.occupationLabel  = $occupationLabel            
        """,
        **artist_data,
    )