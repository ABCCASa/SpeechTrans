import torch
import os
import time
from datetime import datetime
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from transformers.utils import logging
from pathlib import Path
from transformers import M2M100ForConditionalGeneration, NllbTokenizer
from audio_utils import AudioRecorder, get_audio_device
from text_post_process import combin_segment
logging.set_verbosity_error()


# Add ffmpeg to environment (remove this part if it is already set in your environment)
ROOT = Path(__file__).resolve().parent
os.environ["PATH"] += os.pathsep + f"{ROOT}/ffmpeg"
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


#config
pause_threshold = 2 # Finalize temporary transcripts after this many seconds of silence
max_audio_length = 20 # Force-clear the audio buffer when the accumulated audio exceeds this duration
generation_interval = 2 # Run model inference at this interval, in seconds
max_segment_combin_count = 3 # Maximum number of transcript segments to merge when no sentence-ending punctuation is detected
asr_model_name = "openai/whisper-tiny.en"
translate_model_name = "facebook/nllb-200-distilled-600M"
local_files_only=True


#load asr model
asr_processor = WhisperProcessor.from_pretrained(asr_model_name, clean_up_tokenization_spaces=False, local_files_only=local_files_only)
asr_model  = WhisperForConditionalGeneration.from_pretrained(asr_model_name, local_files_only=local_files_only).to(device)
baned_sentence = ["you", "you.", "You", "You.", "Thank you.", "Thank you", "Thank.", "Thank", "Thanks."] # reduce hallucination


#load translation model
translate_tokenizer = NllbTokenizer.from_pretrained(translate_model_name, local_files_only=local_files_only)
translate_model = M2M100ForConditionalGeneration.from_pretrained(translate_model_name, local_files_only=local_files_only).to(device)

def translate(articles):
    if len(articles) == 0:
        return []
    tokens = translate_tokenizer(articles, return_tensors="pt", padding=True).to(device)
    max_new_tokens = 10 + int(tokens["input_ids"].shape[1]) * 2
    translated_tokens = translate_model.generate(**tokens, forced_bos_token_id=translate_tokenizer.convert_tokens_to_ids("zho_Hans"), max_new_tokens = max_new_tokens)
    return translate_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)


# set save file
save_dir = "output"
os.makedirs(save_dir, exist_ok=True)
transcript_file = f"{save_dir}/{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}.txt"
print(f"Transcript will be saved to: {transcript_file}")

# start audio record
audio_device = get_audio_device()
audio_recorder = AudioRecorder(16000, 0.5, audio_device)
audio_recorder.start()

# prediction loop
last_update_time = time.time()
while True:
    if time.time() - last_update_time < generation_interval or not audio_recorder.has_new_chunk():
        continue
    last_update_time = time.time()

    # audio process
    audio_data = audio_recorder.get_audio()
    offset = audio_data["offset"]
    audio = audio_data["audio"]
    audio_length = audio_data["audio_length"]
    inputs = asr_processor(audio, truncation=False, return_attention_mask=True, return_tensors="pt", sampling_rate=16000).to(device)
    generated_ids = asr_model.generate(**inputs, return_timestamps=True, return_segments=True,
                                       condition_on_prev_tokens = True, no_speech_threshold=0.4, temperature = (0.0, 0.2, 0.4, 0.6), logprob_threshold=-1.0, compression_ratio_threshold = 2.4)

    #post-process
    raw_segments = generated_ids["segments"][0]
    processed_segments = []
    for segment in raw_segments:
        text = asr_processor.batch_decode(segment["tokens"], skip_special_tokens=True)[0]
        processed_segments.append({"text":text, "start": segment["start"].item(), "end":segment["end"].item()})
    processed_segments = combin_segment(processed_segments, max_segment_combin_count)

    # translation
    text = [s["text"] for s in processed_segments ]
    translations = translate(text)
    segment_count = len(processed_segments)
    for i in range(segment_count):
        processed_segments[i]["translation"] = translations[i]

    # print result
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
                print(f"\r\033[0m[{start+offset:.0f}-{end+offset:.0f}]\033[32m{text} \033[33m{translated_text}\033[0m", flush=True)
                with open(transcript_file, "a", encoding="utf-8") as f:
                    f.write(f"[{start+offset:.0f}-{end+offset:.0f}]{text} | {translated_text} \n")
        else:
            has_temp_sentence = True
            if not text.strip() in baned_sentence:
                print(f"\r\033[0m[{start+offset:.0f}-{end+offset:.0f}]\033[35m{text} \033[36m{translated_text}\033[0m", end ="", flush=True)

    # audio trim
    if not has_temp_sentence:
        remove_length = max(audio_length - pause_threshold, remove_length)

    if audio_length - remove_length >= max_audio_length:
        print("\n\033[31m------Audio Force Clean-------\033[0m")
        remove_length = audio_length

    if remove_length > 0:
        remove_length = audio_recorder.trim(remove_length)
