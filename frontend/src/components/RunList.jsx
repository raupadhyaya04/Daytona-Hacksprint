// Pulled out of RunsPage so the history list can grow (filtering, sorting,
// pagination) without bloating the page component.
export default function RunList({ runs, onSelectRun }) {
  if (!runs.length) {
    return (
      <section className="run-history">
        <h2>Past runs</h2>
        <p className="empty-state">No runs yet — kick one off above.</p>
      </section>
    );
  }

  return (
    <section className="run-history">
      <h2>Past runs</h2>
      <ul className="run-list">
        {runs.map((r) => (
          <li key={r.run_id} className="run-list-item" onClick={() => onSelectRun(r.run_id)}>
            <span className={`status-dot status-${r.status}`} />
            <span className="run-id">{r.run_id.slice(0, 8)}</span>
            <span className="run-scenario">{r.scenario}</span>
            <span className={`run-outcome ${r.breached ? "breached" : "held"}`}>
              {r.breached ? "Breached" : "Held"}
            </span>
            <span className="run-turns">{r.turns} turns</span>
          </li>
        ))}
      </ul>
    </section>
  );
}