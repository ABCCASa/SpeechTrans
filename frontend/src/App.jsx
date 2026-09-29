import {useEffect, useState} from "react";
import './App.css'
import MessageList from "./MessageList";
import PictureInPicture from "./PictureInPicture";
import {locales} from "./locales";
import {LanguageContext} from "./LanguageContext";
import {SESSION_STATE as STATE, useAudioSession} from "./useAudioSession";
import {usePictureInPicture} from "./usePictureInPicture";

function App() {
    const [language, setLanguage] = useState("en");
    const t = locales[language];
    useEffect(() => {
        document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    }, [language]);

    const {status, messages, tempMessage, start, stop} = useAudioSession();
    const {pipTarget, open: openPictureInPicture} = usePictureInPicture({
        onError: reason => window.alert(reason === "unsupported" ? t.pipUnsupported : t.pipFailed),
    });
    const [selectedDeviceId, setSelectedDeviceId] = useState("")
    const [audioDevices, setAudioDevices] = useState([]);

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
    }, []);

    return (<LanguageContext.Provider value={t}>
        <main className="app-shell">
            <header className="app-header">
                <h1 className="brand"><img className="brand-mark" src={`${import.meta.env.BASE_URL}speechtrans.svg`}
                                           alt="" width="42" height="42"/>SpeechTrans</h1>
                <div className="header-actions">
                    <button type="button" className="pip-button" onClick={openPictureInPicture}>
                        {t.pipOpen}
                    </button>
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
                    <span className={`status-badge status-${status.toLowerCase()}`} role="status">
                <span className="status-dot"/>
                        {status === STATE.Open ? t.recording : status === STATE.Loading ? t.processing : t.idle}
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
                        disabled={status !== STATE.Close}
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
                    className={`record-button ${status === STATE.Open ? "is-recording" : ""}`}
                    type="button"
                    onClick={() => {
                        if (status === STATE.Open) stop();
                        else if (status === STATE.Close) start(selectedDeviceId);
                    }}
                    disabled={status === STATE.Loading || selectedDeviceId === ""}
                    aria-busy={status === STATE.Loading}
                >
                    <span className={`button-symbol ${status === STATE.Loading ? "is-loading" : ""}`}
                          aria-hidden="true"/>
                    {status === STATE.Open ? t.stopRecording : status === STATE.Loading ? t.pleaseWait : t.startRecording}
                </button>
            </section>
            <section className="transcript-panel" aria-labelledby="transcript-title">
                <div className="panel-heading">
                    <h2 id="transcript-title">{t.transcript}</h2>
                </div>
                <MessageList
                    messages={messages}
                    tempMessage={tempMessage}
                />
            </section>
        </main>
        {pipTarget && <PictureInPicture
            target={pipTarget}
            messages={messages}
            tempMessage={tempMessage}
            language={language}
        />}
    </LanguageContext.Provider>);
}

export default App
