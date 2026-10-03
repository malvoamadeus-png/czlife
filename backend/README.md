# CZ Life backend

The backend is a small FastAPI application plus one playback worker. PostgreSQL is the source of truth for the frozen route, chapter text and append-only stream events.

## Local run

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e .
cp .env.example .env
czlife init-demo
czlife lock
uvicorn app.main:app --reload --port 8820
```

The worker is started separately:

```bash
python -m app.worker
```

`AI_API_KEY` can be omitted for a local fallback chapter. Production uses the Penguin OpenAI-compatible endpoint and only configured GPT models.

