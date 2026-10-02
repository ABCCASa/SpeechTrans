from .asr_base import AsrBase
from transformers import AutoModelForTDT, AutoProcessor
import torch
from .utils import combin_segment
class ParakeetTdtASR(AsrBase):
    def __init__(self, device: torch.device,  local_files_only: bool = False):
        model_id = "nvidia/parakeet-tdt-0.6b-v3"
        self._device = device
        self._processor = AutoProcessor.from_pretrained(model_id, local_files_only=local_files_only)
        self._model = AutoModelForTDT.from_pretrained(model_id, local_files_only=local_files_only).to(device)
        self._ignore_tail = 0.6

    def transcribe(self, audio):
        inputs = self._processor(audio, return_tensors="pt", sampling_rate=16000).to(self._device)
        output = self._model.generate(**inputs, return_dict_in_generate=True, max_new_tokens=4096)
        _, decoded_timestamps = self._processor.decode(output.sequences,  durations=output.durations, skip_special_tokens=True)
        raw_segments = decoded_timestamps[0]
        processed_segments = []

        audio_duration = len(audio) / 16000
        cutoff = max(0.0, audio_duration - self._ignore_tail)

        for segment in raw_segments:
            if segment["end"] > cutoff:
                break
            processed_segments.append({"text":segment["token"], "start": segment["start"], "end":segment["end"]})
        processed_segments = combin_segment(processed_segments)

        return processed_segments
