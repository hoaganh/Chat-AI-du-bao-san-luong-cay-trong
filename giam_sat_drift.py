"""Giám sát độ lệch (drift) của dự báo: ghi dự báo trước, điền năng suất thực tế sau, cảnh báo khi sai số tăng.

Dùng:
  python giam_sat_drift.py ghi-du-bao 2025          # lưu dự báo năm 2025 (và khoảng dự báo) vào nhật ký
  python giam_sat_drift.py them-thuc-te 2025 65.7   # khi có số thực tế cùng địa giới với chuỗi huấn luyện
  python giam_sat_drift.py kiem-tra                 # OK / WATCH / DRIFT / NO_DATA

Lưu ý: chuỗi huấn luyện là An Giang CŨ (đến 2024). Từ 2025 địa giới đã hợp nhất, nên số thực tế sau 2024 chỉ được
điền khi có số cùng phạm vi; nếu không, kết quả drift không có ý nghĩa. Module này không tự lấy số liệu.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

import mo_hinh_du_bao as lab

LOG_PATH = lab.OUTPUT / "giam_sat_du_bao.csv"
COLS = ["nam", "du_bao", "khoang_thap", "khoang_cao", "baseline_nam_truoc", "thuc_te", "sai_so", "ngay_ghi"]


def _doc(log_path: Path | None) -> pd.DataFrame:
    p = Path(log_path) if log_path else LOG_PATH
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame(columns=COLS)


def _ghi(df: pd.DataFrame, log_path: Path | None):
    p = Path(log_path) if log_path else LOG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values("nam").to_csv(p, index=False)


def ghi_du_bao(nam: int, log_path: Path | None = None, **kwargs) -> dict:
    """Lưu dự báo của năm `nam` (ghi đè nếu đã có và chưa có thực tế)."""
    kq = lab.forecast_with_decision(int(nam), **kwargs)
    mo = kq["model_output"]
    itv = mo.get("prediction_interval") or {}
    df = _doc(log_path)
    old = df[df["nam"] == nam]
    if not old.empty and pd.notna(old["thuc_te"].iloc[0]):
        raise ValueError(f"Năm {nam} đã có số thực tế; không ghi đè dự báo đã đối chiếu.")
    row = {"nam": int(nam), "du_bao": mo["predicted_value"], "khoang_thap": itv.get("low"),
           "khoang_cao": itv.get("high"), "baseline_nam_truoc": mo["baseline_last_value"],
           "thuc_te": None, "sai_so": None, "ngay_ghi": time.strftime("%Y-%m-%d")}
    df = pd.concat([df[df["nam"] != nam], pd.DataFrame([row])], ignore_index=True)
    _ghi(df, log_path)
    return row


def them_thuc_te(nam: int, thuc_te: float, log_path: Path | None = None) -> dict:
    df = _doc(log_path)
    m = df["nam"] == nam
    if not m.any():
        raise ValueError(f"Chưa có dự báo cho năm {nam}; chạy ghi-du-bao trước (dự báo phải có TRƯỚC khi biết số thực tế).")
    df.loc[m, "thuc_te"] = float(thuc_te)
    df.loc[m, "sai_so"] = float(df.loc[m, "du_bao"].iloc[0]) - float(thuc_te)
    _ghi(df, log_path)
    return df[m].iloc[0].to_dict()


def danh_gia_drift(log_path: Path | None = None, so_nam_gan: int = 3, mae_tham_chieu: float | None = None) -> dict:
    """Quy tắc (khai báo trước, chỉnh được):
    - mae_tham_chieu = MAE cuốn chiếu 2019–2024 của mô hình đã chọn.
    - DRIFT: MAE gần đây >= 2 x tham chiếu, hoặc >=3 năm liên tiếp lệch cùng chiều và |bias| >= tham chiếu.
    - WATCH: MAE gần đây >= 1,5 x tham chiếu, hoặc >=2 năm lệch cùng chiều và |bias| >= 0,75 x tham chiếu.
    """
    if mae_tham_chieu is None:
        mae_tham_chieu = lab.load_bundle()["prediction_interval"]["reference_mae"]
    df = _doc(log_path)
    done = df.dropna(subset=["thuc_te"]).sort_values("nam")
    if done.empty:
        return {"status": "NO_DATA", "message": "Chưa có năm nào có số thực tế để đối chiếu.",
                "n_years_with_actual": 0, "reference_mae": round(mae_tham_chieu, 3)}
    gan = done.tail(so_nam_gan)
    err = gan["sai_so"].astype(float).to_numpy()
    mae = float(abs(err).mean())
    bias = float(err.mean())
    streak = 1
    for i in range(len(err) - 1, 0, -1):
        if err[i] * err[i - 1] > 0:
            streak += 1
        else:
            break
    ratio = mae / mae_tham_chieu
    if ratio >= 2.0 or (streak >= 3 and abs(bias) >= mae_tham_chieu):
        status = "DRIFT"
    elif ratio >= 1.5 or (streak >= 2 and abs(bias) >= 0.75 * mae_tham_chieu):
        status = "WATCH"
    else:
        status = "OK"
    base_err = (gan["baseline_nam_truoc"].astype(float) - gan["thuc_te"].astype(float)).abs()
    mae_base = float(base_err.mean()) if base_err.notna().all() else None
    outside = int(((gan["thuc_te"] < gan["khoang_thap"]) | (gan["thuc_te"] > gan["khoang_cao"])).sum())
    msg = {
        "OK": "Sai số gần đây trong mức tham chiếu; tiếp tục theo dõi.",
        "WATCH": "Sai số hoặc độ lệch một chiều đang tăng; kiểm tra dữ liệu đầu vào và chuẩn bị huấn luyện lại.",
        "DRIFT": "Mô hình lệch rõ so với thực tế; không dùng để ra quyết định, huấn luyện lại bằng dữ liệu mới "
                 "và kiểm tra địa giới/định nghĩa số liệu.",
    }[status]
    return {
        "status": status, "message": msg, "n_years_with_actual": int(len(done)),
        "years_checked": [int(x) for x in gan["nam"]],
        "recent_mae": round(mae, 3), "reference_mae": round(mae_tham_chieu, 3), "ratio_to_reference": round(ratio, 2),
        "recent_bias": round(bias, 3), "same_sign_streak": int(streak),
        "baseline_recent_mae": None if mae_base is None else round(mae_base, 3),
        "model_worse_than_baseline_recently": None if mae_base is None else bool(mae > mae_base),
        "actual_outside_interval": outside,
        "caveat": "Chuỗi huấn luyện là An Giang cũ; số thực tế sau 2024 phải cùng phạm vi.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="lenh", required=True)
    a = sub.add_parser("ghi-du-bao"); a.add_argument("nam", type=int)
    b = sub.add_parser("them-thuc-te"); b.add_argument("nam", type=int); b.add_argument("thuc_te", type=float)
    sub.add_parser("kiem-tra")
    args = ap.parse_args(argv)
    if args.lenh == "ghi-du-bao":
        out = ghi_du_bao(args.nam)
    elif args.lenh == "them-thuc-te":
        out = them_thuc_te(args.nam, args.thuc_te)
    else:
        out = danh_gia_drift()
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    sys.exit(main())
