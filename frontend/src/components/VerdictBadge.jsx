const SEVERITY_COLORS = {
  none: "gray",
  low: "yellow",
  medium: "orange",
  high: "red",
  critical: "darkred",
};

export default function VerdictBadge({ event }) {
  const v = event.verdict ?? {};
  const severity = v.severity || "none";

  if (!v.breached) {
    return (
      <div className="verdict-badge held">
        <span className="verdict-icon">✓</span> Judge: held (turn {event.turn})
      </div>
    );
  }

  return (
    <div className="verdict-badge breached" style={{ borderColor: SEVERITY_COLORS[severity] }}>
      <span className="verdict-icon">⚠</span>
      <strong>Breach — {v.category}</strong>
      <span className={`severity-tag severity-${severity}`}>{severity}</span>
      <p className="verdict-rationale">{v.rationale}</p>
    </div>
  );
}