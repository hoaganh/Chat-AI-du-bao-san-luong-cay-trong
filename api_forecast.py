"""API /forecast cho mô hình dự báo (FastAPI).

Chạy:   uvicorn api_forecast:app --reload      rồi mở http://127.0.0.1:8000/docs
Cần train trước:  python mo_hinh_du_bao.py
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import mo_hinh_du_bao as lab

app = FastAPI(
    title="AgFarm – Forecast API",
    description="Đặc trưng năm t -> năng suất lúa năm t+1 -> risk_level -> recommendation (không điều khiển tự động).",
    version="1.0.0",
)


class ForecastRequest(BaseModel):
    nam_du_bao: int = Field(..., examples=[2025], description="Năm cần dự báo (dùng đặc trưng năm nam_du_bao-1).")
    dien_tich_ha: float | None = Field(None, description="Bỏ trống = lấy từ lua_an_giang.csv của năm trước.")
    mua_tong_mm: float | None = None
    nhiet_tb_c: float | None = None
    ngay_nong: float | None = None
    nang_suat_nam_truoc: float | None = Field(None, description="Tạ/ha; dùng làm baseline và tính risk.")


class YieldRequest(BaseModel):
    nam: int = Field(..., examples=[2025], description="Năm cần dự báo; chỉ hỗ trợ 1 năm kế tiếp sau dữ liệu cuối.")
    kich_ban_mua_phan_tram: float = Field(0, description="% thay đổi lượng mưa so với năm trước (giả định).")
    kich_ban_dien_tich_phan_tram: float = Field(0, description="% thay đổi diện tích so với năm trước (giả định).")


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": lab.BUNDLE_PATH.exists(), "model_bundle_path": str(lab.BUNDLE_PATH)}


@app.get("/model-info")
def model_info():
    if not lab.BUNDLE_PATH.exists():
        return {"model_loaded": False, "message": "Chưa có model. Chạy: python mo_hinh_du_bao.py"}
    b = lab.load_bundle()
    metrics_path = lab.OUTPUT / "forecast_metrics.json"
    metrics = json.loads(Path(metrics_path).read_text(encoding="utf-8")) if metrics_path.exists() else {}
    return {
        "model_loaded": True, "model_name": b["model_name"], "model_version": b["model_version"],
        "target": b["target"], "unit": b["unit"], "forecast_horizon_years": 1,
        "feature_columns": b["feature_columns"], "trained_on_target_years": b["trained_on_target_years"],
        "risk_thresholds": b["risk_thresholds"], "test_metrics": b["test_metrics"],
        "last_value_baseline_test_mae": b["last_value_baseline_test_mae"],
        "beats_last_value_baseline": b["beats_last_value_baseline_on_test"],
        "data_policy": "Bộ dữ liệu chỉ gồm 2015-2024; không có số liệu 2025-2026.",
        "metrics": metrics,
    }


@app.post("/forecast")
def forecast(req: ForecastRequest):
    if not lab.BUNDLE_PATH.exists():
        raise HTTPException(status_code=503, detail="Model chưa được train. Chạy: python mo_hinh_du_bao.py")
    try:
        return lab.forecast_with_decision(
            req.nam_du_bao, req.dien_tich_ha, req.mua_tong_mm, req.nhiet_tb_c, req.ngay_nong, req.nang_suat_nam_truoc
        )
    except lab.NamNgoaiPhamVi as e:   # năm ngoài chân trời 1 năm: từ chối, không tạo số
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/predict-yield")
def predict_yield(req: YieldRequest):
    """Cùng hàm với chat và trang Dự báo: mo_hinh_du_bao.predict_yield (model_id, data_version, đơn vị từng trường)."""
    if not lab.BUNDLE_PATH.exists():
        raise HTTPException(status_code=503, detail="Model chưa được train. Chạy: python mo_hinh_du_bao.py")
    kq = lab.predict_yield(req.nam, req.kich_ban_mua_phan_tram, req.kich_ban_dien_tich_phan_tram)
    if "loi" in kq:
        raise HTTPException(status_code=422, detail=kq["loi"])
    return kq


@app.get("/drift-status")
def drift_status():
    """OK / WATCH / DRIFT / NO_DATA dựa trên nhật ký outputs/giam_sat_du_bao.csv (xem giam_sat_drift.py)."""
    import giam_sat_drift as g
    if not lab.BUNDLE_PATH.exists():
        return {"error": "Model chưa được train. Chạy: python mo_hinh_du_bao.py"}
    return g.danh_gia_drift()
