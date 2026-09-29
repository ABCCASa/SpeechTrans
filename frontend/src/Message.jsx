import { useTranslation } from "./LanguageContext";

export default function Message({ message, temporary = false }) {
    const t = useTranslation();
    const { start, end, text, translation } = message;

    return (
        <article className={`message ${temporary ? "message-temporary" : ""}`}>
            <div className="message-meta">
                <span className="message-time">{`${start.toFixed(0)}–${end.toFixed(0)} ${t.seconds}`}</span>
            </div>
            <div className="message-content">
            <p className="message-original">{text}</p>
            {translation && (
                <p className="message-translation">{translation}</p>
            )}
            </div>
        </article>
    );
}
