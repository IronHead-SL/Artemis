FROM python:3.11.15
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv export --no-emit-project --no-hashes --format requirements-txt > req.txt && pip install --no-cache-dir -r req.txt
COPY wikidata-feeder/ ./
CMD ["python", "main.py", "--loop", "--batch-size", "50"]