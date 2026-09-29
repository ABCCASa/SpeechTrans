import {useLayoutEffect, useRef} from "react";
import Message from "./Message";
import {useTranslation} from "./LanguageContext";
import "./MessageList.css";

export default function MessageList({messages, tempMessage, showTime = true, variant = "main"}) {
    const t = useTranslation();
    const boxRef = useRef(null);
    const followBottomRef = useRef(true);

    useLayoutEffect(() => {
        const box = boxRef.current;
        if (followBottomRef.current) box.scrollTop = box.scrollHeight;
    }, [messages, tempMessage, t, showTime]);

    useLayoutEffect(() => {
        const box = boxRef.current;
        const view = box.ownerDocument.defaultView;
        const handleResize = () => {
            if (followBottomRef.current) box.scrollTop = box.scrollHeight;
        };
        view.addEventListener("resize", handleResize);
        return () => view.removeEventListener("resize", handleResize);
    }, []);

    return (
        <div
            className={`message-list message-list--${variant}${showTime ? "" : " message-list--no-time"}`}
            ref={boxRef}
            tabIndex={0}
            aria-label={t.transcriptContent}
            onScroll={(event) => {
                const box = event.currentTarget;
                followBottomRef.current = box.scrollHeight - box.scrollTop - box.clientHeight <= 2;
            }}
        >
            {messages.length === 0 && tempMessage == null && (
                <div className="empty-state">
                    <p>{t.emptyTranscript}</p>
                </div>
            )}
            {messages.map(message => message.type === "divider" ?
                (  <hr key={message.id} className="session-divider"/> ) :
                ( <Message key={message.id} message={message} showTime={showTime}/> )
            )}
            {tempMessage != null && <Message message={tempMessage} temporary showTime={showTime}/>}
        </div>
    );
}
