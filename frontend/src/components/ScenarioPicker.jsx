// Pulled out of RunsPage so scenario selection + the launch button can be
// iterated on independently (e.g. swapping in scenario descriptions/icons later).
export default function ScenarioPicker({ scenarios, value, onChange, onLaunch, launching }) {
  return (
    <section className="scenario-picker">
      <h2>Start a new run</h2>

      <div className="scenario-options">
        {scenarios.map((s) => {
          const id = s.id ?? s;
          const name = s.name ?? id;
          const description = s.description;
          const selected = id === value;

          return (
            <button
              key={id}
              type="button"
              className={`scenario-card ${selected ? "selected" : ""}`}
              onClick={() => onChange(id)}
            >
              <span className="scenario-name">{name}</span>
              {description && <span className="scenario-description">{description}</span>}
            </button>
          );
        })}
      </div>

      <button
        className="launch-button"
        onClick={onLaunch}
        disabled={launching || !value}
      >
        {launching ? "Provisioning sandboxes…" : "Launch attacker vs defender"}
      </button>
    </section>
  );
}