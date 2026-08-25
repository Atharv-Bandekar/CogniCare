# CogniCare backend image — serves the FastAPI app and runs the Celery
# worker/beat. All three services in docker-compose share this one image;
# only the command differs.
FROM python:3.13-slim

# curl is used by the compose healthcheck; build-essential covers any package
# that needs a C toolchain to build a wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first so this layer is cached until requirements.txt changes.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code. .dockerignore keeps node_modules, .venv, and the frontend out.
COPY . .

EXPOSE 8000

# Default command = honcho (runs FastAPI web + Celery worker via Procfile).
# docker-compose.yml overrides this per-service (api/worker/beat).
CMD ["honcho", "start"]
