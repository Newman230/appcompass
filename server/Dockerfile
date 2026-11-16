# Build from the repo root so the contract in spec/ ships with the server:
#   docker build -f server/Dockerfile -t appcompass-server .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APPCOMPASS_SPEC_DIR=/srv/spec

WORKDIR /srv
COPY spec ./spec
COPY server/pyproject.toml ./server/pyproject.toml
COPY server/app ./server/app
COPY server/migrations ./server/migrations
RUN pip install --no-cache-dir -e ./server \
    && useradd --system --uid 10001 appcompass
USER appcompass

WORKDIR /srv/server
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
