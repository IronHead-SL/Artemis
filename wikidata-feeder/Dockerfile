FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY wikidata-feeder/pyproject.toml ./wikidata-feeder/

RUN uv pip install --system \
    "pymongo>=4.16.0" \
    "neo4j>=5.0.0" \
    "requests>=2.32.5" \
    "python-dotenv>=1.2.2"

COPY wikidata-feeder/ ./wikidata-feeder/

WORKDIR /app/wikidata-feeder

CMD ["python", "main.py", "--loop", "--batch-size", "50"]