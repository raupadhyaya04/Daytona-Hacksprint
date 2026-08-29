import { useEffect, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// One hook to rule the SSE stream. Every component reads derived state from here —
// nobody else should touch EventSource directly.
export function useRunEvents(runId) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("connecting"); // connecting | open | closed | error
  const esRef = useRef(null);

  useEffect(() => {
    if (!runId) return;

    setEvents([]);
    setStatus("connecting");

    const es = new EventSource(`${API_BASE}/api/runs/${runId}/events`);
    esRef.current = es;
    let finished = false; // set once the run reaches a terminal event

    es.onopen = () => setStatus("open");

    es.onmessage = (raw) => {
      try {
        const evt = JSON.parse(raw.data);
        setEvents((prev) => {
          // SSE replays history then streams live — de-dupe by seq in case of reconnect.
          if (prev.length && prev[prev.length - 1].seq >= evt.seq) return prev;
          return [...prev, evt];
        });
        if (evt.type === "run_finished" || evt.type === "error") {
          finished = true;
          setStatus("closed");
          // The run is done — close the stream ourselves so the browser doesn't
          // auto-reconnect (which would replay the whole run and close again).
          es.close();
        }
      } catch (err) {
        console.error("Bad event payload", raw.data, err);
      }
    };

    es.onerror = () => {
      // The backend closes the stream right after the terminal event, which
      // surfaces here as an error — that's a normal finish, not a failure. Only
      // flag an actual error if the run hadn't already finished.
      if (!finished) setStatus("error");
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [runId]);

  return { events, status };
}

// Derived selectors — keep components dumb, put the filtering logic here once.
export function selectMessages(events) {
  return events.filter((e) => e.type === "message");
}

export function selectToolActivity(events) {
  return events.filter((e) => e.type === "tool_call" || e.type === "tool_result");
}

export function selectVerdicts(events) {
  return events.filter((e) => e.type === "verdict" || e.type === "breach");
}

export function selectSandboxStatus(events) {
  const latest = { attacker: "idle", defender: "idle" };
  for (const e of events) {
    if (e.type === "status" && e.sandbox) {
      latest[e.sandbox] = e.content || e.meta?.state || "idle";
    }
  }
  return latest;
}

export function selectSummary(events) {
  const finished = events.find((e) => e.type === "run_finished");
  return finished?.meta?.summary ?? finished?.content ?? null;
}