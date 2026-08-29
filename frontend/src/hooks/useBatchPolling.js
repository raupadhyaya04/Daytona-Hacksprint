import { useEffect, useRef, useState } from "react";
import { api } from "../library/api";

const POLL_INTERVAL_MS = 1000;

// Polls GET /api/batch/{id} at ~1s until status === "completed" (or an error/stopped state).
// Mirrors useRunEvents' shape (events -> batch) so components stay symmetrical.
export function useBatchPolling(batchId) {
  const [batch, setBatch] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!batchId) return;

    let cancelled = false;
    setBatch(null);
    setError(null);

    async function poll() {
      try {
        const data = await api.getBatch(batchId);
        if (cancelled) return;
        setBatch(data);
        if (data.status !== "completed" && data.status !== "error" && data.status !== "stopped") {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    }

    poll();

    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [batchId]);

  const isDone = batch?.status === "completed";
  const isRunning = batch && !isDone && batch.status !== "error" && batch.status !== "stopped";

  return { batch, error, isDone, isRunning };
}