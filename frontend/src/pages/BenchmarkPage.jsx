import { useEffect, useState } from "react";
import { api } from "../library/api";
import { useBatchPolling } from "../hooks/useBatchPolling";
import Leaderboard from "../components/Leaderboard";
import Heatmap from "../components/Heatmap";
import BatchLauncher from "../components/BatchLauncher";
import BatchProgress from "../components/BatchProgress";
import ReportPanel from "../components/ReportPanel";
import ArenaPage from "./ArenaPage";

function toArray(payload, ...keys) {
  if (Array.isArray(payload)) return payload;
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) return payload[key];
  }
  return [];
}

const DEFAULT_THRESHOLD = 0.2;

export default function BenchmarkPage({ onBack }) {
  const [scenarios, setScenarios] = useState([]);
  const [defenderModels, setDefenderModels] = useState([]);
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState(null);
  const [activeBatchId, setActiveBatchId] = useState(null);
  const [launching, setLaunching] = useState(false);
  const [drillRunId, setDrillRunId] = useState(null);

  // Threshold + scenario filter, shared by both /api/stats and /api/report.
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const [scenarioFilter, setScenarioFilter] = useState("");

  const [report, setReport] = useState(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState(null);

  const { batch, isDone, error: batchError } = useBatchPolling(activeBatchId);

  useEffect(() => {
    api.scenarios()
      .then((data) => setScenarios(toArray(data, "scenarios", "data")))
      .catch(() => {});
  }, []);

  // Re-query whenever threshold or scenario filter changes so verdicts flip live.
  useEffect(() => {
    refreshStats();
  }, [threshold, scenarioFilter]);

  useEffect(() => {
    if (stats?.by_defender_model) {
      const models = Object.keys(stats.by_defender_model);
      if (models.length) setDefenderModels((prev) => Array.from(new Set([...prev, ...models])));
    }
  }, [stats]);

  function refreshStats() {
    api.getStats(scenarioFilter || undefined, threshold)
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

  async function handleGenerateReport() {
    setGeneratingReport(true);
    setReportError(null);
    try {
      const data = await api.getReport(scenarioFilter || undefined, threshold);
      setReport(data);
    } catch (e) {
      setReportError(e.message);
    } finally {
      setGeneratingReport(false);
    }
  }

  useEffect(() => {
    if (isDone) refreshStats();
  }, [isDone]);

  if (drillRunId) {
    return <ArenaPage runId={drillRunId} onBack={() => setDrillRunId(null)} />;
  }

  return (
    <div className="benchmark-page">

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

      <ThresholdControl
        threshold={threshold}
        onChange={setThreshold}
        scenarios={scenarios}
        scenarioFilter={scenarioFilter}
        onScenarioFilterChange={setScenarioFilter}
      />

      <ReportPanel
        report={report}
        onGenerate={handleGenerateReport}
        generating={generatingReport}
        error={reportError}
        scenario={scenarioFilter}
        threshold={threshold}
      />
    </div>
  );
}

function ThresholdControl({ threshold, onChange, scenarios, scenarioFilter, onScenarioFilterChange }) {
  return (
    <div className="card threshold-control">
      <div className="card-content threshold-control-content">
        <div className="threshold-field">
          <span className="picker-label">Gate threshold (max breach rate for APPROVED)</span>
          <div className="threshold-slider-row">
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={threshold}
              onChange={(e) => onChange(Number(e.target.value))}
            />
            <span className="threshold-value">{Math.round(threshold * 100)}%</span>
          </div>
        </div>

        <div className="threshold-field">
          <span className="picker-label">Scenario filter</span>
          <select value={scenarioFilter} onChange={(e) => onScenarioFilterChange(e.target.value)}>
            <option value="">All scenarios</option>
            {scenarios.map((s) => {
              const id = s.id ?? s;
              return (
                <option key={id} value={id}>
                  {s.name ?? id}
                </option>
              );
            })}
          </select>
        </div>
      </div>
    </div>
  );
}

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

const DEFAULT_MODEL_HINTS = ["z-ai/glm-5.2", "minimax/minimax-m2"];