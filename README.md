# 我的模拟首富路 / CZ 人生

一个只有一条公共人生路线的直播小说。真实人生节点来自调研资料；掷骰、失败路线、死亡、记忆和首富终局属于平行世界小说机制。首章立即开始，之后每章间隔四小时，MVP 约十八章，公共播放约持续三天。

## Repository layout

- `frontend/`: Next.js App Router reader, Vercel deployment target.
- `backend/`: FastAPI API, deterministic route planner, PostgreSQL event store and playback worker.
- `deploy/`: systemd and Caddy deployment units for `jibai-prod`.
- `我的模拟首富路-系统设计文档.md`: product and state-machine source of truth.

## Local development

The frontend can render a local preview without an API and falls back to the seeded visual state. For the full path, run PostgreSQL, create `backend/.env` from `.env.example`, then:

```bash
cd backend
python -m pip install -e .
czlife init-demo
czlife lock
uvicorn app.main:app --reload --port 8820
```

In another terminal:

```bash
cd backend
python -m app.worker
```

```bash
cd frontend
npm install
npm run dev
```

## Production model configuration

The server environment should contain `AI_BASE_URL=https://api.penguinsaichat.dpdns.org/v1`, `AI_API_KEY`, and the two GPT model names. The model list is checked at startup. `AI_MODEL_PRICES_JSON` stores provider prices for `gpt-5.5` and `gpt-5.6-luna`; the worker selects the lower estimated chapter cost. No reasoning parameter is sent.

## Vercel

Create a Vercel project from this repository with root directory `frontend` and set `NEXT_PUBLIC_API_BASE_URL` to the public Caddy API hostname.
