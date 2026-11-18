"""Kiểm tra chất lượng data/lua_an_giang.csv và ghi docs/NHAT_KY_LAM_SACH_DU_LIEU.md.

Chạy:  python kiem_tra_du_lieu.py
Mỗi mục kiểm tra ghi rõ cách kiểm, kết quả thật và kết luận (Đạt / Lưu ý). Không sửa dữ liệu: chỉ báo cáo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

GOC = Path(__file__).resolve().parent
CSV = GOC / "data" / "lua_an_giang.csv"
DAU_RA = GOC / "docs" / "NHAT_KY_LAM_SACH_DU_LIEU.md"
COT = ["nam", "dien_tich_ha", "san_luong_tan", "nang_suat_ta_ha", "mua_tong_mm", "nhiet_tb_c", "ngay_nong"]
# Ngưỡng "hợp lý" cho lúa ở đồng bằng sông Cửu Long: giả định của nhóm để bắt lỗi đơn vị/nhập liệu, không phải chuẩn khoa học
NGUONG = {
    "dien_tich_ha": (300_000, 900_000, "ha"),
    "san_luong_tan": (2_000_000, 6_000_000, "tấn"),
    "nang_suat_ta_ha": (40, 80, "tạ/ha"),
    "mua_tong_mm": (800, 3000, "mm"),
    "nhiet_tb_c": (24, 31, "°C"),
    "ngay_nong": (0, 120, "ngày"),
}


def vn(x, nd=2):
    s = f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s.rstrip("0").rstrip(",") if "," in s else s


def kiem_tra(d: pd.DataFrame):
    """Trả danh sách (muc, cach_kiem, ket_qua, danh_gia, chi_tiet)."""
    R = []
    thieu_cot = [c for c in COT if c not in d.columns]
    R.append(("1. Cấu trúc bảng", "Đủ 7 cột đúng tên; mọi cột là số", f"Thiếu cột: {thieu_cot or 'không'}; kiểu số: "
              f"{all(pd.api.types.is_numeric_dtype(d[c]) for c in COT if c in d.columns)}", "Đạt" if not thieu_cot else "Lưu ý", ""))
    n_nan = int(d[COT].isna().sum().sum())
    R.append(("2. Ô trống", "Đếm ô trống (NaN) trong 7 cột", f"{n_nan} ô trống", "Đạt" if n_nan == 0 else "Lưu ý", ""))
    trung = d["nam"][d["nam"].duplicated()].tolist()
    R.append(("3. Năm trùng", "Kiểm tra cột nam có giá trị lặp", f"Năm trùng: {trung or 'không'}", "Đạt" if not trung else "Lưu ý", ""))
    nam = sorted(d["nam"].astype(int))
    thieu_nam = [y for y in range(nam[0], nam[-1] + 1) if y not in nam]
    R.append(("4. Năm liên tục và đủ 10 năm", "So sánh với dãy năm đầu–năm cuối; đếm số năm (đề yêu cầu ≥ 10)",
              f"{nam[0]}–{nam[-1]}, {len(nam)} năm; năm thiếu: {thieu_nam or 'không'}", "Đạt" if not thieu_nam and len(nam) >= 10 else "Lưu ý", ""))
    # đơn vị: sản lượng (tấn) = năng suất (tạ/ha) × diện tích (ha) / 10
    tinh = d["nang_suat_ta_ha"] * d["dien_tich_ha"] / 10
    lech = (d["san_luong_tan"] - tinh).abs() / d["san_luong_tan"] * 100
    R.append(("5. Nhất quán đơn vị", "Sản lượng (tấn) so với năng suất (tạ/ha) × diện tích (ha) ÷ 10, từng năm",
              f"Lệch lớn nhất {vn(lech.max(), 3)}% (năm {int(d.loc[lech.idxmax(), 'nam'])}); lệch trung bình {vn(lech.mean(), 3)}%",
              "Đạt" if lech.max() < 0.5 else "Lưu ý",
              "Lệch rất nhỏ, phù hợp với việc làm tròn năng suất ở 2 chữ số" if lech.max() < 0.5 else "Cần đối chiếu lại đơn vị"))
    # khoảng hợp lý
    ngoai = []
    for c, (lo, hi, dv) in NGUONG.items():
        bad = d.loc[(d[c] < lo) | (d[c] > hi), ["nam", c]]
        for _, r in bad.iterrows():
            ngoai.append(f"{int(r['nam'])}: {c}={r[c]} ngoài [{lo}; {hi}] {dv}")
    R.append(("6. Khoảng giá trị hợp lý", "Mỗi cột nằm trong ngưỡng hợp lý (ngưỡng do nhóm đặt: " +
              "; ".join(f"{c} {lo:g}–{hi:g}" for c, (lo, hi, _) in NGUONG.items()) + ")",
              f"Ngoài ngưỡng: {ngoai or 'không'}", "Đạt" if not ngoai else "Lưu ý", ""))
    # bất thường: IQR và nhảy năm/năm
    ct = []
    for c in ("nang_suat_ta_ha", "dien_tich_ha", "mua_tong_mm", "nhiet_tb_c"):
        q1, q3 = d[c].quantile([0.25, 0.75]); iqr = q3 - q1
        out = d.loc[(d[c] < q1 - 1.5 * iqr) | (d[c] > q3 + 1.5 * iqr), "nam"].astype(int).tolist()
        if out:
            ct.append(f"{c}: năm {out}")
    R.append(("7. Giá trị bất thường (IQR)", "Quy tắc 1,5×IQR cho năng suất, diện tích, mưa, nhiệt độ",
              f"Ngoại lệ: {ct or 'không'}", "Đạt" if not ct else "Lưu ý", "Ngoại lệ chưa chắc là lỗi: cần đối chiếu nguồn" if ct else ""))
    d2 = d.sort_values("nam")
    nhay = []
    for c in ("nang_suat_ta_ha", "dien_tich_ha"):
        ch = d2[c].pct_change().abs() * 100
        for i in ch[ch > 8].index:
            nhay.append(f"{c} năm {int(d2.loc[i, 'nam'])}: {vn(ch[i], 1)}%")
    R.append(("8. Biến động năm này so với năm trước", "Đổi quá 8% giữa hai năm liền kề (năng suất, diện tích)",
              f"Vượt ngưỡng: {nhay or 'không'}", "Đạt" if not nhay else "Lưu ý", "Cần xem có thật hay lỗi nhập" if nhay else ""))
    # thời tiết
    R.append(("9. Thời tiết có thật cho mọi năm", "Mưa > 0 và nhiệt độ > 0 ở mọi dòng (không điền giả)",
              f"Mưa nhỏ nhất {vn(d['mua_tong_mm'].min(), 1)} mm; nhiệt độ nhỏ nhất {vn(d['nhiet_tb_c'].min())} °C",
              "Đạt" if (d["mua_tong_mm"] > 0).all() and (d["nhiet_tb_c"] > 0).all() else "Lưu ý", ""))
    return R


def viet_nhat_ky(d, R):
    n_ok = sum(1 for r in R if r[3] == "Đạt")
    L = [f"# Nhật ký làm sạch và kiểm tra dữ liệu — Lúa An Giang {int(d['nam'].min())}–{int(d['nam'].max())}", "",
         "File này do `python kiem_tra_du_lieu.py` sinh ra; chạy lại sau khi đổi `data/lua_an_giang.csv`.", "",
         "## 1. Nguồn và cách lấy",
         "| Nhóm số liệu | Nguồn | Cách lấy / định nghĩa |", "|---|---|---|",
         "| Diện tích, sản lượng, năng suất lúa theo năm | Niên giám Thống kê tỉnh An Giang 2024, biểu 127–129, trang 366–368 | Lấy từ bảng niên giám, đơn vị: diện tích ha; sản lượng tấn; năng suất tạ/ha (cách nhập do nhóm ghi lại trong báo cáo) |",
         "| Tổng mưa mùa vụ (`mua_tong_mm`) | Open-Meteo Historical Weather API (`archive-api.open-meteo.com`) | Tổng `precipitation_sum` hằng ngày, 01/05–30/11 mỗi năm, tọa độ 10,38 Bắc, 105,43 Đông (gần Long Xuyên) |",
         "| Nhiệt độ trung bình (`nhiet_tb_c`) | Open-Meteo | Trung bình `temperature_2m_mean` hằng ngày cùng giai đoạn |",
         "| Số ngày nóng (`ngay_nong`) | Open-Meteo | Số ngày có `temperature_2m_max` > 35 °C cùng giai đoạn |", "",
         "## 2. Các bước xử lý (script trong dự án)",
         "1. `lay_thoi_tiet.py`: gọi Open-Meteo từng năm, tính 3 chỉ số thời tiết, ghi `data/thoi_tiet_an_giang.csv`; năm nào lỗi thì để trống, không điền giả.",
         "2. `ghep_du_lieu.py`: ghép thời tiết vào số liệu lúa theo cột `nam`; **dừng và báo lỗi** nếu thiếu năm, thiếu cột hoặc có năm trùng, không ghi file kết quả.",
         "3. `bo_du_lieu.py`: khi nạp dữ liệu, **từ chối** bộ dưới 10 năm hoặc năm không liên tục; **cảnh báo** (không từ chối) khi năng suất lệch hơn 2% so với sản lượng × 10 ÷ diện tích.",
         "4. `kiem_tra_du_lieu.py` (file này): kiểm tra độc lập sau khi ghép, kết quả ở mục 3.", "",
         f"## 3. Kết quả kiểm tra ({n_ok}/{len(R)} mục Đạt)",
         "| Mục | Cách kiểm | Kết quả thật | Đánh giá | Ghi chú |", "|---|---|---|---|---|"]
    for m, c, k, dg, gc in R:
        L.append(f"| {m} | {c} | {k} | **{dg}** | {gc} |")
    L += ["", "## 4. Bảng số liệu sau kiểm tra", "",
          "| Năm | Diện tích (ha) | Sản lượng (tấn) | Năng suất (tạ/ha) | Mưa (mm) | Nhiệt độ TB (°C) | Ngày nóng |", "|---|---|---|---|---|---|---|"]
    for _, r in d.sort_values("nam").iterrows():
        L.append(f"| {int(r['nam'])} | {vn(r['dien_tich_ha'], 0)} | {vn(r['san_luong_tan'], 0)} | {vn(r['nang_suat_ta_ha'])} | "
                 f"{vn(r['mua_tong_mm'], 1)} | {vn(r['nhiet_tb_c'])} | {int(r['ngay_nong'])} |")
    L += ["", "## 5. Giới hạn dữ liệu (cần nêu trong báo cáo)",
          "- **Chưa đối chiếu lại từng số với bản gốc Niên giám**: bản kiểm tra này chỉ bắt lỗi nhất quán, không thay việc đối chiếu nguồn.",
          "- **Lệch kỳ**: thời tiết tính trong 01/05–30/11, còn năng suất niên giám là số cả năm (có thể gồm cả vụ Đông Xuân). Mưa và nhiệt của mùa vụ có thể không phản ánh hết điều kiện cả năm.",
          "- **Địa giới cũ**: số liệu theo ranh giới An Giang trước hợp nhất (2025); không đại diện tỉnh sau hợp nhất.",
          "- **Một điểm quan trắc**: thời tiết lấy tại một tọa độ gần Long Xuyên, không phải trung bình toàn tỉnh.",
          "- **Chỉ 10 năm**: đủ mức tối thiểu của đề nhưng ít cho việc so sánh mô hình; nên bổ sung các năm trước 2015 khi có nguồn."]
    return "\n".join(L) + "\n"


def main():
    d = pd.read_csv(CSV)
    R = kiem_tra(d)
    DAU_RA.write_text(viet_nhat_ky(d, R), encoding="utf-8")
    for m, c, k, dg, gc in R:
        print(f"[{dg:6s}] {m}: {k}")
    print(f"\nĐã ghi {DAU_RA.relative_to(GOC)}")
    return 0 if all(r[3] == "Đạt" for r in R) else 1


if __name__ == "__main__":
    sys.exit(main())
