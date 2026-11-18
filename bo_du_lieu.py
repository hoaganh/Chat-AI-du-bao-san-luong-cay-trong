"""Quan ly cac bo du lieu (cay trong + tinh) dung de du bao.

- Bo mac dinh "lua_an_giang" doc tu lua_an_giang.csv (nguon da kiem chung, khong sua duoc).
- Cac bo khac do nguoi dung them (luu trong co so du lieu). Du lieu PHAI la so lieu that co nguon;
  he thong khong tu sinh so lieu. Moi bo duoc kiem tra: du cot, nam lien tuc, don vi, nguon bat buoc.
"""

import datetime
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

import db

THU_MUC = os.path.dirname(os.path.abspath(__file__))
MAC_DINH = "lua_an_giang"
COT_BAT_BUOC = ["nam", "dien_tich_ha", "san_luong_tan"]
COT_THOI_TIET = ["mua_tong_mm", "nhiet_tb_c", "ngay_nong"]
COT_DAY_DU = ["nam", "dien_tich_ha", "san_luong_tan", "nang_suat_ta_ha"] + COT_THOI_TIET
MIN_NAM = 10                       # de bai: toi thieu 10 nam; it hon bi tu choi khi nhap
NAM_NHO_NHAT = 1990
NGUONG_LECH_NANG_SUAT = 0.02      # nang suat lech > 2% so voi san luong*10/dien tich -> canh bao

_META_MAC_DINH = {
    "ma": MAC_DINH, "cay": "Lúa", "tinh": "An Giang",
    "nguon": "Niên giám Thống kê tỉnh An Giang 2024 (biểu 127-129, trang 366-368); "
             "thời tiết: Open-Meteo Historical Weather API",
    "lat": 10.38, "lon": 105.43, "thang_bat_dau": 5, "thang_ket_thuc": 11, "co_san": True,
}
_cache_mac_dinh = None
_db_san_sang = False


class KhongCoBo(KeyError):
    def __str__(self):
        return self.args[0]


def _san_sang():
    global _db_san_sang
    if not _db_san_sang:
        db.khoi_tao()
        _db_san_sang = True


def _doc_mac_dinh():
    global _cache_mac_dinh
    if _cache_mac_dinh is None:
        d = pd.read_csv(os.path.join(THU_MUC, "data", "lua_an_giang.csv"))
        _cache_mac_dinh = d[COT_DAY_DU].sort_values("nam").reset_index(drop=True)
    return _cache_mac_dinh.copy()


def lay_bo(ma=None):
    """Tra ve (meta, DataFrame cac nam). Nem KhongCoBo neu ma khong ton tai."""
    ma = (ma or MAC_DINH).strip() if isinstance(ma, str) or ma is None else str(ma)
    if ma == MAC_DINH:
        return dict(_META_MAC_DINH), _doc_mac_dinh()
    _san_sang()
    ket_qua = db.doc_bo_du_lieu_db(ma)
    if ket_qua is None:
        co = ", ".join(b["ma"] for b in ds_bo())
        raise KhongCoBo(f"Khong co bo du lieu '{ma}'. Cac bo hien co: {co}.")
    meta, dong = ket_qua
    d = pd.DataFrame(dong, columns=COT_DAY_DU).astype(float)
    d["nam"] = d["nam"].astype(int)
    return {**meta, "co_san": False}, d.sort_values("nam").reset_index(drop=True)


def _tom_tat(meta, d):
    return {
        "ma": meta["ma"], "cay": meta["cay"], "tinh": meta["tinh"], "nguon": meta["nguon"],
        "nam_dau": int(d["nam"].min()), "nam_cuoi": int(d["nam"].max()), "so_nam": int(len(d)),
        "co_thoi_tiet": bool(d[COT_THOI_TIET].notna().all().all()),
        "lat": meta.get("lat"), "lon": meta.get("lon"), "co_san": bool(meta.get("co_san")),
    }


def ds_bo():
    """Danh sach bo du lieu (co san + do nguoi dung them), co tom tat."""
    ket_qua = [_tom_tat(dict(_META_MAC_DINH), _doc_mac_dinh())]
    _san_sang()
    for m in db.ds_bo_du_lieu_db():
        meta, d = lay_bo(m["ma"])
        ket_qua.append(_tom_tat(meta, d))
    return ket_qua


def tao_ma(cay, tinh):
    """'Cà phê' + 'Đắk Lắk' -> 'ca_phe_dak_lak'."""
    def lam_sach(x):
        x = unicodedata.normalize("NFD", str(x).lower().replace("đ", "d"))
        x = "".join(ch for ch in x if unicodedata.category(ch) != "Mn")
        return re.sub(r"[^a-z0-9]+", "_", x).strip("_")
    return f"{lam_sach(cay)}_{lam_sach(tinh)}"[:80]


def mau_csv():
    """Chi co dong tieu de (khong co so lieu mau de tranh nhap nham du lieu gia)."""
    return ",".join(COT_DAY_DU) + "\n"


def kiem_tra_va_chuan_hoa(df):
    """Tra ve (DataFrame sach hoac None, danh sach loi, danh sach canh bao)."""
    loi, canh_bao = [], []
    d = df.copy().reset_index(drop=True)
    d.columns = [str(c).strip().lower() for c in d.columns]
    thieu = [c for c in COT_BAT_BUOC if c not in d.columns]
    if thieu:
        return None, [f"Thiếu cột bắt buộc: {', '.join(thieu)}. Các cột: {', '.join(COT_DAY_DU)} "
                      "(nang_suat_ta_ha và 3 cột thời tiết là tùy chọn)."], []
    d = d[[c for c in COT_DAY_DU if c in d.columns]].copy()
    for c in d.columns:
        goc = d[c]
        so = pd.to_numeric(goc, errors="coerce")
        hong = so.isna() & goc.notna() & (goc.astype(str).str.strip() != "")
        if hong.any():
            dong = [int(i) + 2 for i in d.index[hong]][:5]       # +2: dong 1 la tieu de
            loi.append(f"Cột {c}: dòng {dong} không phải số (dùng dấu chấm làm dấu thập phân, "
                       "không dùng dấu chấm ngăn cách hàng nghìn).")
        d[c] = so
    if loi:
        return None, loi, canh_bao

    # Reject NaN/Inf in every supplied numeric column before range checks or calculations.
    for c in d.columns:
        invalid = d[c].notna() & ~np.isfinite(d[c])
        if invalid.any():
            dong = [int(i) + 2 for i in d.index[invalid]][:5]
            loi.append(f"Cột {c} có giá trị không hữu hạn (NaN/Inf) ở dòng {dong}.")
    if loi:
        return None, loi, canh_bao

    if d[COT_BAT_BUOC].isna().any().any():
        for c in COT_BAT_BUOC:
            if d[c].isna().any():
                loi.append(f"Cột {c} có ô trống ở dòng {[int(i) + 2 for i in d.index[d[c].isna()]][:5]}.")
        return None, loi, canh_bao

    if (d["nam"] % 1 != 0).any():
        loi.append("Cột nam phải là số nguyên.")
    d["nam"] = d["nam"].astype(int)
    nam_hien_tai = datetime.date.today().year
    if d["nam"].duplicated().any():
        loi.append(f"Năm bị trùng: {sorted(d['nam'][d['nam'].duplicated()].unique().tolist())}.")
    if (d["nam"] < NAM_NHO_NHAT).any() or (d["nam"] > nam_hien_tai).any():
        loi.append(f"Năm phải từ {NAM_NHO_NHAT} đến {nam_hien_tai}.")
    if (d["dien_tich_ha"] <= 0).any() or (d["san_luong_tan"] <= 0).any():
        loi.append("dien_tich_ha và san_luong_tan phải lớn hơn 0.")
    if loi:
        return None, loi, canh_bao

    d = d.sort_values("nam").reset_index(drop=True)
    thieu_nam = sorted(set(range(int(d["nam"].min()), int(d["nam"].max()) + 1)) - set(d["nam"]))
    if thieu_nam:
        loi.append(f"Năm không liên tục, thiếu: {thieu_nam}. Hãy bổ sung đủ số liệu các năm này.")
    if len(d) < MIN_NAM:
        loi.append(f"Cần ít nhất {MIN_NAM} năm dữ liệu, hiện có {len(d)}.")
    if loi:
        return None, loi, canh_bao
    if len(d) < 10:
        canh_bao.append(f"Chỉ có {len(d)} năm dữ liệu; đề bài yêu cầu ít nhất 10 năm.")

    tinh_lai = d["san_luong_tan"] * 10 / d["dien_tich_ha"]      # tan * 10 / ha = ta/ha
    if "nang_suat_ta_ha" not in d.columns or d["nang_suat_ta_ha"].isna().all():
        d["nang_suat_ta_ha"] = tinh_lai
        canh_bao.append("Không có cột năng suất; hệ thống tính năng suất = sản lượng × 10 / diện tích.")
    else:
        if d["nang_suat_ta_ha"].isna().any():
            canh_bao.append("Một số năm thiếu năng suất; đã điền bằng sản lượng × 10 / diện tích.")
            d["nang_suat_ta_ha"] = d["nang_suat_ta_ha"].fillna(tinh_lai)
        if (d["nang_suat_ta_ha"] <= 0).any():
            return None, ["nang_suat_ta_ha phải lớn hơn 0."], canh_bao
        lech = ((d["nang_suat_ta_ha"] - tinh_lai).abs() / tinh_lai) > NGUONG_LECH_NANG_SUAT
        if lech.any():
            canh_bao.append(
                f"Năng suất lệch hơn {NGUONG_LECH_NANG_SUAT:.0%} so với sản lượng × 10 / diện tích ở các năm "
                f"{d['nam'][lech].tolist()}. Hãy kiểm tra đơn vị (tấn, ha, tạ/ha); cũng có thể nguồn tính năng suất "
                "trên diện tích thu hoạch. Hệ thống dùng đúng năng suất bạn cung cấp.")

    for c in COT_THOI_TIET:
        if c not in d.columns or d[c].isna().all():
            d[c] = np.nan
        elif d[c].isna().any():
            canh_bao.append(f"Cột {c} thiếu ở một số năm nên không dùng được dự báo theo thời tiết.")
    if d["mua_tong_mm"].notna().any() and (d["mua_tong_mm"].dropna() < 0).any():
        loi.append("mua_tong_mm không được âm.")
    if d["nhiet_tb_c"].notna().any() and not d["nhiet_tb_c"].dropna().between(-10, 50).all():
        loi.append("nhiet_tb_c phải trong khoảng -10 đến 50 °C.")
    if d["ngay_nong"].notna().any() and not d["ngay_nong"].dropna().between(0, 366).all():
        loi.append("ngay_nong phải từ 0 đến 366.")
    if loi:
        return None, loi, canh_bao

    thay_doi = d["nang_suat_ta_ha"].pct_change().abs()
    if (thay_doi > 0.30).any():
        canh_bao.append(f"Năng suất đổi hơn 30% giữa hai năm liên tiếp ở {d['nam'][thay_doi > 0.30].tolist()}; "
                        "hãy kiểm tra có nhập nhầm không.")
    return d[COT_DAY_DU], loi, canh_bao


def thoi_tiet_lich_su(lat, lon, nam_dau, nam_cuoi, thang_bat_dau, thang_ket_thuc, timeout=60):
    """Lay thoi tiet mua vu tung nam tu Open-Meteo (1 lan goi cho ca khoang nam). Tra ve {'du_lieu': {nam: {...}}}."""
    if nam_cuoi >= datetime.date.today().year:
        return {"loi": "Open-Meteo chua co du so lieu cho nam hien tai; hay dung du lieu den nam truoc."}
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}&start_date={nam_dau}-01-01&end_date={nam_cuoi}-12-31"
        "&daily=temperature_2m_max,temperature_2m_mean,precipitation_sum&timezone=Asia%2FBangkok"
    )
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            ngay = pd.DataFrame(json.loads(resp.read())["daily"])
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
        return {"loi": f"Khong lay duoc thoi tiet tu Open-Meteo: {e}"}
    ngay["time"] = pd.to_datetime(ngay["time"])
    ngay["nam"], ngay["thang"] = ngay["time"].dt.year, ngay["time"].dt.month
    mua_vu = ngay[(ngay["thang"] >= thang_bat_dau) & (ngay["thang"] <= thang_ket_thuc)]
    tong = mua_vu.groupby("nam").agg(
        mua=("precipitation_sum", "sum"), nhiet=("temperature_2m_mean", "mean"),
        nong=("temperature_2m_max", lambda s: int((s > 35).sum())))
    return {"du_lieu": {int(n): {"mua_tong_mm": round(float(r.mua), 1), "nhiet_tb_c": round(float(r.nhiet), 2),
                                 "ngay_nong": int(r.nong)} for n, r in tong.iterrows()}}


def them_bo(cay, tinh, nguon, df, lat=None, lon=None, thang_bat_dau=None, thang_ket_thuc=None, tu_lay_thoi_tiet=False):
    """Kiem tra va luu bo du lieu moi. Tra ve {'ma', 'so_nam', 'co_thoi_tiet', 'canh_bao'} hoac {'loi': ...}."""
    cay, tinh, nguon = str(cay or "").strip(), str(tinh or "").strip(), str(nguon or "").strip()
    loi = []
    if not cay:
        loi.append("Chưa nhập tên cây trồng.")
    if not tinh:
        loi.append("Chưa nhập tên tỉnh.")
    if len(nguon) < 10:
        loi.append("Nguồn dữ liệu là bắt buộc (ghi rõ lấy ở đâu: niên giám/ cổng thống kê nào, năm nào).")
    if (lat is None) != (lon is None):
        loi.append("Cần nhập cả vĩ độ và kinh độ, hoặc để trống cả hai.")
    if lat is not None and lon is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
        loi.append("Vĩ độ phải từ -90 đến 90, kinh độ từ -180 đến 180.")
    if thang_bat_dau is not None or thang_ket_thuc is not None:
        if not (thang_bat_dau and thang_ket_thuc and 1 <= thang_bat_dau <= thang_ket_thuc <= 12):
            loi.append("Tháng mùa vụ phải từ 1 đến 12 và tháng bắt đầu ≤ tháng kết thúc (mùa vụ nằm trong cùng năm).")
    if loi:
        return {"loi": "Dữ liệu không hợp lệ: " + " ".join(loi)}
    ma = tao_ma(cay, tinh)
    if not ma:
        return {"loi": "Dữ liệu không hợp lệ: Tên cây/tỉnh không tạo được mã."}
    _san_sang()
    if ma == MAC_DINH or db.doc_bo_du_lieu_db(ma) is not None:
        return {"loi": f"Da co bo du lieu '{ma}'. Hay xoa bo cu truoc khi them lai."}

    d, loi_bang, canh_bao = kiem_tra_va_chuan_hoa(df)
    if loi_bang:
        return {"loi": "Dữ liệu không hợp lệ: " + " ".join(loi_bang), "chi_tiet_loi": loi_bang}

    if tu_lay_thoi_tiet and not d[COT_THOI_TIET].notna().all().all():
        if lat is None or not thang_bat_dau:
            return {"loi": "Dữ liệu không hợp lệ: Muốn tự lấy thời tiết còn thiếu cần nhập vĩ độ, kinh độ và tháng mùa vụ."}
        tt = thoi_tiet_lich_su(lat, lon, int(d["nam"].min()), int(d["nam"].max()), thang_bat_dau, thang_ket_thuc)
        if "loi" in tt:
            return tt
        thieu = [int(n) for n in d["nam"] if int(n) not in tt["du_lieu"]]
        if thieu:
            return {"loi": f"Không lấy đủ thời tiết cho các năm {thieu}."}
        for c in COT_THOI_TIET:
            gia_tri_api = pd.Series([tt["du_lieu"][int(n)][c] for n in d["nam"]], index=d.index)
            d[c] = d[c].where(d[c].notna(), gia_tri_api)
        canh_bao.append(f"Đã giữ nguyên số liệu thời tiết có sẵn và chỉ điền ô trống từ Open-Meteo, "
                        f"mùa vụ tháng {thang_bat_dau}-{thang_ket_thuc}, tọa độ ({lat}, {lon}).")
    elif tu_lay_thoi_tiet:
        canh_bao.append("Các cột thời tiết đã đầy đủ; không gọi Open-Meteo.")

    dong = [{k: (None if pd.isna(v) else (int(v) if k == "nam" else float(v))) for k, v in r.items()}
            for r in d.to_dict("records")]
    meta = {"ma": ma, "cay": cay, "tinh": tinh, "nguon": nguon, "lat": lat, "lon": lon,
            "thang_bat_dau": thang_bat_dau, "thang_ket_thuc": thang_ket_thuc,
            "tao_luc": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    db.them_bo_du_lieu_db(meta, dong)
    return {"ma": ma, "so_nam": len(d), "co_thoi_tiet": bool(d[COT_THOI_TIET].notna().all().all()),
            "canh_bao": canh_bao}


def xoa_bo(ma):
    if ma == MAC_DINH:
        return {"loi": "Khong the xoa bo du lieu co san."}
    _san_sang()
    if not db.xoa_bo_du_lieu_db(ma):
        return {"loi": f"Khong co bo du lieu '{ma}'."}
    return {"da_xoa": ma}
