from SPARQLWrapper import SPARQLWrapper, JSON
from .constants import SPARQL_ENDPOINT, USER_AGENT


def _build_sparql() -> SPARQLWrapper:
    sparql = SPARQLWrapper(SPARQL_ENDPOINT, agent=USER_AGENT)
    sparql.setReturnFormat(JSON)
    return sparql