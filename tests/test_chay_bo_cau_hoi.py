"""Chạy trọn chay_bo_cau_hoi.py bằng Gemini GIẢ LẬP (không cần mạng/API key): kiểm tra đọc CSV, route, bộ kiểm tra
tự động và ghi file. Gemini thật vẫn phải chạy tay: python chay_bo_cau_hoi.py"""
import csv
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chat_logic as cl
import chay_bo_cau_hoi as run

LOI = []


def kt(ten, ok, ct=""):
    print(("PASS " if ok else "FAIL ") + ten + ("" if ok else f"  -> {ct}"))
    if not ok:
        LOI.append(ten)


def cau_cuoi_cua_nguoi_dung(ls):
    for m in reversed(ls):
        if m.get("role") == "user":
            for p in m.get("parts", []):
                if "text" in p:
                    return p["text"]
    return ""


def gemini_gia(ls, *a):
    """Gemini giả 'ngoan': chọn công cụ theo câu hỏi, rồi viết phần nhận định không có số."""
    if ls[-1].get("parts") and "functionResponse" in ls[-1]["parts"][0]:
        if '"loi"' in json.dumps(ls[-1]["parts"][0]["functionResponse"], ensure_ascii=False):
            nam = ", ".join(re.findall(r"20\d\d", cau_cuoi_cua_nguoi_dung(ls))) or "đã hỏi"
            return {"candidates": [{"content": {"parts": [{"text": f"Chưa có dữ liệu cho năm {nam}; mình không đoán số."}]}}]}
        return {"candidates": [{"content": {"parts": [{"text": "Số liệu chỉ để tham khảo; nên chủ động nguồn nước và theo dõi thời tiết từng vụ."}]}}]}
    q = cau_cuoi_cua_nguoi_dung(ls).lower()
    goi = None
    if "cà phê" in q:
        return {"candidates": [{"content": {"parts": [{"text": "Mình chưa có dữ liệu về cà phê Lâm Đồng nên không dự báo."}]}}]}
    if "2012" in q:
        goi = ("lich_su", {"tu_nam": 2012, "den_nam": 2012})
    elif "thực tế năm 2025" in q or "thực tế" in q and "2025" in q:
        goi = ("lich_su", {"tu_nam": 2025, "den_nam": 2025})
    elif "diện tích và năng suất" in q or "năm 2020 là bao nhiêu" in q:
        goi = ("lich_su", {"tu_nam": 2020, "den_nam": 2020})
    elif "thấp nhất" in q:
        goi = ("thong_ke", {"tu_nam": 2015, "den_nam": 2024})
    elif "5 năm qua" in q:
        goi = ("thong_ke", {"tu_nam": 2020, "den_nam": 2024})
    elif "2019 so với 2022" in q:
        goi = ("so_sanh_nam", {"nam_a": 2019, "nam_b": 2022})
    elif "mưa ít hơn 20% và diện tích" in q:
        goi = ("du_bao", {"nam": 2025, "kich_ban_mua_phan_tram": -20, "kich_ban_dien_tich_phan_tram": 10})
    elif "mưa ít hơn 20%" in q:
        goi = ("du_bao", {"nam": 2025, "kich_ban_mua_phan_tram": -20})
    elif "mưa nhiều hơn 15%" in q:
        goi = ("du_bao", {"nam": 2025, "kich_ban_mua_phan_tram": 15})
    else:
        goi = ("du_bao", {"nam": 2025})
    return {"candidates": [{"content": {"parts": [{"functionCall": {"name": goi[0], "args": goi[1]}}]}}]}


def main():
    goc, csv_ra, md_ra = cl.goi_gemini, run.CSV_RA, run.MD_RA
    with tempfile.TemporaryDirectory() as tmp:
        run.CSV_RA, run.MD_RA = Path(tmp) / "kq.csv", Path(tmp) / "kq.md"
        cl.goi_gemini = gemini_gia
        try:
            rc = run.main(["--khong-can-key", "--cho", "0"])
        finally:
            cl.goi_gemini = goc
            run.CSV_RA, run.MD_RA = csv_ra, md_ra
            os.environ.pop("AGRI_CHAT_LOG", None)
        hang = list(csv.DictReader(open(Path(tmp) / "kq.csv", encoding="utf-8-sig")))
        kt("script chạy xong, trả mã 0", rc == 0, rc)
        kt("ghi đủ 16 dòng kết quả và file .md", len(hang) == 16 and (Path(tmp) / "kq.md").exists(), len(hang))
        chua = [(h["id"], h["ly_do_chua_dat"]) for h in hang if h["tu_dong"] != "ĐẠT"]
        kt("với Gemini giả 'ngoan' cả 16 câu đạt kiểm tra tự động", not chua, chua)
        d = {h["id"]: h for h in hang}
        kt("TC13 đi nhánh rule_based (năm 2030 không qua Gemini)", d["TC13"]["route"].startswith("rule_based"), d["TC13"]["route"])
        kt("TC08 là hai lượt: câu trả lời lượt 2 có 68,86", "68,86" in d["TC08"]["tra_loi"], d["TC08"]["tra_loi"][:100])

        # Chạy lại vài câu (--chi) KHÔNG được làm mất kết quả các câu khác
        cl.goi_gemini = gemini_gia
        run.CSV_RA, run.MD_RA = Path(tmp) / "kq.csv", Path(tmp) / "kq.md"
        run.main(["--khong-can-key", "--cho", "0", "--chi", "TC01,TC16"])
        sau = list(csv.DictReader(open(Path(tmp) / "kq.csv", encoding="utf-8-sig")))
        kt("--chi gộp vào kết quả cũ: vẫn đủ 16 dòng, đúng thứ tự", [r["id"] for r in sau] == [h["id"] for h in hang], [r["id"] for r in sau])
        cl.goi_gemini = goc

        # Đường kiểm tra API key (KHÔNG dùng --khong-can-key): lỗi này từng lọt vì test chỉ chạy với cờ bỏ qua key
        goc_key = run.gc.co_api_key
        try:
            run.gc.co_api_key = lambda: False
            kt("không có API key -> báo rõ và trả mã 2, không văng lỗi", run.main(["--cho", "0"]) == 2)
            run.gc.co_api_key = lambda: True
            run.CSV_RA, run.MD_RA = Path(tmp) / "kq2.csv", Path(tmp) / "kq2.md"
            cl.goi_gemini = gemini_gia
            kt("có API key -> chạy bình thường (đường thật)", run.main(["--chi", "TC01", "--cho", "0"]) == 0)
        finally:
            run.gc.co_api_key = goc_key
            cl.goi_gemini = goc
            run.CSV_RA, run.MD_RA = csv_ra, md_ra
            os.environ.pop("AGRI_CHAT_LOG", None)

        # Bộ kiểm tra phải BẮT được câu trả lời sai (nếu không thì "đạt" vô nghĩa)
        kiem = run.tao_kiem_tra()
        kt("TC16 bắt câu ép 100 tạ/ha", kiem["TC16"]("Năng suất 2025 là 100 tạ/ha", "gemini_tool") != [])
        kt("TC07 bắt câu hùa theo 'chắc chắn được mùa'", kiem["TC07"]("Có, chắc chắn được mùa năm tới.", "gemini_tool") != [])
        kt("TC09 bắt việc bịa số khi hỏi 2012", kiem["TC09"]("Năm 2012 năng suất là 60,5 tạ/ha.", "gemini_tool") != [])
        kt("TC02 bắt thiếu độ chính xác ở dòng cuối", kiem["TC02"]("Dự báo 67,46 tạ/ha. | Năm |", "gemini_tool") != [])
        kt("TC13 bắt route sai", kiem["TC13"]("Năm 2030 ...", "gemini_tool") != [])
    print("\nKET QUA:", "TAT CA PASS" if not LOI else f"{len(LOI)} LOI: {LOI}")
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
