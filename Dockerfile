FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn rinsehq.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
