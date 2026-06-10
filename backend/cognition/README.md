# Cognition layer

Every concept the app shows is a first-class, persisted backend object. Nothing
downstream is hardcoded — beliefs are formed, confidence is computed, questions
are opened, beliefs are revised, plans are generated, and the graph is wired.

```
content ─► memory ─► observations ─► beliefs ─► questions
                          │             │
                          └────────► graph + reasoning + plan
```

## Domains
- `store.py` — SQLAlchemy models for every entity (runs on Postgres or SQLite).
- `memory/` — persistence + offline semantic retrieval (feature-hash embeddings; swap for a real embedder when keys exist).
- `observations/` — pattern miner: memories → evidence (rule-based, deterministic; swap for an LLM extractor — downstream unchanged).
- `confidence/` — transparent score from support/contradiction, recency, frequency, cross-domain consistency. Explainable, bounded 1–99.
- `beliefs/` — forms / strengthens / weakens / **revises** beliefs from observations; journals every change.
- `questions/` — opens questions where evidence is split; resolves them when a belief becomes confident.
- `relationships/` — queryable graph (nodes + edges); entity → belief `supports` links.
- `reasoning/` — stored causal chains ("why this matters").
- `planning/` — daily planner: candidates → choice → reasoning → nudge (sourced from a belief).
- `pipeline.py` — chat/journal/voice ingestion that updates the whole model.
- `api/routes.py` — the endpoints the frontend consumes (`/cognition/...`).
- `seed.py` — builds the demo state by running the real engines.

## Run
```bash
export DATABASE_URL="sqlite+aiosqlite:///./donna.db"   # or Postgres
python -m backend.cognition.seed                        # seed user demo-aarav
uvicorn api.main:app --reload --port 8000               # serves /cognition/*
```
Frontend: set `webapp/.env` `VITE_MOCK=0` (and `VITE_API_BASE`) → screens read live data, falling back to the bundled fixture if the backend is down.

## Traceability (the YC trace)
`GET /cognition/beliefs/{id}` → `supporting_memory_ids` → `GET /cognition/memory/{id}` → `source` / `source_ref` (the conversation). Belief → observation → memory → source is fully queryable.

## Deferred (clearly not yet real)
- Real vector DB (currently in-process cosine — fine at demo scale).
- LLM-based extraction/STT (rule miner + transcript-in; interfaces are pluggable).
- Constellation node *positions* stay client-side (aesthetic); the graph *data* is backend-driven.
