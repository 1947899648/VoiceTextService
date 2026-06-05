import sys

import requests


SERVER_URL = "http://localhost:8000"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tests/test_tts.py <text>")
        sys.exit(1)
    text = sys.argv[1]
    r = requests.post(f"{SERVER_URL}/tts", json={"text": text})
    print(f"Status: {r.status_code}")
    print(r.json())
