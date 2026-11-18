"""Chạy 16 câu nghiệm thu (docs/test_cases.csv) qua chat thật và ghi kết quả.

Cần API key Gemini (biến môi trường GEMINI_API_KEY, Streamlit secrets hoặc api_key.txt).
Chạy:   python chay_bo_cau_hoi.py                 # cả 16 câu
        python chay_bo_cau_hoi.py --chi TC04,TC05 # chỉ vài câu
        python chay_bo_cau_hoi.py --cho 3          # nghỉ 3 giây giữa các lượt gọi (khi bị giới hạn tốc độ)
Ghi ra:  outputs/ket_qua_16_cau.csv  và  outputs/ket_qua_16_cau.md

"Kiểm tra tự động" chỉ là bộ lọc theo chuỗi (có đúng số, đúng cấu trúc, không có số cấm). KHÔNG thay người chấm:
hãy đọc câu trả lời và điền cột nguoi_cham trước khi đưa vào báo cáo.
Mỗi câu chạy với lịch sử chat mới (trừ câu 8 là hai lượt liên tiếp) để không bị ảnh hưởng bởi câu trước.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

GOC = Path(__file__).resolve().parent
sys.path.insert(0, str(GOC))
import chat_logic as cl  # noqa: E402
import gemini_client as gc  # noqa: E402
import ham_xu_ly as hx  # noqa: E402
from trinh_bay_tra_loi import vn  # noqa: E402

CSV_VAO = GOC / "docs" / "test_cases.csv"
CSV_RA = GOC / "outputs" / "ket_qua_16_cau.csv"
MD_RA = GOC / "outputs" / "ket_qua_16_cau.md"
TU_CHOI = ("chưa có dữ liệu", "không có dữ liệu", "chưa có số liệu", "không có số liệu", "chưa hỗ trợ")
# Câu hỏi thật gửi cho chat (TC08 là hai lượt liên tiếp)
LUOT = {"TC08": ["Năm tới năng suất khoảng bao nhiêu?", "Còn nếu mưa nhiều hơn 15% thì sao?"]}


def dong_cuoi(s):
    d = [x for x in s.strip().split("\n") if x.strip()]
    return d[-1] if d else ""


def tao_kiem_tra():
    """Trả dict mã câu -> hàm(tra_loi, route) -> danh sách điều kiện còn thiếu. Số kỳ vọng lấy từ hàm thật."""
    p, p20, p15, pk = hx.du_bao(2025), hx.du_bao(2025, -20), hx.du_bao(2025, 15), hx.du_bao(2025, -20, 10)
    tk, ls20 = hx.thong_ke(2015, 2024), hx.lich_su(2020, 2020)["du_lieu"][0]
    ss = hx.so_sanh_nam(2019, 2022)["chi_tieu"]["nang_suat"]
    cx = vn(p["do_chinh_xac_phan_tram"], 1)

    def can(*cum):
        return lambda t, r: [f"thiếu '{c}'" for c in cum if c not in t]

    def can_mot(*cum):
        return lambda t, r: [] if any(c.casefold() in t.casefold() for c in cum) else [f"thiếu một trong {list(cum)}"]

    def cam(*mau):
        return lambda t, r: [f"có mẫu cấm /{m}/" for m in mau if re.search(m, t, re.I)]

    def gop(*fs):
        return lambda t, r: [x for f in fs for x in f(t, r)]

    cuoi_chinh_xac = lambda t, r: [] if dong_cuoi(t).startswith("**Độ chính xác tham khảo") else ["dòng cuối không phải độ chính xác %"]
    nguyen_nhan = cam(r"nguyên nhân (chính )?(là|do)\b", r"\bvì (mưa|nhiệt)")
    return {
        "TC01": gop(can(vn(ls20["nang_suat_ta_ha"])), can_mot("thực tế")),
        "TC02": gop(can(vn(p["nang_suat_du_bao"]), cx), cuoi_chinh_xac, can("| Năm |")),
        "TC03": gop(can(vn(p20["nang_suat_du_bao"]), vn(p20["nang_suat_co_so"])), can_mot("kịch bản", "giả định"), cuoi_chinh_xac),
        "TC04": gop(can(str(tk["nho_nhat"]["nam"]), vn(tk["nho_nhat"]["gia_tri"])), nguyen_nhan),
        "TC05": gop(can_mot("TĂNG"), can_mot(vn(hx.thong_ke(2020, 2024)["xu_huong_moi_nam"], 3), vn(hx.thong_ke(2020, 2024)["xu_huong_moi_nam"], 2))),
        "TC06": gop(can(vn(ss["chenh_lech"]), vn(ss["nam_b"])), nguyen_nhan),
        "TC07": gop(cam(r"chắc chắn (được mùa|sẽ|là|rồi)", r"^\s*có,? chắc chắn"), can_mot("tham khảo"), can(cx)),
        "TC08": can(vn(p15["nang_suat_du_bao"])),
        # được phép nêu số của các năm CÓ dữ liệu (vd 2015); cấm nêu số năng suất gắn với năm 2012
        "TC09": gop(can_mot(*TU_CHOI), cam(r"2012\D{0,60}\d+[,.]\d+\s*tạ/ha")),
        "TC10": can_mot(*TU_CHOI),
        "TC11": gop(can(vn(p["nang_suat_du_bao"]), "Nguồn", "2024"), cuoi_chinh_xac),
        "TC12": can(vn(pk["nang_suat_du_bao"]), vn(pk["san_luong_uoc_tinh_tan"], 0), vn(pk["dien_tich_gia_dinh_ha"], 0)),
        "TC13": lambda t, r: ([] if r.startswith("rule_based") else [f"route={r}, kỳ vọng rule_based"]) + ([] if "2030" in t else ["không nhắc năm 2030"]),
        "TC14": gop(can_mot("chưa có", "không có"), can("2025"), cam(r"thực tế (là|:) ?6\d")),
        "TC15": can(vn(ls20["dien_tich_ha"], 0), vn(ls20["nang_suat_ta_ha"])),
        "TC16": gop(cam(r"100 tạ/ha"), can_mot(vn(p["nang_suat_du_bao"]), "không thể xác nhận", "không thể khẳng định",
                                               "không làm theo", "không có căn cứ", "không thể nói")),
    }


def chay_mot(ma, cau_hoi, log_tam):
    """Chạy các lượt của một câu hỏi với lịch sử mới; trả (câu trả lời lượt cuối, route, công cụ, lỗi)."""
    ls, tra_loi, loi = None, "", None
    cac = LUOT.get(ma, [cau_hoi])
    try:
        for q in cac:
            tra_loi, ls = cl.hoi(q, ls, in_nhat_ky=False)
    except Exception as e:  # noqa: BLE001
        loi = f"{type(e).__name__}: {e}"
    route, ham = "", []
    try:
        dong = [json.loads(x) for x in open(log_tam, encoding="utf-8") if x.strip()]
        route = dong[-1]["route"] if dong else ""
        ham = [h for d in dong[-len(cac):] for h in (d.get("tool_name") or [])]
    except Exception:  # noqa: BLE001
        pass
    return tra_loi or "", route, ham, loi


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chi", default="", help="chỉ chạy các mã câu, vd TC04,TC05")
    ap.add_argument("--cho", type=float, default=1.5, help="giây nghỉ giữa các câu")
    ap.add_argument("--khong-can-key", action="store_true", help="bỏ qua kiểm tra API key (dùng khi thử với Gemini giả)")
    a = ap.parse_args(argv)
    if not a.khong_can_key and not gc.co_api_key():
        print("Chưa có API key Gemini. Đặt GEMINI_API_KEY (xem .env.example) rồi chạy lại.")
        return 2
    cac_ma = {x.strip() for x in a.chi.split(",") if x.strip()}
    hang = list(csv.DictReader(open(CSV_VAO, encoding="utf-8-sig", newline="")))
    kiem = tao_kiem_tra()
    ket_qua = []
    with tempfile.TemporaryDirectory() as tmp:
        log_tam = os.path.join(tmp, "chat_log.jsonl")
        os.environ["AGRI_CHAT_LOG"] = log_tam
        for h in hang:
            ma = h["id"]
            if cac_ma and ma not in cac_ma:
                continue
            tra_loi, route, ham, loi = chay_mot(ma, h["cau_hoi"], log_tam)
            thieu = [f"LỖI khi chạy: {loi}"] if loi else kiem[ma](tra_loi, route)
            if "đã ẩn phần trả lời" in tra_loi:
                thieu.append("câu trả lời bị ẩn vì số chưa xác nhận")
            ket_qua.append({"id": ma, "nhom": h["nhom"], "cau_hoi": h["cau_hoi"], "route": route, "cong_cu": ",".join(ham),
                            "tra_loi": tra_loi, "tu_dong": "ĐẠT" if not thieu else "CHƯA ĐẠT", "ly_do_chua_dat": "; ".join(thieu),
                            "nguoi_cham": "", "ghi_chu": ""})
            print(f"{ma} [{ket_qua[-1]['tu_dong']}] route={route} cong_cu={ham} {('| ' + '; '.join(thieu)) if thieu else ''}")
            time.sleep(max(a.cho, 0))
    os.environ.pop("AGRI_CHAT_LOG", None)
    if cac_ma and CSV_RA.exists():
        # Chạy lại vài câu (--chi): chỉ thay đúng các dòng đó, GIỮ kết quả các câu khác từ lần chạy trước
        cu = {r["id"]: r for r in csv.DictReader(open(CSV_RA, encoding="utf-8-sig", newline=""))}
        cu.update({r["id"]: r for r in ket_qua})
        thu_tu = [h["id"] for h in hang]
        ket_qua = [cu[i] for i in thu_tu if i in cu]
        print(f"(--chi: đã gộp vào kết quả cũ, tổng {len(ket_qua)} câu)")
    CSV_RA.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_RA, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ket_qua[0].keys()))
        w.writeheader(); w.writerows(ket_qua)
    viet_md(ket_qua)
    print(f"\nĐã ghi {CSV_RA} và {MD_RA}")
    return 0


def viet_md(kq):
    dat = [r for r in kq if r["tu_dong"] == "ĐẠT"]
    kho = [r for r in kq if r["nhom"] == "kho"]
    kho_dat = [r for r in kho if r["tu_dong"] == "ĐẠT"]
    L = ["# Kết quả chạy bộ 16 câu nghiệm thu", "",
         f"- Thời điểm chạy: {time.strftime('%d/%m/%Y %H:%M')}; mô hình chat: {cl.MODEL_GEMINI}.",
         f"- Kiểm tra tự động: **{len(dat)}/{len(kq)}** câu đạt; câu khó: **{len(kho_dat)}/{len(kho)}** (đề yêu cầu ≥ 4/6 câu khó).",
         "- Kiểm tra tự động chỉ lọc theo chuỗi; **người chấm phải đọc câu trả lời** trước khi đưa vào báo cáo.", "",
         "| Mã | Nhóm | Câu hỏi | Route | Công cụ | Tự động | Lý do chưa đạt |", "|---|---|---|---|---|---|---|"]
    for r in kq:
        q = r["cau_hoi"].replace("|", "/")
        L.append(f"| {r['id']} | {r['nhom']} | {q} | {r['route']} | {r['cong_cu']} | {r['tu_dong']} | {r['ly_do_chua_dat']} |")
    L += ["", "## Câu trả lời đầy đủ", ""]
    for r in kq:
        L += [f"### {r['id']} ({r['tu_dong']}): {r['cau_hoi']}", "", r["tra_loi"], ""]
    MD_RA.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
