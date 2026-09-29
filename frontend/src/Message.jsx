function formatTime(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remainingSeconds = total % 60;
    const parts = hours > 0
        ? [hours, minutes, remainingSeconds]
        : [minutes, remainingSeconds];
    return parts
        .map(value => String(value).padStart(2, "0"))
        .join(":");
}

export default function Message({ message, temporary = false, showTime = true }) {
    const { start, end, text, translation } = message;

    return (
        <article className={`message ${temporary ? "message-temporary" : ""}`}>
            {showTime && <div className="message-meta">
                <span className="message-time">{`${formatTime(start)}–${formatTime(end)}`}</span>
            </div>}
            <div className="message-content">
            <p className="message-original">{text}</p>
            {translation && (
                <p className="message-translation">{translation}</p>
            )}
            </div>
        </article>
    );
}
