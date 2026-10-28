# FinAlly — AI Trading Workstation

An AI-powered trading workstation: live streaming prices, a simulated $10k portfolio, and an LLM chat assistant that can analyze positions and execute trades. Built entirely by coding agents as the capstone of an agentic AI coding course.

## Features

- Live prices over SSE with green/red flash animations and sparklines
- Simulated trading — market orders, instant fills, no fees
- Portfolio heatmap, P&L chart and positions table
- AI chat (LiteLLM → OpenAI) that can trade and manage the watchlist
- Dark, Bloomberg-style terminal UI

## Stack

Single Docker container on port 8000:

- **Frontend**: Next.js + TypeScript + Tailwind (static export)
- **Backend**: FastAPI (Python, `uv`), SSE streaming
- **Database**: SQLite, initialized lazily
- **Market data**: built-in GBM simulator, or Massive (Polygon.io) API

## Status

The market data backend is complete; the rest of the platform is in progress. See [`planning/PLAN.md`](planning/PLAN.md).

## Quick Start

```bash
cp .env.example .env   # add your OPENAI_API_KEY
docker build -t finally .
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
# open http://localhost:8000
```

Backend tests:

```bash
cd backend && uv run --extra dev pytest
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Unless `LLM_MOCK=true` | OpenAI key for the AI chat |
| `MASSIVE_API_KEY` | No | Real market data; omit to use the simulator |
| `LLM_MOCK` | No | `true` for deterministic mock LLM responses (testing) |

## Project Structure

```
finally/
├── frontend/   # Next.js app
├── backend/    # FastAPI uv project
├── planning/   # Specs and agent docs
├── test/       # Playwright E2E tests
├── scripts/    # Start/stop helpers
└── db/         # SQLite volume mount
```

## License

See [LICENSE](LICENSE).
