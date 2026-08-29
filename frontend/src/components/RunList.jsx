import { useMemo, useState } from "react";

const RECENT_COUNT = 5;

// Pulled out of RunsPage so the history list can grow (filtering, sorting,
// pagination) without bloating the page component.
// Two view modes: "recent" shows the last 5 runs compactly, "all" shows the
// full history plus a summary stats strip.
//
// Per API_CONTRACT.md, GET /api/runs returns run objects shaped as:
//   { run_id, status, created_at, finished_at, config, sandboxes,
//     summary: { breached, breach_count, first_breach_turn, turns_run, categories, judge_flags } }
// All outcome data lives under `summary`, not flat on the run — every helper
// below reads through `run.summary`.
export default function RunList({ runs, onSelectRun }) {
  const [view, setView] = useState("recent"); // "recent" | "all"

  const sorted = useMemo(
    () => [...runs].sort((a, b) => new Date(b.created_at ?? 0) - new Date(a.created_at ?? 0)),
    [runs]
  );

  const visible = view === "recent" ? sorted.slice(0, RECENT_COUNT) : sorted;

  const summary = useMemo(() => {
    const total = runs.length;
    const breached = runs.filter(isBreached).length;
    const turnsValues = runs.map(getTurnsRun).filter((t) => t != null);
    const avgTurns = turnsValues.length
      ? Math.round(turnsValues.reduce((sum, t) => sum + t, 0) / turnsValues.length)
      : 0;
    return { total, breached, held: total - breached, avgTurns };
  }, [runs]);

  return (
    <section className="run-history">
      <div className="run-history-header">
        <h2>Past runs</h2>
        <div className="view-switch">
          <button
            className={`view-switch-option ${view === "recent" ? "active" : ""}`}
            onClick={() => setView("recent")}
          >
            Recent
          </button>
          <button
            className={`view-switch-option ${view === "all" ? "active" : ""}`}
            onClick={() => setView("all")}
          >
            All ({runs.length})
          </button>
        </div>
      </div>

      {view === "all" && runs.length > 0 && <RunSummaryStrip summary={summary} />}

      {runs.length === 0 ? (
        <p className="empty-state">No runs yet — kick one off above.</p>
      ) : (
        <ul className="run-list">
          {visible.map((r) => (
            <li key={r.run_id} className="run-list-item" onClick={() => onSelectRun(r.run_id)}>
              <span className={`status-dot status-${r.status}`} />
              <span className="run-id">{r.run_id.slice(0, 8)}</span>
              <span className="run-scenario">{r.config?.scenario ?? "—"}</span>
              <span className={`run-outcome ${isBreached(r) ? "breached" : "held"}`}>
                {isBreached(r) ? "Breached" : "Held"}
              </span>
              <span className="run-turns">{formatTurns(r)}</span>
            </li>
          ))}
        </ul>
      )}

      {view === "recent" && runs.length > RECENT_COUNT && (
        <button className="show-all-link" onClick={() => setView("all")}>
          Show all {runs.length} runs →
        </button>
      )}
    </section>
  );
}

function isBreached(run) {
  return Boolean(run.summary?.breached);
}

function getTurnsRun(run) {
  const value = run.summary?.turns_run;
  return typeof value === "number" ? value : null;
}

function getFirstBreachTurn(run) {
  const value = run.summary?.first_breach_turn;
  return typeof value === "number" ? value : null;
}

// The number that matters for a red-teaming result is time-to-breach. A breached
// run reports when it broke ("broke on turn 3"); a held run reports how long it
// lasted ("held 4 turns"). Keep these consistent with the outcome label so we
// never say a *breached* run "held".
function formatTurns(run) {
  const turnsRun = getTurnsRun(run);
  if (turnsRun == null) return "— turns";

  if (isBreached(run)) {
    const breachTurn = getFirstBreachTurn(run) ?? turnsRun;
    return `broke on turn ${breachTurn}`;
  }
  return `held ${turnsRun} turn${turnsRun === 1 ? "" : "s"}`;
}

function RunSummaryStrip({ summary }) {
  return (
    <div className="run-summary-strip">
      <SummaryStat label="Total runs" value={summary.total} />
      <SummaryStat label="Breached" value={summary.breached} tone="danger" />
      <SummaryStat label="Held" value={summary.held} tone="success" />
      <SummaryStat label="Avg turns" value={summary.avgTurns} />
    </div>
  );
}

function SummaryStat({ label, value, tone }) {
  return (
    <div className="run-summary-stat">
      <span className={`run-summary-value ${tone ? `tone-${tone}` : ""}`}>{value}</span>
      <span className="run-summary-label">{label}</span>
    </div>
  );
}