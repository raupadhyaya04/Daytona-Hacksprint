const LABELS = {
  connecting: "Connecting…",
  open: "Live",
  closed: "Finished",
  error: "Connection lost",
};

export default function ConnectionStatus({ status }) {
  return <span className={`connection-status status-${status}`}>{LABELS[status] ?? status}</span>;
}