# FinAlly — Issues found by E2E testing

Owner: integration-tester. Each app bug gets an id, owner (per `API.md` §1), repro steps, expected vs actual, and evidence.

## Open

None. E2E run on 2026-10-28: 9/9 passed locally (Phase A) and 9/9 against the `finally` Docker image (Phase B).

## Test-side notes (not app bugs)

- `context.setOffline(true)` in Chromium does not cut an already-open EventSource, so the SSE resilience test blocks the stream with `page.route` and then restores it. A real mid-session drop was checked once by hand (`docker restart` of the container): status went `reconnecting` → `connected`.
