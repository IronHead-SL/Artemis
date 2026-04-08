"""
Relationship helpers for Neo4j.
 
All functions take a live neo4j Session as their first argument.
They do NOT take `self` — they are pure helpers, not methods.
"""
from neo4j import Session
 
 
def link_artwork_to_artist(session: Session, artwork_wid: str, artist_wid: str) -> None:
    session.run(
        """
        MATCH (artwork:Artwork {wikidataId: $artwork_wid})
        MATCH (artist:Artist   {wikidataId: $artist_wid})
        MERGE (artwork)-[:CREATED_BY]->(artist)
        """,
        artwork_wid=artwork_wid,
        artist_wid=artist_wid,
    )
 
 
def link_artwork_to_genre(session: Session, artwork_wid: str, genre_label: str) -> None:
    session.run(
        """
        MATCH (artwork:Artwork {wikidataId: $artwork_wid})
        MERGE (g:Genre {label: $genre_label})
        MERGE (artwork)-[:HAS_GENRE]->(g)
        """,
        artwork_wid=artwork_wid,
        genre_label=genre_label,
    )
 
 
def link_artwork_to_movement(session: Session, artwork_wid: str, movement_label: str) -> None:
    session.run(
        """
        MATCH (artwork:Artwork {wikidataId: $artwork_wid})
        MERGE (m:Movement {label: $movement_label})
        MERGE (artwork)-[:PART_OF]->(m)
        """,
        artwork_wid=artwork_wid,
        movement_label=movement_label,
    )
 
 
def link_artwork_to_concept(
    session: Session,
    artwork_wid: str,
    concept_wid: str,
    concept_label: str,
) -> None:
    session.run(
        """
        MATCH (artwork:Artwork {wikidataId: $artwork_wid})
        MERGE (c:Concept {wikidataId: $concept_wid})
        SET c.label = $concept_label
        MERGE (artwork)-[:DEPICTS]->(c)
        """,
        artwork_wid=artwork_wid,
        concept_wid=concept_wid,
        concept_label=concept_label,
    )
 
 
def link_artist_to_country(session: Session, artist_wid: str, country_label: str) -> None:
    session.run(
        """
        MATCH (artist:Artist {wikidataId: $artist_wid})
        MERGE (c:Country {label: $country_label})
        MERGE (artist)-[:NATIONALITY]->(c)
        """,
        artist_wid=artist_wid,
        country_label=country_label,
    )
 
 
def link_artist_influenced_by(
    session: Session,
    artist_wid: str,
    influence_wid: str,
    influence_name: str,
) -> None:
    session.run(
        """
        MATCH (artist:Artist {wikidataId: $artist_wid})
        MERGE (inf:Artist {wikidataId: $influence_wid})
        ON CREATE SET inf.name = $influence_name
        MERGE (artist)-[:INFLUENCED_BY]->(inf)
        """,
        artist_wid=artist_wid,
        influence_wid=influence_wid,
        influence_name=influence_name,
    )
 
 
def link_artist_to_institution(
    session: Session, artist_wid: str, institution_label: str
) -> None:
    session.run(
        """
        MATCH (artist:Artist {wikidataId: $artist_wid})
        MERGE (i:Institution {label: $institution_label})
        MERGE (artist)-[:STUDIED_AT]->(i)
        """,
        artist_wid=artist_wid,
        institution_label=institution_label,
    )
 
 
def link_artist_to_movement(
    session: Session, artist_wid: str, movement_label: str
) -> None:
    session.run(
        """
        MATCH (artist:Artist {wikidataId: $artist_wid})
        MERGE (m:Movement {label: $movement_label})
        MERGE (artist)-[:PART_OF]->(m)
        """,
        artist_wid=artist_wid,
        movement_label=movement_label,
    )