"""Check the configured Gemini API key with one minimal request."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gemini_client import MODEL, doc_api_key

try:
    api_key = doc_api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "Tra loi dung 1 chu: 1+1 bang may?"}]}]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    candidates = data.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
    text = next((part.get("text") for part in parts if part.get("text")), None)
    if not text:
        raise RuntimeError("Gemini khong tra ve noi dung.")
    print("KEY HOAT DONG BINH THUONG!")
    print(f"Gemini tra loi: {text}")
except urllib.error.HTTPError as e:
    # Do not print the request URL: it contains the API key.
    print(f"LOI: HTTP {e.code}")
    print(e.read().decode("utf-8", errors="replace"))
    print("Kiem tra key, quyen truy cap API va model trong gemini_client.py.")
except Exception as e:
    print(f"Khong kiem tra duoc API key: {e}")
