import os
import time
from contextlib import asynccontextmanager

import soundfile as sf
sf.SoundFileRuntimeError = RuntimeError

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import wenet

MODEL_NAME = os.getenv("WENET_MODEL", "paraformer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[INIT] Loading model: {MODEL_NAME} ...")
    start = time.time()
    app.state.model = wenet.load_model(MODEL_NAME)
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
    return {
        "status": "ok",
        "asr": getattr(app.state, "model", None) is not None,
        "tts": False,
    }


from asr import router as asr_router
app.include_router(asr_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
