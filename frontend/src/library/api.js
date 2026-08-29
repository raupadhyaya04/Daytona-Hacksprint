const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

function buildQuery(params) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (!entries.length) return "";
  return `?${entries.map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&")}`;
}

export const api = {
  health: () => request("/api/health"),
  scenarios: () => request("/api/scenarios"),

  // Single-run flow
  listRuns: () => request("/api/runs"),
  getRun: (id) => request(`/api/runs/${id}`),
  startRun: (payload) =>
    request("/api/runs", { method: "POST", body: JSON.stringify(payload) }),
  stopRun: (id) => request(`/api/runs/${id}/stop`, { method: "POST" }),

  // Benchmark / batch flow
  getStats: (scenario, threshold) =>
    request(`/api/stats${buildQuery({ scenario, threshold })}`),
  createBatch: (payload) =>
    request("/api/batch", { method: "POST", body: JSON.stringify(payload) }),
  getBatch: (id) => request(`/api/batch/${id}`),
  listBatches: () => request("/api/batches"),

  // Sign-off report — the buyer-facing artifact
  getReport: (scenario, threshold) =>
    request(`/api/report${buildQuery({ scenario, threshold })}`),
};