"""Kiểm tra schema API /forecast không cần mở cổng (dùng TestClient). Ghi outputs/api_test_result.json."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
from fastapi.testclient import TestClient

import mo_hinh_du_bao as lab
from api_forecast import app

client = TestClient(app)


def main():
    results = {}
    h = client.get("/health").json()
    assert h["model_loaded"] is True, h
    results["health"] = h
    info = client.get("/model-info").json()
    assert info["model_loaded"] and "test_metrics" in info
    results["model_info_keys"] = sorted(info.keys())

    r = client.post("/forecast", json={"nam_du_bao": 2025}).json()
    for k in ("model_output", "evaluation_hint", "decision", "api_check"):
        assert k in r, f"thiếu {k}"
    for k in ("predicted_value", "unit", "model_version"):
        assert k in r["model_output"]
    for k in ("risk_level", "recommendation", "reason", "safety_note"):
        assert k in r["decision"]
    assert r["decision"]["risk_level"] in {"NORMAL", "WARNING", "HIGH", "CRITICAL", "UNKNOWN"}
    itv = r["model_output"]["prediction_interval"]
    assert itv and itv["low"] < r["model_output"]["predicted_value"] < itv["high"]
    assert r["decision"]["risk_level_if_low_bound"] in {"NORMAL", "WARNING", "HIGH", "CRITICAL"}
    results["forecast_2025_default_features"] = r
    d = client.get("/drift-status").json()
    assert d["status"] in {"OK", "WATCH", "DRIFT", "NO_DATA"}
    results["drift_status"] = d

    # kịch bản mưa: kiểm tra đặc trưng ghi đè được TRUYỀN ĐÚNG và đầu ra hợp lệ. Không áp đặt dự báo phải đổi:
    # mô hình được chọn (vd Random Forest) có thể không dùng biến mưa nên đầu ra có thể không đổi.
    r2 = client.post("/forecast", json={"nam_du_bao": 2025, "mua_tong_mm": 1200}).json()
    assert r2["model_output"]["input_features"]["mua_tong_mm"] == 1200, r2["model_output"]["input_features"]
    assert 0 < r2["model_output"]["predicted_value"] < 200, r2["model_output"]["predicted_value"]
    results["forecast_2025_mua_1200"] = r2["model_output"]["predicted_value"]

    # một nguồn dự báo: /predict-yield, /forecast và ham_xu_ly.du_bao cùng ra một con số + model_id
    import ham_xu_ly as hx
    py = client.post("/predict-yield", json={"nam": 2025}).json()
    assert py["predicted_yield"]["value"] == r["model_output"]["predicted_value"] == hx.du_bao(2025)["nang_suat_du_bao"], py
    assert py["model_id"] == r["model_output"]["model_id"] == hx.du_bao(2025)["model_id"]
    assert py["predicted_yield"]["unit"] == "tạ/ha" and py["area_assumed"]["unit"] == "ha"
    results["predict_yield_2025"] = py

    # kiểm tra lớp quyết định: giảm mạnh phải ra mức rủi ro cao hơn
    th = lab.load_bundle()["risk_thresholds"]
    d_nor = lab.decision_layer(65.0, 65.0, th)["risk_level"]
    d_crit = lab.decision_layer(65.0 * (1 - 2 * th["critical_drop_percent"] / 100), 65.0, th)["risk_level"]
    assert d_nor == "NORMAL" and d_crit == "CRITICAL", (d_nor, d_crit)
    results["decision_layer_check"] = {"no_change": d_nor, "big_drop": d_crit}

    # năm vượt chân trời 1 năm: TỪ CHỐI (422), không tạo số
    r3 = client.post("/forecast", json={"nam_du_bao": 2030})
    assert r3.status_code == 422 and "2030" in r3.json()["detail"], (r3.status_code, r3.text)
    assert client.post("/predict-yield", json={"nam": 2030}).status_code == 422
    results["forecast_2030"] = {"status": r3.status_code, "detail": r3.json()["detail"]}

    (lab.OUTPUT / "api_test_result.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK: /health, /model-info, /forecast đúng schema; đã ghi outputs/api_test_result.json")
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
