import { useLayoutEffect, useRef } from "react";
import { createPortal } from "react-dom";
import Message from "./Message";
import { useTranslation } from "./LanguageContext";
import styles from "./PictureInPicture.css?inline";

export default function PictureInPicture({ target, messages, tempMessage, recording, language }) {
    const t = useTranslation();
    const boxRef = useRef(null);
    const followBottomRef = useRef(true);

    useLayoutEffect(() => {
        target.ownerDocument.documentElement.lang = language === "zh" ? "zh-CN" : "en";
        if (boxRef.current && followBottomRef.current) {
            boxRef.current.scrollTop = boxRef.current.scrollHeight;
        }
    }, [target, messages, tempMessage, language]);

    useLayoutEffect(() => {
        const view = target.ownerDocument.defaultView;
        const handleResize = () => {
            if (boxRef.current && followBottomRef.current) {
                boxRef.current.scrollTop = boxRef.current.scrollHeight;
            }
        };
        view.addEventListener("resize", handleResize);
        return () => view.removeEventListener("resize", handleResize);
    }, [target]);

    return createPortal(<>
        <style>{styles}</style>
        <div
            className="pip-transcript"
            ref={boxRef}
            tabIndex={0}
            aria-label={t.transcriptContent}
            onScroll={(event) => {
                const box = event.currentTarget;
                followBottomRef.current = box.scrollHeight - box.scrollTop - box.clientHeight <= 2;
            }}
        >
            {messages.length === 0 && tempMessage == null && (
                <p className="pip-empty">{recording ? t.waitingForTranscript : t.emptyTranscript}</p>
            )}
            {messages.map(message => message.type === "divider" ? (
                <hr key={message.id} className="session-divider" />
            ) : (
                <Message key={message.id} message={message} showTime={false} />
            ))}
            {tempMessage != null && <Message message={tempMessage} temporary showTime={false} />}
        </div>
    </>, target);
}
