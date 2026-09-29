import { useEffect, useRef, useState } from "react";

export const SESSION_STATE = { Loading: "Loading", Open: "Open", Close: "Close" };

export function useAudioSession() {
    const [status, setStatus] = useState(SESSION_STATE.Close);
    const [messages, setMessages] = useState([]);
    const [tempMessage, setTempMessage] = useState(null);
    const sessionRef = useRef(null);
    const nextMessageId = useRef(0);

    useEffect(() => () => {
        sessionRef.current?.finish(false);
    }, []);

    async function start(deviceId) {
        if (sessionRef.current || !deviceId) return;

        const session = { stream: null, recorder: null, ws: null, closed: false, temp: null, finish };
        sessionRef.current = session;
        setStatus(SESSION_STATE.Loading);

        function finish(updateState = true) {
            if (session.closed) return;
            session.closed = true;

            const { recorder, stream, ws } = session;
            if (recorder) {
                recorder.ondataavailable = null;
                recorder.onerror = null;
                recorder.onstop = null;
                if (recorder.state !== "inactive") recorder.stop();
            }
            stream?.getTracks().forEach(track => track.stop());
            if (ws) {
                ws.onopen = ws.onmessage = ws.onclose = ws.onerror = null;
                if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) ws.close();
            }
            if (sessionRef.current === session) sessionRef.current = null;
            if (!updateState) return;

            const savedMessage = session.temp == null ? null : {
                ...session.temp,
                id: nextMessageId.current++,
                type: "message",
            };
            const divider = { id: nextMessageId.current++, type: "divider" };
            setStatus(SESSION_STATE.Close);
            setTempMessage(null);
            setMessages(prev => {
                const next = savedMessage == null ? prev : [...prev, savedMessage];
                // Avoid empty or consecutive session separators.
                if (next.length === 0 || next[next.length - 1]?.type === "divider") return next;
                return [...next, divider];
            });
        }

        function fail(error) {
            if (session.closed) return;
            console.error("Audio session failed:", error);
            finish();
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: false,
                audio: {
                    deviceId: { exact: deviceId },
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                },
            });
            // Permission may resolve after the session was stopped or unmounted.
            if (session.closed) {
                stream.getTracks().forEach(track => track.stop());
                return;
            }
            session.stream = stream;
            const recorder = new MediaRecorder(stream);
            session.recorder = recorder;
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const ws = new WebSocket(`${protocol}//${window.location.host}/api/asr`);
            session.ws = ws;

            recorder.ondataavailable = event => {
                if (!session.closed && event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                    try {
                        ws.send(event.data);
                    } catch (error) {
                        fail(error);
                    }
                }
            };
            recorder.onerror = fail;
            recorder.onstop = () => finish();
            stream.getAudioTracks().forEach(track => {
                track.addEventListener("ended", () => finish(), { once: true });
            });

            ws.onopen = () => {
                if (session.closed) return;
                try {
                    recorder.start(100);
                    setStatus(SESSION_STATE.Open);
                } catch (error) {
                    fail(error);
                }
            };
            ws.onmessage = event => {
                if (session.closed) return;
                try {
                    const data = JSON.parse(event.data);
                    const newSegments = data.final_sentences.map(sentence => ({
                        ...sentence,
                        id: nextMessageId.current++,
                        type: "message",
                    }));
                    if (newSegments.length > 0) setMessages(prev => [...prev, ...newSegments]);
                    session.temp = data.temp_sentence ?? null;
                    setTempMessage(session.temp);
                } catch (error) {
                    fail(error);
                }
            };
            ws.onclose = () => finish();
            ws.onerror = fail;
        } catch (error) {
            fail(error);
        }
    }

    function stop() {
        sessionRef.current?.finish();
    }

    return { status, messages, tempMessage, start, stop };
}
