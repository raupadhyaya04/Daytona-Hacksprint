// The two-box visual that sells "these are real isolated machines".
export default function SandboxPanel({ sandboxStatus }) {
  return (
    <div className="sandbox-panel">
      <SandboxNode role="attacker" state={sandboxStatus.attacker} />
      <div className="sandbox-link" />
      <SandboxNode role="defender" state={sandboxStatus.defender} />
    </div>
  );
}

function SandboxNode({ role, state }) {
  const isActive = state === "executing" || state === "thinking";
  return (
    <div className={`sandbox-node role-${role} ${isActive ? "active" : "idle"}`}>
      <span className="sandbox-role">{role}</span>
      <span className="sandbox-state">{state}</span>
    </div>
  );
}