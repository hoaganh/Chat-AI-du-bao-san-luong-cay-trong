"""
Cac ham xu ly du lieu nang suat - KHONG dung AI, chi tinh toan thuan.
Day la cac ham ma LLM se "goi" thong qua function calling.
Moi con so trong cau tra loi phai di qua day, LLM khong duoc tu bia.

Moi ham nhan them tham so bo_du_lieu (ma cay-tinh, vi du 'lua_an_giang'); bo trong = lua An Giang.
"""

import hashlib
import json
import os
import urllib.request
import urllib.error
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

import bo_du_lieu as _bdl
import du_bao_dai_han as _dlh

MAC_DINH = _bdl.MAC_DINH
MIN_NAM_THOI_TIET = 10     # mo hinh theo thoi tiet (4 bien) can it nhat 10 nam, nhu de bai yeu cau

# Bo mac dinh (lua An Giang) - giu cac ten cu de phan con lai cua he thong dung duoc
_meta_mac_dinh, df = _bdl.lay_bo(MAC_DINH)

features = ["nam", "dien_tich_ha", "mua_tong_mm", "nhiet_tb_c", "ngay_nong"]
target = "nang_suat_ta_ha"

NAM_CUOI_CO_DU_LIEU = int(df["nam"].max())
NAM_DAU_CO_DU_LIEU = int(df["nam"].min())


def _lay(bo_du_lieu):
    """Tra ve (meta, DataFrame, None) hoac (None, None, {'loi': ...})."""
    try:
        meta, d = _bdl.lay_bo(bo_du_lieu)
    except _bdl.KhongCoBo as e:
        return None, None, {"loi": str(e)}
    return meta, d, None


def ds_bo_du_lieu():
    """Danh sach cac bo du lieu cay-tinh dang co (de AI biet he thong co du lieu cho cay/tinh nao)."""
    return {"bo_du_lieu": _bdl.ds_bo(), "mac_dinh": MAC_DINH}


def _co_thoi_tiet(d):
    return len(d) >= MIN_NAM_THOI_TIET and bool(d[_bdl.COT_THOI_TIET].notna().all().all())


_cache_mo_hinh = {}
_cache_mae = {}


def _chu_ky(ma, d):
    return (ma, len(d), round(float(d[target].sum()), 6), round(float(d[features].sum().sum()), 6))


def _tao_du_lieu_huan_luyen(d):
    """Dùng đặc trưng năm t để dự báo năng suất năm t+1."""
    s = d.sort_values("nam").reset_index(drop=True).copy()
    s[target] = s[target].shift(-1)
    s["nam"] = s["nam"] + 1
    return s.dropna(subset=features + [target]).reset_index(drop=True)


def _mo_hinh(ma, d):
    """Huấn luyện hồi quy một bước: đặc trưng năm trước -> năng suất năm kế tiếp."""
    kh = _chu_ky(ma, d)
    if kh not in _cache_mo_hinh:
        s = _tao_du_lieu_huan_luyen(d)
        _cache_mo_hinh[kh] = LinearRegression().fit(s[features], s[target])
    return _cache_mo_hinh[kh]


def _danh_gia(d, nam_bat_dau_kiem_tra):
    s = _tao_du_lieu_huan_luyen(d)
    train = s[s["nam"] < nam_bat_dau_kiem_tra]
    test = s[s["nam"] >= nam_bat_dau_kiem_tra]
    if len(train) < 3 or test.empty:
        return {"loi": "Cần ít nhất 3 năm huấn luyện và ít nhất 1 năm kiểm tra theo thời gian."}
    m = LinearRegression().fit(train[features], train[target])
    mae_linear = float(np.mean(np.abs(m.predict(test[features]) - test[target].values)))
    # Walk-forward một năm: baseline chỉ dùng ba năng suất đã biết trước từng năm đích.
    baseline_preds = [float(d.loc[d["nam"] < int(nam), target].tail(3).mean())
                      for nam in test["nam"]]
    mae_baseline = float(np.mean(np.abs(np.asarray(baseline_preds) - test[target].values)))
    return {
        "mae_linear": round(mae_linear, 3),
        "mae_baseline": round(mae_baseline, 3),
        "baseline_du_bao": [round(v, 3) for v in baseline_preds],
        "nam_huan_luyen": [int(train["nam"].min()), int(train["nam"].max())],
        "nam_kiem_tra": [int(test["nam"].min()), int(test["nam"].max())],
    }


def danh_gia_mo_hinh(nam_bat_dau_kiem_tra=None, bo_du_lieu=None):
    """
    Đánh giá dự báo năng suất năm kế tiếp theo thứ tự thời gian; mặc định giữ 3 năm đích cuối làm test.
    Đặc trưng mỗi năm đích chỉ lấy từ năm liền trước; MAE trên 3 năm không phải khoảng tin cậy.
    """
    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    if not _co_thoi_tiet(d):
        return {"loi": f"Bo du lieu '{meta['ma']}' khong du du lieu thoi tiet (can 3 cot thoi tiet day du va it nhat "
                       f"{MIN_NAM_THOI_TIET} nam) de danh gia mo hinh theo thoi tiet."}
    if nam_bat_dau_kiem_tra is None:
        nam_bat_dau_kiem_tra = int(d["nam"].max()) - 2
    kh = (_chu_ky(meta["ma"], d), nam_bat_dau_kiem_tra)
    if kh not in _cache_mae:
        _cache_mae[kh] = _danh_gia(d, nam_bat_dau_kiem_tra)
    return dict(_cache_mae[kh])


MAE_KIEM_TRA = danh_gia_mo_hinh()


def _du_bao_tu_mo_hinh(nam, mua_pct, dt_pct, meta, mae, nam_dau, nam_cuoi):
    """Doi ket qua mo_hinh_du_bao.predict_yield sang dang dict cu cua du_bao. Tra None neu chua co model dự báo."""
    import mo_hinh_du_bao as lab
    if not lab.BUNDLE_PATH.exists():
        return None
    py = lab.predict_yield(nam, mua_pct, dt_pct)
    if "loi" in py:
        return {"loi": py["loi"]}
    ns = py["predicted_yield"]["value"]
    ns_cs = py["baseline_yield_no_scenario"]["value"]
    baseline = py["baseline_mean3"]["value"]
    ghi_chu = f"Du bao tu mo hinh {py['model_id'].split('/')[-1]} (chon theo validation) huan luyen tren du lieu {nam_dau}-{nam_cuoi}."
    if mua_pct != 0:
        ghi_chu += f" Gia dinh mua thay doi {float(mua_pct):+.0f}%."
    if dt_pct != 0:
        ghi_chu += f" Gia dinh dien tich thay doi {float(dt_pct):+.0f}%."
    # Bang chung kiem chung: cac nam test ma mo hinh CHUA thay khi hoc (du bao vs thuc te) + do chinh xac tu sai so %
    kiem_chung = []
    for n in lab.cac_nam_kiem_tra():
        r = lab.du_bao_nam_kiem_tra(n)
        if "loi" in r:
            continue
        lech = r["sai_so_mo_hinh"]
        kiem_chung.append({"nam": n, "thuc_te": r["nang_suat_thuc_te"], "du_bao": r["nang_suat_du_bao_mo_hinh"],
                           "lech": lech, "lech_phan_tram": round(abs(lech) / r["nang_suat_thuc_te"] * 100, 2),
                           "baseline_last_value": r["baseline_last_value"], "lech_baseline": r["sai_so_baseline"]})
    mape = lab.load_bundle()["test_metrics"]["mape_percent"]
    lech_max = max((k["lech"] for k in kiem_chung), key=abs, default=None)
    f_dung = py.get("input_features_used", {})
    return {
        "bo_du_lieu": meta["ma"],
        "cay": meta.get("cay"), "vung": meta.get("tinh"), "nguon_du_lieu": meta.get("nguon"),
        "nam_dau_du_lieu": int(nam_dau), "nam_cuoi_du_lieu": int(nam_cuoi),
        "dau_vao_nam_truoc": {k: f_dung[k] for k in ("dien_tich_ha", "mua_tong_mm", "nhiet_tb_c", "ngay_nong") if k in f_dung},
        "dau_vao_goc": {k: py["input_features_base"][k] for k in ("dien_tich_ha", "mua_tong_mm", "nhiet_tb_c", "ngay_nong") if k in py.get("input_features_base", {})},
        "kich_ban": py["scenario"],
        "kiem_chung": kiem_chung,
        "mape_kiem_tra_phan_tram": round(mape, 2),
        "do_chinh_xac_phan_tram": round(100 - mape, 1),
        "so_nam_lech_duoi_5_phan_tram": sum(1 for k in kiem_chung if k["lech_phan_tram"] < 5),
        "lech_lon_nhat_kiem_chung": lech_max,
        "khoang_kiem_chung": ({"low": round(ns - abs(lech_max), 2), "high": round(ns + abs(lech_max), 2),
                               "co_so": "± sai lệch lớn nhất quan sát được trong các năm kiểm chứng (bảng trên)"}
                              if lech_max is not None else None),
        "mo_hinh_hon_baseline_last_value": bool(py["beats_last_value_baseline"]),
        "baseline_last_value_mae": py["last_value_baseline_test_mae"]["value"],
        "nang_suat_du_bao": ns,
        "nang_suat_co_so": ns_cs,
        "dien_tich_gia_dinh_ha": py["area_assumed"]["value"],
        "san_luong_uoc_tinh_tan": py["production_estimate"]["value"],
        "san_luong_co_so_tan": py["production_no_scenario"]["value"],
        "baseline_tb_3_nam": baseline,
        "chenh_lech_so_voi_baseline": round(ns - baseline, 2),
        "chenh_lech_so_voi_co_so": round(ns - ns_cs, 2),
        "sai_so_uoc_tinh": py["test_mae"]["value"],
        "ghi_chu_sai_so": (
            f"Sai so kiem tra (MAE) cua mo hinh tren cac nam {py['test_mae']['years'][0]}-{py['test_mae']['years'][1]} "
            f"(huan luyen {mae['nam_huan_luyen'][0]}-{mae['nam_huan_luyen'][1]}); baseline rolling MAE {mae['mae_baseline']} ta/ha; "
            f"baseline Last Value MAE {py['last_value_baseline_test_mae']['value']} ta/ha"
            + ("" if py["beats_last_value_baseline"] else " (mo hinh CHUA hon baseline Last Value tren test)")
            + "; khong phai khoang tin cay."
        ),
        "khoang_sai_so_tham_khao": py["interval"],
        "du_lieu_den_nam": nam_cuoi,
        "ghi_chu": ghi_chu,
        "model_id": py["model_id"],
        "data_version": py["data_version"],
        "engine": "mo_hinh_du_bao.predict_yield",
    }


def du_bao(nam, kich_ban_mua_phan_tram=0, kich_ban_dien_tich_phan_tram=0, bo_du_lieu=None):
    """
    Du bao nang suat (ta/ha) cho 1 nam theo thoi tiet, co the kem kich ban thay doi.
    Chi du bao 1 nam ke tiep; muon du bao xa hon dung du_bao_nhieu_nam.

    Args:
        nam: nam can du bao (vd 2025)
        kich_ban_mua_phan_tram: % thay doi luong mua so voi trung binh
            (vd -20 nghia la "neu mua it hon 20%")
        kich_ban_dien_tich_phan_tram: % thay doi dien tich so voi nam gan nhat
        bo_du_lieu: ma bo du lieu cay-tinh (mac dinh lua An Giang)

    Returns:
        dict gom: nang_suat_du_bao, sai_so_uoc_tinh, du_lieu_den_nam, ghi_chu
    """
    try:
        if isinstance(nam, bool) or not np.isfinite(float(nam)) or float(nam) % 1:
            return {"loi": "Năm dự báo phải là số nguyên hữu hạn."}
        nam = int(nam)
        kich_ban_mua_phan_tram = float(kich_ban_mua_phan_tram)
        kich_ban_dien_tich_phan_tram = float(kich_ban_dien_tich_phan_tram)
    except (TypeError, ValueError, OverflowError):
        return {"loi": "Năm và các kịch bản mưa/diện tích phải là số hợp lệ."}
    if not np.isfinite(kich_ban_mua_phan_tram) or not -100 <= kich_ban_mua_phan_tram <= 300:
        return {"loi": "Kịch bản mưa phải là số hữu hạn trong khoảng -100% đến +300%."}
    if not np.isfinite(kich_ban_dien_tich_phan_tram) or not -100 < kich_ban_dien_tich_phan_tram <= 300:
        return {"loi": "Kịch bản diện tích phải là số hữu hạn lớn hơn -100% và không quá +300%."}

    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    nam_dau, nam_cuoi = int(d["nam"].min()), int(d["nam"].max())

    if nam < nam_dau:
        # Nam truoc ca moc du lieu som nhat - KHONG du bao, tra loi ro la khong co du lieu
        return {
            "loi": f"Khong co du lieu cho nam {nam}. "
                   f"Du lieu hien co tu nam {nam_dau} den {nam_cuoi}. "
                   f"Khong the du bao nguoc ve qua khu truoc khi co du lieu."
        }

    if nam <= nam_cuoi:
        # Nam da co du lieu thuc te, tra ve luon, khong can du bao
        hang = d[d["nam"] == nam]
        if len(hang) > 0:
            return {
                "nang_suat_du_bao": float(hang["nang_suat_ta_ha"].iloc[0]),
                "sai_so_uoc_tinh": 0.0,
                "du_lieu_den_nam": nam_cuoi,
                "ghi_chu": f"Nam {nam} da co so lieu thuc te, khong phai du bao.",
            }

    if nam > nam_cuoi + 1:
        # Mo hinh theo thoi tiet lay dieu kien nam gan nhat lam diem xuat phat nen chi du bao 1 nam tiep theo
        # (cac nam xa hon se cho cung 1 con so). Muon du bao xa hon: du_bao_nhieu_nam (xu huong).
        return {
            "loi": f"Mo hinh chi du bao duoc 1 nam tiep theo ({nam_cuoi + 1}). "
                   f"Khong du bao cho nam {nam}. Nam xa hon chi duoc tra loi bang ngoai suy xu huong rieng (khong phai du bao cua mo hinh nay)."
        }

    mae = danh_gia_mo_hinh(bo_du_lieu=meta["ma"])
    if "loi" in mae:
        return {"loi": mae["loi"] + " Bo du lieu nay chi xem lich su/xu huong, khong du bao theo thoi tiet."}

    # NGUON DU BAO DUY NHAT cho bo mac dinh: mo_hinh_du_bao.predict_yield (cung engine voi trang Mo hinh AI va API).
    # Chat, trang Du bao va API vi vay luon ra cung mot con so/model_id/data_version.
    if meta["ma"] == MAC_DINH:
        kq_lab = _du_bao_tu_mo_hinh(nam, kich_ban_mua_phan_tram, kich_ban_dien_tich_phan_tram, meta, mae, nam_dau, nam_cuoi)
        if kq_lab is not None:
            return kq_lab

    mo_hinh = _mo_hinh(meta["ma"], d)

    # Dùng đặc trưng năm cuối làm cơ sở cho năm dự báo; không dùng thời tiết thực tế tương lai.
    hang_gan_nhat = d.iloc[-1]
    dien_tich = hang_gan_nhat["dien_tich_ha"] * (1 + kich_ban_dien_tich_phan_tram / 100)
    mua = hang_gan_nhat["mua_tong_mm"] * (1 + kich_ban_mua_phan_tram / 100)
    nhiet = hang_gan_nhat["nhiet_tb_c"]
    ngay_nong = hang_gan_nhat["ngay_nong"]

    X_moi = pd.DataFrame([[nam, dien_tich, mua, nhiet, ngay_nong]], columns=features)
    du_bao_gia_tri = float(mo_hinh.predict(X_moi)[0])

    # Muc co so = cung nam do nhung KHONG kich ban; tinh o day de AI khong nham muc co so voi muc kich ban
    X_co_so = pd.DataFrame(
        [[nam, hang_gan_nhat["dien_tich_ha"], hang_gan_nhat["mua_tong_mm"], nhiet, ngay_nong]], columns=features
    )
    co_so = float(mo_hinh.predict(X_co_so)[0])

    ghi_chu = (
        f"Bo du lieu phu - hoi quy tuyen tinh tham khao (khong qua pipeline mo_hinh_du_bao), huan luyen tren du lieu {nam_dau}-{nam_cuoi}."
    )
    if kich_ban_mua_phan_tram != 0:
        ghi_chu += f" Gia dinh mua thay doi {kich_ban_mua_phan_tram:+.0f}%."
    if kich_ban_dien_tich_phan_tram != 0:
        ghi_chu += f" Gia dinh dien tich thay doi {kich_ban_dien_tich_phan_tram:+.0f}%."

    ns = round(du_bao_gia_tri, 2)
    ns_co_so = round(co_so, 2)
    dien_tich_co_so = float(hang_gan_nhat["dien_tich_ha"])
    baseline = round(float(d.tail(3)[target].mean()), 2)

    return {
        "bo_du_lieu": meta["ma"],
        "nang_suat_du_bao": ns,
        "nang_suat_co_so": ns_co_so,
        "dien_tich_gia_dinh_ha": round(float(dien_tich)),
        "san_luong_uoc_tinh_tan": round(ns * float(dien_tich) / 10),  # ta/ha * ha / 10 = tan
        "san_luong_co_so_tan": round(ns_co_so * dien_tich_co_so / 10),
        "baseline_tb_3_nam": baseline,
        "chenh_lech_so_voi_baseline": round(ns - baseline, 2),
        "chenh_lech_so_voi_co_so": round(ns - ns_co_so, 2),
        "sai_so_uoc_tinh": mae["mae_linear"],
        "ghi_chu_sai_so": (
            f"Sai so kiem tra (MAE) cua mo hinh tren cac nam {mae['nam_kiem_tra'][0]}-"
            f"{mae['nam_kiem_tra'][1]} (huan luyen {mae['nam_huan_luyen'][0]}-"
            f"{mae['nam_huan_luyen'][1]}); baseline rolling MAE {mae['mae_baseline']} ta/ha; "
            f"khong phai khoang tin cay."
        ),
        "du_lieu_den_nam": nam_cuoi,
        "ghi_chu": ghi_chu,
        "model_id": "LinearRegression[in-memory, bo du lieu phu]",
        "data_version": f"{meta['ma']}@sha256:" + hashlib.sha256(d.to_csv(index=False).encode("utf-8")).hexdigest()[:12],
        "engine": "ham_xu_ly.hoi_quy_tuyen_tinh_tham_khao (khong qua pipeline mo_hinh_du_bao)",
    }


def du_bao_nhieu_nam(so_nam=5, dien_tich_phan_tram=0, do_tin_cay=0.8, bo_du_lieu=None):
    """
    Du bao nang suat va san luong cho NHIEU nam tiep theo (toi da 10) theo xu huong tuyen tinh lich su,
    kem khoang du bao, moc phang TB 3 nam, ket qua kiem tra cuon chieu va canh bao do tin cay.
    Khong dung thoi tiet. Hoi ve mua/kich ban thoi tiet thi dung du_bao (1 nam).
    """
    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    kq = _dlh.du_bao_nhieu_nam(d, so_nam, dien_tich_phan_tram, do_tin_cay)
    if "loi" in kq:
        return kq
    return {"bo_du_lieu": meta["ma"], "cay": meta["cay"], "tinh": meta["tinh"], "nguon": meta["nguon"], **kq}


def giai_thich(nam, bo_du_lieu=None):
    """
    Giai thich cac yeu to anh huong nang suat nam do (chi nam co du lieu thuc).

    Returns:
        dict gom du lieu nam do + so sanh voi nam truoc
    """
    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    hang = d[d["nam"] == nam]
    if len(hang) == 0:
        return {
            "loi": f"Khong co du lieu cho nam {nam}. "
                   f"Du lieu hien co: {int(d['nam'].min())}-{int(d['nam'].max())}."
        }

    h = hang.iloc[0]
    ket_qua = {
        "nam": int(h["nam"]),
        "nang_suat_ta_ha": float(h["nang_suat_ta_ha"]),
        "dien_tich_ha": float(h["dien_tich_ha"]),
    }
    # Cac chi tieu thoi tiet chi co khi bo du lieu co cot do
    if pd.notna(h["mua_tong_mm"]):
        ket_qua["mua_tong_mm"] = float(h["mua_tong_mm"])
    if pd.notna(h["nhiet_tb_c"]):
        ket_qua["nhiet_tb_c"] = float(h["nhiet_tb_c"])
    if pd.notna(h["ngay_nong"]):
        ket_qua["ngay_nong"] = int(h["ngay_nong"])

    # So sanh voi nam truoc neu co
    nam_truoc = d[d["nam"] == nam - 1]
    if len(nam_truoc) > 0:
        t = nam_truoc.iloc[0]
        so_voi = {"chenh_lech_nang_suat": round(float(h["nang_suat_ta_ha"] - t["nang_suat_ta_ha"]), 2)}
        if pd.notna(h["mua_tong_mm"]) and pd.notna(t["mua_tong_mm"]):
            so_voi["chenh_lech_mua_mm"] = round(float(h["mua_tong_mm"] - t["mua_tong_mm"]), 1)
        if pd.notna(h["nhiet_tb_c"]) and pd.notna(t["nhiet_tb_c"]):
            so_voi["chenh_lech_nhiet_c"] = round(float(h["nhiet_tb_c"] - t["nhiet_tb_c"]), 2)
        ket_qua["so_voi_nam_truoc"] = so_voi

    return ket_qua


def _nam_thieu(d, tu_nam, den_nam):
    """Cac nam nguoi dung hoi nhung bo du lieu KHONG co (de bao ro, khong cat khoang am tham)."""
    try:
        a, b = int(tu_nam), int(den_nam)
    except (TypeError, ValueError):
        return []
    if b < a or b - a > 80:
        return []
    co = {int(x) for x in d["nam"]}
    return [y for y in range(a, b + 1) if y not in co]


def _gop_nam(nam):
    """[2012, 2013, 2014, 2018] -> '2012-2014, 2018'."""
    kq, i = [], 0
    while i < len(nam):
        j = i
        while j + 1 < len(nam) and nam[j + 1] == nam[j] + 1:
            j += 1
        kq.append(str(nam[i]) if i == j else f"{nam[i]}-{nam[j]}")
        i = j + 1
    return ", ".join(kq)


def _them_luu_y_thieu(ket_qua, d, tu_nam, den_nam):
    th = _nam_thieu(d, tu_nam, den_nam)
    if th:
        ket_qua["thieu_nam"] = th
        ket_qua["luu_y_thieu_nam"] = (f"Khong co du lieu cac nam {_gop_nam(th)}; du lieu hien co "
                                      f"{int(d['nam'].min())}-{int(d['nam'].max())}. Ket qua chi tinh tren cac nam co so lieu.")
    return ket_qua


def lich_su(tu_nam, den_nam, bo_du_lieu=None):
    """
    Tra ve du lieu lich su trong khoang nam, va tinh xu huong (tang/giam).

    Returns:
        dict gom danh sach du lieu + xu huong tinh bang hoi quy don gian
    """
    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    doan = d[(d["nam"] >= tu_nam) & (d["nam"] <= den_nam)].copy()
    if len(doan) == 0:
        return {
            "loi": f"Khong co du lieu trong khoang {tu_nam}-{den_nam}. "
                   f"Du lieu hien co: {int(d['nam'].min())}-{int(d['nam'].max())}."
        }

    danh_sach = doan[["nam", "nang_suat_ta_ha", "dien_tich_ha", "san_luong_tan"]].to_dict("records")

    # Tinh xu huong bang hoi quy tuyen tinh don gian: nang_suat ~ nam
    xu_huong = None
    if len(doan) >= 2:
        X = doan[["nam"]]
        y = doan["nang_suat_ta_ha"]
        mo_hinh_xu_huong = LinearRegression().fit(X, y)
        do_doc = mo_hinh_xu_huong.coef_[0]  # ta/ha moi nam
        if do_doc > 0.1:
            xu_huong = f"TANG trung binh {do_doc:.2f} ta/ha moi nam"
        elif do_doc < -0.1:
            xu_huong = f"GIAM trung binh {abs(do_doc):.2f} ta/ha moi nam"
        else:
            xu_huong = "Khong ro xu huong tang hay giam (gan nhu khong doi)"

    ket_qua = {
        "du_lieu": danh_sach,
        "xu_huong_nang_suat": xu_huong,
    }
    if len(doan) >= 2:
        # so lieu xu huong dang so (de Gemini nen cau tra loi bang so do HAM tinh, khong tu cong tru)
        ket_qua["so_nam"] = int(len(doan))
        ket_qua["xu_huong_moi_nam"] = round(float(do_doc), 3)
        ket_qua["thay_doi_dau_cuoi_nang_suat"] = round(float(doan["nang_suat_ta_ha"].iloc[-1] - doan["nang_suat_ta_ha"].iloc[0]), 2)
    return _them_luu_y_thieu(ket_qua, d, tu_nam, den_nam)



# Toa do Long Xuyen, An Giang (ranh gioi cu) - dung chung voi lay_thoi_tiet.py
LAT = 10.38
LON = 105.43


# Cac chi tieu co trong du lieu: ten ngan -> (cot trong CSV, don vi)
CHI_TIEU = {
    "nang_suat": ("nang_suat_ta_ha", "ta/ha"),
    "dien_tich": ("dien_tich_ha", "ha"),
    "san_luong": ("san_luong_tan", "tan"),
    "mua": ("mua_tong_mm", "mm"),
    "nhiet_do": ("nhiet_tb_c", "do C"),
    "ngay_nong": ("ngay_nong", "ngay"),
}


def _chi_tieu_hop_le(ten):
    ten = str(ten or "").strip().lower()
    if ten not in CHI_TIEU:
        return None, {"loi": f"Chi tieu '{ten}' khong co. Cac chi tieu hop le: {', '.join(CHI_TIEU)}."}
    return CHI_TIEU[ten], None


def so_sanh_nam(nam_a, nam_b, bo_du_lieu=None):
    """So sanh moi chi tieu giua 2 nam co du lieu. chenh_lech = gia tri nam_b - gia tri nam_a."""
    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    try:
        nam_a, nam_b = int(nam_a), int(nam_b)
    except (TypeError, ValueError):
        return {"loi": "nam_a va nam_b phai la so nam."}
    hang_a, hang_b = d[d["nam"] == nam_a], d[d["nam"] == nam_b]
    thieu = [n for n, h in ((nam_a, hang_a), (nam_b, hang_b)) if h.empty]
    if thieu:
        return {"loi": f"Khong co du lieu cho nam {', '.join(map(str, thieu))}. "
                       f"Du lieu hien co tu nam {int(d['nam'].min())} den {int(d['nam'].max())}."}
    ra, rb = hang_a.iloc[0], hang_b.iloc[0]
    ket_qua = {}
    for ten, (cot, don_vi) in CHI_TIEU.items():
        va, vb = float(ra[cot]), float(rb[cot])
        if np.isnan(va) or np.isnan(vb):      # chi tieu thoi tiet co the vang o bo du lieu nay
            continue
        ket_qua[ten] = {
            "don_vi": don_vi, "nam_a": va, "nam_b": vb,
            "chenh_lech": round(vb - va, 2),
            "phan_tram_thay_doi": round((vb - va) / va * 100, 2) if va else None,
        }
    return {"nam_a": nam_a, "nam_b": nam_b, "cach_tinh": "chenh_lech = nam_b - nam_a", "chi_tieu": ket_qua}


def thong_ke(tu_nam, den_nam, chi_tieu="nang_suat", bo_du_lieu=None):
    """Trung binh, nho nhat/lon nhat (kem nam), do lech chuan, xu huong moi nam cua 1 chi tieu trong khoang nam."""
    cot_don_vi, loi = _chi_tieu_hop_le(chi_tieu)
    if loi:
        return loi
    cot, don_vi = cot_don_vi
    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    try:
        tu_nam, den_nam = int(tu_nam), int(den_nam)
    except (TypeError, ValueError):
        return {"loi": "tu_nam va den_nam phai la so nam."}
    nam_dau_bo, nam_cuoi_bo = int(d["nam"].min()), int(d["nam"].max())
    if d[cot].isna().all():
        return {"loi": f"Bo du lieu '{meta['ma']}' khong co chi tieu '{str(chi_tieu).lower()}'."}
    doan = d[(d["nam"] >= tu_nam) & (d["nam"] <= den_nam) & d[cot].notna()]
    if doan.empty:
        return {"loi": f"Khong co du lieu trong khoang {tu_nam}-{den_nam}. "
                       f"Du lieu hien co tu nam {nam_dau_bo} den {nam_cuoi_bo}."}
    gia_tri = doan[cot].astype(float)
    nam = doan["nam"].astype(int)
    ket_qua = {
        "chi_tieu": str(chi_tieu).lower(), "don_vi": don_vi,
        "tu_nam": int(nam.min()), "den_nam": int(nam.max()), "so_nam": int(len(doan)),
        "trung_binh": round(float(gia_tri.mean()), 2),
        "nho_nhat": {"gia_tri": float(gia_tri.min()), "nam": int(nam[gia_tri.idxmin()])},
        "lon_nhat": {"gia_tri": float(gia_tri.max()), "nam": int(nam[gia_tri.idxmax()])},
        "thay_doi_dau_cuoi": round(float(gia_tri.iloc[-1] - gia_tri.iloc[0]), 2),
        "gia_tri_dau": {"nam": int(nam.iloc[0]), "gia_tri": float(gia_tri.iloc[0])},
        "gia_tri_cuoi": {"nam": int(nam.iloc[-1]), "gia_tri": float(gia_tri.iloc[-1])},
    }
    # Thoi tiet CUNG NAM cua nam nho nhat/lon nhat (neu bo du lieu co cot thoi tiet): thong tin di kem cho cau hoi "vi sao"
    tt = {}
    for nhan, nam_can in (("thoi_tiet_nam_nho_nhat", ket_qua["nho_nhat"]["nam"]), ("thoi_tiet_nam_lon_nhat", ket_qua["lon_nhat"]["nam"])):
        h = d[d["nam"] == nam_can].iloc[0]
        cac = {}
        if pd.notna(h.get("mua_tong_mm")):
            cac["mua_tong_mm"] = float(h["mua_tong_mm"])
        if pd.notna(h.get("nhiet_tb_c")):
            cac["nhiet_tb_c"] = float(h["nhiet_tb_c"])
        if pd.notna(h.get("ngay_nong")):
            cac["ngay_nong"] = int(h["ngay_nong"])
        if cac:
            tt[nhan] = {"nam": nam_can, **cac}
    if tt:
        ket_qua.update(tt)
        ket_qua["luu_y_nguyen_nhan"] = ("Thoi tiet cung nam chi la thong tin di kem; chuoi nam ngan khong chung minh "
                                        "thoi tiet la nguyen nhan cua muc thap/cao nhat.")
    if len(doan) >= 2:
        ket_qua["do_lech_chuan"] = round(float(gia_tri.std(ddof=1)), 2)
        ket_qua["xu_huong_moi_nam"] = round(float(np.polyfit(nam.astype(float), gia_tri, 1)[0]), 3)
    if tu_nam < int(nam.min()) or den_nam > int(nam.max()):
        ket_qua["ghi_chu"] = (f"Chi co du lieu tu {int(nam.min())} den {int(nam.max())} "
                              "nen thong ke tren khoang nay.")
    return _them_luu_y_thieu(ket_qua, d, tu_nam, den_nam)


def tuong_quan(chi_tieu_a, chi_tieu_b, bo_du_lieu=None):
    """He so tuong quan Pearson giua 2 chi tieu tren cac nam co du lieu."""
    a, loi = _chi_tieu_hop_le(chi_tieu_a)
    if loi:
        return loi
    b, loi = _chi_tieu_hop_le(chi_tieu_b)
    if loi:
        return loi
    if a[0] == b[0]:
        return {"loi": "Hai chi tieu phai khac nhau."}
    meta, d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    cap = d[[a[0], b[0]]].astype(float).dropna()
    if len(cap) < 3:
        return {"loi": f"Bo du lieu '{meta['ma']}' khong du du lieu cho 2 chi tieu nay "
                       "(can it nhat 3 nam co day du ca hai)."}
    r = cap[a[0]].corr(cap[b[0]])
    if pd.isna(r):
        return {"loi": "Khong tinh duoc tuong quan (du lieu khong doi)."}
    nam_cap = d.loc[cap.index, "nam"]
    return {
        "chi_tieu_a": str(chi_tieu_a).lower(), "chi_tieu_b": str(chi_tieu_b).lower(),
        "he_so_tuong_quan_pearson": round(float(r), 3),
        "so_nam": int(len(cap)), "tu_nam": int(nam_cap.min()), "den_nam": int(nam_cap.max()),
        "luu_y": f"Chi dua tren {len(cap)} nam; tuong quan khong chung minh quan he nhan qua.",
    }


def thoi_tiet_du_bao(so_ngay=7, bo_du_lieu=None):
    """
    Lay du bao thoi tiet THAT cho vai ngay toi tu Open-Meteo Forecast API
    (goi truc tiep luc chat). Day la du bao ngan han, KHONG phai du bao ca mua vu.

    Args:
        so_ngay: so ngay can du bao (1-14), mac dinh 7
        bo_du_lieu: ma bo du lieu; lay thoi tiet tai toa do cua bo do (mac dinh lua An Giang)

    Returns:
        dict gom danh sach tung ngay + tong mua va nhiet do trung binh,
        hoac {"loi": ...} neu khong goi duoc API
    """
    try:
        so_ngay = max(1, min(14, int(so_ngay)))
    except (TypeError, ValueError):
        so_ngay = 7

    meta, _d, loi = _lay(bo_du_lieu)
    if loi:
        return loi
    if meta["ma"] == MAC_DINH:
        lat, lon = LAT, LON
    else:
        lat, lon = meta.get("lat"), meta.get("lon")
        if lat is None or lon is None:
            return {"loi": f"Bo du lieu '{meta['ma']}' khong co toa do de lay thoi tiet."}

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&forecast_days={so_ngay}&timezone=Asia%2FBangkok"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        d = data["daily"]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
        return {"loi": f"Khong lay duoc du bao thoi tiet tu Open-Meteo: {e}"}

    ngay = []
    for i, ten in enumerate(d["time"]):
        ngay.append({
            "ngay": ten,
            "nhiet_cao_c": d["temperature_2m_max"][i],
            "nhiet_thap_c": d["temperature_2m_min"][i],
            "mua_mm": d["precipitation_sum"][i],
        })

    mua = [x["mua_mm"] for x in ngay if x["mua_mm"] is not None]
    cao = [x["nhiet_cao_c"] for x in ngay if x["nhiet_cao_c"] is not None]
    return {
        "nguon": "Open-Meteo Forecast API",
        "so_ngay": len(ngay),
        "tong_mua_mm": round(sum(mua), 1),
        "nhiet_cao_trung_binh_c": round(sum(cao) / len(cao), 1) if cao else None,
        "so_ngay_nong_tren_35c": sum(1 for x in cao if x > 35),
        "chi_tiet": ngay,
        "ghi_chu": "Du bao ngan han, khong dung de suy ra nang suat ca mua vu.",
    }


# ===== Test nhanh cac ham khi chay truc tiep file nay =====
if __name__ == "__main__":
    print("Test du_bao(2025):")
    print(du_bao(2025))
    print()

    print("Test du_bao(2025, kich_ban_mua_phan_tram=-20):")
    print(du_bao(2025, kich_ban_mua_phan_tram=-20))
    print()

    print("Test giai_thich(2022):")
    print(giai_thich(2022))
    print()

    print("Test lich_su(2020, 2024):")
    print(lich_su(2020, 2024))
    print()

    print("Test thoi_tiet_du_bao(3):")
    print(thoi_tiet_du_bao(3))
    print()

    print("Test gia tri ngoai du lieu - giai_thich(2030):")
    print(giai_thich(2030))

