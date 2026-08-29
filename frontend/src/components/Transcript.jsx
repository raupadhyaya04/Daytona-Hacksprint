import MessageBubble from "./MessageBubble";
import VerdictBadge from "./VerdictBadge";

// Merges messages + verdicts back into one chronological feed by seq,
// since the backend emits them as separate event types.
export default function Transcript({ messages, verdicts }) {
  const feed = [...messages, ...verdicts].sort((a, b) => a.seq - b.seq);

  return (
    <div className="transcript-panel">
      <h3>Exchange</h3>
      <div className="transcript-scroll">
        {feed.length === 0 && <p className="empty-state">Waiting for the attacker to open…</p>}
        {feed.map((evt) =>
          evt.type === "message" ? (
            <MessageBubble key={evt.seq} event={evt} />
          ) : (
            <VerdictBadge key={evt.seq} event={evt} />
          )
        )}
      </div>
    </div>
  );
}