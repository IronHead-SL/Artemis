from neo4j.exceptions import ClientError
import logging


logger = logging.getLogger(__name__)

def setup_constraints(self):
    """
    Create uniqueness constraints and indexes.
    Must be run once before ingestion.
    """
    constraints = [
        "CREATE CONSTRAINT artwork_wikidata IF NOT EXISTS FOR (a:Artwork) REQUIRE a.wikidataId IS UNIQUE",
        "CREATE CONSTRAINT artist_wikidata IF NOT EXISTS FOR (a:Artist) REQUIRE a.wikidataId IS UNIQUE",
        "CREATE CONSTRAINT genre_label IF NOT EXISTS FOR (g:Genre) REQUIRE g.label IS UNIQUE",
        "CREATE CONSTRAINT movement_label IF NOT EXISTS FOR (m:Movement) REQUIRE m.label IS UNIQUE",
        "CREATE CONSTRAINT concept_wikidata IF NOT EXISTS FOR (c:Concept) REQUIRE c.wikidataId IS UNIQUE",
        "CREATE CONSTRAINT country_label IF NOT EXISTS FOR (c:Country) REQUIRE c.label IS UNIQUE",
        "CREATE CONSTRAINT institution_label IF NOT EXISTS FOR (i:Institution) REQUIRE i.label IS UNIQUE",
    ]
    with self.driver.session() as session:
        for constraint in constraints:
            try:
                session.run(constraint)
            except ClientError as e:
                logger.debug(f"Constraint already exists or skipped: {e}")
    logger.info("Neo4j constraints ensured.")