FROM python:3.11.15

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./

RUN uv export --format requirements-txt > req.txt && pip install --no-cache-dir -r req.txt

COPY metmuseum-feeder/ ./

CMD ["python", "mongodb_try.py"]