ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE} AS base

ARG PIP_INDEX_URL=https://pypi.org/simple

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    locales \
    && rm -rf /var/lib/apt/lists/* \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r requirements.txt

COPY backend/bot ./bot
COPY config ./config
RUN mkdir -p /app/logs /app/images

FROM base AS runtime

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; raise SystemExit(0 if urlopen('http://127.0.0.1:8080/health', timeout=5).status == 200 else 1)"]
CMD ["python", "-m", "bot.main"]

FROM base AS dev

COPY requirements-dev.txt ./
RUN python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r requirements-dev.txt
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=6 \
    CMD ["python", "-c", "from urllib.request import urlopen; raise SystemExit(0 if urlopen('http://127.0.0.1:8080/health', timeout=3).status == 200 else 1)"]
CMD ["watchfiles", "--filter", "python", "python -m bot.main", "/app/bot"]

FROM base AS test

COPY requirements-dev.txt ./
RUN python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" -r requirements-dev.txt
COPY backend ./backend
COPY Dockerfile docker-compose.yml docker-compose.dev.yml docker-compose.test.yml docker-compose.prod.yml pyproject.toml ./
COPY .env.dev.example .env.test.example .env.prod.example ./
COPY tests ./tests
CMD ["python", "-m", "pytest", "-q", "tests"]
