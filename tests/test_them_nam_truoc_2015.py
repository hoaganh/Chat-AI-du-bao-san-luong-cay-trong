"""Kiểm tra script ghép năm trước 2015 bằng dữ liệu GIẢ trong thư mục tạm (không bao giờ ghi vào data/ thật)."""
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import them_nam_truoc_2015 as t

LOI = []


def kt(ten, ok, ct=""):
    print(("PASS " if ok else "FAIL ") + ten + ("" if ok else f"  -> {ct}"))
    if not ok:
        LOI.append(ten)


def main():
    goc_data = Path(t.DATA)
    truoc = goc_data.read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        data, mau = Path(tmp) / "lua.csv", Path(tmp) / "mau.csv"
        shutil.copyfile(goc_data, data)
        shutil.copyfile(t.MAU, mau)
        kt("mẫu để trống -> KHÔNG ghép, không tạo .bak", t.main([], mau, data) == 1 and not Path(str(data) + ".bak").exists())
        kt("file lua_an_giang.csv không bị đổi khi mẫu còn trống", data.read_bytes() == truoc)
        m = pd.read_csv(mau)
        m["dien_tich_ha"] = [650000 + 1000 * i for i in range(5)]
        m["san_luong_tan"] = [3_500_000 + 20_000 * i for i in range(5)]
        m["nang_suat_ta_ha"] = (m["san_luong_tan"] * 10 / m["dien_tich_ha"]).round(2)   # SỐ GIẢ chỉ để thử code
        m.to_csv(mau, index=False)
        kt("--thu hợp lệ nhưng KHÔNG ghi", t.main(["--thu"], mau, data) == 0 and data.read_bytes() == truoc)
        kt("ghép thật: 15 năm 2010–2024, có .bak", t.main([], mau, data) == 0 and Path(str(data) + ".bak").exists())
        g = pd.read_csv(data)
        kt("kết quả sắp theo năm, đủ cột, 15 dòng", len(g) == 15 and g["nam"].is_monotonic_increasing and list(g.columns) == t.COT, len(g))
        kt("không ghép lại lần hai (năm đã có)", t.main([], mau, data) == 1)
        # sai đơn vị: nghìn ha
        shutil.copyfile(goc_data, data)
        m2 = m.copy(); m2["dien_tich_ha"] = m2["dien_tich_ha"] / 1000
        m2.to_csv(mau, index=False)
        kt("diện tích theo nghìn ha bị chặn", t.main([], mau, data) == 1)
        m3 = m.copy(); m3.loc[0, "nang_suat_ta_ha"] = 99.0
        m3.to_csv(mau, index=False)
        kt("năng suất không khớp sản lượng/diện tích bị chặn", t.main([], mau, data) == 1)
    kt("data/lua_an_giang.csv thật không bị đổi sau test", goc_data.read_bytes() == truoc)
    print("\nKET QUA:", "TAT CA PASS" if not LOI else f"{len(LOI)} LOI: {LOI}")
    sys.exit(1 if LOI else 0)


if __name__ == "__main__":
    main()
