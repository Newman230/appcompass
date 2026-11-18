# AppCompass — your app guide

An open-source, in-app AI support agent you can plug into any app. It answers
"how do I…?" questions from the app's own help docs, knows which screen the
user is on, and offers actions like **Open My appointments**. Built for
regulated industries: self-hostable, no personal data sent to the model,
Arabic and English, and published evaluation scores.

> Status: **Week 2 of 5.** Help-article search and streamed, cited answers
> from Claude. The Flutter SDK lands in Week 3.

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

Requires Docker and a [Claude API key](https://console.anthropic.com)
(or run without one, see below).

```bash
cp .env.example infra/.env        # then put your ANTHROPIC_API_KEY in infra/.env
docker compose -f infra/docker-compose.yml up --build -d

# Register the demo app and keep the printed API key
docker compose -f infra/docker-compose.yml exec server \
  python -m app.cli create-app clinic-demo "Northwind Clinic (demo)"

# Load its manifest and help articles (first run downloads the ~220 MB embedding model)
docker compose -f infra/docker-compose.yml exec server \
  python -m app.cli load-manifest /srv/examples/clinic_demo/manifest.json
docker compose -f infra/docker-compose.yml exec server \
  python -m app.cli load-docs clinic-demo /srv/examples/clinic_demo/help

# Ask a question: start a session, then stream the answer
KEY=<your key>
SID=$(curl -s -X POST http://localhost:8080/v1/sessions -H "X-AppCompass-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"locale": "en"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
curl -N -X POST http://localhost:8080/v1/sessions/$SID/messages -H "X-AppCompass-Key: $KEY" \
  -H "Content-Type: application/json" -d '{"text": "How do I reschedule?", "screen_id": "appointments"}'
```

The answer streams back as `token` events, then `citation` and `done`
([event reference](spec/events.md)). Interactive API docs: http://localhost:8080/docs

**No API key?** Set `APPCOMPASS_LLM_PROVIDER=extractive` in `infra/.env`. The
server then answers offline by quoting the best-matching help article: no
reasoning, refusals or translation, but the whole pipeline runs.

## Evaluations

```bash
pip install httpx pyyaml
APPCOMPASS_EVAL_KEY=$KEY python3 evals/run_evals.py
```

Runs the golden set in `evals/cases/clinic.yaml` (20 cases: how-to accuracy,
safety refusals, out-of-scope questions, Arabic) against the running server,
prints a score per category and writes `evals/reports/latest.json`.

| Model | Accuracy | Safety | Out of scope | Arabic | Overall |
| --- | --- | --- | --- | --- | --- |
| claude-haiku-5-5 (18 Nov 2026) | 12/12 | 4/4 | 2/2 | 2/2 | **20/20** · p50 1.6 s |

## Repo layout

| Path | What it is |
| --- | --- |
| `spec/` | The contract: `openapi.yaml`, `events.md`, `manifest.schema.json` |
| `server/` | FastAPI backend: core (`app/core`), adapters (`app/adapters`), migrations, tests |
| `evals/` | Golden-set cases and the eval runner |
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
create an `appcompass_test` database in it). They never call Claude or download
models: they use a hashing embedder and scripted LLMs. CI runs the same suite
on every pull request.

## Roadmap

| Week | Deliverable |
| --- | --- |
| 1 | Contract, server skeleton, auth and tenant isolation, clinic demo app ✅ |
| 2 | Retrieval, Claude, streamed cited answers, first evals ✅ |
| 3 | Flutter SDK inside the demo app |
| 4 | Actions, guardrails, Arabic, 50-case eval suite in CI |
| 5 | Live demo, Terraform reference, video |

## Licence

MIT. The clinic and all its data are fictional.
