from __future__ import annotations

from infrastructure.adapters.db import get_neo4j
from infrastructure.adapters.graph.queries import neo4j_metadata, neo4j_related
from infrastructure.ports.graph_query import GraphQuery


class Neo4jGraphQuery(GraphQuery):
    def __init__(self, driver=None):
        self._driver = driver or get_neo4j()

    def get_metadata_and_related(self, id_str: str) -> tuple[dict, list[tuple[int, str]]]:
        with self._driver.session() as session:
            meta = neo4j_metadata(session, id_str)
            related = neo4j_related(session, id_str)
        return meta, related
