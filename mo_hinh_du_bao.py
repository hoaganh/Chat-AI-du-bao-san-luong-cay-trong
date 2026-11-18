"""Mô hình dự báo – Forecasting & Predictive Analytics cho năng suất lúa An Giang.

Chạy:  python mo_hinh_du_bao.py
Sinh ra:
  models/forecast_model_bundle_v1.joblib
  outputs/metrics_all_models.csv, model_comparison.csv, tuning_log.csv
  outputs/predictions_test.csv, forecast_log.csv, forecast_metrics.json
  outputs/model_card_lua.md
  figures/forecast_vs_actual.png, forecast_error_over_time.png, model_comparison_mae.png

Quy ước:
  * đặc trưng năm t  ->  năng suất năm t+1 (horizon = 1 năm)
  * chia theo thời gian: train 2016-2019, validation 2020-2021, test 2022-2024
  * bộ dữ liệu chỉ gồm 2015-2024; project không chứa số liệu 2025-2026.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data" / "lua_an_giang.csv"
MODEL_DIR = ROOT / "models"
OUTPUT = ROOT / "outputs"
FIGURES = ROOT / "figures"
BUNDLE_PATH = MODEL_DIR / "forecast_model_bundle_v1.joblib"

TARGET = "nang_suat_ta_ha"
FEATURES = ["nam", "dien_tich_ha", "mua_tong_mm", "nhiet_tb_c", "ngay_nong"]
VALIDATION_START = 2020
TEST_START = 2022
MODEL_VERSION = "lua_forecast_v1"
UNIT = "tạ/ha"

SAFETY_NOTE = (
    "Dự báo chỉ là tín hiệu khuyến nghị, không phải lệnh tự động. "
    "Cần người có chuyên môn xác nhận trước khi thay đổi kế hoạch sản xuất."
)

RECOMMENDATIONS = {
    "NORMAL": "THEO_DOI_BINH_THUONG",
    "WARNING": "THEO_DOI_SAT_VA_CHUAN_BI_PHUONG_AN",
    "HIGH": "RA_SOAT_KY_THUAT_CANH_TAC_VA_THOI_TIET",
    "CRITICAL": "BAO_CAO_CO_QUAN_CHUYEN_MON_VA_LAP_KE_HOACH_UNG_PHO",
}
RECOMMENDATION_TEXT = {
    "NORMAL": "Năng suất dự báo không giảm đáng kể so với năm trước; theo dõi bình thường.",
    "WARNING": "Dự báo giảm nhẹ; theo dõi sát thời tiết/sâu bệnh và chuẩn bị phương án.",
    "HIGH": "Dự báo giảm rõ; rà soát kỹ thuật canh tác, lịch xuống giống và thời tiết.",
    "CRITICAL": "Dự báo giảm mạnh; báo cáo cơ quan chuyên môn và lập kế hoạch ứng phó.",
}


# ---------------------------------------------------------------- dữ liệu
class NamNgoaiPhamVi(ValueError):
    """Năm dự báo nằm ngoài chân trời 1 năm mà mô hình hỗ trợ."""


def data_version() -> str:
    """Định danh phiên bản dữ liệu huấn luyện: tên CSV + 12 ký tự đầu của SHA-256 nội dung."""
    h = hashlib.sha256(INPUT.read_bytes()).hexdigest()
    return f"{INPUT.name}@sha256:{h[:12]}"


def make_supervised(df: pd.DataFrame) -> pd.DataFrame:
    """Cặp (đặc trưng năm t, năng suất năm t+1). Cột 'nam' = năm đích đã biết."""
    s = df.sort_values("nam").reset_index(drop=True)
    d = s.copy()
    d["nam"] = d["nam"] + 1
    d[TARGET] = s[TARGET].shift(-1).to_numpy()
    return d.dropna(subset=FEATURES + [TARGET]).reset_index(drop=True)


def split_time(sup: pd.DataFrame):
    train = sup[sup["nam"] < VALIDATION_START]
    val = sup[(sup["nam"] >= VALIDATION_START) & (sup["nam"] < TEST_START)]
    test = sup[sup["nam"] >= TEST_START]
    train_val = sup[sup["nam"] < TEST_START]
    return train, val, test, train_val


def metrics(y_true, y_pred) -> dict:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    err = p - y
    return {
        "mae": float(mean_absolute_error(y, p)),
        "rmse": float(np.sqrt(mean_squared_error(y, p))),
        "mape_percent": float(np.mean(np.abs(err / y)) * 100),
        "r2": float(r2_score(y, p)) if len(y) > 1 else None,
        "bias_pred_minus_actual": float(np.mean(err)),
    }


def last_value_before(raw: pd.DataFrame, year: int) -> float:
    return float(raw.loc[raw["nam"] < year, TARGET].iloc[-1])


def mean3_before(raw: pd.DataFrame, year: int) -> float:
    return float(raw.loc[raw["nam"] < year, TARGET].tail(3).mean())


# ---------------------------------------------------------------- lớp quyết định
def risk_thresholds_from_history(raw: pd.DataFrame, before_year: int = TEST_START) -> dict:
    """Ngưỡng rủi ro = bội số độ lệch chuẩn của biến động năng suất theo năm (%), chỉ dùng năm < before_year."""
    h = raw[raw["nam"] < before_year].sort_values("nam")[TARGET]
    yoy = (h.pct_change().dropna() * 100).to_numpy()
    sigma = float(np.std(yoy, ddof=1)) if len(yoy) > 1 else 3.0
    return {
        "sigma_yoy_percent": round(sigma, 3),
        "warning_drop_percent": round(0.5 * sigma, 3),
        "high_drop_percent": round(1.0 * sigma, 3),
        "critical_drop_percent": round(1.5 * sigma, 3),
        "rule": "risk theo mức GIẢM dự báo so với năng suất năm liền trước (đơn vị %).",
    }


def risk_from_change(change_percent: float, th: dict) -> str:
    drop = -float(change_percent)
    if drop >= th["critical_drop_percent"]:
        return "CRITICAL"
    if drop >= th["high_drop_percent"]:
        return "HIGH"
    if drop >= th["warning_drop_percent"]:
        return "WARNING"
    return "NORMAL"


def decision_layer(predicted: float, last_observed: float | None, th: dict) -> dict:
    if last_observed is None or last_observed <= 0:
        return {
            "risk_level": "UNKNOWN",
            "recommendation": "CAN_THEM_NANG_SUAT_NAM_TRUOC",
            "reason": "Thiếu năng suất năm liền trước nên không tính được mức thay đổi.",
            "change_vs_last_percent": None,
            "safety_note": SAFETY_NOTE,
        }
    change = (predicted - last_observed) / last_observed * 100
    risk = risk_from_change(change, th)
    return {
        "risk_level": risk,
        "recommendation": RECOMMENDATIONS[risk],
        "recommendation_text": RECOMMENDATION_TEXT[risk],
        "reason": f"Dự báo {predicted:.2f} {UNIT}, thay đổi {change:+.2f}% so với năm trước ({last_observed:.2f}).",
        "change_vs_last_percent": round(change, 3),
        "safety_note": SAFETY_NOTE,
    }


# ---------------------------------------------------------------- huấn luyện
def build_candidates() -> list[tuple[str, str, object]]:
    """(tên, mô tả tham số, model). Mỗi dòng sẽ được ghi vào tuning_log.csv."""
    # Chỉ 2 mô hình + 2 baseline (Last Value, TB 3 năm): chuỗi chỉ có 4 năm train / 2 năm validation nên
    # không tinh chỉnh siêu tham số (tuning trên 2 năm validation chỉ là chọn theo nhiễu).
    return [
        ("LinearRegression", "default", LinearRegression()),
        ("RandomForest", "n_estimators=60, max_depth=3, min_samples_leaf=2",
         RandomForestRegressor(n_estimators=60, max_depth=3, min_samples_leaf=2, random_state=42)),
    ]


# ---------------------------------------------------------------- đánh giá cuốn chiếu & thí nghiệm bỏ thời tiết
def fixed_configs() -> dict:
    """Cấu hình khai báo TRƯỚC (không chọn theo kết quả) để walk-forward không bị rò rỉ từ validation."""
    return {
        "LinearRegression": lambda: LinearRegression(),
        "RandomForest(60,3,2)": lambda: RandomForestRegressor(n_estimators=60, max_depth=3, min_samples_leaf=2, random_state=42),
    }


def walk_forward(raw: pd.DataFrame, make_model, features: list[str], min_train: int = 3) -> pd.DataFrame:
    """Với mỗi năm đích Y: chỉ train trên các dòng có năm đích < Y, rồi dự báo Y (không nhìn tương lai)."""
    sup = make_supervised(raw)
    rows = []
    for _, r in sup.iterrows():
        y = int(r["nam"])
        tr = sup[sup["nam"] < y]
        if len(tr) < min_train:
            continue
        m = make_model().fit(tr[features], tr[TARGET])
        rows.append({"nam": y, "actual": float(r[TARGET]),
                     "pred": float(m.predict(pd.DataFrame([r[features]]))[0]),
                     "last_value": last_value_before(raw, y), "mean3": mean3_before(raw, y), "n_train": len(tr)})
    return pd.DataFrame(rows)


def _summ(actual, pred) -> dict:
    m = metrics(actual, pred)
    return {k: m[k] for k in ("mae", "rmse", "mape_percent", "bias_pred_minus_actual")}


def run_walk_forward_and_ablation(raw: pd.DataFrame) -> dict:
    # 1) walk-forward cho từng họ mô hình + 2 baseline
    pred_tbl = None
    summary_rows = []
    for name, mk in fixed_configs().items():
        wf = walk_forward(raw, mk, FEATURES)
        if pred_tbl is None:
            pred_tbl = wf[["nam", "actual", "last_value", "mean3", "n_train"]].copy()
        pred_tbl[name] = wf["pred"].to_numpy()
    actual = pred_tbl["actual"].to_numpy()
    lv_err = np.abs(pred_tbl["last_value"].to_numpy() - actual)
    for name in list(fixed_configs()) + ["last_value", "mean3"]:
        p = pred_tbl[name].to_numpy()
        row = {"model": {"last_value": "LastValue_baseline", "mean3": "MovingAverage3_baseline"}.get(name, name),
               "n_years": len(actual), **_summ(actual, p),
               "years_better_than_last_value": int(np.sum(np.abs(p - actual) < lv_err)) if name != "last_value" else None}
        summary_rows.append(row)
    summary = pd.DataFrame(summary_rows).sort_values("mae").reset_index(drop=True)
    lv_mae = float(summary.loc[summary["model"] == "LastValue_baseline", "mae"].iloc[0])
    summary["mae_vs_last_value_percent"] = (lv_mae - summary["mae"]) / lv_mae * 100
    pred_tbl.to_csv(OUTPUT / "walk_forward_predictions.csv", index=False)
    summary.to_csv(OUTPUT / "walk_forward_summary.csv", index=False)

    # 2) thí nghiệm bỏ/giữ nhóm đặc trưng (LinearRegression, walk-forward)
    sets = {
        "day_du (nam+dien_tich+3 bien thoi tiet)": FEATURES,
        "khong_thoi_tiet (nam+dien_tich)": ["nam", "dien_tich_ha"],
        "chi_thoi_tiet (mua+nhiet+ngay_nong)": ["mua_tong_mm", "nhiet_tb_c", "ngay_nong"],
        "chi_nam": ["nam"],
        "chi_dien_tich": ["dien_tich_ha"],
    }
    abl_rows = []
    for label, feats in sets.items():
        wf = walk_forward(raw, lambda: LinearRegression(), feats)
        abl_rows.append({"feature_set": label, "n_features": len(feats), "n_years": len(wf),
                         **_summ(wf["actual"], wf["pred"])})
    abl_rows.append({"feature_set": "LastValue_baseline (khong dung dac trung)", "n_features": 0,
                     "n_years": len(pred_tbl), **_summ(actual, pred_tbl["last_value"])})
    ablation = pd.DataFrame(abl_rows).sort_values("mae").reset_index(drop=True)
    ablation.to_csv(OUTPUT / "ablation_features.csv", index=False)

    # 3) hệ số: Ridge trên đặc trưng chuẩn hoá (so sánh được) + hệ số thô của hồi quy tuyến tính, fit trên train+validation
    from sklearn.preprocessing import StandardScaler
    sup = make_supervised(raw)
    tv = sup[sup["nam"] < TEST_START]
    sc = StandardScaler().fit(tv[FEATURES])
    ridge_std = Ridge(alpha=1.0).fit(sc.transform(tv[FEATURES]), tv[TARGET])
    lin_raw = LinearRegression().fit(tv[FEATURES], tv[TARGET])
    coef = pd.DataFrame({"feature": FEATURES, "ridge_std_coef": ridge_std.coef_, "linear_raw_coef": lin_raw.coef_})
    coef["abs_ridge_std"] = coef["ridge_std_coef"].abs()
    coef = coef.sort_values("abs_ridge_std", ascending=False).drop(columns="abs_ridge_std")
    coef.to_csv(OUTPUT / "linear_coefficients.csv", index=False)

    best_abl = ablation.iloc[0]["feature_set"]
    full_mae = float(ablation.loc[ablation["feature_set"].str.startswith("day_du"), "mae"].iloc[0])
    no_w_mae = float(ablation.loc[ablation["feature_set"].str.startswith("khong_thoi_tiet"), "mae"].iloc[0])
    return {
        "walk_forward": {
            "target_years": [int(pred_tbl["nam"].min()), int(pred_tbl["nam"].max())],
            "n_years": int(len(pred_tbl)),
            "rule": "mỗi năm đích chỉ train trên các năm đích trước đó (tối thiểu 3 dòng); cấu hình mô hình khai báo trước",
            "mae_by_model": {r["model"]: round(float(r["mae"]), 3) for _, r in summary.iterrows()},
            "best_model": summary.iloc[0]["model"],
            "best_beats_last_value": bool(summary.iloc[0]["model"] != "LastValue_baseline"),
        },
        "ablation": {
            "best_feature_set": best_abl,
            "mae_full_features": round(full_mae, 3),
            "mae_without_weather": round(no_w_mae, 3),
            "weather_helps": bool(full_mae < no_w_mae),
        },
    }, summary, ablation, pred_tbl


def run_all() -> dict:
    for p in (MODEL_DIR, OUTPUT, FIGURES):
        p.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(INPUT).sort_values("nam").reset_index(drop=True)
    sup = make_supervised(raw)
    train, val, test, train_val = split_time(sup)
    if len(train) < 3 or val.empty or test.empty:
        raise ValueError("Cần ≥3 năm train, có validation và test theo thời gian.")

    # --- 1) tuning: chọn theo validation, ghi tuning_log.csv ---
    tuning_rows = []
    fitted_on_train = {}
    for i, (family, params, model) in enumerate(build_candidates()):
        model.fit(train[FEATURES], train[TARGET])
        tr = metrics(train[TARGET], model.predict(train[FEATURES]))
        va = metrics(val[TARGET], model.predict(val[FEATURES]))
        tuning_rows.append({
            "run_id": i, "model": family, "params": params,
            "train_mae": tr["mae"], "val_mae": va["mae"], "val_rmse": va["rmse"],
            "val_mape_percent": va["mape_percent"], "val_bias": va["bias_pred_minus_actual"],
        })
        fitted_on_train[i] = (family, params)
    tuning = pd.DataFrame(tuning_rows)
    best_idx = int(tuning["val_mae"].idxmin())
    tuning["selected"] = tuning["run_id"] == best_idx
    tuning["overfit_gap_val_minus_train_mae"] = tuning["val_mae"] - tuning["train_mae"]
    tuning.to_csv(OUTPUT / "tuning_log.csv", index=False)

    # --- 2) đánh giá cuối trên test: mỗi cấu hình train lại trên train+validation ---
    y_test = test[TARGET].to_numpy(float)
    test_years = test["nam"].astype(int).to_numpy()
    preds = {
        "LastValue_baseline": np.array([last_value_before(raw, y) for y in test_years]),
        "MovingAverage3_baseline": np.array([mean3_before(raw, y) for y in test_years]),
    }
    for i, (family, params, model) in enumerate(build_candidates()):
        model.fit(train_val[FEATURES], train_val[TARGET])
        name = f"{family}[{params}]"
        preds[name] = model.predict(test[FEATURES])
    selected_name = f"{fitted_on_train[best_idx][0]}[{fitted_on_train[best_idx][1]}]"

    # chỉ giữ cấu hình được chọn của mỗi họ + 2 baseline để bảng gọn, nhưng tuning_log vẫn đủ mọi cấu hình
    best_per_family = tuning.loc[tuning.groupby("model")["val_mae"].idxmin(), "run_id"].tolist()
    keep = {"LastValue_baseline", "MovingAverage3_baseline"} | {
        f"{fitted_on_train[i][0]}[{fitted_on_train[i][1]}]" for i in best_per_family}

    rows = []
    for name, p in preds.items():
        if name not in keep:
            continue
        for split, y_true, y_pred in (("test", y_test, p),):
            rows.append({"model": name, "split": split,
                         "is_baseline": name.endswith("_baseline"),
                         "is_selected": name == selected_name, **metrics(y_true, y_pred)})
    for i in best_per_family:
        fam, par = fitted_on_train[i]
        m = build_candidates()[i][2].fit(train[FEATURES], train[TARGET])
        rows.append({"model": f"{fam}[{par}]", "split": "validation",
                     "is_baseline": False, "is_selected": i == best_idx,
                     **metrics(val[TARGET], m.predict(val[FEATURES]))})
    metrics_all = pd.DataFrame(rows)
    metrics_all.to_csv(OUTPUT / "metrics_all_models.csv", index=False)

    comp = metrics_all[metrics_all["split"] == "test"].sort_values("mae").reset_index(drop=True)
    lv_mae = float(comp.loc[comp["model"] == "LastValue_baseline", "mae"].iloc[0])
    comp["mae_improvement_vs_last_value_percent"] = (lv_mae - comp["mae"]) / lv_mae * 100
    comp["beats_last_value"] = comp["mae"] < lv_mae
    comp.to_csv(OUTPUT / "model_comparison.csv", index=False)

    sel_test = metrics(y_test, preds[selected_name])
    beats = bool(sel_test["mae"] < lv_mae)

    # --- 3) dự báo + lớp quyết định trên test -> forecast_log.csv ---
    th = risk_thresholds_from_history(raw)
    log_rows = []
    for y, actual, pred in zip(test_years, y_test, preds[selected_name]):
        last = last_value_before(raw, int(y))
        d = decision_layer(float(pred), last, th)
        log_rows.append({
            "nam": int(y), "nang_suat_thuc_te_ta_ha": actual,
            "nang_suat_du_bao_mo_hinh_ta_ha": float(pred),
            "sai_so_mo_hinh_ta_ha": float(pred - actual),
            "sai_so_tuyet_doi_ta_ha": float(abs(pred - actual)),
            "nang_suat_nam_truoc_ta_ha": last,
            "baseline_last_value_ta_ha": last,
            "baseline_trung_binh_3_nam_ta_ha": mean3_before(raw, int(y)),
            "thay_doi_du_bao_so_voi_nam_truoc_percent": d["change_vs_last_percent"],
            "risk_level": d["risk_level"], "recommendation": d["recommendation"], "reason": d["reason"],
        })
    forecast_log = pd.DataFrame(log_rows)
    forecast_log.to_csv(OUTPUT / "forecast_log.csv", index=False)
    pred_frame = pd.DataFrame({"nam": test_years, "actual": y_test,
                               **{k: v for k, v in preds.items() if k in keep}})
    pred_frame.to_csv(OUTPUT / "predictions_test.csv", index=False)

    # --- 4b) đánh giá cuốn chiếu + thí nghiệm bỏ thời tiết ---
    extra, wf_summary, ablation, wf_pred = run_walk_forward_and_ablation(raw)

    # --- 5) bundle: huấn luyện lại mô hình đã chọn trên train+validation (test vẫn không dùng để chọn) ---
    medians = raw[FEATURES].median().to_dict()
    # khoảng sai số tham khảo: phần dư cuốn chiếu của cấu hình đại diện cho họ mô hình đã chọn
    fam_key = {"LinearRegression": "LinearRegression", "RandomForest": "RandomForest(60,3,2)"}[
        selected_name.split("[")[0]]
    wf_res = (wf_pred[fam_key] - wf_pred["actual"]).to_numpy()
    interval = {
        "half_width": float(np.max(np.abs(wf_res))), "n_residuals": int(len(wf_res)),
        "reference_mae": float(np.mean(np.abs(wf_res))),
        "method": "khoảng sai số tham khảo: ± độ lệch tuyệt đối lớn nhất của dự báo cuốn chiếu 2019–2024",
        "note": ("Chỉ 6 phần dư, gồm cả các năm test 2022–2024 và tính từ cấu hình đại diện của họ mô hình "
                 "(không nhất thiết đúng cấu hình được chọn). Không có hiệu chỉnh độc lập nên KHÔNG diễn giải "
                 "thành xác suất bao phủ; không gồm rủi ro đổi chiều xu hướng."),
    }

    # sau khi đánh giá xong, huấn luyện lại cấu hình đã chọn trên TOÀN BỘ các năm đã biết để dự báo năm kế tiếp
    # (giống hx.du_bao); số đo sai số vẫn là số đo trên test ở trên.
    deployed_model = build_candidates()[best_idx][2].fit(sup[FEATURES], sup[TARGET])
    bundle = {
        "model": deployed_model, "model_version": MODEL_VERSION, "model_name": selected_name,
        "target": TARGET, "unit": UNIT, "feature_columns": FEATURES,
        "forecast_horizon_years": 1, "feature_medians": medians,
        "risk_thresholds": th,
        "prediction_interval": interval,
        "test_metrics": sel_test,
        "last_value_baseline_test_mae": lv_mae,
        "beats_last_value_baseline_on_test": beats,
        "trained_on_target_years": [int(sup["nam"].min()), int(sup["nam"].max())],
        "created_at_unix": int(time.time()),
        "data_version": data_version(),
        "data_until_year": int(raw["nam"].max()),
    }
    joblib.dump(bundle, BUNDLE_PATH)

    summary = {
        "model_version": MODEL_VERSION,
        "target": TARGET, "unit": UNIT, "feature_columns": FEATURES, "forecast_horizon_years": 1,
        "split": {
            "train_target_years": [int(train["nam"].min()), int(train["nam"].max())],
            "validation_target_years": [int(val["nam"].min()), int(val["nam"].max())],
            "test_target_years": [int(test["nam"].min()), int(test["nam"].max())],
            "train_rows": int(len(train)), "validation_rows": int(len(val)), "test_rows": int(len(test)),
            "policy": "Chia theo thời gian, không random; chọn mô hình/tham số chỉ bằng validation.",
        },
        "selected_model_by_validation_mae": selected_name,
        "selected_model_test_metrics": sel_test,
        "last_value_baseline_test_mae": lv_mae,
        "selected_model_beats_last_value_on_test": beats,
        "risk_thresholds": th,
        "data_policy": "Bộ dữ liệu chỉ gồm 2015-2024; không có số liệu 2025-2026.",
        **extra,
        "caveat": "Chỉ 4 dòng train, 2 validation, 3 test; chỉ số dao động mạnh, không bảo đảm cho tương lai.",
    }
    summary["prediction_interval"] = interval
    (OUTPUT / "forecast_metrics.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    make_figures(raw, test_years, y_test, preds, selected_name, comp)
    make_extra_figures(wf_pred, wf_summary, ablation)
    write_model_card(summary, comp, tuning)

    print(f"Chọn theo validation MAE: {selected_name}")
    print(comp[["model", "mae", "rmse", "mape_percent", "r2", "bias_pred_minus_actual",
                "mae_improvement_vs_last_value_percent"]].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"Mô hình đã chọn {'THẮNG' if beats else 'THUA'} baseline Last Value trên test.")
    print(forecast_log[["nam", "nang_suat_thuc_te_ta_ha", "nang_suat_du_bao_mo_hinh_ta_ha",
                        "risk_level"]].to_string(index=False))
    return summary


# ---------------------------------------------------------------- hình & model card
def make_figures(raw, years, actual, preds, selected_name, comp):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure(figsize=(8, 4.5))
    plt.plot(raw["nam"], raw[TARGET], "-o", color="#888", label="thực tế (toàn chuỗi)")
    plt.plot(years, preds[selected_name], "-s", label=f"dự báo: {selected_name}")
    plt.plot(years, preds["LastValue_baseline"], "--^", label="baseline Last Value")
    plt.axvspan(TEST_START - 0.5, years.max() + 0.5, alpha=0.1, label="test 2022–2024")
    plt.xlabel("năm"); plt.ylabel(f"năng suất ({UNIT})")
    plt.title("Dự báo vs thực tế (năng suất lúa An Giang)")
    plt.legend(fontsize=8); plt.tight_layout()
    plt.savefig(FIGURES / "forecast_vs_actual.png", dpi=150); plt.close()

    plt.figure(figsize=(7, 4))
    w = 0.38
    xs = np.arange(len(years))
    plt.bar(xs - w / 2, preds[selected_name] - actual, w, label="mô hình đã chọn")
    plt.bar(xs + w / 2, preds["LastValue_baseline"] - actual, w, label="Last Value")
    plt.axhline(0, color="k", lw=0.8)
    plt.xticks(xs, years); plt.ylabel(f"dự báo − thực tế ({UNIT})")
    plt.title("Sai số dự báo theo năm test"); plt.legend(); plt.tight_layout()
    plt.savefig(FIGURES / "forecast_error_over_time.png", dpi=150); plt.close()

    plt.figure(figsize=(9, 4.5))
    plt.bar(range(len(comp)), comp["mae"],
            color=["#2a9d8f" if b else "#e76f51" for b in comp["is_baseline"]])
    plt.xticks(range(len(comp)), [m.split("[")[0] for m in comp["model"]], rotation=25, ha="right")
    plt.ylabel(f"MAE test ({UNIT})")
    plt.title("So sánh MAE trên test (xanh = baseline)"); plt.tight_layout()
    plt.savefig(FIGURES / "model_comparison_mae.png", dpi=150); plt.close()



def make_extra_figures(wf_pred, wf_summary, ablation):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.figure(figsize=(8, 4.5))
    plt.plot(wf_pred["nam"], wf_pred["actual"], "-o", color="#333", label="thực tế")
    plt.plot(wf_pred["nam"], wf_pred["LinearRegression"], "-s", label="LinearRegression (walk-forward)")
    plt.plot(wf_pred["nam"], wf_pred["last_value"], "--^", label="Last Value")
    plt.xlabel("năm đích"); plt.ylabel(f"năng suất ({UNIT})")
    plt.title("Đánh giá cuốn chiếu: mỗi năm chỉ train trên quá khứ")
    plt.legend(fontsize=8); plt.tight_layout()
    plt.savefig(FIGURES / "walk_forward_vs_actual.png", dpi=150); plt.close()

    plt.figure(figsize=(9, 4.5))
    base = wf_summary["model"].str.contains("baseline")
    plt.bar(range(len(wf_summary)), wf_summary["mae"], color=["#2a9d8f" if b else "#e76f51" for b in base])
    plt.xticks(range(len(wf_summary)), wf_summary["model"], rotation=25, ha="right")
    plt.ylabel(f"MAE walk-forward ({UNIT})"); plt.title("MAE cuốn chiếu (xanh = baseline)")
    plt.tight_layout(); plt.savefig(FIGURES / "walk_forward_mae.png", dpi=150); plt.close()

    plt.figure(figsize=(9, 4.5))
    plt.barh(range(len(ablation)), ablation["mae"], color="#457b9d")
    plt.yticks(range(len(ablation)), [x.split(" (")[0] for x in ablation["feature_set"]])
    plt.gca().invert_yaxis(); plt.xlabel(f"MAE walk-forward ({UNIT})")
    plt.title("Bỏ/giữ nhóm đặc trưng (hồi quy tuyến tính)"); plt.tight_layout()
    plt.savefig(FIGURES / "ablation_features_mae.png", dpi=150); plt.close()


def write_model_card(summary, comp, tuning):
    sel = summary["selected_model_test_metrics"]
    lines = [
        "# Model card – dự báo năng suất lúa An Giang",
        "",
        f"- Phiên bản: `{summary['model_version']}`; mô hình đã chọn theo validation: **{summary['selected_model_by_validation_mae']}**",
        f"- Đầu vào: {', '.join(summary['feature_columns'])} của năm t. Đầu ra: năng suất năm t+1 ({UNIT}).",
        f"- Chia thời gian: train {summary['split']['train_target_years']}, validation {summary['split']['validation_target_years']}, "
        f"test {summary['split']['test_target_years']}.",
        "- Bộ dữ liệu chỉ gồm 2015–2024; project không chứa số liệu 2025–2026.",
        "",
        "## Kết quả test",
        f"MAE {sel['mae']:.3f}, RMSE {sel['rmse']:.3f}, MAPE {sel['mape_percent']:.2f}%, bias {sel['bias_pred_minus_actual']:+.3f} {UNIT}.",
        f"Last Value baseline MAE {summary['last_value_baseline_test_mae']:.3f}. "
        + ("Mô hình hơn baseline." if summary["selected_model_beats_last_value_on_test"]
           else "**Mô hình KHÔNG hơn baseline Last Value trên test** – chưa nên dùng thay baseline."),
        "",
        "## Đánh giá cuốn chiếu (walk-forward) 2019–2024",
        "Mỗi năm đích chỉ train trên quá khứ, cấu hình khai báo trước. MAE (tạ/ha): "
        + ", ".join(f"{k} {v}" for k, v in summary["walk_forward"]["mae_by_model"].items()) + ".",
        f"Mô hình tốt nhất theo MAE cuốn chiếu: {summary['walk_forward']['best_model']}. Chỉ 6 điểm, đọc thận trọng.",
        f"Bỏ thời tiết: MAE {summary['ablation']['mae_without_weather']} so với đầy đủ {summary['ablation']['mae_full_features']} "
        + ("(thời tiết giúp giảm sai số trong thí nghiệm này)." if summary["ablation"]["weather_helps"]
           else "(thời tiết không giúp giảm sai số)."),
        "",
        "## Giới hạn",
        "- Chỉ 4 dòng train, 2 validation, 3 test; ước lượng sai số rất không ổn định.",
        "- R² trên test rất âm vì năng suất 2022–2024 gần như đi ngang (phương sai nhỏ); ưu tiên đọc MAE/MAPE.",
        "- Không phải LSTM/deep learning: với 9–10 điểm dữ liệu, mô hình sâu không có cơ sở huấn luyện.",
        "- Không dùng thời tiết thực tế của năm đích; dự báo từ 2025 trở đi là ngoại suy của chuỗi An Giang cũ, không phải số liệu thực tế.",
        "",
        "## An toàn",
        SAFETY_NOTE,
    ]
    (OUTPUT / "model_card_lua.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- suy luận (API + LLM tool)
_bundle_cache = None


def load_bundle():
    global _bundle_cache
    if _bundle_cache is None:
        if not BUNDLE_PATH.exists():
            raise FileNotFoundError("Chưa có model. Chạy: python mo_hinh_du_bao.py")
        _bundle_cache = joblib.load(BUNDLE_PATH)
    return _bundle_cache


def forecast_with_decision(nam_du_bao: int, dien_tich_ha=None, mua_tong_mm=None, nhiet_tb_c=None,
                           ngay_nong=None, nang_suat_nam_truoc=None) -> dict:
    """Trả JSON theo cấu trúc: model_output / evaluation_hint / decision / api_check.

    Đặc trưng thiếu được lấy từ năm nam_du_bao-1 trong lua_an_giang.csv nếu có.
    """
    t0 = time.time()
    b = load_bundle()
    raw = pd.read_csv(INPUT).sort_values("nam").reset_index(drop=True)
    nam_dau, nam_cuoi = int(raw["nam"].min()), int(raw["nam"].max())
    if isinstance(nam_du_bao, bool) or int(nam_du_bao) != nam_du_bao:
        raise NamNgoaiPhamVi("Năm dự báo phải là số nguyên.")
    nam_du_bao = int(nam_du_bao)
    # Chính sách chân trời: mô hình 1 bước chỉ hỗ trợ [năm đầu + 1, năm cuối + 1]; ngoài đó từ chối, không ngoại suy.
    if not nam_dau + 1 <= nam_du_bao <= nam_cuoi + 1:
        raise NamNgoaiPhamVi(
            f"Mô hình chỉ dự báo 1 năm kế tiếp: năm {nam_dau + 1}–{nam_cuoi + 1} (dữ liệu {nam_dau}–{nam_cuoi}). "
            f"Không dự báo năm {nam_du_bao}; muốn nhìn xa hơn hãy dùng hàm xu hướng riêng (du_bao_nhieu_nam).")
    row = raw[raw["nam"] == nam_du_bao - 1]
    warnings: list[str] = []

    def pick(value, col):
        if value is not None:
            return float(value)
        if not row.empty:
            return float(row[col].iloc[0])
        warnings.append(f"Thiếu {col} và không có năm {nam_du_bao - 1} trong dữ liệu; dùng trung vị lịch sử.")
        return float(b["feature_medians"][col])

    feats = {
        "nam": float(nam_du_bao),
        "dien_tich_ha": pick(dien_tich_ha, "dien_tich_ha"),
        "mua_tong_mm": pick(mua_tong_mm, "mua_tong_mm"),
        "nhiet_tb_c": pick(nhiet_tb_c, "nhiet_tb_c"),
        "ngay_nong": pick(ngay_nong, "ngay_nong"),
    }
    X = pd.DataFrame([feats])[b["feature_columns"]]
    predicted = float(b["model"].predict(X)[0])

    if nang_suat_nam_truoc is not None:
        last = float(nang_suat_nam_truoc)
    elif not row.empty:
        last = float(row[TARGET].iloc[0])
    else:
        last = None
    if nam_du_bao <= nam_cuoi:
        warnings.append(f"Năm {nam_du_bao} đã có số liệu thực tế và nằm trong dữ liệu huấn luyện: đây là kết quả hồi cứu, "
                        "không phải dự báo chưa biết trước.")
    else:
        warnings.append("Chuỗi An Giang cũ đến 2024; không đại diện địa giới An Giang sau hợp nhất.")
    dv_hien_tai = data_version()
    if b.get("data_version") and b["data_version"] != dv_hien_tai:
        warnings.append(f"CSV hiện tại ({dv_hien_tai}) khác bản dùng để train ({b['data_version']}); "
                        "chạy lại python mo_hinh_du_bao.py trước khi tin kết quả.")
    if not b["beats_last_value_baseline_on_test"]:
        warnings.append("Trên test mô hình chưa vượt baseline Last Value; xem baseline_last_value để đối chiếu.")

    itv = b.get("prediction_interval")
    interval_out = None
    decision = decision_layer(predicted, last, b["risk_thresholds"])
    if itv:
        lo, hi = predicted - itv["half_width"], predicted + itv["half_width"]
        interval_out = {"low": round(lo, 3), "high": round(hi, 3), "half_width": round(itv["half_width"], 3),
                        "method": itv["method"], "note": itv["note"]}
        decision["risk_level_if_low_bound"] = decision_layer(lo, last, b["risk_thresholds"])["risk_level"]
    return {
        "model_output": {
            "target": b["target"], "forecast_horizon_years": 1,
            "predicted_value": round(predicted, 2), "prediction_interval": interval_out, "unit": b["unit"],
            "model_version": b["model_version"], "model_name": b["model_name"],
            "model_id": f"{b['model_version']}/{b['model_name']}", "data_version": dv_hien_tai,
            "input_year": nam_du_bao - 1, "output_year": nam_du_bao,
            "baseline_last_value": None if last is None else round(last, 3),
            "input_features": feats,
        },
        "evaluation_hint": {
            "metrics_file": "outputs/forecast_metrics.json",
            "test_target_years": [TEST_START, 2024],
            "test_mae": round(b["test_metrics"]["mae"], 3),
            "test_rmse": round(b["test_metrics"]["rmse"], 3),
            "test_mape_percent": round(b["test_metrics"]["mape_percent"], 2),
            "test_bias": round(b["test_metrics"]["bias_pred_minus_actual"], 3),
            "last_value_baseline_test_mae": round(b["last_value_baseline_test_mae"], 3),
            "beats_last_value_baseline": b["beats_last_value_baseline_on_test"],
            "note": "MAE trên 3 năm test, không phải khoảng tin cậy.",
        },
        "decision": decision,
        "api_check": {"latency_ms": round((time.time() - t0) * 1000, 2), "warnings": warnings},
    }


def du_bao_co_rui_ro(nam, mua_tong_mm=None, dien_tich_ha=None, nhiet_tb_c=None, ngay_nong=None):
    """Hàm gọn cho LLM: mô hình nhỏ nội bộ -> dự báo + risk_level + khuyến nghị + sai số kiểm tra."""
    try:
        return forecast_with_decision(int(nam), dien_tich_ha, mua_tong_mm, nhiet_tb_c, ngay_nong)
    except (FileNotFoundError, NamNgoaiPhamVi) as e:
        return {"loi": str(e)}


def predict_yield(nam, kich_ban_mua_phan_tram=0, kich_ban_dien_tich_phan_tram=0) -> dict:
    """NGUỒN DỰ BÁO DUY NHẤT của hệ thống (chat, trang Dự báo, API đều đi qua forecast_with_decision).

    Dự báo năng suất lúa năm `nam` (1 năm kế tiếp) bằng mô hình đã chọn theo validation. Kịch bản mưa/diện tích
    là % thay đổi so với đặc trưng năm nam-1; đây là mô phỏng giả định, không phải kết luận nhân quả.
    Trả về JSON có đơn vị rõ từng trường; lỗi trả {"loi": ...} và KHÔNG tạo con số.
    """
    try:
        if isinstance(nam, bool) or not np.isfinite(float(nam)) or float(nam) % 1:
            return {"loi": "Năm dự báo phải là số nguyên hữu hạn."}
        nam = int(nam)
        mua_pct, dt_pct = float(kich_ban_mua_phan_tram), float(kich_ban_dien_tich_phan_tram)
    except (TypeError, ValueError, OverflowError):
        return {"loi": "Năm và các kịch bản mưa/diện tích phải là số hợp lệ."}
    if not np.isfinite(mua_pct) or not -100 <= mua_pct <= 300:
        return {"loi": "Kịch bản mưa phải là số hữu hạn trong khoảng -100% đến +300%."}
    if not np.isfinite(dt_pct) or not -100 < dt_pct <= 300:
        return {"loi": "Kịch bản diện tích phải là số hữu hạn lớn hơn -100% và không quá +300%."}
    try:
        co_so = forecast_with_decision(nam)
        feats = co_so["model_output"]["input_features"]
        kb = co_so if (mua_pct == 0 and dt_pct == 0) else forecast_with_decision(
            nam, dien_tich_ha=feats["dien_tich_ha"] * (1 + dt_pct / 100),
            mua_tong_mm=feats["mua_tong_mm"] * (1 + mua_pct / 100))
    except (FileNotFoundError, NamNgoaiPhamVi) as e:
        return {"loi": str(e)}
    mo, mo0, ev = kb["model_output"], co_so["model_output"], kb["evaluation_hint"]
    raw = pd.read_csv(INPUT).sort_values("nam")
    mean3 = round(float(raw[raw["nam"] < nam][TARGET].tail(3).mean()), 2)
    dt_gd = float(kb["model_output"]["input_features"]["dien_tich_ha"])
    dt_cs = float(feats["dien_tich_ha"])
    return {
        "model_id": mo["model_id"], "data_version": mo["data_version"],
        "data_until_year": int(raw["nam"].max()), "input_year": mo["input_year"], "output_year": mo["output_year"],
        "predicted_yield": {"value": mo["predicted_value"], "unit": UNIT},
        "baseline_yield_no_scenario": {"value": mo0["predicted_value"], "unit": UNIT},
        "baseline_mean3": {"value": mean3, "unit": UNIT},
        "area_assumed": {"value": round(dt_gd), "unit": "ha"},
        "production_estimate": {"value": round(mo["predicted_value"] * dt_gd / 10), "unit": "tấn"},
        "production_no_scenario": {"value": round(mo0["predicted_value"] * dt_cs / 10), "unit": "tấn"},
        "scenario": {"rain_change_percent": mua_pct, "area_change_percent": dt_pct},
        "test_mae": {"value": ev["test_mae"], "unit": UNIT, "years": [TEST_START, int(raw["nam"].max())]},
        "last_value_baseline_test_mae": {"value": ev["last_value_baseline_test_mae"], "unit": UNIT},
        "beats_last_value_baseline": ev["beats_last_value_baseline"],
        "interval": mo["prediction_interval"], "risk": kb["decision"],
        "input_features_base": feats, "input_features_used": mo["input_features"],
        "warnings": kb["api_check"]["warnings"],
    }


def cac_nam_kiem_tra() -> list[int]:
    p = OUTPUT / "forecast_log.csv"
    if not p.exists():
        return []
    return [int(n) for n in pd.read_csv(p)["nam"]]


def du_bao_nam_kiem_tra(nam) -> dict:
    """Dự báo của mô hình AI cho một năm trong tập kiểm tra, đối chiếu với thực tế và baseline (đọc forecast_log.csv)."""
    nam = int(nam)
    ds = cac_nam_kiem_tra()
    if not ds:
        return {"loi": "Chưa có kết quả kiểm tra. Chạy: python mo_hinh_du_bao.py"}
    if nam not in ds:
        return {"loi": f"Năm {nam} không nằm trong các năm kiểm tra {min(ds)}–{max(ds)}."}
    log = pd.read_csv(OUTPUT / "forecast_log.csv")
    r = log[log["nam"] == nam].iloc[0]
    m = json.loads((OUTPUT / "forecast_metrics.json").read_text(encoding="utf-8"))
    thuc, du_bao, base = float(r["nang_suat_thuc_te_ta_ha"]), float(r["nang_suat_du_bao_mo_hinh_ta_ha"]), float(r["baseline_last_value_ta_ha"])

    raw = pd.read_csv(INPUT).sort_values("nam").reset_index(drop=True)
    goc = raw[raw["nam"] == nam].iloc[0]
    sup = make_supervised(raw)
    dau_vao = sup[sup["nam"] == nam].iloc[0]          # đặc trưng của năm nam-1, cột 'nam' = năm đích
    cach_tinh = None
    if m["selected_model_by_validation_mae"].split("[")[0] == "LinearRegression":
        tv = sup[sup["nam"] < TEST_START]              # đúng tập đã dùng để huấn luyện bản kiểm tra (2016-2021)
        lr = LinearRegression().fit(tv[FEATURES], tv[TARGET])
        parts = [{"dac_trung": f, "gia_tri": float(dau_vao[f]), "he_so": float(c), "dong_gop": float(c * dau_vao[f])}
                 for f, c in zip(FEATURES, lr.coef_)]
        tong = float(lr.intercept_ + sum(p["dong_gop"] for p in parts))
        if abs(tong - du_bao) < 0.01:                  # chỉ trình bày công thức khi khớp đúng số trong forecast_log
            # làm tròn giống cách hiển thị để các con số Gemini chép lại khớp đúng kết quả hàm
            cach_tinh = {"hang_so": round(float(lr.intercept_), 3), "tong": round(tong, 3),
                         "thanh_phan": [{"dac_trung": p_["dac_trung"], "gia_tri": p_["gia_tri"],
                                         "he_so": round(p_["he_so"], 7), "he_so_text": f"{p_['he_so']:.7f}", "dong_gop": round(p_["dong_gop"], 3)}
                                        for p_ in parts]}
    nguon = "Niên giám Thống kê tỉnh An Giang 2024; thời tiết: Open-Meteo Historical Weather API"
    try:
        import bo_du_lieu
        nguon = next(b["nguon"] for b in bo_du_lieu.ds_bo() if b["ma"] == "lua_an_giang")
    except Exception:
        pass
    tm = m["selected_model_test_metrics"]
    return {
        "nam": nam, "nang_suat_thuc_te": round(thuc, 2), "nang_suat_du_bao_mo_hinh": round(du_bao, 2),
        "sai_so_mo_hinh": round(du_bao - thuc, 2), "baseline_last_value": round(base, 2),
        "sai_so_baseline": round(base - thuc, 2),
        "du_lieu_goc": {"dien_tich_ha": float(goc["dien_tich_ha"]), "san_luong_tan": float(goc["san_luong_tan"]),
                        "nang_suat_ta_ha": float(goc["nang_suat_ta_ha"]), "mua_tong_mm": float(goc["mua_tong_mm"]),
                        "nhiet_tb_c": float(goc["nhiet_tb_c"]), "ngay_nong": float(goc["ngay_nong"]), "nguong_ngay_nong_c": 35},
        "nam_dau_vao": nam - 1, "cach_tinh": cach_tinh, "nguon_du_lieu": nguon,
        "mae_mo_hinh_kiem_tra": round(tm["mae"], 3),
        "mae_baseline_kiem_tra": round(m["last_value_baseline_test_mae"], 3),
        "nam_kiem_tra": [min(ds), max(ds)], "huan_luyen_den_nam": m["split"]["validation_target_years"][1],
        "mo_hinh_hon_baseline": bool(m["selected_model_beats_last_value_on_test"]),
        "ghi_chu": "Mô hình chưa thấy năm này khi học; sai số = dự báo - thực tế.",
    }


if __name__ == "__main__":
    run_all()
