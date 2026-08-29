import { useState } from "react";
import RunsPage from "./pages/Runspage";
import ArenaPage from "./pages/ArenaPage";

export default function App() {
  // No router needed for a hacksprint — one piece of state decides the "page".
  const [activeRunId, setActiveRunId] = useState(null);

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Agent Red-Team Arena</h1>
        <span className="subtitle">Attacker vs Defender · isolated Daytona sandboxes</span>
      </header>

      {activeRunId ? (
        <ArenaPage runId={activeRunId} onBack={() => setActiveRunId(null)} />
      ) : (
        <RunsPage onSelectRun={setActiveRunId} />
      )}
    </div>
  );
}