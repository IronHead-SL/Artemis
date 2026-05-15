FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY ia-image-processor/pyproject.toml ./ia-image-processor/

RUN uv pip install --system \
    "pymongo>=4.16.0" \
    "qdrant-client>=1.17.1" \
    "torch>=2.11.0" \
    "torchvision>=0.26.0" \
    "open-clip-torch>=3.3.0" \
    "huggingface-hub>=0.23" \
    "Pillow>=10.0" \
    "requests>=2.32.5"

COPY ia-image-processor/ ./ia-image-processor/

WORKDIR /app/ia-image-processor

CMD ["python", "-u", "main.py"]