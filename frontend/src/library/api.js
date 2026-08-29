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

export const api = {
  health: () => request("/api/health"),
  scenarios: () => request("/api/scenarios"),
  listRuns: () => request("/api/runs"),
  getRun: (id) => request(`/api/runs/${id}`),
  startRun: (payload) =>
    request("/api/runs", { method: "POST", body: JSON.stringify(payload) }),
  stopRun: (id) => request(`/api/runs/${id}/stop`, { method: "POST" }),
};