// Renders GET /api/batch/{id}'s progress block while a batch is in flight.
export default function BatchProgress({ batch }) {
  if (!batch) return null;

  const { status, progress } = batch;
  const pct = progress?.total ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <div className="card batch-progress">
      <div className="card-content">
        <div className="progress-header">
          <span className={`badge status-${status}`}>
            <span className="badge-dot" /> {status}
          </span>
          <span className="progress-count">
            {progress?.done ?? 0} / {progress?.total ?? 0} runs
          </span>
        </div>

        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
        </div>

        {progress?.by_status && (
          <div className="progress-breakdown">
            {Object.entries(progress.by_status).map(([key, count]) => (
              <span key={key} className={`breakdown-chip chip-${key}`}>
                {key}: {count}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}