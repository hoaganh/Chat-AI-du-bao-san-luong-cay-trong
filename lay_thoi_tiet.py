"""
Lay du lieu thoi tiet An Giang tu Open-Meteo Historical API,
tinh tong mua, nhiet do trung binh, so ngay nong (>35C) theo tung nam.
Mua vu chinh o An Giang thuong roi vao thang 5-11 (vu He Thu + Thu Dong),
co the chinh lai khoang thang cho phu hop vu lua ban chon.
Nguon: https://archive-api.open-meteo.com/v1/archive (mien phi, khong can API key)
"""

import csv
from pathlib import Path
import time
import urllib.request
import json

# Toa do gan Long Xuyen, An Giang (theo ranh gioi cu, truoc sap nhap 7/2025)
LAT = 10.38
LON = 105.43

NAM_BAT_DAU = 2010
NAM_KET_THUC = 2024

# Khoang thang tinh la "mua vu" - chinh lai neu nhom chon vu khac
THANG_BAT_DAU = "05-01"
THANG_KET_THUC = "11-30"


def lay_du_lieu_nam(nam):
    start = f"{nam}-{THANG_BAT_DAU}"
    end = f"{nam}-{THANG_KET_THUC}"
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&start_date={start}&end_date={end}"
        "&daily=temperature_2m_max,temperature_2m_mean,precipitation_sum"
        "&timezone=Asia%2FBangkok"
    )
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())

    daily = data["daily"]
    mua_tong = sum(x for x in daily["precipitation_sum"] if x is not None)
    nhiet_list = [x for x in daily["temperature_2m_mean"] if x is not None]
    nhiet_tb = sum(nhiet_list) / len(nhiet_list) if nhiet_list else None
    ngay_nong = sum(1 for x in daily["temperature_2m_max"] if x is not None and x > 35)

    return round(mua_tong, 1), round(nhiet_tb, 2) if nhiet_tb else None, ngay_nong


def main():
    ket_qua = {}
    for nam in range(NAM_BAT_DAU, NAM_KET_THUC + 1):
        print(f"Dang lay du lieu nam {nam}...")
        try:
            mua, nhiet, ngay_nong = lay_du_lieu_nam(nam)
            ket_qua[nam] = (mua, nhiet, ngay_nong)
            print(f"  -> mua={mua}mm, nhiet_tb={nhiet}C, ngay_nong={ngay_nong}")
        except Exception as e:
            print(f"  Loi nam {nam}: {e}")
            ket_qua[nam] = (None, None, None)
        time.sleep(1)  # tranh goi API qua nhanh

    # Ghi ra file rieng, sau do tu ghep vao lua_an_giang.csv cung cot nam
    duong_dan_csv = Path(__file__).resolve().parent / "data" / "thoi_tiet_an_giang.csv"
    with open(duong_dan_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["nam", "mua_tong_mm", "nhiet_tb_c", "ngay_nong"])
        for nam, (mua, nhiet, ngay_nong) in sorted(ket_qua.items()):
            writer.writerow([nam, mua, nhiet, ngay_nong])

    print(f"\nDa ghi xong file {duong_dan_csv.relative_to(Path(__file__).resolve().parent)}")


if __name__ == "__main__":
    main()
