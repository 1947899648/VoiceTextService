import sys

import requests


SERVER_URL = "http://localhost:8000"


def test_health():
    print("[TEST] Health check...")
    r = requests.get(f"{SERVER_URL}/health")
    assert r.status_code == 200
    print(f"       OK: {r.json()}")


def test_asr(audio_path: str):
    print(f"[TEST] ASR with: {audio_path}")
    with open(audio_path, "rb") as f:
        r = requests.post(f"{SERVER_URL}/asr", files={"audio": f})
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text}"
    data = r.json()
    print(f"       text: {data['text']}")
    print(f"       duration: {data['duration']}s")
    print(f"       inference: {data['inference_time']}s")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tests/test_asr.py <audio.wav>")
        print("       python tests/test_asr.py <audio.wav> --skip-health")
        sys.exit(1)

    audio_path = sys.argv[1]
    skip_health = "--skip-health" in sys.argv

    if not skip_health:
        test_health()
    test_asr(audio_path)
    print("\nAll tests passed.")
