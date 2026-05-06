FROM python:3.11.15

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./

RUN uv export --no-emit-project --no-hashes --format requirements-txt > req.txt && \
    pip install --no-cache-dir -r req.txt && \
    rm req.txt

COPY ia-image-processor/ ./

CMD ["python", "-u", "main.py"]