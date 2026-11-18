"""Ghép các năm lúa An Giang trước 2015 (số liệu THẬT bạn điền) vào data/lua_an_giang.csv, có kiểm tra.

Bước 1: mở data/bo_sung_lua_an_giang_2010_2014_MAU.csv, điền 3 cột dien_tich_ha, san_luong_tan, nang_suat_ta_ha
        cho từng năm từ Niên giám Thống kê tỉnh An Giang (đúng đơn vị: ha, tấn, tạ/ha; ranh giới An Giang cũ).
        Cột thời tiết đã điền sẵn từ data/thoi_tiet_an_giang.csv (Open-Meteo).
Bước 2: python them_nam_truoc_2015.py --thu     # chỉ kiểm tra, không ghi
        python them_nam_truoc_2015.py           # ghi thật (tự sao lưu file cũ thành .bak)
Bước 3: python mo_hinh_du_bao.py && python kiem_tra_du_lieu.py
Script KHÔNG tự bịa số: còn ô trống hoặc số không nhất quán thì dừng, không ghi gì.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

GOC = Path(__file__).resolve().parent
DATA = GOC / "data" / "lua_an_giang.csv"
MAU = GOC / "data" / "bo_sung_lua_an_giang_2010_2014_MAU.csv"
COT = ["nam", "dien_tich_ha", "san_luong_tan", "nang_suat_ta_ha", "mua_tong_mm", "nhiet_tb_c", "ngay_nong"]
CAN_DIEN = ["dien_tich_ha", "san_luong_tan", "nang_suat_ta_ha"]
NGUONG_LECH = 0.02   # năng suất lệch > 2% so với sản lượng × 10 ÷ diện tích -> coi là sai đơn vị/nhập liệu


def kiem_tra_mau(mau: pd.DataFrame, chinh: pd.DataFrame) -> list[str]:
    loi = []
    if list(mau.columns) != COT:
        return [f"File mẫu phải có đúng các cột {COT}."]
    trong = [(int(r["nam"]), c) for _, r in mau.iterrows() for c in CAN_DIEN if pd.isna(r[c])]
    if trong:
        loi.append("Còn ô trống cần điền số thật: " + "; ".join(f"năm {n} cột {c}" for n, c in trong))
        return loi
    if mau["nam"].duplicated().any():
        loi.append("Có năm bị trùng trong file mẫu.")
    trung = sorted(set(mau["nam"]) & set(chinh["nam"]))
    if trung:
        loi.append(f"Năm đã có trong lua_an_giang.csv: {trung}.")
    nam = sorted(mau["nam"].astype(int))
    if nam != list(range(nam[0], nam[-1] + 1)):
        loi.append(f"Các năm bổ sung phải liên tục, hiện là {nam}.")
    if nam[-1] != int(chinh["nam"].min()) - 1:
        loi.append(f"Năm bổ sung phải nối liền với năm đầu hiện có ({int(chinh['nam'].min())}); hiện kết thúc ở {nam[-1]}.")
    for c in COT[1:]:
        if (pd.to_numeric(mau[c], errors="coerce").isna()).any():
            loi.append(f"Cột {c} có giá trị không phải số.")
    if loi:
        return loi
    tinh = mau["san_luong_tan"] * 10 / mau["dien_tich_ha"]
    lech = ((mau["nang_suat_ta_ha"] - tinh).abs() / tinh) > NGUONG_LECH
    if lech.any():
        loi.append(f"Năng suất lệch hơn {NGUONG_LECH * 100:.0f}% so với sản lượng × 10 ÷ diện tích ở năm {mau['nam'][lech].tolist()}: "
                   "kiểm tra đơn vị (Niên giám hay ghi nghìn ha, nghìn tấn).")
    if (mau[["dien_tich_ha", "san_luong_tan", "nang_suat_ta_ha"]] <= 0).any().any():
        loi.append("Diện tích, sản lượng, năng suất phải lớn hơn 0.")
    if (mau["dien_tich_ha"] < 1000).any():
        loi.append("Diện tích dưới 1.000 ha: có thể đang dùng đơn vị nghìn ha; hãy đổi sang ha.")
    return loi


def main(argv=None, mau_path=MAU, data_path=DATA):
    ap = argparse.ArgumentParser()
    ap.add_argument("--thu", action="store_true", help="chỉ kiểm tra, không ghi")
    a = ap.parse_args(argv)
    chinh = pd.read_csv(data_path)
    mau = pd.read_csv(mau_path)
    loi = kiem_tra_mau(mau, chinh)
    if loi:
        print("KHÔNG GHÉP. Cần sửa:")
        for x in loi:
            print(" -", x)
        return 1
    gop = pd.concat([mau, chinh], ignore_index=True)[COT].sort_values("nam").reset_index(drop=True)
    print(f"Hợp lệ: thêm {len(mau)} năm ({int(mau['nam'].min())}–{int(mau['nam'].max())}); tổng {len(gop)} năm "
          f"({int(gop['nam'].min())}–{int(gop['nam'].max())}).")
    if a.thu:
        print("Chạy thử: chưa ghi file.")
        return 0
    shutil.copyfile(data_path, str(data_path) + ".bak")
    gop.to_csv(data_path, index=False)
    print(f"Đã ghi {data_path} (bản cũ: {data_path}.bak). Bước tiếp: python mo_hinh_du_bao.py && python kiem_tra_du_lieu.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
