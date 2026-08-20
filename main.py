import subprocess
import torch
import os
import time
from datetime import datetime
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from transformers.utils import logging
from pathlib import Path
from transformers import M2M100ForConditionalGeneration, NllbTokenizer
from audio_utils import AudioRecorder
from text_post_process import combin_segment
logging.set_verbosity_error()

# Add ffmpeg to environment
ROOT = Path(__file__).resolve().parent
os.environ["PATH"] += os.pathsep + f"{ROOT}/ffmpeg"
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

pause_threshold = 2
max_audio_length = 20
generation_interval = 2
max_segment_combin_count = 3

asr_model_name = "openai/whisper-tiny"
translate_model_name = "facebook/nllb-200-distilled-600M"

local_files_only=True
asr_processor = WhisperProcessor.from_pretrained(asr_model_name, clean_up_tokenization_spaces=False, local_files_only=local_files_only)
asr_model  = WhisperForConditionalGeneration.from_pretrained(asr_model_name, local_files_only=local_files_only).to(device)
baned_sentence = ["you", "you.", "You", "You.", "Thank you.", "Thank you", "Thank.", "Thank", "Thanks."] # reduce hallucination


translate_tokenizer = NllbTokenizer.from_pretrained(translate_model_name, local_files_only=local_files_only)
translate_model = M2M100ForConditionalGeneration.from_pretrained(translate_model_name, local_files_only=local_files_only).to(device)

def translate(articles):
    if len(articles) == 0:
        return []
    tokens = translate_tokenizer(articles, return_tensors="pt", padding=True).to(device)
    max_new_tokens = 10 + int(tokens["input_ids"].shape[1]) * 2
    translated_tokens = translate_model.generate(**tokens, forced_bos_token_id=translate_tokenizer.convert_tokens_to_ids("zho_Hans"), max_new_tokens = max_new_tokens)
    return translate_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)

save_dir = "output"
os.makedirs(save_dir, exist_ok=True)
transcript_file = f"{save_dir}/{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}.txt"
print(f"Transcript will be saved to: {transcript_file}")

def get_device():
    command = ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", ""]
    try:
        ffmpeg_devices = subprocess.run(command, text=True, stderr=subprocess.PIPE, encoding="utf-8")
        microphone_lines = [line for line in ffmpeg_devices.stderr.splitlines() if "(audio)" in line]
        name_list = []
        for index, line in enumerate(microphone_lines):
            microphone_name =line.split('"')[1]
            name_list.append(microphone_name)
            print(f"[{index}] {microphone_name}")
        if len(name_list) == 0:
            print("Device not found.")
            exit(0)
        selected = input("Select your audio device: ")
        while not selected.isdigit() or not (0 <= int(selected) < len(name_list)):
            selected = input("Invalid input, try again: ")
        return f"audio={name_list[int(selected)]}"
    except FileNotFoundError:
        print("ffmpeg was not found. Please install it or make sure it is in your system PATH.")

audio_recorder = AudioRecorder(16000, 0.5, get_device())
audio_recorder.start()

last_update_time = time.time()
while True:
    if time.time() - last_update_time < generation_interval or not audio_recorder.has_new_chunk():
        continue
    last_update_time = time.time()

    audio_data = audio_recorder.get_audio()
    offset = audio_data["offset"]
    audio = audio_data["audio"]
    audio_length = audio_data["audio_length"]

    inputs = asr_processor(audio, truncation=False, return_attention_mask=True, return_tensors="pt", sampling_rate=16000).to(device)
    generated_ids = asr_model.generate(**inputs, return_timestamps=True, return_segments=True, task="transcribe",  # language ="en",
                                       condition_on_prev_tokens =False, no_speech_threshold=0.3, temperature = (0.0, 0.2, 0.4), logprob_threshold=-1.0, compression_ratio_threshold = 2.4)

    raw_segments = generated_ids["segments"][0]
    processed_segments = []
    for segment in raw_segments:
        text = asr_processor.batch_decode(segment["tokens"], skip_special_tokens=True)[0]
        start = segment["start"].item()
        end = segment["end"].item()
        processed_segments.append({"text":text, "start":start, "end":end})

    processed_segments = combin_segment(processed_segments, max_segment_combin_count)

    text = [s["text"] for s in processed_segments ]
    translations = translate(text)

    segment_count = len(processed_segments)
    for i in range(segment_count):
        processed_segments[i]["translation"] = translations[i]

    has_temp_sentence = False
    remove_length = 0
    for i in range(segment_count):
        segment = processed_segments[i]
        text = segment["text"]
        zh_text =  segment["translation"]
        start = segment["start"]
        end = segment["end"]
        if i < segment_count - 1 or audio_length - end >= pause_threshold:
            remove_length = end
            if not text.strip() in baned_sentence:
                print(f"\r\033[0m[{start+offset:.0f}-{end+offset:.0f}]\033[32m{text} \033[33m{zh_text}\033[0m", flush=True)
                with open(transcript_file, "a", encoding="utf-8") as f:
                    f.write(f"[{start+offset:.0f}-{end+offset:.0f}]{text} | {zh_text} \n")
        else:
            has_temp_sentence = True
            if not text.strip() in baned_sentence:
                print(f"\r\033[0m[{start+offset:.0f}-{end+offset:.0f}]\033[35m{text} \033[36m{zh_text}\033[0m", end = "", flush=True)

    if not has_temp_sentence:
        remove_length = max(audio_length - pause_threshold, remove_length)

    if audio_length - remove_length >= 20:
        print("\n\033[31m------Audio Force Clean-------\033[0m")
        remove_length = audio_length

    if remove_length > 0:
        remove_length = audio_recorder.trim(remove_length)
