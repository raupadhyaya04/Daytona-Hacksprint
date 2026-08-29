export default function BreachSummary({ summary, verdicts }) {
  const breachCount = verdicts.filter((v) => v.verdict?.breached).length;
  const asr = verdicts.length ? Math.round((breachCount / verdicts.length) * 100) : 0;

  return (
    <div className="breach-summary">
      <h3>Run finished</h3>
      <div className="summary-stats">
        <Stat label="Breached" value={summary?.breached ? "Yes" : "No"} />
        <Stat label="Turns" value={summary?.turns ?? verdicts.length} />
        <Stat label="Attack success rate" value={`${asr}%`} />
        {summary?.category && <Stat label="Category" value={summary.category} />}
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}