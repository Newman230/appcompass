# AppCompass — your app guide

An open-source, in-app AI support agent you can plug into any app. It answers
"how do I…?" questions from the app's own help docs, knows which screen the
user is on, and offers actions like **Open My appointments**. Built for
regulated industries: self-hostable, no personal data sent to the model,
Arabic and English, and published evaluation scores.

> Status: **Week 1 of 5.** Contract, server skeleton, clinic demo app.
> Answers (retrieval + Claude + streaming) land in Week 2.

## How it fits together

```
  Flutter SDK (v1)   React Native / web (v2)   Native (later)
          \                  |                     /
           +---- Contract v1: OpenAPI · SSE events · manifest schema ----+
                                     |
                     AppCompass server (FastAPI)
           retrieval · agent · guardrails · audit   ->  LLM provider (Claude)
                                     |
                           Postgres + pgvector
```

Only the core is AppCompass's own code. The model, embeddings, vector store,
audit sink, PII detector, knowledge source and handoff channel are **ports**
(`server/app/core/ports.py`) with swappable adapters chosen in config. The
core never imports a vendor SDK, and a test enforces it.

## Quick start

Requires Docker.

```bash
docker compose -f infra/docker-compose.yml up --build -d

# Register the demo app and keep the printed API key
docker compose -f infra/docker-compose.yml exec server \
  python -m app.cli create-app clinic-demo "Northwind Clinic (demo)"

# Load its manifest
docker compose -f infra/docker-compose.yml exec server \
  python -m app.cli load-manifest /srv/examples/clinic_demo/manifest.json

# Start a session
curl -s -X POST http://localhost:8080/v1/sessions \
  -H "X-AppCompass-Key: <your key>" -H "Content-Type: application/json" \
  -d '{"locale": "en"}'
```

Interactive API docs: http://localhost:8080/docs

## Repo layout

| Path | What it is |
| --- | --- |
| `spec/` | The contract: `openapi.yaml`, `events.md`, `manifest.schema.json` |
| `server/` | FastAPI backend, migrations, tests |
| `examples/clinic_demo/` | Fictional clinic: manifest, 16 help articles, Flutter app |
| `infra/` | Docker Compose (Terraform reference arrives in Week 5) |
| `docs/` | Architecture notes and the guide to writing a new platform SDK |

## Run the tests

```bash
cd server
pip install -e ".[dev]"
APPCOMPASS_TEST_DATABASE_URL=postgresql://appcompass:appcompass@localhost:5432/appcompass_test pytest -q
```

Tests need Postgres with the `vector` extension (the Compose `db` service works;
create an `appcompass_test` database in it). CI runs the same suite on every pull request.

## Roadmap

| Week | Deliverable |
| --- | --- |
| 1 | Contract, server skeleton, auth and tenant isolation, clinic demo app ✅ |
| 2 | Retrieval, Claude, streamed cited answers, first evals |
| 3 | Flutter SDK inside the demo app |
| 4 | Actions, guardrails, Arabic, 50-case eval suite in CI |
| 5 | Live demo, Terraform reference, video |

## Licence

MIT. The clinic and all its data are fictional.
