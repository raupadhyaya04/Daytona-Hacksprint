import { useEffect, useState } from "react";
import { api } from "../library/api";
import ScenarioPicker from "../components/ScenarioPicker";
import RunList from "../components/RunList";

export default function RunsPage({ onSelectRun }) {
  const [scenarios, setScenarios] = useState([]);
  const [runs, setRuns] = useState([]);
  const [scenario, setScenario] = useState("");
  const [starting, setStarting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    api.scenarios()
      .then((data) => {
        setScenarios(data);
        if (data.length) setScenario(data[0].id ?? data[0]);
      })
      .catch((e) => setErrorMsg(e.message));

    api.listRuns().then(setRuns).catch((e) => setErrorMsg(e.message));
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