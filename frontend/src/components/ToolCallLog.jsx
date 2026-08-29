// Pairs tool_call with its following tool_result by seq proximity, per sandbox.
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
          <div key={evt.seq} className={`tool-entry sandbox-${evt.sandbox}`}>
            <span className="tool-sandbox-tag">{evt.sandbox}</span>
            {evt.type === "tool_call" ? (
              <code className="tool-command">$ {evt.tool?.name} {formatInput(evt.tool?.input)}</code>
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