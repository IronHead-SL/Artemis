import os
import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from utils import link, upsert, constraints


logger = logging.getLogger(__name__)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def verify_connection(self):
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j connection verified.")
        except ServiceUnavailable as e:
            logger.error(f"Cannot connect to Neo4j: {e}")
            raise

    def setup_constraints(self):
        constraints.setup_constraints(self)

    def upsert_artwork(self, session, artwork_data: dict):
        upsert.upsert_artwork(self, session, artwork_data)

    def upsert_artist(self, session, artist_data: dict):
        upsert.upsert_artist(self, session, artist_data)

    def link_artwork_to_artist(self, session, artwork_wid: str, artist_wid: str):
        link.link_artwork_to_artist(session, artwork_wid, artist_wid)

    def link_artwork_to_genre(self, session, artwork_wid: str, genre_label: str):
        link.link_artwork_to_genre(session, artwork_wid, genre_label)

    def link_artwork_to_movement(self, session, artwork_wid: str, movement_label: str):
        link.link_artwork_to_movement(session, artwork_wid, movement_label)

    def link_artwork_to_concept(self, session, artwork_wid: str, concept_wid: str, concept_label: str):
        link.link_artwork_to_concept(session, artwork_wid, concept_wid, concept_label)

    def link_artist_to_country(self, session, artist_wid: str, country_label: str):
        link.link_artist_to_country(session, artist_wid, country_label)

    def link_artist_influenced_by(self, session, artist_wid: str, influence_wid: str, influence_name: str):
        link.link_artist_influenced_by(session, artist_wid, influence_wid, influence_name)

    def link_artist_to_institution(self, session, artist_wid: str, institution_label: str):
        link.link_artist_to_institution(session, artist_wid, institution_label)

    def link_artist_to_movement(self, session, artist_wid: str, movement_label: str):
        link.link_artist_to_movement(session, artist_wid, movement_label)

    def link_artist_to_movement(self, session, artist_wid: str, movement_label: str):
        link.link_artist_to_movement(session, artist_wid, movement_label)

    def run_in_session(self, fn):
        """Execute fn(session) inside a managed session."""
        with self.driver.session() as session:
            fn(session)