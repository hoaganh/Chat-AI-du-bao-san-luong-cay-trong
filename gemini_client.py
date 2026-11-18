"""Goi Gemini API dung chung cho chat (function calling) va phan tich anh."""

import json
import os
import time
import urllib.error
import urllib.request

MODEL = "gemini-flash-lite-latest"  # con mo cho tai khoan moi, han muc on dinh
THU_MUC = os.path.dirname(os.path.abspath(__file__))


class ThieuApiKey(RuntimeError):
    """Chua cau hinh API key."""


def doc_api_key():
    """Doc key tu bien moi truong GEMINI_API_KEY hoac file api_key.txt (cung thu muc)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:  # Streamlit secrets (.streamlit/secrets.toml hoặc cấu hình Cloud) - ưu tiên hơn file văn bản
        import streamlit as st
        key = str(st.secrets.get("GEMINI_API_KEY", "")).strip()
        if key:
            return key
    except Exception:  # noqa: BLE001  (không có streamlit/secrets thì bỏ qua)
        pass
    for duong_dan in (os.path.join(THU_MUC, "api_key.txt"), "api_key.txt"):
        if os.path.exists(duong_dan):
            with open(duong_dan, "r", encoding="utf-8") as f:
                key = f.read().strip()
            if key:
                return key
    raise ThieuApiKey(
        "Chưa có API key. Đặt biến môi trường GEMINI_API_KEY (khuyên dùng) hoặc Streamlit secrets; "
        "chỉ dùng file api_key.txt (1 dòng) cho máy cá nhân và KHÔNG nộp file này."
    )


def co_api_key():
    try:
        doc_api_key()
        return True
    except ThieuApiKey:
        return False


def goi_api(payload, so_lan_thu_lai=5, timeout=90):
    """
    Goi generateContent. Tu dong thu lai khi gap loi tam thoi:
    429 (qua gioi han request/phut) va 500/503 (server nghen).
    """
    key = doc_api_key()
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={key}"
    )
    du_lieu = json.dumps(payload).encode("utf-8")

    for lan_thu in range(so_lan_thu_lai):
        try:
            req = urllib.request.Request(
                url, data=du_lieu, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            con_luot = lan_thu < so_lan_thu_lai - 1
            if e.code == 429 and con_luot:
                cho = 20 * (lan_thu + 1)  # 20s, 40s, 60s...
                print(f"  [NHAT KY] Gemini loi 429 (qua gioi han/phut), thu lai sau {cho}s...")
                time.sleep(cho)
                continue
            if e.code in (500, 503) and con_luot:
                cho = 2 ** lan_thu  # 1s, 2s, 4s...
                print(f"  [NHAT KY] Gemini loi {e.code} (nghen tam thoi), thu lai sau {cho}s...")
                time.sleep(cho)
                continue
            raise
    raise RuntimeError("Không gọi được Gemini sau nhiều lần thử.")
