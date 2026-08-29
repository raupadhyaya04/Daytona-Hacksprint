// Pairs tool_call with its following tool_result by seq proximity, per sandbox.
// plant_artifact tool calls get distinct treatment — that's the attacker writing
// a poisoned file into the DEFENDER's sandbox (sandbox: "defender" on an
// attacker-actor event), which is the "payload arrived via a file, not chat" beat.
export default function ToolCallLog({ activity }) {
  const sorted = [...activity].sort((a, b) => a.seq - b.seq);

  return (
    <div className="tool-call-log">
      <h3>Sandbox activity</h3>
      <div className="tool-log-scroll">
        {sorted.length === 0 && (
          <p className="empty-state">No commands executed yet.</p>
        )}
        {sorted.map((evt) => (
          <div
            key={evt.seq}
            className={`tool-entry sandbox-${evt.sandbox} ${
              evt.tool?.name === "plant_artifact" ? "plant-artifact" : ""
            }`}
          >
            <span className="tool-sandbox-tag">{evt.sandbox}</span>
            {evt.type === "tool_call" ? (
              evt.tool?.name === "plant_artifact" ? (
                <code className="tool-command plant-artifact-command">
                  🧨 planted {formatPlantPath(evt.tool?.input)} into the target
                </code>
              ) : (
                <code className="tool-command">$ {evt.tool?.name} {formatInput(evt.tool?.input)}</code>
              )
            ) : (
              <pre className={`tool-output exit-${evt.output?.exit_code ?? "unknown"}`}>
                {evt.output?.stdout}
                {evt.output?.exit_code != null && (
                  <span className="exit-code"> [exit {evt.output.exit_code}]</span>
                )}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatInput(input) {
  if (!input) return "";
  if (typeof input === "string") return input;
  return Object.values(input).join(" ");
}

function formatPlantPath(input) {
  if (!input) return "~/inbox/…";
  return input.path ?? input.filename ?? input.target ?? "~/inbox/…";
}