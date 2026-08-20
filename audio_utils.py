import threading
import numpy as np
from transformers.pipelines.audio_utils import ffmpeg_microphone

class AudioRecorder:
    def __init__( self, sample_rate=16000,  chunk_length_s = 1, ffmpeg_input_device=None):
        self._has_new_chunk = False
        self._sample_rate = sample_rate
        self._ffmpeg_input_device = ffmpeg_input_device
        self._chunk_length_s = chunk_length_s

        self._audio = np.empty(0, dtype=np.float32)
        self._lock = threading.RLock()
        self._run_id = 0
        self._offset = 0.0

    def start(self):
        with self._lock:
            self._run_id += 1
            current_run_id = self._run_id
        threading.Thread(target=self._record_loop, args=[current_run_id], daemon=True).start()

    def _record_loop(self, current_run_id):
        microphone = ffmpeg_microphone(self._sample_rate, self._chunk_length_s, ffmpeg_input_device=self._ffmpeg_input_device)
        try:
            for chunk in microphone:
                if current_run_id != self._run_id:
                    break
                chunk = np.frombuffer(chunk, dtype=np.float32)
                with self._lock:
                    if self._audio.size == 0:
                        self._audio = chunk.copy()
                    else:
                        self._audio = np.concatenate((self._audio, chunk))
                    self._has_new_chunk = True
        except Exception as e:
            print(f"Audio recorder error: {e}")


    def has_new_chunk(self):
        with self._lock:
            return self._has_new_chunk

    def get_audio(self, copy=True):
        with (self._lock):
            data = {
                "offset": self._offset,
                "audio_length": self._audio.size / self._sample_rate,
                "audio": self._audio.copy() if copy else self._audio}
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

    def stop(self):
        with self._lock:
            self._run_id += 1