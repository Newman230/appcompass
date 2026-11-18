# Build from the repo root so the contract in spec/ ships with the server:
#   docker build -f server/Dockerfile -t appcompass-server .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APPCOMPASS_SPEC_DIR=/srv/spec \
    APPCOMPASS_MODEL_CACHE=/srv/models \
    HF_HOME=/srv/models/huggingface

WORKDIR /srv
COPY spec ./spec
COPY server/pyproject.toml ./server/pyproject.toml
COPY server/app ./server/app
COPY server/migrations ./server/migrations
# The model downloader writes caches, locks and logs under HF_HOME and $HOME,
# so the user needs a real home and everything model-related lives in the
# writable /srv/models volume.
RUN pip install --no-cache-dir -e ./server \
    && useradd --system --create-home --uid 10001 appcompass \
    && mkdir -p /srv/models/huggingface && chown -R appcompass /srv/models
    
USER appcompass

WORKDIR /srv/server
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
