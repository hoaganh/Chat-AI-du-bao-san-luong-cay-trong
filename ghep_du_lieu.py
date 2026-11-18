"""Ghep thoi tiet vao du lieu lua theo nam va ghi ra tep moi an toan."""
import csv
import os
import tempfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
FILE_CHINH = DATA_DIR / "lua_an_giang.csv"
FILE_THOI_TIET = DATA_DIR / "thoi_tiet_an_giang.csv"
FILE_KET_QUA = DATA_DIR / "lua_an_giang_ghep.csv"
COT_TT = ("mua_tong_mm", "nhiet_tb_c", "ngay_nong")


def doc_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    du_lieu_chinh = doc_csv(FILE_CHINH)
    du_lieu_thoi_tiet = doc_csv(FILE_THOI_TIET)
    if not du_lieu_chinh or not du_lieu_thoi_tiet:
        raise ValueError("Một trong hai CSV không có dòng dữ liệu.")
    if any("nam" not in r for r in du_lieu_chinh + du_lieu_thoi_tiet):
        raise ValueError("Cả hai CSV phải có cột nam.")
    nam_tt = [r["nam"].strip() for r in du_lieu_thoi_tiet]
    if len(set(nam_tt)) != len(nam_tt):
        raise ValueError("CSV thời tiết có năm bị trùng.")
    for c in COT_TT:
        if any(c not in r for r in du_lieu_thoi_tiet):
            raise ValueError(f"CSV thời tiết thiếu cột {c}.")
    bang_tt = {r["nam"].strip(): r for r in du_lieu_thoi_tiet}
    thieu = []
    for row in du_lieu_chinh:
        nam = row["nam"].strip()
        tt = bang_tt.get(nam)
        if tt is None or any(not str(tt.get(c, "")).strip() for c in COT_TT):
            thieu.append(nam)
        else:
            row.update({c: tt[c] for c in COT_TT})
    if thieu:
        raise ValueError(f"Thiếu thời tiết đầy đủ cho các năm {sorted(set(thieu))}; không ghi tệp kết quả.")
    cols = ["nam", "dien_tich_ha", "san_luong_tan", "nang_suat_ta_ha", *COT_TT]
    thu_muc = os.path.dirname(os.path.abspath(FILE_KET_QUA))
    fd, tam = tempfile.mkstemp(prefix="ghep_", suffix=".csv", dir=thu_muc, text=True)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(du_lieu_chinh)
        os.replace(tam, FILE_KET_QUA)
    except Exception:
        if os.path.exists(tam):
            os.remove(tam)
        raise
    print(f"Đã ghép xong vào {FILE_KET_QUA}; tệp nguồn {FILE_CHINH} được giữ nguyên.")


if __name__ == "__main__":
    main()
