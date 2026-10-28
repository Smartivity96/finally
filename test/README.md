# FinAlly E2E tests

Playwright (Chromium only) end-to-end tests for the scenarios in `planning/PLAN.md` §12.
Playwright runs locally against a running app; no Playwright container is needed.

## Setup

```bash
cd test
npm install
npx playwright install chromium
```

## Requirements on the app under test

- **Fresh database.** `01-fresh-start.spec.ts` checks the seeded state ($10,000 cash, 10 default tickers),
  so it must run first, against a new DB. The other specs assert on relative changes and can run in any order.
- **`LLM_MOCK=true`**, so chat replies follow the keyword rules in `planning/API.md` §3.

Tests run one at a time (`workers: 1`) because they share one backend.

## Phase A: local backend (no Docker)

```bash
./run-local.sh            # builds frontend, starts backend on :8012 with a temp DB, runs the suite
./run-local.sh chat       # extra args are passed to `playwright test`
```

## Phase B: Docker image

```bash
docker run -d --rm --name finally-e2e -p 8010:8000 -e LLM_MOCK=true finally   # no volume → fresh DB
npx playwright test                                                            # BASE_URL defaults to http://localhost:8010
docker stop finally-e2e
```

## Any other target

```bash
BASE_URL=http://127.0.0.1:9000 npx playwright test
```

On failure, screenshots and traces are in `test-results/` (`npx playwright show-trace <trace.zip>`).
