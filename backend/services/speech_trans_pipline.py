import torch
from .automatic_speech_recognition.whisper_asr import WhisperASR
from .automatic_speech_recognition.parakeet_tdt_asr import ParakeetTdtASR
from transformers.utils import logging
from transformers import M2M100ForConditionalGeneration, NllbTokenizer
from services.audio_recorder import AudioRecorder
import threading

__all__ = ["process"]

logging.set_verbosity_error()

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

#config
pause_threshold = 4 # Finalize temporary transcripts after this many seconds of silence

asr_model_name = "openai/whisper-small.en"
translate_model_name = "facebook/nllb-200-distilled-1.3B"
local_files_only= False

#load asr model
asr_model = ParakeetTdtASR(device, local_files_only)

#load translation model
translate_tokenizer = NllbTokenizer.from_pretrained(translate_model_name, local_files_only=local_files_only)
translate_model = M2M100ForConditionalGeneration.from_pretrained(translate_model_name, local_files_only=local_files_only).to(device)


def translate(articles: list[str]) -> list[str]:
    if len(articles) == 0:
        return []
    tokens = translate_tokenizer(articles, return_tensors="pt", padding=True).to(device)
    max_new_tokens = 10 + int(tokens["input_ids"].shape[1]) * 3
    translated_tokens = translate_model.generate(**tokens, forced_bos_token_id=translate_tokenizer.convert_tokens_to_ids("zho_Hans"), max_new_tokens = max_new_tokens)
    return translate_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)




inference_lock = threading.Lock()


def process(audio_recorder: AudioRecorder):
    with inference_lock:
        if not audio_recorder.has_new_chunk():
            return None

        audio_data = audio_recorder.get_audio()
        offset = audio_data["offset"]
        audio = audio_data["audio"]
        audio_length = audio_data["audio_length"]

        processed_segments = asr_model.transcribe(audio)

        segment_count = len(processed_segments)

        # translation
        translations = translate([s["text"] for s in processed_segments])
        for i in range(segment_count):
            processed_segments[i]["translation"] = translations[i]

        # final result
        temp_sentence = None
        final_sentences = []

        has_temp_sentence = False
        remove_length = 0
        for i in range(segment_count):
            segment = processed_segments[i]
            text = segment["text"]
            translated_text = segment["translation"]
            start = segment["start"]
            end = segment["end"]
            if i < segment_count - 1 or audio_length - end >= pause_threshold:
                remove_length = end
                final_sentences.append({"text":text, "translation": translated_text, "start": start+offset, "end": end+offset})
            else:
                has_temp_sentence = True
                temp_sentence = {"text":text, "translation": translated_text, "start": start+offset, "end": end+offset}

        # audio trim
        if not has_temp_sentence:
            remove_length = max(audio_length - pause_threshold, remove_length)


        if remove_length > 0:
            audio_recorder.trim(remove_length)

        return { "final_sentences": final_sentences, "temp_sentence": temp_sentence }


