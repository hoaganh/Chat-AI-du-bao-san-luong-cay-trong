"""Kiem thu cac ham tinh tren nhieu bo du lieu cay-tinh. Chay: python test_nhieu_bo_du_lieu.py (khong can mang).
LUU Y: bo du lieu trong file nay la SO TONG HOP chi de kiem tra logic, KHONG phai so lieu nong nghiep that."""
import os
import sys
import tempfile

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)
if not os.environ.get("DATABASE_URL"):
    os.environ["AGFARM_DB"] = os.path.join(tempfile.mkdtemp(prefix="agfarm_nbd_"), "test.db")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import bo_du_lieu as bdl  # noqa: E402
import db  # noqa: E402
import du_bao_dai_han as dlh  # noqa: E402
import ham_xu_ly as hx  # noqa: E402

LOI = []


def kt(ten, dieu_kien, chi_tiet=""):
    dat = bool(dieu_kien)
    them = "" if dat or (isinstance(chi_tiet, str) and not chi_tiet) else f"  -> {chi_tiet}"
    print(("PASS  " if dat else "FAIL  ") + ten + them)
    if not dat:
        LOI.append(ten)


def bang(n, nam_dau, co_thoi_tiet, hat=0):
    rng = np.random.RandomState(hat)
    i = np.arange(n)
    dien_tich = 500.0 + 7 * i
    mua = 1000.0 + 37 * ((i * 7) % 11)
    nhiet = 24.0 + 0.3 * ((i * 5) % 7)
    nong = ((i * 3) % 5).astype(float)
    nang_suat = 40 + 0.4 * i + 0.01 * (mua - 1200) - 0.8 * (nong) + rng.normal(0, 0.3, n)
    d = pd.DataFrame({"nam": nam_dau + i, "dien_tich_ha": dien_tich, "san_luong_tan": nang_suat * dien_tich / 10,
                      "nang_suat_ta_ha": nang_suat})
    if co_thoi_tiet:
        d["mua_tong_mm"], d["nhiet_tb_c"], d["ngay_nong"] = mua, nhiet, nong
    return d


def hoi_quy(d, cot):
    """Hoi quy tuyen tinh doc lap bang numpy lstsq: tra ve ham du bao."""
    x = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cot])
    he_so, *_ = np.linalg.lstsq(x, d["nang_suat_ta_ha"].to_numpy(float), rcond=None)
    return lambda hang: float(np.r_[1.0, [hang[c] for c in cot]] @ he_so)


class PhanHoiGia:
    def __init__(self, nd): self.nd = nd
    def read(self): return self.nd
    def __enter__(self): return self
    def __exit__(self, *a): return False


def chay():
    db.khoi_tao()
    nguon = "Nguon gia lap chi de test logic (khong phai so lieu that)"
    kq_a = bdl.them_bo("Ngô", "Sơn La", nguon, bang(10, 2013, False, 1))                       # khong thoi tiet, khong toa do
    kq_b = bdl.them_bo("Chè", "Thái Nguyên", nguon, bang(12, 2011, True, 2), lat=21.6, lon=105.8,
                       thang_bat_dau=5, thang_ket_thuc=11)                                      # co thoi tiet, co toa do
    kq_c = bdl.them_bo("Cao su", "Bình Phước", nguon, bang(9, 2014, True, 3), lat=11.5, lon=106.9,
                       thang_bat_dau=5, thang_ket_thuc=11)                                      # 9 nam: it hon 10
    kt("bo 9 nam bi TU CHOI khi nhap (de bai yeu cau >= 10 nam), khong duoc luu", "loi" in kq_c and "ma" not in kq_c, kq_c)
    kt("tao 2 bo thu nghiem hop le (>= 10 nam)", all("ma" in k for k in (kq_a, kq_b)), (kq_a, kq_b))
    A, B = "ngo_son_la", "che_thai_nguyen"
    dA, dB = bdl.lay_bo(A)[1], bdl.lay_bo(B)[1]

    # ---- bo khong ton tai: moi ham deu bao loi ro rang ----
    ham = [lambda b: hx.du_bao(2025, bo_du_lieu=b), lambda b: hx.giai_thich(2020, bo_du_lieu=b),
           lambda b: hx.lich_su(2015, 2020, bo_du_lieu=b), lambda b: hx.so_sanh_nam(2015, 2020, bo_du_lieu=b),
           lambda b: hx.thong_ke(2015, 2020, bo_du_lieu=b), lambda b: hx.tuong_quan("mua", "nang_suat", bo_du_lieu=b),
           lambda b: hx.thoi_tiet_du_bao(3, bo_du_lieu=b), lambda b: hx.du_bao_nhieu_nam(3, bo_du_lieu=b),
           lambda b: hx.danh_gia_mo_hinh(bo_du_lieu=b)]
    kt("bo 'ca_phe_lam_dong' khong ton tai -> moi ham tra loi 'Khong co bo du lieu'",
       all(str(f("ca_phe_lam_dong").get("loi", "")).startswith("Khong co bo du lieu") for f in ham))

    # ---- bo A: khong co thoi tiet ----
    ls = hx.lich_su(2015, 2018, bo_du_lieu=A)
    kt("lich_su bo A dung 4 nam", [r["nam"] for r in ls["du_lieu"]] == [2015, 2016, 2017, 2018], ls)
    kt("lich_su bo A khop du lieu", abs(ls["du_lieu"][0]["nang_suat_ta_ha"] - float(dA["nang_suat_ta_ha"].iloc[2])) < 1e-9)
    tk = hx.thong_ke(2013, 2022, "nang_suat", bo_du_lieu=A)
    kt("thong_ke bo A: trung binh khop numpy", tk["trung_binh"] == round(float(dA["nang_suat_ta_ha"].mean()), 2), tk)
    kt("thong_ke bo A: lon nhat khop", tk["lon_nhat"]["nam"] == int(dA["nam"][dA["nang_suat_ta_ha"].idxmax()]), tk)
    kt("thong_ke bo A: chi tieu 'mua' khong co -> loi", "khong co chi tieu" in hx.thong_ke(2013, 2022, "mua", bo_du_lieu=A).get("loi", ""))
    gt = hx.giai_thich(2016, bo_du_lieu=A)
    kt("giai_thich bo A: khong co khoa thoi tiet", "mua_tong_mm" not in gt and "ngay_nong" not in gt and "nang_suat_ta_ha" in gt, gt)
    kt("giai_thich bo A: so voi nam truoc chi co nang suat", list(gt["so_voi_nam_truoc"]) == ["chenh_lech_nang_suat"], gt)
    ss = hx.so_sanh_nam(2014, 2020, bo_du_lieu=A)
    kt("so_sanh_nam bo A: bo qua chi tieu thoi tiet", sorted(ss["chi_tieu"]) == ["dien_tich", "nang_suat", "san_luong"], ss["chi_tieu"].keys())
    kt("so_sanh_nam bo A: chenh lech nang suat dung",
       ss["chi_tieu"]["nang_suat"]["chenh_lech"] == round(float(dA["nang_suat_ta_ha"].iloc[7] - dA["nang_suat_ta_ha"].iloc[1]), 2))
    kt("tuong_quan mua-nang suat bo A -> loi (khong co du lieu mua)", "loi" in hx.tuong_quan("mua", "nang_suat", bo_du_lieu=A))
    r = hx.tuong_quan("dien_tich", "nang_suat", bo_du_lieu=A)
    kt("tuong_quan dien tich-nang suat bo A khop numpy",
       r["he_so_tuong_quan_pearson"] == round(float(np.corrcoef(dA["dien_tich_ha"], dA["nang_suat_ta_ha"])[0, 1]), 3), r)
    kt("du_bao 1 nam bo A -> loi, chi xem lich su/xu huong", "xu huong" in hx.du_bao(2023, bo_du_lieu=A).get("loi", ""))
    kt("thoi_tiet_du_bao bo A (khong toa do) -> loi", "khong co toa do" in hx.thoi_tiet_du_bao(3, bo_du_lieu=A).get("loi", ""))

    # ---- du_bao_nhieu_nam tren bo A ----
    nn = hx.du_bao_nhieu_nam(4, bo_du_lieu=A)
    truc_tiep = dlh.du_bao_nhieu_nam(dA, 4)
    kt("du_bao_nhieu_nam bo A khop tinh truc tiep tren DataFrame", nn["du_bao"] == truc_tiep["du_bao"], nn["du_bao"][:1])
    kt("du_bao_nhieu_nam gan nhan cay-tinh-nguon", (nn["cay"], nn["tinh"], nn["bo_du_lieu"]) == ("Ngô", "Sơn La", A) and nn["nguon"] == nguon)
    kt("du_bao_nhieu_nam bat dau tu nam sau nam cuoi cua bo A (2023)", nn["du_bao"][0]["nam"] == 2023)
    kt("du_bao_nhieu_nam mac dinh = lua An Giang", hx.du_bao_nhieu_nam(3)["bo_du_lieu"] == "lua_an_giang"
       and hx.du_bao_nhieu_nam(3)["du_bao"][0]["nam"] == 2025)

    # ---- bo B: kiem tra doc lap theo dung bai toan t -> t+1 ----
    cot = hx.features
    supervised = dB.sort_values("nam").reset_index(drop=True).copy()
    supervised["nang_suat_ta_ha"] = supervised["nang_suat_ta_ha"].shift(-1)
    supervised["nam"] = supervised["nam"] + 1
    supervised = supervised.dropna().reset_index(drop=True)
    hang_cuoi = dB.iloc[-1]
    du_doan = hoi_quy(supervised, cot)  # fit tren cac cap nam t -> t+1
    hang_du_bao = hang_cuoi.copy(); hang_du_bao["nam"] = 2023
    mong_doi = du_doan(hang_du_bao)
    kq = hx.du_bao(2023, bo_du_lieu=B)
    kt("bo B: du bao nam tiep theo khop hoi quy numpy doc lap", abs(kq["nang_suat_du_bao"] - round(mong_doi, 2)) < 0.006, (kq["nang_suat_du_bao"], mong_doi))
    kq20 = hx.du_bao(2023, kich_ban_mua_phan_tram=-20, bo_du_lieu=B)
    hang_kb = hang_du_bao.copy(); hang_kb["mua_tong_mm"] *= 0.8
    kt("bo B: kich ban mua -20% khop hoi quy numpy", abs(kq20["nang_suat_du_bao"] - round(du_doan(hang_kb), 2)) < 0.006, kq20)
    kt("bo B: muc co so khong doi theo kich ban", kq20["nang_suat_co_so"] == kq["nang_suat_co_so"] == kq["nang_suat_du_bao"])
    nam_kt = int(dB["nam"].max()) - 2
    huan_luyen = supervised[supervised["nam"] < nam_kt]
    kiem_tra = supervised[supervised["nam"] >= nam_kt]
    f = hoi_quy(huan_luyen, cot)
    mae_doc_lap = float(np.mean([abs(f(r) - r["nang_suat_ta_ha"]) for _, r in kiem_tra.iterrows()]))
    kt("bo B: MAE kiem tra khop tinh doc lap (3 nam dich cuoi)", kq["sai_so_uoc_tinh"] == round(mae_doc_lap, 3), (kq["sai_so_uoc_tinh"], mae_doc_lap))
    kt("bo B: nam xa hon nam ke tiep -> loi chi duoc ngoai suy xu huong rieng", "xu huong" in hx.du_bao(2025, bo_du_lieu=B).get("loi", ""))
    kt("bo B: nam co du lieu thuc te tra ve so thuc", hx.du_bao(2015, bo_du_lieu=B)["nang_suat_du_bao"] == float(dB[dB["nam"] == 2015]["nang_suat_ta_ha"].iloc[0]))
    kt("bo B: giai_thich co day du thoi tiet", {"mua_tong_mm", "nhiet_tb_c", "ngay_nong"} <= set(hx.giai_thich(2015, bo_du_lieu=B)))
    rq = hx.tuong_quan("mua", "nang_suat", bo_du_lieu=B)
    kt("bo B: tuong_quan mua-nang suat khop numpy",
       rq["he_so_tuong_quan_pearson"] == round(float(np.corrcoef(dB["mua_tong_mm"], dB["nang_suat_ta_ha"])[0, 1]), 3) and rq["so_nam"] == 12, rq)

    # ---- bo 9 nam khong ton tai trong he thong (bi tu choi o buoc nhap) ----
    kt("bo 9 nam khong co trong he thong -> moi ham bao loi, khong du bao", "loi" in hx.du_bao(2023, bo_du_lieu="cao_su_binh_phuoc"))

    # ---- toa do thoi tiet theo bo ----
    urls = []
    that = hx.urllib.request.urlopen
    def gia(url, timeout=0):
        urls.append(url)
        return PhanHoiGia(b'{"daily": {"time": ["2026-01-01"], "temperature_2m_max": [30.0], "temperature_2m_min": [22.0], "precipitation_sum": [1.5]}}')
    hx.urllib.request.urlopen = gia
    hx.thoi_tiet_du_bao(1, bo_du_lieu=B); hx.thoi_tiet_du_bao(1)
    hx.urllib.request.urlopen = that
    kt("thoi tiet bo B dung toa do Thai Nguyen (21.6, 105.8)", "latitude=21.6&longitude=105.8" in urls[0], urls)
    kt("thoi tiet mac dinh dung toa do Long Xuyen", f"latitude={hx.LAT}&longitude={hx.LON}" in urls[1], urls)

    # ---- danh sach cho AI ----
    ds = hx.ds_bo_du_lieu()
    ma = [b["ma"] for b in ds["bo_du_lieu"]]
    kt("ds_bo_du_lieu liet ke ca 3 bo (bo co san dau, con lai theo ma), mac dinh lua An Giang",
       ma == ["lua_an_giang"] + sorted([A, B]) and ds["mac_dinh"] == "lua_an_giang", ma)
    tt = {b["ma"]: b["co_thoi_tiet"] for b in ds["bo_du_lieu"]}
    kt("co_thoi_tiet = du 3 cot thoi tiet: lua=True, A=False, B=True", tt == {"lua_an_giang": True, A: False, B: True}, tt)

    # ---- bo nho dem khong dung lai ket qua cu khi du lieu doi ----
    truoc = hx.du_bao(2023, bo_du_lieu=B)["nang_suat_du_bao"]
    bdl.xoa_bo(B)
    moi = bang(12, 2011, True, 2); moi["nang_suat_ta_ha"] += np.linspace(0, 6, 12); moi["san_luong_tan"] = moi["nang_suat_ta_ha"] * moi["dien_tich_ha"] / 10
    bdl.them_bo("Chè", "Thái Nguyên", nguon, moi, lat=21.6, lon=105.8, thang_bat_dau=5, thang_ket_thuc=11)
    sau = hx.du_bao(2023, bo_du_lieu=B)["nang_suat_du_bao"]
    kt("doi du lieu cung ma bo -> mo hinh duoc huan luyen lai (khong dung ket qua cu)", abs(sau - truoc) > 0.5, (truoc, sau))


if __name__ == "__main__":
    chay()
    print("\nKET QUA:", "TAT CA PASS" if not LOI else f"CO {len(LOI)} LOI: {LOI}")
    sys.exit(1 if LOI else 0)

