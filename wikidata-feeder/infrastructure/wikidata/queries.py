SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
REQUEST_DELAY   = 1.2
MAX_RETRIES     = 3
USER_AGENT      = "ArtemisMuseumBot/1.0 (https://github.com/yourrepo/artemis)"

ARTIST_QUERY = """
SELECT DISTINCT
    ?name
    ?birthDate
    ?deathDate
    ?genderLabel
    ?occupationLabel
    ?nationalityLabel
    ?movement        ?movementLabel
    ?influencedBy    ?influencedByLabel
    ?studiedAt       ?studiedAtLabel
WHERE {{
    OPTIONAL {{ wd:{wid} wdt:P569 ?birthDate. }}
    OPTIONAL {{ wd:{wid} wdt:P570 ?deathDate. }}
    OPTIONAL {{ wd:{wid} wdt:P21  ?gender. }}
    OPTIONAL {{ wd:{wid} wdt:P106 ?occupation. }}
    OPTIONAL {{ wd:{wid} wdt:P27  ?nationality. }}
    OPTIONAL {{ wd:{wid} wdt:P135 ?movement. }}
    OPTIONAL {{ wd:{wid} wdt:P737 ?influencedBy. }}
    OPTIONAL {{ wd:{wid} wdt:P69  ?studiedAt. }}
    SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "en,es,fr,de".
        wd:{wid}        rdfs:label ?name.
        ?gender         rdfs:label ?genderLabel.
        ?occupation     rdfs:label ?occupationLabel.
        ?nationality    rdfs:label ?nationalityLabel.
        ?movement       rdfs:label ?movementLabel.
        ?influencedBy   rdfs:label ?influencedByLabel.
        ?studiedAt      rdfs:label ?studiedAtLabel.
    }}
}}
LIMIT 50
"""

ARTWORK_QUERY = """
SELECT DISTINCT
    ?genre       ?genreLabel
    ?movement    ?movementLabel
    ?depicts     ?depictsLabel
    ?creator     ?creatorLabel
    ?inception
WHERE {{
    OPTIONAL {{ wd:{wid} wdt:P136 ?genre. }}
    OPTIONAL {{ wd:{wid} wdt:P135 ?movement. }}
    OPTIONAL {{ wd:{wid} wdt:P180 ?depicts. }}
    OPTIONAL {{ wd:{wid} wdt:P170 ?creator. }}
    OPTIONAL {{ wd:{wid} wdt:P571 ?inception. }}
    SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "en,es,fr,de".
        ?genre      rdfs:label ?genreLabel.
        ?movement   rdfs:label ?movementLabel.
        ?depicts    rdfs:label ?depictsLabel.
        ?creator    rdfs:label ?creatorLabel.
    }}
}}
LIMIT 50
"""