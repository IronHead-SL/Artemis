FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY metmuseum-feeder/pyproject.toml ./metmuseum-feeder/

RUN uv pip install --system \
    "pymongo>=4.16.0" \
    "requests>=2.32.5"

COPY metmuseum-feeder/ ./metmuseum-feeder/

WORKDIR /app/metmuseum-feeder

CMD ["python", "-u", "main.py"]