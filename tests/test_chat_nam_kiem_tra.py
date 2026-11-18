"""Hỏi về năm kiểm tra 2022-2024: hàm lấy kết quả train/test của mô hình AI -> đưa cho Gemini viết câu trả lời.
Nếu Gemini lỗi, trả rỗng hoặc viết số không khớp kết quả hàm thì dùng văn bản dự phòng dựng từ chính kết quả đó."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["AGFARM_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")

import chat_logic as c
import mo_hinh_du_bao as lab

FAILS = []


def kt(ten, dk):
    print(("PASS  " if dk else "FAIL  ") + ten)
    if not dk:
        FAILS.append(ten)


def phan_hoi_text(t):
    return {"candidates": [{"content": {"parts": [{"text": t}]}}]}


def chay(gemini_gia_lap, cau_hoi="2024"):
    """Chạy hoi() với Gemini giả; trả (câu trả lời, các lịch sử đã gửi cho Gemini, nhật ký)."""
    da_gui, nk = [], []

    def gia(lich_su, *a, **k):
        da_gui.append([dict(x) for x in lich_su])
        return gemini_gia_lap(len(da_gui))
    c.goi_gemini = gia
    tl, ls = c.hoi(cau_hoi, in_nhat_ky=False, nhat_ky=nk)
    return tl, da_gui, nk, ls


# ---- nhận diện câu hỏi
kt("'2024' trơn -> năm kiểm tra", c._nam_kiem_tra("2024") == 2024)
kt("'Năm 2023 năng suất bao nhiêu?' -> năm kiểm tra", c._nam_kiem_tra("Năm 2023 năng suất bao nhiêu?") == 2023)
kt("'dự đoán 2022' -> năm kiểm tra", c._nam_kiem_tra("mô hình dự đoán năm 2022") == 2022)
kt("năm 2021 -> không phải năm kiểm tra", c._nam_kiem_tra("2021") is None)
kt("hai năm -> không chặn", c._nam_kiem_tra("So sánh năng suất năm 2019 và 2022") is None)
kt("sản lượng năm 2024 -> không chặn", c._nam_kiem_tra("Sản lượng lúa năm 2024 là bao nhiêu tấn?") is None)
kt("mưa năm 2023 -> không chặn", c._nam_kiem_tra("Mưa năm 2023 bao nhiêu?") is None)
kt("vì sao năng suất 2022 thấp -> để LLM giải thích", c._nam_kiem_tra("Vì sao năng suất năm 2022 thấp?") is None)
kt("2025 -> không chặn", c._nam_kiem_tra("2025") is None)

# ---- kịch bản A: Gemini viết đúng theo kết quả hàm
kq = lab.du_bao_nam_kiem_tra(2024)
f = lambda x, d=2: f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
dung = (f"Năm 2024 năng suất thực tế là {f(kq['nang_suat_thuc_te'])} tạ/ha. Mô hình AI dự báo {f(kq['nang_suat_du_bao_mo_hinh'])} tạ/ha, "
        f"lệch {f(kq['sai_so_mo_hinh'])} tạ/ha so với thực tế; baseline dự báo {f(kq['baseline_last_value'])} tạ/ha. "
        f"MAE mô hình {f(kq['mae_mo_hinh_kiem_tra'], 3)}, baseline {f(kq['mae_baseline_kiem_tra'], 3)} tạ/ha.")
tl, da_gui, nk, ls = chay(lambda n: phan_hoi_text(dung))
kt("A: câu trả lời cuối là do Gemini viết (không phải văn bản dự phòng)", tl == dung)
kt("A: Gemini nhận kết quả hàm du_bao_nam_kiem_tra trước khi trả lời",
   len(da_gui) == 1 and "functionResponse" in str(da_gui[0][-1]) and "du_bao_nam_kiem_tra" in str(da_gui[0][-1]))
res = da_gui[0][-1]["parts"][0]["functionResponse"]["response"]["result"]
kt("A: kết quả gửi cho Gemini có số liệu gốc, đầu vào, công thức, sai số, nguồn",
   all(k in res for k in ("du_lieu_goc", "nam_dau_vao", "cach_tinh", "sai_so_mo_hinh", "mae_mo_hinh_kiem_tra", "nguon_du_lieu")))
kt("A: ghi nhật ký hàm", nk and nk[0]["ham"] == "du_bao_nam_kiem_tra" and nk[0]["tham_so"] == {"nam": 2024})

# ---- kịch bản B: Gemini bịa số -> văn bản dự phòng từ kết quả hàm
tl, *_ = chay(lambda n: phan_hoi_text("Mô hình dự báo năm 2024 là 70,12 tạ/ha."))
kt("B: số bịa bị chặn, thay bằng văn bản dự phòng đúng số", "70,12" not in tl and f(kq["nang_suat_du_bao_mo_hinh"]) in tl)
kt("B: văn bản dự phòng có đủ kết quả gốc, nguồn, công thức", "Niên giám" in tl and "Hằng số" in tl and f(kq["nang_suat_thuc_te"]) in tl)

# ---- kịch bản C, D: Gemini lỗi / trả rỗng
def loi(n):
    raise RuntimeError("mất mạng")
tl, *_ = chay(loi)
kt("C: Gemini lỗi -> vẫn trả lời bằng kết quả mô hình", f(kq["nang_suat_du_bao_mo_hinh"]) in tl)
tl, *_ = chay(lambda n: {"candidates": []})
kt("D: Gemini trả rỗng -> vẫn trả lời bằng kết quả mô hình", f(kq["nang_suat_du_bao_mo_hinh"]) in tl)

# ---- kịch bản E: câu hỏi không phải năm kiểm tra thì không nạp sẵn hàm
tl, da_gui, nk, ls = chay(lambda n: phan_hoi_text("Xin chào."), cau_hoi="Vì sao năng suất năm 2022 thấp?")
kt("E: câu hỏi giải thích không bị nạp sẵn kết quả kiểm tra", "functionResponse" not in str(da_gui[0]))

# ---- văn bản dự phòng tự nó phải qua được bộ kiểm tra số (mọi số đều có trong kết quả hàm)
for nam in (2022, 2023, 2024):
    ket = [{"tham_so": {"nam": nam}, "ket_qua": lab.du_bao_nam_kiem_tra(nam)}]
    kt(f"văn bản dự phòng năm {nam} không chứa số lạ", c._so_chua_xac_nhan(c._tra_loi_nam_kiem_tra(nam), ket) == [])

# ---- nội dung dự phòng khớp forecast_log
kq24 = lab.du_bao_nam_kiem_tra(2024)
tong = kq24["cach_tinh"]["hang_so"] + sum(p["dong_gop"] for p in kq24["cach_tinh"]["thanh_phan"])
kt("công thức cộng lại đúng bằng dự báo trong forecast_log", abs(tong - kq24["nang_suat_du_bao_mo_hinh"]) < 0.01)
kt("năm ngoài tập kiểm tra trả lỗi rõ ràng", "loi" in lab.du_bao_nam_kiem_tra(2019))
kt("chat chỉ khai báo 5 công cụ cốt lõi, khớp bảng hàm; du_bao_nam_kiem_tra chạy qua nhánh rule-based nội bộ",
   sorted(c.CAC_HAM) == ["ds_bo_du_lieu", "du_bao", "lich_su", "so_sanh_nam", "thong_ke"]
   and sorted(t["name"] for t in c.KHAI_BAO_HAM) == sorted(c.CAC_HAM) and "du_bao_nam_kiem_tra" not in c.CAC_HAM)

print("\nKET QUA:", "TAT CA PASS" if not FAILS else f"{len(FAILS)} LOI")
raise SystemExit(1 if FAILS else 0)
