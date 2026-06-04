import os
import tempfile
import time
from contextlib import asynccontextmanager

# Fix: soundfile 0.11+ removed SoundFileRuntimeError, breaking librosa fallback
import soundfile as sf
sf.SoundFileRuntimeError = RuntimeError

import librosa
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import wenet


MODEL_NAME = os.getenv("WENET_MODEL", "paraformer")

model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    print(f"[INIT] Loading model: {MODEL_NAME} ...")
    start = time.time()
    model = wenet.load_model(MODEL_NAME)
    elapsed = time.time() - start
    print(f"[INIT] Model loaded in {elapsed:.1f}s, ready for requests")
    yield
    print("[SHUTDOWN] Server stopped")


app = FastAPI(title="VoiceTextService", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/asr")
async def asr(audio: UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    suffix = os.path.splitext(audio.filename)[1] or ".wav"
    data = await audio.read()

    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with open(fd, "wb") as f:
            f.write(data)

        start = time.time()
        result = model.transcribe(tmp_path)
        elapsed = time.time() - start

        audio_duration = round(librosa.get_duration(path=tmp_path), 2)

        return {
            "text": result.text,
            "duration": audio_duration,
            "inference_time": round(elapsed, 2),
        }
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
