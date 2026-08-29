import { useEffect, useState } from "react";
import { api } from "../library/api";
import ScenarioPicker from "../components/ScenarioPicker";
import RunList from "../components/RunList";

// Normalizes whatever shape the backend sends for scenarios/runs into a plain array.
function toArray(payload, ...keys) {
  if (Array.isArray(payload)) return payload;
  for (const key of keys) {
    if (Array.isArray(payload?.[key])) return payload[key];
  }
  return [];
}

export default function RunsPage({ onSelectRun }) {
  const [scenarios, setScenarios] = useState([]);
  const [runs, setRuns] = useState([]);
  const [scenario, setScenario] = useState("");
  const [starting, setStarting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    api.scenarios()
      .then((data) => {
        const list = toArray(data, "scenarios", "data");
        setScenarios(list);
        if (list.length) setScenario(list[0].id ?? list[0]);
      })
      .catch((e) => setErrorMsg(e.message));

    api.listRuns()
      .then((data) => setRuns(toArray(data, "runs", "data")))
      .catch((e) => setErrorMsg(e.message));
  }, []);

  async function handleLaunch() {
    setStarting(true);
    setErrorMsg(null);
    try {
      const { run_id } = await api.startRun({ scenario });
      onSelectRun(run_id);
    } catch (e) {
      setErrorMsg(e.message);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="runs-page">
      <ScenarioPicker
        scenarios={scenarios}
        value={scenario}
        onChange={setScenario}
        onLaunch={handleLaunch}
        launching={starting}
      />
      {errorMsg && <p className="error-text">{errorMsg}</p>}
      <RunList runs={runs} onSelectRun={onSelectRun} />
    </div>
  );
}