// actor: "attacker" | "defender" | "judge" | "system"
export default function MessageBubble({ event }) {
  const { actor, content, turn } = event;

  return (
    <div className={`message-bubble actor-${actor}`}>
      <div className="message-meta">
        <span className="actor-label">{actor}</span>
        <span className="turn-label">turn {turn}</span>
      </div>
      <p className="message-content">{content}</p>
    </div>
  );
}