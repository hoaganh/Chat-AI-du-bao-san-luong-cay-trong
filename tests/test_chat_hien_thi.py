"""Giao diện chat phải hiển thị: hàm hệ thống đã gọi, kết quả đưa cho Gemini, và nguồn câu trả lời."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["AGFARM_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.chdir(Path(__file__).resolve().parents[1])

from streamlit.testing.v1 import AppTest

import chat_logic as c
import mo_hinh_du_bao as lab

FAILS = []


def kt(ten, dk, chi_tiet=""):
    print(("PASS  " if dk else "FAIL  ") + ten + (f" -> {chi_tiet}" if not dk else ""))
    if not dk:
        FAILS.append(ten)


kq = lab.du_bao_nam_kiem_tra(2024)
f = lambda x: f"{x:.2f}".replace(".", ",")


def gemini(text):
    return lambda *a, **k: {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def hoi_tren_app(tra_loi_gemini):
    c.goi_gemini = gemini(tra_loi_gemini)
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=120).run()
    at.sidebar.radio(key="trang").set_value("Trợ lý AI").run()
    at.chat_input[0].set_value("2024").run()
    return at


def noi_dung(at):
    exp = [e for e in at.expander if "đã gọi" in e.label]
    code = " ".join(x.value for x in at.code)
    cap = " ".join(x.value for x in at.caption)
    return exp, code, cap


dung = f"Năm 2024 thực tế {f(kq['nang_suat_thuc_te'])} tạ/ha, mô hình dự báo {f(kq['nang_suat_du_bao_mo_hinh'])} tạ/ha."
at = hoi_tren_app(dung)
exp, code, cap = noi_dung(at)
kt("không lỗi khi chat", not at.exception, [e.value for e in at.exception])
kt("có khung 'Hệ thống đã gọi ... hàm'", len(exp) >= 1, [e.label for e in at.expander])
kt("hiển thị tên hàm và tham số", any("du_bao_nam_kiem_tra" in m.value and "nam=2024" in m.value for m in at.markdown))
kt("hiển thị kết quả hàm đưa cho Gemini", "nang_suat_du_bao_mo_hinh" in code and str(kq["nang_suat_du_bao_mo_hinh"]) in code)
kt("ghi rõ câu trả lời do Gemini viết", "do Gemini viết" in cap)

at = hoi_tren_app("Mô hình dự báo năm 2024 là 70,12 tạ/ha.")
exp, code, cap = noi_dung(at)
kt("khi Gemini viết sai số: ghi rõ là văn bản dựng sẵn", "không phải Gemini viết" in cap)
kt("khi Gemini viết sai số: số bịa không hiện ra", not any("70,12" in m.value for m in at.markdown))

print("\nKET QUA:", "TAT CA PASS" if not FAILS else f"{len(FAILS)} LOI")
raise SystemExit(1 if FAILS else 0)
