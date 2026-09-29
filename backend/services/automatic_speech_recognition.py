import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from transformers.utils import logging
from transformers import M2M100ForConditionalGeneration, NllbTokenizer
from services.audio_recorder import AudioRecorder
import threading

__all__ = ["process"]

logging.set_verbosity_error()

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


#config
pause_threshold = 2 # Finalize temporary transcripts after this many seconds of silence
max_segment_combin_count = 3 # Maximum number of transcript segments to merge when no sentence-ending punctuation is detected
asr_model_name = "openai/whisper-small.en"
translate_model_name = "facebook/nllb-200-distilled-1.3B"
local_files_only= False

#load asr model
asr_processor = WhisperProcessor.from_pretrained(asr_model_name, clean_up_tokenization_spaces=False, local_files_only=local_files_only)
asr_model  = WhisperForConditionalGeneration.from_pretrained(asr_model_name, local_files_only=local_files_only).to(device)
baned_sentence = ["you", "you.", "You", "You.", "Thank you.", "Thank you", "Thank.", "Thank", "Thanks.", ".", "okay", "Bye.", "Bye"] # reduce hallucination

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


sentence_end = [".", "!", "?", "...", "？", "。", "！"]
def combin_segment(segments, max_count):
    result = []
    current = None
    count = 0
    for seg in segments:
        text = seg["text"]
        if text is None or text.strip() == "":
            continue

        if current is None:
            current = {
                "text": text,
                "start": seg["start"],
                "end": seg["end"],
            }
            count = 1
        else:
            current["text"] += text
            current["end"] = seg["end"]
            count += 1

        if current["text"][-1] in sentence_end or count >= max_count:
            result.append(current)
            current = None
            count = 0

    # 最后一段不足 max_count 且没有句末标点
    if current is not None:
        result.append(current)

    return result

inference_lock = threading.Lock()


def process(audio_recorder: AudioRecorder):
    with inference_lock:
        if not audio_recorder.has_new_chunk():
            return None

        audio_data = audio_recorder.get_audio()
        offset = audio_data["offset"]
        audio = audio_data["audio"]
        audio_length = audio_data["audio_length"]
        inputs = asr_processor(audio, truncation=False, return_attention_mask=True, return_tensors="pt",
                               sampling_rate=16000).to(device)
        generated_ids = asr_model.generate(**inputs, return_timestamps=True, return_segments=True,
                                           condition_on_prev_tokens=True, no_speech_threshold=0.4,
                                           temperature=(0.0, 0.2, 0.4, 0.6), logprob_threshold=-1.0,
                                           compression_ratio_threshold=2.4)

        #post-process
        raw_segments = generated_ids["segments"][0]
        processed_segments = []
        for segment in raw_segments:
            text = asr_processor.batch_decode(segment["tokens"], skip_special_tokens=True)[0]
            processed_segments.append({"text":text, "start": segment["start"].item(), "end":segment["end"].item()})
        processed_segments = combin_segment(processed_segments, max_segment_combin_count)
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
                if not text.strip() in baned_sentence:
                    final_sentences.append({"text":text, "translation": translated_text, "start": start+offset, "end": end+offset})
            else:
                has_temp_sentence = True
                if not text.strip() in baned_sentence:
                    temp_sentence = {"text":text, "translation": translated_text, "start": start+offset, "end": end+offset}

        # audio trim
        if not has_temp_sentence:
            remove_length = max(audio_length - pause_threshold, remove_length)


        if remove_length > 0:
            audio_recorder.trim(remove_length)

        return { "final_sentences": final_sentences, "temp_sentence": temp_sentence }


