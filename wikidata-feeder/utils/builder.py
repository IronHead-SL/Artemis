from SPARQLWrapper import SPARQLWrapper, JSON
from utils.query.queries_constants import *


def _build_sparql() -> SPARQLWrapper:
    sparql = SPARQLWrapper(SPARQL_ENDPOINT, agent=USER_AGENT)
    sparql.setReturnFormat(JSON)
    return sparql