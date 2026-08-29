import { useEffect, useState } from "react";
import { api } from "../library/api";
import { useBatchPolling } from "../hooks/useBatchPolling";
import Leaderboard from "../components/Leaderboard";
import Heatmap from "../components/Heatmap";
import BatchLauncher from "../components/BatchLauncher";
import BatchProgress from "../components/BatchProgress";
import ArenaPage from "./ArenaPage";

function toArray(payload, ...keys) {
  if (Array.isArray(payload)) return payload;
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) return payload[key];
  }
  return [];
}

export default function BenchmarkPage({ onBack }) {
  const [scenarios, setScenarios] = useState([]);
  const [defenderModels, setDefenderModels] = useState([]);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState(null);
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [launching, setLaunching] = useState(false);
  const [drillRunId, setDrillRunId] = useState(null);

  const { batch, isDone, error: batchError } = useBatchPolling(activeBatchId);

  useEffect(() => {
    api.scenarios()
      .then((data) => setScenarios(toArray(data, "scenarios", "data")))
      .catch(() => {});
    refreshStats();
  }, []);

  // Backend doesn't (yet) expose a dedicated "list defender models" endpoint per
  // the ticket, so derive the options from whatever stats.by_defender_model has
  // seen so far, plus anything the launcher already knows about.
  useEffect(() => {
    if (stats?.by_defender_model) {
      const models = Object.keys(stats.by_defender_model);
      if (models.length) setDefenderModels((prev) => Array.from(new Set([...prev, ...models])));
    }
  }, [stats]);

  function refreshStats(scenario) {
    api.getStats(scenario)
      .then(setStats)
      .catch((e) => setStatsError(e.message));
  }

  async function handleLaunch({ scenarios: pickedScenarios, defender_models, reps }) {
    setLaunching(true);
    try {
      const { batch_id } = await api.createBatch({
        scenarios: pickedScenarios,
        defender_models,
        reps,
      });
      setActiveBatchId(batch_id);
    } catch (e) {
      setStatsError(e.message);
    } finally {
      setLaunching(false);
    }
  }

  // Refresh the leaderboard/heatmap once the batch finishes.
  useEffect(() => {
    if (isDone) refreshStats();
  }, [isDone]);

  if (drillRunId) {
    return <ArenaPage runId={drillRunId} onBack={() => setDrillRunId(null)} />;
  }

  return (
    <div className="benchmark-page">
      <div className="arena-toolbar">
        <button onClick={onBack}>&larr; Back to runs</button>
        <span className="run-id-label">benchmark</span>
      </div>

      {statsError && <p className="error-text">{statsError}</p>}
      {batchError && <p className="error-text">{batchError}</p>}

      <div className="benchmark-grid">
        <Leaderboard leaderboard={stats?.leaderboard} />
        <Heatmap
          matrix={stats?.matrix}
          onCellClick={(cell) => setDrillRunId(cell.run_id)}
        />
      </div>

      <BatchLauncher
        scenarios={scenarios}
        defenderModels={defenderModels.length ? defenderModels : DEFAULT_MODEL_HINTS}
        onLaunch={handleLaunch}
        launching={launching}
      />

      {batch && <BatchProgress batch={batch} />}

      {batch?.cells?.length > 0 && (
        <LiveCellGrid cells={batch.cells} onCellClick={(cell) => cell.run_id && setDrillRunId(cell.run_id)} />
      )}
    </div>
  );
}

// Shown while a batch is mid-flight so individual cells can be clicked into
// before GET /api/stats has caught up (stats only refresh on completion).
function LiveCellGrid({ cells, onCellClick }) {
  return (
    <div className="card live-cell-grid">
      <div className="card-header">
        <h3 className="card-title">Batch runs</h3>
      </div>
      <div className="card-content cell-grid-content">
        {cells.map((cell) => (
          <button
            key={`${cell.defender_model}-${cell.scenario}-${cell.rep}`}
            className={`live-cell status-${cell.status} ${cell.breached ? "breached" : ""}`}
            disabled={cell.status !== "completed"}
            onClick={() => onCellClick(cell)}
            title={`${cell.defender_model} · ${cell.scenario} · rep ${cell.rep}`}
          >
            <span className="live-cell-model">{cell.defender_model}</span>
            <span className="live-cell-scenario">{cell.scenario}</span>
            <span className="live-cell-status">
              {cell.status === "completed"
                ? cell.breached
                  ? `breach @${cell.first_breach_turn ?? "?"}`
                  : "held"
                : cell.status}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

// Fallback model hints only used before any batch has ever populated stats —
// keeps the launcher usable on a completely fresh MOCK=1 backend.
const DEFAULT_MODEL_HINTS = ["z-ai/glm-5.2", "minimax/minimax-m2"];