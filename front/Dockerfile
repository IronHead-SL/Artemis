FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY front/pyproject.toml ./front/

RUN uv pip install --system \
    "pymongo>=4.16.0" \
    "neo4j>=5.0.0" \
    "qdrant-client>=1.17.1" \
    "streamlit>=1.57.0" \
    "open-clip-torch>=3.3.0" \
    "torch>=2.11.0" \
    "torchvision>=0.26.0" \
    "Pillow>=10.0" \
    "requests>=2.32.5"

COPY front/ ./front/

WORKDIR /app/front

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]