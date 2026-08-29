import { useState } from "react";

// Multi-select pickers for scenarios + defender models, plus a reps count.
// Fires POST /api/batch and hands the resulting batch_id back up to BenchmarkPage.
export default function BatchLauncher({ scenarios, defenderModels, onLaunch, launching }) {
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [selectedModels, setSelectedModels] = useState([]);
  const [reps, setReps] = useState(2);

  function toggle(list, setList, value) {
    setList(list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  }

  const canLaunch = selectedScenarios.length > 0 && selectedModels.length > 0 && !launching;
  const totalRuns = selectedScenarios.length * selectedModels.length * reps;

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Run a benchmark batch</h3>
      </div>
      <div className="card-content batch-launcher">
        <div className="picker-group">
          <span className="picker-label">Scenarios</span>
          <div className="pill-options">
            {scenarios.map((s) => {
              const id = s.id ?? s;
              const selected = selectedScenarios.includes(id);
              return (
                <button
                  key={id}
                  type="button"
                  className={`pill-option ${selected ? "selected" : ""}`}
                  onClick={() => toggle(selectedScenarios, setSelectedScenarios, id)}
                >
                  {s.name ?? id}
                </button>
              );
            })}
          </div>
        </div>

        <div className="picker-group">
          <span className="picker-label">Defender models</span>
          <div className="pill-options">
            {defenderModels.map((m) => {
              const selected = selectedModels.includes(m);
              return (
                <button
                  key={m}
                  type="button"
                  className={`pill-option ${selected ? "selected" : ""}`}
                  onClick={() => toggle(selectedModels, setSelectedModels, m)}
                >
                  {m}
                </button>
              );
            })}
          </div>
        </div>

        <div className="picker-group reps-group">
          <span className="picker-label">Reps per pair</span>
          <div className="reps-stepper">
            <button type="button" onClick={() => setReps((r) => Math.max(1, r - 1))}>
              −
            </button>
            <span className="reps-value">{reps}</span>
            <button type="button" onClick={() => setReps((r) => Math.min(10, r + 1))}>
              +
            </button>
          </div>
        </div>

        <div className="launch-row">
          <span className="total-runs-hint">
            {totalRuns > 0 ? `${totalRuns} run${totalRuns === 1 ? "" : "s"} total` : "Pick at least one scenario and model"}
          </span>
          <button
            className="launch-button"
            disabled={!canLaunch}
            onClick={() =>
              onLaunch({
                scenarios: selectedScenarios,
                defender_models: selectedModels,
                reps,
              })
            }
          >
            {launching ? "Launching batch…" : "Launch batch"}
          </button>
        </div>
      </div>
    </div>
  );
}