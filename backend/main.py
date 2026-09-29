import uvicorn
from fastapi import FastAPI
from api.asr import router as audio_router

app = FastAPI()
app.include_router(audio_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8080)