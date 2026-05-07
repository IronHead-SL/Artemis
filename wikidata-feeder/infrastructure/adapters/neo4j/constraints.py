import logging
from neo4j.exceptions import ClientError

logger = logging.getLogger(__name__)

_CONSTRAINTS = [
    "CREATE CONSTRAINT artwork_wikidata IF NOT EXISTS FOR (a:Artwork) REQUIRE a.wikidataId IS UNIQUE",
    "CREATE CONSTRAINT artist_wikidata IF NOT EXISTS FOR (a:Artist) REQUIRE a.wikidataId IS UNIQUE",
    "CREATE CONSTRAINT genre_label IF NOT EXISTS FOR (g:Genre) REQUIRE g.label IS UNIQUE",
    "CREATE CONSTRAINT movement_label IF NOT EXISTS FOR (m:Movement) REQUIRE m.label IS UNIQUE",
    "CREATE CONSTRAINT concept_wikidata IF NOT EXISTS FOR (c:Concept) REQUIRE c.wikidataId IS UNIQUE",
    "CREATE CONSTRAINT country_label IF NOT EXISTS FOR (c:Country) REQUIRE c.label IS UNIQUE",
    "CREATE CONSTRAINT institution_label IF NOT EXISTS FOR (i:Institution) REQUIRE i.label IS UNIQUE",
    "CREATE CONSTRAINT technique_label IF NOT EXISTS FOR (t:Technique) REQUIRE t.label IS UNIQUE",
]

def setup_constraints(driver) -> None:
    with driver.session() as session:
        for cypher in _CONSTRAINTS:
            try:
                session.run(cypher)
            except ClientError as e:
                logger.debug(f"Constraint already exists or skipped: {e}")
    logger.info("Neo4j constraints ensured.")