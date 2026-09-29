import { useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import MessageList from "./MessageList";
import baseStyles from "./index.css?inline";
import messageStyles from "./MessageList.css?inline";
import windowStyles from "./PictureInPicture.css?inline";

export default function PictureInPicture({ target, messages, tempMessage, language }) {
    useLayoutEffect(() => {
        target.ownerDocument.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    }, [target, language]);

    return createPortal(<>
        <style>{baseStyles}</style>
        <style>{messageStyles}</style>
        <style>{windowStyles}</style>
        <MessageList
            messages={messages}
            tempMessage={tempMessage}
            showTime={false}
            variant="pip"
        />
    </>, target);
}
