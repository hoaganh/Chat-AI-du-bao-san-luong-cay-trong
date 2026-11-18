"""Kiểm tra đánh giá cuốn chiếu không nhìn tương lai và các file phân tích mô hình."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import numpy as np
import pandas as pd
import mo_hinh_du_bao as lab

FAILS = []


def kt(ten, dieu_kien):
    print(("PASS  " if dieu_kien else "FAIL  ") + ten)
    if not dieu_kien:
        FAILS.append(ten)


raw = pd.read_csv(lab.INPUT).sort_values("nam").reset_index(drop=True)
mk = lab.fixed_configs()["LinearRegression"]
base = lab.walk_forward(raw, mk, lab.FEATURES)
kt("walk-forward bắt đầu 2019 và kết thúc 2024 (6 năm)", list(base["nam"]) == [2019, 2020, 2021, 2022, 2023, 2024])
kt("mỗi fold dùng ≥3 dòng và số dòng train tăng dần", base["n_train"].is_monotonic_increasing and base["n_train"].min() >= 3)

# không rò rỉ: đổi toàn bộ số liệu từ năm Y trở đi thành rác thì dự báo năm Y phải giữ nguyên
ok = True
for y in (2021, 2022, 2024):
    r2 = raw.copy()
    mask = r2["nam"] >= y
    for c in lab.FEATURES[1:] + [lab.TARGET]:
        r2.loc[mask, c] = 9999.0
    p_goc = float(base.loc[base["nam"] == y, "pred"].iloc[0])
    p_rac = float(lab.walk_forward(r2, mk, lab.FEATURES).query("nam == @y")["pred"].iloc[0]) if y < 2022 else None
    if y >= 2022:
        # với y>=2022, đặc trưng năm y-1 vẫn là số thật; chỉ đổi từ năm y trở đi
        p_rac = float(lab.walk_forward(r2, mk, lab.FEATURES).query("nam == @y")["pred"].iloc[0])
    ok &= bool(np.isclose(p_goc, p_rac))
kt("đổi số liệu từ năm đích trở đi không làm đổi dự báo năm đó (không rò rỉ)", ok)

for f in ("walk_forward_summary.csv", "walk_forward_predictions.csv", "ablation_features.csv", "linear_coefficients.csv"):
    kt(f"có outputs/{f}", (lab.OUTPUT / f).exists())
for f in ("walk_forward_vs_actual.png", "walk_forward_mae.png", "ablation_features_mae.png"):
    kt(f"có figures/{f}", (lab.FIGURES / f).exists())
m = json.loads((lab.OUTPUT / "forecast_metrics.json").read_text(encoding="utf-8"))
kt("forecast_metrics.json có walk_forward và ablation", "walk_forward" in m and "ablation" in m)
ab = pd.read_csv(lab.OUTPUT / "ablation_features.csv")
kt("ablation có đủ 6 dòng gồm baseline", len(ab) == 6 and ab["feature_set"].str.contains("LastValue").any())

print("\nKET QUA:", "TAT CA PASS" if not FAILS else f"{len(FAILS)} LOI")
raise SystemExit(1 if FAILS else 0)
