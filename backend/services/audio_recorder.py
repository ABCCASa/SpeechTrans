
import threading
import os
from pathlib import Path
import subprocess
import numpy as np

# Add ffmpeg to environment (remove this part if it is already set in your environment)
ROOT = Path(__file__).resolve().parent.parent
os.environ["PATH"] += os.pathsep + f"{ROOT}/ffmpeg"

class AudioRecorder:
    def __init__( self, sample_rate=16000):
        self._disposed = False
        self._has_new_chunk = False
        self._sample_rate = sample_rate
        self._audio = np.empty(0, dtype=np.float32)
        self._offset = 0.0
        self._lock = threading.Lock()
        self._process = subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel", "error",
                "-i", "pipe:0",
                "-ac", "1",
                "-ar", str(sample_rate),
                "-f", "f32le",
                "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

        self._thread = threading.Thread(
            target=self._read_audio,
            daemon=True,
        )
        self._thread.start()

    def _read_audio(self):
        while not self._disposed:
            data = self._process.stdout.read(6400)
            if not data:
                break
            audio = np.frombuffer(data, dtype=np.float32)
            with self._lock:
                if self._audio.size == 0:
                    self._audio = audio
                else:
                    self._audio = np.concatenate((self._audio, audio))
                self._has_new_chunk = True


    def add_audio_chunk(self, chunk):
        if self._disposed:
            return
        self._process.stdin.write(chunk)
        self._process.stdin.flush()

    def has_new_chunk(self):
        with self._lock:
            return self._has_new_chunk

    def get_audio(self):
        with self._lock:
            data = {
                "offset": self._offset,
                "audio_length": self._audio.size / self._sample_rate,
                "audio": self._audio.copy()}
            self._has_new_chunk = False
            return data

    def trim(self, seconds):
        with self._lock:
            samples = min(int(seconds * self._sample_rate), self._audio.size)
            if samples <= 0:
                return 0
            self._audio = self._audio[samples:]
            actual_seconds = samples / self._sample_rate
            self._offset += actual_seconds
            return actual_seconds

    def dispose(self):
        if self._disposed:
            return
        self._disposed = True
        self._process.kill()
