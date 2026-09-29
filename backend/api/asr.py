from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.audio_recorder import AudioRecorder
from services.automatic_speech_recognition import process as asr_process
import asyncio

router = APIRouter()

@router.websocket("/asr")
async def asr_websocket(websocket: WebSocket):
    await websocket.accept()
    print("Audio WebSocket connected")
    audio_recorder = AudioRecorder()
    receiver_task = asyncio.create_task(receiver(websocket, audio_recorder))
    processor_task = asyncio.create_task(processor(websocket, audio_recorder))
    try:
        await asyncio.gather(
            receiver_task,
            processor_task
        )
    except WebSocketDisconnect:
        pass
    finally:
        audio_recorder.dispose()
        receiver_task.cancel()
        processor_task.cancel()
        await asyncio.gather(
            receiver_task,
            processor_task,
            return_exceptions=True,
        )

async def receiver(websocket: WebSocket, audio_recorder: AudioRecorder):
    while True:
        audio = await websocket.receive_bytes()
        await asyncio.to_thread(audio_recorder.add_audio_chunk, audio)

async def processor(websocket: WebSocket, audio_recorder: AudioRecorder):
    while True:
        await asyncio.sleep(0.2)
        result = await asyncio.to_thread(asr_process,audio_recorder)
        if result is not None:
            await websocket.send_json(result)
