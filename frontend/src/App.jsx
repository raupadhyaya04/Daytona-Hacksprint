import { useState } from "react";
import RunsPage from "./pages/Runspage";
import ArenaPage from "./pages/ArenaPage";
import BenchmarkPage from "./pages/BenchmarkPage";

// No router — three flat "screens" controlled by simple state, matching the
// low-ceremony approach of the rest of the app.
export default function App() {
  const [view, setView] = useState("runs"); // "runs" | "arena" | "benchmark"
  const [activeRunId, setActiveRunId] = useState(null);

  function openRun(runId) {
    setActiveRunId(runId);
    setView("arena");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Agent Red-Team Arena</h1>
        <span className="subtitle">Attacker vs Defender, but agents</span>
        <nav className="header-nav">
          <button
            className={`nav-link ${view !== "benchmark" ? "active" : ""}`}
            onClick={() => setView("runs")}
          >
            Runs
          </button>
          <button
            className={`nav-link ${view === "benchmark" ? "active" : ""}`}
            onClick={() => setView("benchmark")}
          >
            Benchmark
          </button>
        </nav>
      </header>

      {view === "arena" && activeRunId ? (
        <ArenaPage runId={activeRunId} onBack={() => setView("runs")} />
      ) : view === "benchmark" ? (
        <BenchmarkPage onBack={() => setView("runs")} />
      ) : (
        <RunsPage onSelectRun={openRun} />
      )}
    </div>
  );
}