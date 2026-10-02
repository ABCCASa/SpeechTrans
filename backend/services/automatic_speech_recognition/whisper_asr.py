from .asr_base import AsrBase
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import torch
from .utils import combin_segment
class WhisperASR(AsrBase):
    def __init__(self, device: torch.device,  local_files_only: bool = False):
        asr_model_name = "openai/whisper-small.en"
        self._device = device
        self._asr_processor = WhisperProcessor.from_pretrained(asr_model_name, clean_up_tokenization_spaces=False, local_files_only=local_files_only)
        self._asr_model = WhisperForConditionalGeneration.from_pretrained(asr_model_name, local_files_only=local_files_only).to(device)
        self._baned_sentence = ["you", "you.", "You", "You.", "Thank you.", "Thank you", "Thank.", "Thank", "Thanks.", ".", "okay", "Bye.", "Bye"]  # reduce hallucination

    def transcribe(self, audio):
        inputs = self._asr_processor(audio, truncation=False, return_attention_mask=True, return_tensors="pt",
                               sampling_rate=16000).to(self._device)
        generated_ids = self._asr_model.generate(**inputs, return_timestamps=True, return_segments=True,
                                           condition_on_prev_tokens=False, no_speech_threshold=0.2,
                                           temperature=(0.0, 0.2, 0.4, 0.6), logprob_threshold=-1.0,
                                           compression_ratio_threshold=2.4)
        raw_segments = generated_ids["segments"][0]
        processed_segments = []
        for segment in raw_segments:
            text = self._asr_processor.batch_decode(segment["tokens"], skip_special_tokens=True)[0]
            if not text.strip() in self._baned_sentence:
                processed_segments.append({"text":text, "start": segment["start"].item(), "end":segment["end"].item()})

        processed_segments = combin_segment(processed_segments, 5)
        return processed_segments



