"""Kiem thu du bao nhieu nam. Chay: python test_du_bao_dai_han.py (khong can mang)."""
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)
import du_bao_dai_han as dlh  # noqa: E402

LOI = []


def kt(ten, dieu_kien, chi_tiet=""):
    print(("PASS  " if dieu_kien else "FAIL  ") + ten + ("" if dieu_kien or not chi_tiet else f"  -> {chi_tiet}"))
    if not dieu_kien:
        LOI.append(ten)


def chay():
    d = pd.read_csv(os.path.join(THU_MUC, "data", "lua_an_giang.csv")).sort_values("nam")
    nam, y = d["nam"].to_numpy(float), d["nang_suat_ta_ha"].to_numpy(float)

    # ---- khop thu vien doc lap ----
    kq = dlh.du_bao_nhieu_nam(d, 5)
    lr = stats.linregress(nam, y)
    kt("xu huong khop scipy.linregress", abs(kq["xu_huong_ta_ha_moi_nam"] - lr.slope) < 5e-4, (kq["xu_huong_ta_ha_moi_nam"], lr.slope))
    h1 = kq["du_bao"][0]
    kt("nam du bao dau = nam cuoi + 1", h1["nam"] == 2025 and kq["du_lieu_den_nam"] == 2024, h1)
    kt("du bao 2025 khop scipy (intercept + slope * 2025)", abs(h1["nang_suat_ta_ha"] - (lr.intercept + lr.slope * 2025)) < 0.006, h1)
    res = y - (lr.intercept + lr.slope * nam)
    kt("sai so chuan phan du khop numpy ddof=2", abs(kq["sai_so_chuan_phan_du_ta_ha"] - np.sqrt((res ** 2).sum() / 8)) < 0.006, kq["sai_so_chuan_phan_du_ta_ha"])
    kt("moc phang = TB 3 nam cuoi", kq["moc_phang_tb_3_nam"] == round(float(y[-3:].mean()), 2), kq["moc_phang_tb_3_nam"])

    # ---- khoang du bao ----
    rong = [r["khoang_cao"] - r["khoang_thap"] for r in kq["du_bao"]]
    kt("khoang du bao rong dan theo do xa", all(rong[i] < rong[i + 1] for i in range(len(rong) - 1)), rong)
    kt("khoang chua gia tri du bao", all(r["khoang_thap"] <= r["nang_suat_ta_ha"] <= r["khoang_cao"] for r in kq["du_bao"]))
    kq95 = dlh.du_bao_nhieu_nam(d, 5, do_tin_cay=0.95)
    kt("khoang 95% rong hon 80%", all((b["khoang_cao"] - b["khoang_thap"]) > (a["khoang_cao"] - a["khoang_thap"])
                                       for a, b in zip(kq["du_bao"], kq95["du_bao"])))
    kt("san luong = nang suat x dien tich / 10", kq["du_bao"][0]["san_luong_tan"] == round(h1["nang_suat_ta_ha"] * 618586 / 10), h1)
    kq_dt = dlh.du_bao_nhieu_nam(d, 1, dien_tich_phan_tram=10)
    kt("kich ban dien tich +10% nhan san luong 1,1", abs(kq_dt["du_bao"][0]["san_luong_tan"] / h1["san_luong_tan"] - 1.1) < 1e-3, kq_dt["du_bao"][0])
    kt("nang suat khong doi khi doi kich ban dien tich", kq_dt["du_bao"][0]["nang_suat_ta_ha"] == h1["nang_suat_ta_ha"])

    # ---- kiem chung thong ke: khoang "80%" phai chua gia tri that khoang 80% so lan ----
    rng = np.random.default_rng(12345)
    t = np.arange(2015, 2025, dtype=float)
    chua, tong = 0, 20000
    for _ in range(tong):
        moi = 50 + 0.5 * (t - 2015) + rng.normal(0, 1.5, len(t))
        dd = pd.DataFrame({"nam": t, "nang_suat_ta_ha": moi, "dien_tich_ha": 100.0})
        r = dlh.du_bao_nhieu_nam(dd, 1, do_tin_cay=0.8)["du_bao"][0]
        that = 50 + 0.5 * (2025 - 2015) + rng.normal(0, 1.5)
        chua += r["khoang_thap"] <= that <= r["khoang_cao"]
    kt(f"mo phong {tong} lan: khoang 80% chua gia tri that ~80%", 0.78 <= chua / tong <= 0.82, chua / tong)

    # ---- kiem tra cuon chieu: doi chieu voi vong lap doc lap da chay truoc ----
    kc = {r["so_nam_truoc"]: r for r in kq["kiem_tra_cuon_chieu"]}
    kt("cuon chieu: co do xa 1,2,3 nam", sorted(kc) == [1, 2, 3], kc)
    kt("cuon chieu: so moc 5/4/3", [kc[h]["so_moc_kiem_tra"] for h in (1, 2, 3)] == [5, 4, 3], kc)
    kt("cuon chieu: MAE xu huong 0,95 / 1,60 / 1,81", [kc[h]["mae_xu_huong"] for h in (1, 2, 3)] == [0.95, 1.6, 1.81], kc)
    kt("cuon chieu: MAE TB 3 nam 1,38 / 2,40 / 2.72", [kc[h]["mae_tb_3_nam"] for h in (1, 2, 3)] == [1.38, 2.4, 2.72], kc)

    # ---- muc tin cay & canh bao ----
    muc = [r["muc_tin_cay"] for r in dlh.du_bao_nhieu_nam(d, 10)["du_bao"]]
    kt("muc tin cay giam theo do xa", muc == ["tham khao"] * 2 + ["thap"] * 3 + ["rat thap"] * 5, muc)
    kt("so_nam <= 3 khong co canh bao 'xa hon 3 nam'", not any("3 năm" in c for c in dlh.du_bao_nhieu_nam(d, 3)["canh_bao"]))
    kt("so_nam = 5 co canh bao xa hon 3 nam", any("3 năm" in c for c in kq["canh_bao"]))

    # ---- bien ----
    for ten, loi_goi in [("so_nam=0", dict(so_nam=0)), ("so_nam=11", dict(so_nam=11)), ("so_nam chu", dict(so_nam="x")),
                         ("do_tin_cay=0.3", dict(so_nam=2, do_tin_cay=0.3)), ("do_tin_cay=1", dict(so_nam=2, do_tin_cay=1)),
                         ("dien tich -150%", dict(so_nam=2, dien_tich_phan_tram=-150))]:
        kt(f"tham so sai ({ten}) -> loi", "loi" in dlh.du_bao_nhieu_nam(d, **loi_goi))
    kt("it hon 6 nam -> loi", "loi" in dlh.du_bao_nhieu_nam(d.head(5), 2))
    kt("6 nam du bao duoc, nhung khong co kiem tra cuon chieu", "loi" not in dlh.du_bao_nhieu_nam(d.head(6), 2)
       and dlh.du_bao_nhieu_nam(d.head(6), 2)["kiem_tra_cuon_chieu"] == [])
    kt("co canh bao du lieu < 10 nam", any("năm dữ liệu" in c for c in dlh.du_bao_nhieu_nam(d.head(8), 2)["canh_bao"]))
    giam = d.copy(); giam["nang_suat_ta_ha"] = np.linspace(20, 2, len(giam))
    kt("xu huong giam manh: can duoi khong am", all(r["khoang_thap"] >= 0 for r in dlh.du_bao_nhieu_nam(giam, 10)["du_bao"]))


if __name__ == "__main__":
    chay()
    print("\nKET QUA:", "TAT CA PASS" if not LOI else f"CO {len(LOI)} LOI: {LOI}")
    sys.exit(1 if LOI else 0)
