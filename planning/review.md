# 2026-10-27 — Review of changes since the last commit

Scope: all staged, unstaged, and untracked changes present before this review, including the renamed inference skill, README, plan additions, review agents, documentation command, Stop hook, and existing review document. Findings are ordered by severity. Existing findings that still apply are included where independently verified.

## Findings

### 1. [P2] Install the optional dev extra in the backend test command

Location: `README.md:38`.

The new command uses `uv sync --dev`, but this project declares pytest and its plugins under `[project.optional-dependencies].dev` in `backend/pyproject.toml:18`, rather than a dev dependency group. Consequently the command does not select the test dependencies. An offline, frozen dry run against the current environment explicitly proposed uninstalling pytest, pytest-asyncio, pytest-cov, and Ruff. On a fresh environment the documented test command therefore cannot run the intended suite. Use `uv sync --extra dev && uv run --extra dev pytest`, keeping the extra selected during both synchronization and execution, or migrate the dependencies into a dev group.

### 2. [P2] Separate review output filenames and preserve existing feedback

Locations: `.claude/agents/change-reviewer.md:11`; `.claude/agents/codex-reviewer.md:7`; `.claude/agents/reviewer.md:7`.

The change reviewer writes `planning/review.md`, while both plan reviewers write `planning/REVIEW.md`. On this workspace's case-insensitive filesystem, both paths resolve to the same inode. Running either workflow can replace the other workflow's report; none of these agent instructions requires retaining earlier feedback. On a case-sensitive filesystem the reports instead remain separate, making the behavior platform-dependent. Use filenames differing by more than capitalization, such as `change-review.md` and `plan-review.md`, update all producers, and explicitly instruct each writer to preserve existing reviews when adding a new dated entry.

### 3. [P2] Include untracked file contents in the reminder fingerprint

Location: `.claude/hooks/review-reminder.sh:12`.

The fingerprint hashes `git status --porcelain` and `git diff HEAD`. For an untracked file, status records only its path and the diff excludes its contents. After a first reminder, subsequent edits to that same untracked file leave the fingerprint unchanged, so line 22 suppresses a review even though the implementation has changed. This also applies to files inside an untracked directory, whose status entry is normally collapsed to the directory name. Reproduced in an isolated repository: creating `new.py` triggered a reminder, changing its contents after the continuation produced no reminder, and changing a tracked file triggered one again. Include a deterministic, filename-safe digest of each non-ignored untracked file's contents, using an expanded list such as `git ls-files --others --exclude-standard -z`.

### 4. [P3] Correct the plan's claim about the inference skill name

Location: `planning/PLAN.md:468`.

The added review says the skill is named `openai` and asks agents to align Section 9's `openai-inference` reference. However, `.claude/skills/openai/SKILL.md:2` explicitly declares `name: openai-inference`; `openai` is the directory name. Section 9 already matches the declared name. Remove this claimed inconsistency or describe the directory and declared name separately, so an agent resolving the plan does not introduce a mismatch.

## Validation and limits

Read every changed and untracked file and compared tracked changes with HEAD. Cross-checked the relevant plan assertions against the market stream, cache, and model code. Validated the hook with `bash -n` and exercised its reminder behavior in a temporary Git repository without touching the project's Git metadata. Verified the report-path collision with filesystem metadata. Ran `uv sync --dev --dry-run --offline --frozen --no-cache` without modifying the environment. No application code changed, so the application test suite and external model calls were not run. `git diff --check HEAD` additionally reports trailing whitespace at `.claude/skills/openai/SKILL.md:12`.

---

# Review of changes since HEAD

Scope: staged, unstaged, and untracked changes present at the start of this review, including the inference skill migration, README, plan additions, review agents, documentation command, and existing plan review. No application code changed.

## Findings

### 1. [P2] Make report writing explicit in the Codex review commands

Locations: `.claude/agents/change-reviewer.md:11`; `.claude/agents/codex-reviewer.md:7`.

Both commands ask `codex exec` to write a Markdown file but neither selects a writable sandbox nor captures the final response to a file. With a read-only Codex configuration, the review can run but cannot save the requested feedback; noninteractive execution cannot rely on a later permission prompt. These agents then have no instruction to save the returned review themselves. Make output creation independent of the model's filesystem permissions, for example by asking for the review as the final response and using `codex exec --output-last-message <report-path> <prompt>`. Alternatively, explicitly configure the workspace-write sandbox where supported. Check command success and report existence before claiming completion.

### 2. [P2] Give change reviews and plan reviews distinct output paths

Locations: `.claude/agents/change-reviewer.md:11`; `.claude/agents/codex-reviewer.md:7`; `.claude/agents/reviewer.md:8`.

The change reviewer writes `planning/review.md`, while both plan reviewers write `planning/REVIEW.md`. On this workspace's case-insensitive filesystem these are the same file: both paths existed and had inode `12947364` before this review. Running either workflow can overwrite the other workflow's feedback, including the existing untracked plan review. On a case-sensitive filesystem they instead produce separate files, so behavior differs by platform. Use names differing by more than case, such as `planning/change-review.md` and `planning/plan-review.md`, and update every producer consistently.

### 3. [P3] Correct the newly added skill-name inconsistency claim

Location: `planning/PLAN.md:468`.

Section 13.1.3 says the skill is named `openai` and asks agents to align the Section 9 reference, which currently uses `openai-inference`. However, `.claude/skills/openai/SKILL.md:2` explicitly declares `name: openai-inference`; `openai` is its directory name. The existing Section 9 reference already matches the declared skill name. Remove this finding or distinguish the directory path from the declared name so downstream agents do not introduce a naming mismatch while attempting to resolve it.

## Validation and limits

Compared tracked changes against HEAD and read every untracked review/configuration file. Cross-checked plan additions against the market stream, cache, models, simulator, and Massive client. Inspected the installed `codex exec --help` for sandbox and output-file options and verified the report-path collision through filesystem metadata. No nested review agent or paid inference call was launched. Application tests were not run because these changes contain no application code; sandbox behavior was assessed from the command configuration, not an end-to-end nested run. `git diff --check HEAD` also reports trailing whitespace at `.claude/skills/openai/SKILL.md:12`.

---

# Preserved earlier plan review

The following feedback existed before this change review and is retained verbatim.

# Review of `PLAN.md`

This review covers issues **not already raised in Section 13**. The findings below are ordered by impact. Section 13's existing API, ticker tracking, trade atomicity, and testing questions still need decisions; they are not repeated here.

## Findings

1. **High — The documented launch exposes an unauthenticated trading and paid chat API.** The app has no login (`PLAN.md:15`), while the Docker command publishes port 8000 on all host interfaces (`PLAN.md:399`). Anyone who can reach that port can change the shared portfolio and call `/api/chat` using the server's OpenAI key. The optional public cloud deployment (`PLAN.md:420-422`) makes this more consequential. Bind the local container to `127.0.0.1:8000:8000` by default. Require an access control design before describing public deployment as supported; also cover request limits for `/api/chat`. The fake balance removes financial loss from trades, but does not remove API cost or unwanted changes to the shared state.

2. **High — Simulator prices restart from seeds while holdings and value history persist.** The database and snapshots survive container restarts (`PLAN.md:67`, `PLAN.md:228-232`, `PLAN.md:394-402`), but the simulator starts from seed prices (`PLAN.md:150-157`; `backend/app/market/simulator.py`). A restart can therefore cause an artificial jump in current portfolio value and the P&L chart. Decide whether to persist and restore the simulator's last price per ticker, or explicitly reset portfolio and snapshots with each simulated market session. Add a restart test with an open position and existing snapshots.

3. **High — The real data path has no price freshness rule for instant fills.** Market orders fill at the current price (`PLAN.md:27`), while Massive polls only every 15 seconds on the stated free tier (`PLAN.md:159-165`) and the cache retains its last update through poll failures (`backend/app/market/massive_client.py`). A displayed or cached price could be old while the API still executes a trade at it, including outside market hours. Define a maximum acceptable quote age for trading, return a clear unavailable or stale price error when exceeded, and show the timestamp or stale state in the UI. Decide whether trading outside market hours is disabled or explicitly treated as simulation.

4. **Medium — Repeated trade requests can execute twice.** `POST /api/portfolio/trade` (`PLAN.md:260`) and `/api/chat` (`PLAN.md:273`, `PLAN.md:290-299`) both cause side effects. If a response is lost after execution, a browser retry or double submit can duplicate a trade or a batch of AI actions. Transactional execution, already mentioned in Section 13.2.18, does not prevent this. Define a client generated idempotency key for each request, store its result, and return the original result on repetition. At minimum, the UI should disable duplicate submits while a request is pending, but that alone does not handle network retries.

5. **Medium — The cloud deployment statement conflicts with the single file, in-memory design.** `PLAN.md:420-422` says the container is designed for App Runner, Render, or any container platform. The design relies on a persistent SQLite volume and one in-memory price cache/background poller (`PLAN.md:60-70`, `PLAN.md:169-172`, `PLAN.md:394-402`). Multiple replicas would have different caches and pollers, and a platform without a persistent writable volume would lose the portfolio. State the deployment constraints explicitly: one process/replica, persistent writable storage, and no horizontal scaling. Treat a different datastore and shared market data service as prerequisites for multi-replica deployment.

6. **Medium — Existing database files have no upgrade path.** Lazy initialization creates missing tables (`PLAN.md:186-192`), but it does not change an existing table when the schema evolves. The claim of "no separate migration step" leaves users with persistent volumes at risk of startup or runtime failures after an update. Specify a schema version and small startup migrations, or state that persistent data is only supported within one schema version and give a backup/reset procedure. Do not silently reseed or overwrite an existing database.

## Suggested order

Resolve findings 1-3 before wiring trade execution and deployment. Findings 4-6 can be written into the API and operations contracts alongside the Section 13 decisions.
