import io
import os
import time

import librosa
import numpy as np
import soundfile as sf
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/tts")

TARGET_SR = 16000


def _resample_16k(waveform: np.ndarray, orig_sr: int) -> np.ndarray:
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=0)
    if orig_sr != TARGET_SR:
        waveform = librosa.resample(
            y=waveform.astype(np.float64),
            orig_sr=orig_sr,
            target_sr=TARGET_SR,
        )
    return waveform.astype(np.float32)


@router.get("/voices")
async def list_voices(request: Request):
    model = request.app.state.tts_model
    if model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    voices = model.list_available_spks()
    return {"voices": voices}


@router.post("")
async def tts(request: Request):
    model = request.app.state.tts_model
    if model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")

    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    spk_id = body.get("spk_id", "中文女")

    available = model.list_available_spks()
    if spk_id not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown spk_id: {spk_id}. Available: {available}",
        )

    start = time.time()
    results = list(model.inference_sft(text, spk_id, stream=False))
    elapsed = time.time() - start

    if not results:
        raise HTTPException(status_code=500, detail="TTS inference produced no output")

    audio_tensor = results[0]["tts_speech"]
    audio_np = audio_tensor.squeeze(0).numpy()

    audio_np = _resample_16k(audio_np, orig_sr=22050)

    buf = io.BytesIO()
    sf.write(buf, audio_np, TARGET_SR, format="WAV")
    wav_bytes = buf.getvalue()

    duration = round(len(audio_np) / TARGET_SR, 2)

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "X-Duration": str(duration),
            "X-Inference-Time": str(round(elapsed, 2)),
        },
    )
