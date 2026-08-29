// Single source of truth for the Event.type values coming off the SSE stream.
// Import these instead of typing raw strings in components — if the backend
// renames a type, this is the only file you touch.

export const EVENT_TYPES = {
  RUN_STARTED: "run_started",
  STATUS: "status",
  MESSAGE: "message",
  TOOL_CALL: "tool_call",
  TOOL_RESULT: "tool_result",
  VERDICT: "verdict",
  BREACH: "breach",
  RUN_FINISHED: "run_finished",
  ERROR: "error",
};

export const ACTORS = {
  ATTACKER: "attacker",
  DEFENDER: "defender",
  JUDGE: "judge",
  SYSTEM: "system",
};

export const SANDBOXES = {
  ATTACKER: "attacker",
  DEFENDER: "defender",
};

export const SEVERITY = {
  NONE: "none",
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
};

export const RUN_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  STOPPED: "stopped",
  ERROR: "error",
};

// Groups used by the selector functions in useRunEvents.js —
// keeps the "exchange layer vs interaction layer" split explicit and named.
export const EXCHANGE_EVENT_TYPES = [
  EVENT_TYPES.MESSAGE,
  EVENT_TYPES.VERDICT,
  EVENT_TYPES.BREACH,
];

export const INTERACTION_EVENT_TYPES = [
  EVENT_TYPES.STATUS,
  EVENT_TYPES.TOOL_CALL,
  EVENT_TYPES.TOOL_RESULT,
];

export function isTerminalEvent(type) {
  return type === EVENT_TYPES.RUN_FINISHED || type === EVENT_TYPES.ERROR;
}