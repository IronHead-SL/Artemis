FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN uv export --no-emit-project --no-hashes --format requirements-txt > req.txt && \
    pip install --no-cache-dir -r req.txt && \
    rm req.txt

COPY metmuseum-feeder/ ./

CMD ["python", "-u", "main.py"]