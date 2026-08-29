import {
  useRunEvents,
  selectMessages,
  selectToolActivity,
  selectVerdicts,
  selectSandboxStatus,
  selectSummary,
} from "../hooks/useRunEvents";
import Transcript from "../components/Transcript";
import ToolCallLog from "../components/ToolCallLog";
import SandboxPanel from "../components/SandboxPanel";
import BreachSummary from "../components/BreachSummary";
import ConnectionStatus from "../components/ConnectionStatus";

export default function ArenaPage({ runId, onBack }) {
  const { events, status } = useRunEvents(runId);

  const messages = selectMessages(events);
  const toolActivity = selectToolActivity(events);
  const verdicts = selectVerdicts(events);
  const sandboxStatus = selectSandboxStatus(events);
  const summary = selectSummary(events);

  return (
    <div className="arena-page">
      <div className="arena-toolbar">
        <button onClick={onBack}>&larr; Back to runs</button>
        <ConnectionStatus status={status} />
        <span className="run-id-label">run {runId.slice(0, 8)}</span>
      </div>

      <div className="arena-grid">
        <div className="exchange-column">
          <SandboxPanel sandboxStatus={sandboxStatus} />
          <Transcript messages={messages} verdicts={verdicts} />
        </div>

        <div className="interaction-column">
          <ToolCallLog activity={toolActivity} />
        </div>
      </div>

      {summary && <BreachSummary summary={summary} verdicts={verdicts} />}
    </div>
  );
}