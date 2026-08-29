const SEVERITY_COLORS = {
  none: "gray",
  low: "yellow",
  medium: "orange",
  high: "red",
  critical: "darkred",
};

const VECTOR_LABELS = {
  indirect_injection: "⚠ indirect injection",
  direct: "direct",
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
      <div className="verdict-badge-top">
        <span className="verdict-icon">⚠</span>
        <strong>Breach — {v.category}</strong>
        <span className={`severity-tag severity-${severity}`}>{severity}</span>
        {v.vector && (
          <span className={`vector-tag vector-${v.vector}`}>
            {VECTOR_LABELS[v.vector] ?? v.vector}
          </span>
        )}
      </div>
      <p className="verdict-rationale">{v.rationale}</p>
    </div>
  );
}