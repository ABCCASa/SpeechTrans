# SpeechTrans

A simple real-time speech recognition and translation tool.

SpeechTrans captures microphone audio, transcribes English speech using Whisper, and translates the transcription into Simplified Chinese.

## Features

* Real-time microphone speech recognition
* English speech-to-text
* English-to-Chinese translation
* Real-time transcription and translation display
* Automatic transcript saving
* CUDA GPU acceleration when available

## How It Works

```text id="p4g6cw"
Microphone
    ↓
FFmpeg Audio Capture
    ↓
Whisper Speech Recognition
    ↓
English Transcription
    ↓
NLLB Translation
    ↓
Chinese Translation
    ↓
Terminal Display + Transcript File
```

SpeechTrans continuously captures microphone audio with FFmpeg. Whisper converts the audio into English text, then NLLB translates the transcription into Simplified Chinese. The results are displayed in real time and saved to the `output/` folder.

## Usage

### 1. Install Dependencies

```bash id="2os8za"
pip install -r requirements.txt
```

### 2. Install FFmpeg

FFmpeg is not included in this repository. Download FFmpeg separately and place `ffmpeg.exe` in the `ffmpeg` folder:

```text id="8ssijw"
SpeechTrans/
├── ffmpeg/
│   └── ffmpeg.exe
├── output/
├── main.py
├── requirements.txt
└── run.bat
```

Only `ffmpeg.exe` is required. `ffplay.exe` and `ffprobe.exe` are not needed.

### 3. Run

```bash id="q5gngv"
python main.py
```

Or on Windows:

```text id="gvkx8p"
run.bat
```

Select your microphone when prompted. SpeechTrans will start recognizing speech and displaying the transcription and Chinese translation in real time.

Example:

```text id="9mocvu"
Select your audio device:
[0] Microphone (Realtek Audio)
[1] Microphone (USB Audio Device)

> 1
```

Transcripts are automatically saved in the `output/` folder.
