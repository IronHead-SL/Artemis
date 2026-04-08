import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import logging
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

import graph_ops.constraints as _constraints
import graph_ops.upsert as _upsert
import graph_ops.link as _link

logger = logging.getLogger(__name__)

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class Neo4jClient:
    """
    Thin wrapper around the Neo4j driver.
    All Cypher logic lives in neo4j/{constraints,upsert,link}.py.
    """

    def __init__(self):
        self.driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        self.driver.close()

    def verify_connection(self) -> None:
        try:
            self.driver.verify_connectivity()
            logger.info("Neo4j connection verified.")
        except ServiceUnavailable as e:
            logger.error(f"Cannot connect to Neo4j: {e}")
            raise

    def setup_constraints(self) -> None:
        _constraints.setup_constraints(self.driver)

    # ── Upserts ───────────────────────────────────────────────────────────────

    def upsert_artwork(self, session, artwork_data: dict) -> None:
        _upsert.upsert_artwork(session, artwork_data)

    def upsert_artist(self, session, artist_data: dict) -> None:
        _upsert.upsert_artist(session, artist_data)

    # ── Artwork relationships ─────────────────────────────────────────────────

    def link_artwork_to_artist(self, session, artwork_wid: str, artist_wid: str) -> None:
        _link.link_artwork_to_artist(session, artwork_wid, artist_wid)

    def link_artwork_to_genre(self, session, artwork_wid: str, genre_label: str) -> None:
        _link.link_artwork_to_genre(session, artwork_wid, genre_label)

    def link_artwork_to_movement(self, session, artwork_wid: str, movement_label: str) -> None:
        _link.link_artwork_to_movement(session, artwork_wid, movement_label)

    def link_artwork_to_concept(
        self, session, artwork_wid: str, concept_wid: str, concept_label: str
    ) -> None:
        _link.link_artwork_to_concept(session, artwork_wid, concept_wid, concept_label)

    # ── Artist relationships ───────────────────────────────────────────────────

    def link_artist_to_country(self, session, artist_wid: str, country_label: str) -> None:
        _link.link_artist_to_country(session, artist_wid, country_label)

    def link_artist_to_movement(self, session, artist_wid: str, movement_label: str) -> None:
        _link.link_artist_to_movement(session, artist_wid, movement_label)

    def link_artist_influenced_by(
        self, session, artist_wid: str, influence_wid: str, influence_name: str
    ) -> None:
        _link.link_artist_influenced_by(session, artist_wid, influence_wid, influence_name)

    def link_artist_to_institution(
        self, session, artist_wid: str, institution_label: str
    ) -> None:
        _link.link_artist_to_institution(session, artist_wid, institution_label)

    # ── Utility ───────────────────────────────────────────────────────────────

    def run_in_session(self, fn):
        """Execute fn(session) inside a managed session."""
        with self.driver.session() as session:
            return fn(session)
