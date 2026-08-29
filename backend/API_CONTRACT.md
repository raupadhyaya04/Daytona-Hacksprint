# API Contract — Agent Red-Team Arena

Backend for the frontend to build against. **Everything the UI needs streams as one
flat `Event` type**, so the dashboard is essentially a live timeline of events plus a
summary header.

- Base URL (dev): `http://localhost:8000`
- CORS: open by default (`CORS_ORIGINS=*`).
- **You can build the entire UI with no API keys**: run the backend with `MOCK=1` and
  every endpoint below behaves identically, replaying a realistic run that ends in a breach.
- Interactive API docs: `http://localhost:8000/docs`

---

## The `Event` object

Both the SSE stream and `GET /api/runs/{id}` return these. Fields that don't apply are omitted.

| field | type | notes |
|-------|------|-------|
| `run_id` | string | |
| `seq` | int | 0-based, strictly increasing per run — use to dedupe/order |
| `ts` | string | ISO-8601 UTC |
| `turn` | int | conversation turn (0 for setup/teardown) |
| `actor` | string | `attacker` \| `defender` \| `judge` \| `system` |
| `type` | string | see below |
| `content` | string? | text (message body, status text, breach/verdict rationale) |
| `tool` | object? | `{ name, input }` for `tool_call` |
| `output` | object? | `{ stdout, exit_code }` for `tool_result` |
| `sandbox` | string? | `attacker` \| `defender` — which sandbox a tool ran in |
| `verdict` | object? | `{ breached, severity, category, rationale, source, ... }` for `verdict`/`breach` |
| `meta` | object? | extra data (run config on `run_started`, summary on `run_finished`) |

### `type` values
| type | actor | meaning |
|------|-------|---------|
| `run_started` | system | run began. `meta` = scenario, goal, models, mock flag |
| `status` | system | lifecycle note (provisioning, sandboxes ready, teardown, early-stop) |
| `message` | attacker/defender | a chat message (`content`) |
| `tool_call` | attacker/defender | agent invoked a tool. `tool={name,input}`, `sandbox` |
| `tool_result` | attacker/defender | result of that tool. `output={stdout,exit_code}`, `sandbox` |
| `verdict` | judge | judge scored the exchange. `verdict={breached,severity,category,rationale,source:"judge"}` |
| `breach` | system | **deterministic, ground-truth breach**. `verdict={...,source:"deterministic"}` |
| `run_finished` | system | terminal success. `meta` = summary |
| `error` | system | terminal failure. `content` = message |

`severity`: `none` \| `low` \| `medium` \| `high` \| `critical`.
`category` (breach/verdict): `secret_leak` \| `secret_exposed` \| `destructive` \| `exfil` \|
`forbidden_command` \| `policy_violation` \| `refusal` \| `none`.

**Terminal events** are `run_finished` and `error`; the SSE stream closes after one.

---

## Endpoints

### `GET /api/health`
```json
{ "ok": true, "mock": true, "tensorix_configured": false, "daytona_configured": false,
  "models": { "attacker": "z-ai/glm-5.2", "defender": "z-ai/glm-5.2", "judge": "z-ai/glm-5.2" } }
```

### `GET /api/scenarios`
```json
{ "scenarios": [
  { "id": "secret-flag", "name": "Exfiltrate the secret flag",
    "description": "...", "attacker_goal": "...", "success_hint": "..." },
  { "id": "aws-creds", "name": "Leak cloud credentials", "...": "..." },
  { "id": "destructive-ops", "name": "Trick into destructive commands", "...": "..." }
] }
```

### `POST /api/runs`
Body (only `scenario` is required):
```json
{ "scenario": "secret-flag", "max_turns": 8, "early_stop": true,
  "use_attacker_sandbox": true,
  "models": { "attacker": "z-ai/glm-5.2", "defender": "z-ai/glm-5.2", "judge": "z-ai/glm-5.2" } }
```
Response — the run starts in the background; subscribe to events next:
```json
{ "run_id": "a1b2c3d4e5f6", "status": "provisioning" }
```

### `GET /api/runs`
```json
{ "runs": [ { "run_id": "...", "status": "completed", "created_at": "...", "finished_at": "...",
  "config": {...}, "sandboxes": { "defender": "...", "attacker": "..." },
  "summary": { "breached": true, "breach_count": 1, "first_breach_turn": 3, "turns_run": 3,
               "categories": ["secret_leak"], "judge_flags": 1 } } ] }
```
`status`: `provisioning` \| `running` \| `completed` \| `failed` \| `stopped`.

### `GET /api/runs/{run_id}`
Full record: the summary object above **plus** `"events": [ ...all Event objects... ]`.
Use this to render a finished run or to hydrate before subscribing.

### `GET /api/runs/{run_id}/events`  — **SSE**
`Content-Type: text/event-stream`. Replays the full history, then streams live events, then
closes after a terminal event. Each event arrives as a `data:` line with the JSON `Event`.
During long sandbox provisioning the server also emits `: ping` comment lines to keep the
connection alive — `EventSource` ignores comments automatically, so no handling is needed.

### `POST /api/runs/{run_id}/stop`
`{ "run_id": "...", "stopping": true }` — requests a graceful stop between turns.

---

## Benchmark & batch endpoints

Run history **persists across server restarts** (loaded from JSONL on startup), so these
aggregates keep accumulating.

### `GET /api/stats`  (optional `?scenario=<id>`)
Leaderboard-ready aggregation over all scored runs (`completed`/`stopped`):
```json
{ "total_runs": 13, "scored_runs": 13,
  "overall": { "runs": 13, "breaches": 11, "breach_rate": 0.846,
               "avg_first_breach_turn": 3.0, "judge_flag_runs": 11,
               "categories": { "secret_leak": 9, "destructive": 2 } },
  "by_defender_model": { "z-ai/glm-5.2": { "runs": 11, "breach_rate": 0.818, "...": "..." } },
  "by_scenario":       { "secret-flag": { "...": "..." } },
  "by_attacker_model": { "z-ai/glm-5.2": { "...": "..." } },
  "matrix": [ { "defender_model": "z-ai/glm-5.2", "scenario": "secret-flag",
                "runs": 4, "breaches": 3, "breach_rate": 0.75, "avg_first_breach_turn": 3.0,
                "judge_flag_runs": 3, "categories": {"secret_leak": 3} } ],
  "leaderboard": {
    "most_resistant_defenders": [ { "model": "...", "breach_rate": 0.0, "runs": 5, "...": "..." } ],
    "most_effective_attackers": [ { "model": "...", "breach_rate": 1.0, "...": "..." } ] } }
```
`breach_rate` is the deterministic (ground-truth) rate; `judge_flag_runs` counts runs the LLM
judge flagged. `avg_first_breach_turn` is time-to-breach. Ideal for a leaderboard + a
defender-model × scenario heatmap.

### `POST /api/batch`  — run a model matrix
Body (`scenarios` required; models default to the server defaults):
```json
{ "scenarios": ["secret-flag","aws-creds"],
  "defender_models": ["z-ai/glm-5.2","minimax/minimax-m2"],
  "attacker_models": ["z-ai/glm-5.2"], "reps": 3, "max_turns": 6, "early_stop": true }
```
Expands to `scenarios × defender_models × attacker_models × reps` runs (capped by
`BATCH_MAX_RUNS`, default 24; `truncated:true` if the cap clipped it), launched under the global
concurrency cap. Response:
```json
{ "batch_id": "cee1e9a062", "status": "running", "run_ids": ["...","..."], "truncated": false }
```

### `GET /api/batches` / `GET /api/batch/{batch_id}`
List batches, or one batch's detail: its `spec`, `run_ids`, `progress`
(`{total, done, by_status}`), per-cell results (`cells[]` with `status`, `breached`,
`first_breach_turn`), and a `stats` block (same shape as `/api/stats`, scoped to the batch).
Poll this to render a live-filling matrix; each cell's `run_id` links to that run's SSE stream.

---

## Minimal frontend consumption (vanilla)

```js
// 1) start a run
const { run_id } = await fetch("http://localhost:8000/api/runs", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ scenario: "secret-flag" }),
}).then(r => r.json());

// 2) stream its events
const es = new EventSource(`http://localhost:8000/api/runs/${run_id}/events`);
es.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  switch (ev.type) {
    case "message":      addBubble(ev.actor, ev.content, ev.turn); break;
    case "tool_call":    addToolCall(ev.sandbox, ev.tool); break;
    case "tool_result":  addToolResult(ev.sandbox, ev.output); break;
    case "verdict":      addJudgeVerdict(ev.verdict); break;
    case "breach":       flashBreach(ev.verdict); break;      // the money moment
    case "run_finished": showSummary(ev.meta); es.close(); break;
    case "error":        showError(ev.content); es.close(); break;
  }
};
```

`EventSource` only does GET (no custom headers) — that's exactly what the events endpoint
expects. Start the run with `fetch`, then open the `EventSource`.

## Suggested UI
- **Header:** scenario name, status pill, breach badge (from `summary.breached` / `run_finished.meta`).
- **Two sandbox columns** (attacker / defender) showing their IDs + tool activity.
- **Center transcript:** attacker vs. defender bubbles per turn; judge verdict chip under each turn.
- **Breach events**: highlight loudly (red), show the `category`, `severity`, and `rationale`.
