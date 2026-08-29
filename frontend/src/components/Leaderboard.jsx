// stats.leaderboard.most_resistant_defenders is already sorted ascending by
// breach_rate — this component just renders it as ranked rows, no re-sorting.
export default function Leaderboard({ leaderboard }) {
  const defenders = leaderboard?.most_resistant_defenders ?? [];
  const attackers = leaderboard?.most_effective_attackers ?? [];

  return (
    <div className="card leaderboard-card">
      <div className="card-header">
        <h3 className="card-title">Most resistant defenders</h3>
      </div>
      <div className="card-content">
        {defenders.length === 0 ? (
          <p className="empty-state">Run a batch to populate the leaderboard.</p>
        ) : (
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Defender model</th>
                <th>Breach rate</th>
                <th>Runs</th>
              </tr>
            </thead>
            <tbody>
              {defenders.map((row, i) => (
                <tr key={row.defender_model}>
                  <td className="rank-cell">{i + 1}</td>
                  <td className="model-cell">{row.defender_model}</td>
                  <td>
                    <BreachRateBar rate={row.breach_rate} />
                  </td>
                  <td className="runs-cell">{row.runs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {attackers.length > 0 && (
          <div className="attacker-leaderboard">
            <span className="picker-label">Most effective attackers</span>
            <ul className="attacker-list">
              {attackers.map((row) => (
                <li key={row.attacker_model}>
                  <span className="model-cell">{row.attacker_model}</span>
                  <BreachRateBar rate={row.breach_rate} danger />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function BreachRateBar({ rate, danger }) {
  const pct = Math.round((rate ?? 0) * 100);
  return (
    <div className="breach-rate-bar">
      <div className="breach-rate-track">
        <div
          className={`breach-rate-fill ${danger ? "fill-danger" : "fill-scale"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="breach-rate-value">{pct}%</span>
    </div>
  );
}