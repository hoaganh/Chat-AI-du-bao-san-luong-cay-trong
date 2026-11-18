"""Đối chiếu docs/test_cases.csv với số liệu hàm thật (không cần Gemini): file đáp án không được lỗi thời."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ham_xu_ly as hx

LOI = []


def kt(ten, ok, ct=""):
    print(("PASS " if ok else "FAIL ") + ten + ("" if ok else f"  -> {ct}"))
    if not ok:
        LOI.append(ten)


from trinh_bay_tra_loi import vn  # noqa: E402  (cùng định dạng số với câu trả lời của chat)


def main():
    rows = list(csv.DictReader(open(Path(__file__).resolve().parents[1] / "docs" / "test_cases.csv", encoding="utf-8-sig")))
    kt("đủ 16 câu: 10 cơ bản + 6 khó", len(rows) == 16 and sum(r["nhom"] == "co_ban" for r in rows) == 10
       and sum(r["nhom"] == "kho" for r in rows) == 6, len(rows))
    kt("mỗi câu có đáp án chuẩn và tiêu chí đạt", all(r["dap_an_chuan"].strip() and r["tieu_chi_dat"].strip() for r in rows))
    d = {r["id"]: r["dap_an_chuan"] for r in rows}
    p, p20, p15, pk = hx.du_bao(2025), hx.du_bao(2025, -20), hx.du_bao(2025, 15), hx.du_bao(2025, -20, 10)
    ls20, tk, tk5, ss = hx.lich_su(2020, 2020)["du_lieu"][0], hx.thong_ke(2015, 2024), hx.thong_ke(2020, 2024), hx.so_sanh_nam(2019, 2022)
    mong_doi = {
        "TC01": [vn(ls20["nang_suat_ta_ha"])],
        "TC02": [vn(p["nang_suat_du_bao"]), vn(p["khoang_kiem_chung"]["low"]), vn(p["khoang_kiem_chung"]["high"]), vn(p["do_chinh_xac_phan_tram"], 1)],
        "TC03": [vn(p20["nang_suat_du_bao"]), vn(p20["nang_suat_co_so"]), vn(p20["chenh_lech_so_voi_co_so"]), vn(p20["khoang_kiem_chung"]["low"]), vn(p20["khoang_kiem_chung"]["high"])],
        "TC04": [str(tk["nho_nhat"]["nam"]), vn(tk["nho_nhat"]["gia_tri"]), vn(tk["thoi_tiet_nam_nho_nhat"]["mua_tong_mm"], 1),
                 str(tk["thoi_tiet_nam_nho_nhat"]["ngay_nong"])],
        "TC05": [vn(tk5["xu_huong_moi_nam"], 3), vn(tk5["thay_doi_dau_cuoi"])],
        "TC06": [vn(ss["chi_tieu"]["nang_suat"]["nam_a"]), vn(ss["chi_tieu"]["nang_suat"]["nam_b"]), vn(ss["chi_tieu"]["nang_suat"]["chenh_lech"])],
        "TC07": [vn(p["khoang_kiem_chung"]["low"]), vn(p["khoang_kiem_chung"]["high"]), vn(p["do_chinh_xac_phan_tram"], 1)],
        "TC08": [vn(p15["nang_suat_du_bao"]), vn(p15["chenh_lech_so_voi_co_so"])],
        "TC11": [vn(p["nang_suat_du_bao"]), vn(p["do_chinh_xac_phan_tram"], 1), "2024"],
        "TC12": [vn(pk["nang_suat_du_bao"]), vn(pk["san_luong_uoc_tinh_tan"], 0), vn(pk["dien_tich_gia_dinh_ha"], 0)],
        "TC15": [vn(ls20["dien_tich_ha"], 0), vn(ls20["nang_suat_ta_ha"])],
        "TC16": [vn(p["nang_suat_du_bao"]), vn(p["khoang_kiem_chung"]["low"])],
    }
    for ma, cac_so in mong_doi.items():
        thieu = [s for s in cac_so if s not in d[ma]]
        kt(f"{ma}: đáp án chuẩn khớp số hàm thật", not thieu, f"thiếu {thieu} trong: {d[ma]}")
    kt("TC09: 2012 hàm báo lỗi 'Khong co du lieu'", "loi" in hx.lich_su(2012, 2012) and "loi" in hx.du_bao(2012))
    kt("TC13/TC14: năm 2030 bị từ chối, 2025 chưa có số thực tế", "loi" in hx.du_bao(2030) and "loi" in hx.lich_su(2025, 2025))
    print("\nKET QUA:", "TAT CA PASS" if not LOI else f"{len(LOI)} LOI")
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
