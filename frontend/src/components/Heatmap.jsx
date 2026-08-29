import { useMemo, useState } from "react";

// stats.matrix[] = { defender_model, scenario, runs, breaches, breach_rate,
//   avg_first_breach_turn, judge_flag_runs, categories }
// Pivoted here into rows (defender_model) x cols (scenario); color = breach_rate.
export default function Heatmap({ matrix, onCellClick }) {
  const [hovered, setHovered] = useState(null);

  const { defenderModels, scenarios, cellLookup } = useMemo(() => {
    const defenders = [];
    const scenarioSet = [];
    const lookup = new Map();

    for (const cell of matrix ?? []) {
      if (!defenders.includes(cell.defender_model)) defenders.push(cell.defender_model);
      if (!scenarioSet.includes(cell.scenario)) scenarioSet.push(cell.scenario);
      lookup.set(`${cell.defender_model}::${cell.scenario}`, cell);
    }
    return { defenderModels: defenders, scenarios: scenarioSet, cellLookup: lookup };
  }, [matrix]);

  if (!matrix || matrix.length === 0) {
    return (
      <div className="card heatmap-card">
        <div className="card-header">
          <h3 className="card-title">Breach rate heatmap</h3>
        </div>
        <div className="card-content">
          <p className="empty-state">Launch a batch below to populate the heatmap.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card heatmap-card">
      <div className="card-header">
        <h3 className="card-title">Breach rate heatmap</h3>
      </div>
      <div className="card-content heatmap-scroll">
        <table className="heatmap-table">
          <thead>
            <tr>
              <th className="heatmap-corner" />
              {scenarios.map((s) => (
                <th key={s} className="heatmap-col-label">{s}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {defenderModels.map((model) => (
              <tr key={model}>
                <th className="heatmap-row-label">{model}</th>
                {scenarios.map((scenario) => {
                  const cell = cellLookup.get(`${model}::${scenario}`);
                  const key = `${model}::${scenario}`;
                  return (
                    <td
                      key={scenario}
                      className="heatmap-cell-wrap"
                      onMouseEnter={() => setHovered(key)}
                      onMouseLeave={() => setHovered((h) => (h === key ? null : h))}
                    >
                      <HeatmapCell cell={cell} onClick={() => cell?.run_id && onCellClick?.(cell)} />
                      {hovered === key && cell && <HeatmapTooltip cell={cell} />}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <HeatmapLegend />
      </div>
    </div>
  );
}

function HeatmapCell({ cell, onClick }) {
  if (!cell) {
    return <div className="heatmap-cell heatmap-cell-empty">–</div>;
  }
  const bg = breachRateColor(cell.breach_rate);
  return (
    <div
      className="heatmap-cell"
      style={{ background: bg }}
      onClick={onClick}
      role="button"
      tabIndex={0}
    >
      {Math.round((cell.breach_rate ?? 0) * 100)}%
    </div>
  );
}

function HeatmapTooltip({ cell }) {
  return (
    <div className="heatmap-tooltip">
      <div className="tooltip-row"><strong>{cell.defender_model}</strong> · {cell.scenario}</div>
      <div className="tooltip-row">Runs: {cell.runs} · Breaches: {cell.breaches}</div>
      {cell.avg_first_breach_turn != null && (
        <div className="tooltip-row">Avg first breach turn: {cell.avg_first_breach_turn}</div>
      )}
      {cell.judge_flag_runs != null && (
        <div className="tooltip-row">Judge-flagged: {cell.judge_flag_runs}</div>
      )}
      {cell.categories?.length > 0 && (
        <div className="tooltip-row">Categories: {cell.categories.join(", ")}</div>
      )}
    </div>
  );
}

function HeatmapLegend() {
  return (
    <div className="heatmap-legend">
      <span>Safe</span>
      <div className="legend-gradient" />
      <span>Breached</span>
    </div>
  );
}

// 0 -> green (safe), 1 -> red (breached), interpolated through amber.
function breachRateColor(rate) {
  const r = Math.max(0, Math.min(1, rate ?? 0));
  if (r <= 0.5) {
    const t = r / 0.5;
    return `rgb(${74 + t * (251 - 74)}, ${222 + t * (191 - 222)}, ${128 + t * (36 - 128)})`;
  }
  const t = (r - 0.5) / 0.5;
  return `rgb(${251 + t * (248 - 251)}, ${191 + t * (113 - 191)}, ${36 + t * (113 - 36)})`;
}