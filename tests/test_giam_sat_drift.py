"""Kiểm tra giám sát drift bằng nhật ký tạm (không đụng outputs/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempfile
from pathlib import Path

import pandas as pd

import giam_sat_drift as g

FAILS = []


def kt(ten, dk):
    print(("PASS  " if dk else "FAIL  ") + ten)
    if not dk:
        FAILS.append(ten)


def tao(rows):
    p = Path(tempfile.mkdtemp()) / "log.csv"
    pd.DataFrame(rows, columns=g.COLS).to_csv(p, index=False)
    return p


def dong(nam, du_bao, thuc_te, base=65.0, half=2.0):
    return [nam, du_bao, du_bao - half, du_bao + half, base, thuc_te, None if thuc_te is None else du_bao - thuc_te, "2026-01-01"]


REF = 1.25
p0 = Path(tempfile.mkdtemp()) / "trong.csv"
kt("chưa có dữ liệu -> NO_DATA", g.danh_gia_drift(p0, mae_tham_chieu=REF)["status"] == "NO_DATA")
kt("sai số nhỏ, hai chiều -> OK", g.danh_gia_drift(tao([dong(2025, 66, 65.5), dong(2026, 66, 66.4), dong(2027, 66, 65.8)]), mae_tham_chieu=REF)["status"] == "OK")
kt("sai số gấp 2 lần tham chiếu -> DRIFT", g.danh_gia_drift(tao([dong(2025, 66, 63.0), dong(2026, 66, 69.0), dong(2027, 66, 63.2)]), mae_tham_chieu=REF)["status"] == "DRIFT")
kt("2 năm lệch cùng chiều đủ lớn -> WATCH", g.danh_gia_drift(tao([dong(2026, 66.0, 65.0), dong(2027, 66.0, 64.9)]), mae_tham_chieu=REF)["status"] in ("WATCH", "DRIFT"))
r = g.danh_gia_drift(tao([dong(2025, 66, 60.0, base=60.5)]), mae_tham_chieu=REF)
kt("thực tế ngoài khoảng được đếm", r["actual_outside_interval"] == 1)
kt("so với baseline: mô hình kém hơn được phát hiện", r["model_worse_than_baseline_recently"] is True)

# ghi dự báo -> thêm thực tế
p = Path(tempfile.mkdtemp()) / "log.csv"
row = g.ghi_du_bao(2025, log_path=p)
kt("ghi dự báo 2025 có khoảng và baseline", row["khoang_thap"] < row["du_bao"] < row["khoang_cao"] and row["baseline_nam_truoc"] is not None)
try:
    g.them_thuc_te(2031, 60.0, log_path=p); loi = False
except ValueError:
    loi = True
kt("không cho điền thực tế cho năm chưa có dự báo", loi)
out = g.them_thuc_te(2025, 65.7, log_path=p)
kt("sai số = dự báo - thực tế", abs(out["sai_so"] - (row["du_bao"] - 65.7)) < 1e-9)
try:
    g.ghi_du_bao(2025, log_path=p); loi2 = False
except ValueError:
    loi2 = True
kt("không ghi đè dự báo đã có số thực tế", loi2)

print("\nKET QUA:", "TAT CA PASS" if not FAILS else f"{len(FAILS)} LOI")
raise SystemExit(1 if FAILS else 0)
