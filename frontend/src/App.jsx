import {useEffect, useRef, useState, useLayoutEffect} from "react";
import './App.css'
import Message from "./Message";
import { cloneElement } from "react";
import { locales } from "./locales";
import { LanguageContext } from "./LanguageContext";
const STATE = {Loading: "Loading", Open: "Open", Close: "Close"}

function App() {
    const [language, setLanguage] = useState("en");
    const t = locales[language];

    useEffect(() => {
        document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    }, [language]);

    const [state, setState] = useState(STATE.Close)
    const [messages, setMessages] = useState([]);
    const [tempMessage, setTempMessage] = useState(null);
    const [selectedDeviceId, setSelectedDeviceId] = useState("")
    const [audioDevices, setAudioDevices] = useState([]);

    const wsRef = useRef(null);
    const messageBoxRef = useRef(null);
    const followBottomRef = useRef(true);
    const nextMessageId = useRef(0);

    async function button_click() {
        if (state === STATE.Loading) return
        if (state === STATE.Open) {
            setState(STATE.Loading)
            wsRef.current.close();
        } else {
            setState(STATE.Loading)

            let stream;
            let recorder;

            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: false,
                    audio: {
                        deviceId: {exact: selectedDeviceId},
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: false,
                    },
                });
                recorder = new MediaRecorder(stream);
            } catch (error) {
                stream?.getTracks().forEach((track) => track.stop());
                console.error("启动录音失败：", error);
                setState(STATE.Close);
                return;
            }

            recorder.ondataavailable = (event) => {
                if (event.data.size === 0) return;
                const ws = wsRef.current;
                if (ws?.readyState === WebSocket.OPEN) ws.send(event.data);
            };

            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const ws = new WebSocket(`${protocol}//${window.location.host}/api/asr`);
            wsRef.current = ws;

            ws.onopen = async () => {
                console.log("WebSocket connected");
                recorder.start(100);
                setState(STATE.Open);
            };

            let last_temp_message = null;
            let closeHandled = false;
            ws.onmessage = (event) => {
                if (closeHandled) return;
                const data = JSON.parse(event.data);
                if (data.final_sentences.length > 0) {
                    const newSegments = data.final_sentences.map((sentence) => (
                        <Message key = {nextMessageId.current++} message={sentence}  temporary={false}/>
                    ));
                    setMessages((prev) => [...prev, ...newSegments]);
                }
                const temp = data.temp_sentence;
                if (temp == null)
                {
                    last_temp_message = null;
                }
                else
                {
                    last_temp_message = <Message key = {nextMessageId.current} message= {temp} temporary={true}/>;
                }
                setTempMessage(last_temp_message)
            };

            function onClose() {
                if (closeHandled) return;
                closeHandled = true;
                console.log("WebSocket disconnected");
                if (recorder.state !== "inactive") recorder.stop();
                stream.getTracks().forEach((track) => track.stop());
                setState(STATE.Close)
                const savedMessage = last_temp_message == null ? null : cloneElement(
                    last_temp_message,
                    { key: nextMessageId.current++, temporary: false }
                );
                const divider = <hr key={nextMessageId.current++} className="session-divider" />;
                last_temp_message = null;
                setTempMessage(null);
                setMessages((prev) => {
                    const next = savedMessage == null ? prev : [...prev, savedMessage];
                    // Avoid empty or consecutive session separators.
                    if (next.length === 0 || next[next.length - 1]?.type === "hr") return next;
                    return [...next, divider];
                });
            }

            ws.onclose = onClose;
            ws.onerror = (error) => {
                console.error("WebSocket error:", error);
                onClose();
            };
        }
    }

    async function get_audio_device_list() {
        setSelectedDeviceId("")
        setAudioDevices((await navigator.mediaDevices.enumerateDevices())
            .filter((device) => device.kind === "audioinput")
            .map((device, index) =>
                ({
                    deviceId: device.deviceId, name: device.label, number: index + 1,
                })));
    }

    useEffect(() => {
        get_audio_device_list();
        return () => {
            wsRef.current?.close();
        }
    }, []);

    function handleMessageScroll(event) {
        const box = event.currentTarget;
        const distanceToBottom = box.scrollHeight - box.scrollTop - box.clientHeight;
        followBottomRef.current = distanceToBottom <= 2;
    }

    useLayoutEffect(() => {
        const box = messageBoxRef.current;
        if (box && followBottomRef.current) {
            box.scrollTop = box.scrollHeight;
        }
    }, [messages, tempMessage, language]);

    return (<LanguageContext.Provider value={t}><main className="app-shell">
        <header className="app-header">
            <h1 className="brand"><img className="brand-mark" src={`${import.meta.env.BASE_URL}speechtrans.svg`} alt="" width="42" height="42" />SpeechTrans</h1>
            <div className="header-actions">
            <select
                className="language-select"
                aria-label={t.language}
                title={t.language}
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
            >
                <option value="zh" lang="zh-CN">中文</option>
                <option value="en" lang="en">English</option>
            </select>
            <span className={`status-badge status-${state.toLowerCase()}`} role="status">
                <span className="status-dot" />
                {state === STATE.Open ? t.recording : state === STATE.Loading ? t.processing : t.idle}
            </span>
            </div>
        </header>
        <section className="controls" aria-label={t.recordingControls}>
            <div className="device-field">
            <label htmlFor="audio-device">{t.audioInput}</label>
            <select
                id="audio-device"
                value={selectedDeviceId}
                onChange={(event) => {
                    setSelectedDeviceId(event.target.value)
                }}
                disabled={state !== STATE.Close}
            >
                <option value="">{t.selectDevice}</option>
                {audioDevices.map((device) => (
                    <option
                        key={device.deviceId}
                        value={device.deviceId}
                    >
                        {device.name || `${t.audioDevice} ${device.number}`}
                    </option>
                ))}
            </select>
            </div>
            <button
                className={`record-button ${state === STATE.Open ? "is-recording" : ""}`}
                type="button"
                onClick={button_click}
                disabled={state === STATE.Loading || selectedDeviceId === ""}
                aria-busy={state === STATE.Loading}
            >
                <span className={`button-symbol ${state === STATE.Loading ? "is-loading" : ""}`} aria-hidden="true" />
                {state === STATE.Open ? t.stopRecording : state === STATE.Loading ? t.pleaseWait : t.startRecording}
            </button>
        </section>
        <section className="transcript-panel" aria-labelledby="transcript-title">
            <div className="panel-heading">
                <h2 id="transcript-title">{t.transcript}</h2>
            </div>
        <div
            className="message-list"
            ref={messageBoxRef}
            onScroll={handleMessageScroll}
            tabIndex={0}
            aria-label={t.transcriptContent}
        >
            {messages.length === 0 && tempMessage == null && (
                <div className="empty-state">
                    <p>{state === STATE.Open ? t.waitingForTranscript : t.emptyTranscript}</p>
                </div>
            )}
            {messages}
           {tempMessage}
        </div>
        </section>
    </main></LanguageContext.Provider>);
}

export default App
