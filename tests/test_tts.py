import argparse
import sys

import requests

SERVER_URL = "http://localhost:8000"


def list_voices():
    print("[TEST] Listing available TTS voices ...")
    r = requests.get(f"{SERVER_URL}/tts/voices")
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    data = r.json()
    print(f"       Voices: {data['voices']}")


def synthesize(text: str, spk_id: str, output_path: str):
    print(f"[TEST] TTS: \"{text}\" (spk={spk_id})")
    r = requests.post(
        f"{SERVER_URL}/tts",
        json={"text": text, "spk_id": spk_id},
    )
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"

    duration = r.headers.get("X-Duration", "?")
    inference = r.headers.get("X-Inference-Time", "?")
    print(f"       duration: {duration}s")
    print(f"       inference: {inference}s")

    with open(output_path, "wb") as f:
        f.write(r.content)
    print(f"       saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoiceTextService TTS test tool")
    parser.add_argument("text", nargs="?", help="Text to synthesize")
    parser.add_argument("--spk", default="中文女", help="Speaker ID (default: 中文女)")
    parser.add_argument("--out", default="tts_output.wav", help="Output WAV path")
    parser.add_argument("--voices", action="store_true", help="List available voices")
    args = parser.parse_args()

    if args.voices:
        list_voices()
    elif args.text:
        synthesize(args.text, args.spk, args.out)
    else:
        print("Usage:")
        print("  python tests/test_tts.py --voices")
        print("  python tests/test_tts.py \"你好世界\" --spk \"中文女\" --out output.wav")
        sys.exit(1)
