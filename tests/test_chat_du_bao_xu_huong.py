"""Hồi quy: câu hỏi dự báo xu hướng năm tương lai phải trả lời được (từng bị thiếu hàm sau khi dọn code)."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["AGFARM_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")

import chat_logic as c

FAILS = []


def kt(ten, dk):
    print(("PASS  " if dk else "FAIL  ") + ten)
    if not dk:
        FAILS.append(ten)


def khong_goi_gemini(*a, **k):
    raise AssertionError("câu hỏi dự báo xu hướng được trả lời cố định, không gọi Gemini")


kt("nhận diện 'dự báo năng suất năm 2027'", c._nam_du_bao_xu_huong("Dự báo năng suất lúa năm 2027") == 2027)
c.goi_gemini = khong_goi_gemini
nk = []
tl, _ = c.hoi("Dự báo năng suất lúa năm 2027 là bao nhiêu?", in_nhat_ky=False, nhat_ky=nk)
kt("hỏi dự báo 2027 trả lời được, có đơn vị và năm", "2027" in tl and "tạ/ha" in tl)
kt("nêu rõ là ngoại suy tham khảo, không phải dự báo chính thức", "không phải dự báo chính thức" in tl)
kt("ghi nhật ký hàm du_bao_nhieu_nam", nk and nk[0]["ham"] == "du_bao_nhieu_nam")
tl2, _ = c.hoi("Dự báo năng suất lúa năm 2030", in_nhat_ky=False)
kt("năm xa hơn vẫn trả lời, không lỗi", "2030" in tl2)

print("\nKET QUA:", "TAT CA PASS" if not FAILS else f"{len(FAILS)} LOI")
raise SystemExit(1 if FAILS else 0)
