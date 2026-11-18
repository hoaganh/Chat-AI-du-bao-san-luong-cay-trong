"""Kiem thu quan ly bo du lieu cay-tinh. Chay: python test_bo_du_lieu.py (khong can mang).
LUU Y: du lieu trong file nay la SO TONG HOP chi de kiem tra logic, KHONG phai so lieu nong nghiep that."""
import os
import sys
import tempfile

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)
if not os.environ.get("DATABASE_URL"):
    os.environ["AGFARM_DB"] = os.path.join(tempfile.mkdtemp(prefix="agfarm_bdl_"), "test.db")

import datetime  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import urllib.error  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sqlalchemy as sa  # noqa: E402

import bo_du_lieu as bdl  # noqa: E402
import db  # noqa: E402

LOI = []


def kt(ten, dieu_kien, chi_tiet=""):
    dat = bool(dieu_kien)
    them = "" if dat or (isinstance(chi_tiet, str) and not chi_tiet) else f"  -> {chi_tiet}"
    print(("PASS  " if dat else "FAIL  ") + ten + them)
    if not dat:
        LOI.append(ten)


def bang_tong_hop(n=10, nam_dau=2013):
    nam = np.arange(nam_dau, nam_dau + n)
    dien_tich = 1000.0 + 10 * np.arange(n)
    san_luong = dien_tich * (5.0 + 0.05 * np.arange(n))          # tan; nang suat = san luong*10/dien tich
    return pd.DataFrame({"nam": nam, "dien_tich_ha": dien_tich, "san_luong_tan": san_luong})


class PhanHoiGia:
    def __init__(self, noi_dung): self.noi_dung = noi_dung
    def read(self): return self.noi_dung
    def __enter__(self): return self
    def __exit__(self, *a): return False


def thoi_tiet_gia(nam_dau, nam_cuoi):
    ngay = pd.date_range(f"{nam_dau}-01-01", f"{nam_cuoi}-12-31")
    return json.dumps({"daily": {
        "time": [d.strftime("%Y-%m-%d") for d in ngay],
        "precipitation_sum": [1.0] * len(ngay),
        "temperature_2m_mean": [28.0] * len(ngay),
        "temperature_2m_max": [36.0 if d.day == 1 else 30.0 for d in ngay],
    }}).encode()


def chay():
    # ---- tien ich ----
    kt("mau_csv chi co tieu de, khong co so lieu", bdl.mau_csv() == "nam,dien_tich_ha,san_luong_tan,nang_suat_ta_ha,mua_tong_mm,nhiet_tb_c,ngay_nong\n")
    kt("tao_ma bo dau tieng Viet", bdl.tao_ma("Cà phê", "Đắk Lắk") == "ca_phe_dak_lak", bdl.tao_ma("Cà phê", "Đắk Lắk"))
    kt("bo mac dinh lua An Giang 10 nam", len(bdl.lay_bo()[1]) == 10 and bdl.lay_bo()[0]["co_san"] is True)

    # ---- kiem tra du lieu ----
    d, loi, cb = bdl.kiem_tra_va_chuan_hoa(bang_tong_hop())
    kt("du lieu hop le qua kiem tra", d is not None and not loi, loi)
    kt("khong co cot nang suat -> tu tinh = san luong x 10 / dien tich",
       abs(d["nang_suat_ta_ha"].iloc[0] - 50.0) < 1e-9 and any("tính năng suất" in c for c in cb), (d["nang_suat_ta_ha"].iloc[0], cb))
    kt("cot thoi tiet vang -> NaN", d[bdl.COT_THOI_TIET].isna().all().all())
    kt("tieu de viet hoa / thua khoang trang van nhan", bdl.kiem_tra_va_chuan_hoa(bang_tong_hop().rename(columns=lambda c: f" {c.upper()} "))[0] is not None)

    def loi_cua(df): return bdl.kiem_tra_va_chuan_hoa(df)[1]
    kt("thieu cot bat buoc -> loi", any("Thiếu cột" in x for x in loi_cua(bang_tong_hop().drop(columns=["san_luong_tan"]))))
    vn = bang_tong_hop().astype({"san_luong_tan": object}); vn.loc[2, "san_luong_tan"] = "4.073.742"
    kt("so kieu Viet Nam '4.073.742' -> loi chi ro dong 4", any("dòng [4]" in x for x in loi_cua(vn)), loi_cua(vn))
    trung = bang_tong_hop(); trung.loc[3, "nam"] = trung.loc[2, "nam"]
    kt("nam trung -> loi", any("trùng" in x for x in loi_cua(trung)), loi_cua(trung))
    thieu = bang_tong_hop().drop(index=4)
    kt("thieu nam giua chuoi -> loi nam khong lien tuc", any("không liên tục" in x for x in loi_cua(thieu)), loi_cua(thieu))
    kt("it hon 10 nam -> loi", any("ít nhất 10" in x for x in loi_cua(bang_tong_hop(7))))
    kt("9 nam -> BI TU CHOI (khong chi canh bao)", any("ít nhất 10" in x for x in loi_cua(bang_tong_hop(9))))
    am = bang_tong_hop(); am.loc[1, "dien_tich_ha"] = -5
    kt("dien tich am -> loi", any("lớn hơn 0" in x for x in loi_cua(am)))
    tuong_lai = bang_tong_hop(10, datetime.date.today().year - 5)
    kt("nam o tuong lai -> loi", any("Năm phải từ" in x for x in loi_cua(tuong_lai)))
    o_trong = bang_tong_hop(); o_trong.loc[2, "dien_tich_ha"] = np.nan
    kt("o trong cot bat buoc -> loi", any("ô trống" in x for x in loi_cua(o_trong)))
    lech = bang_tong_hop(); lech["nang_suat_ta_ha"] = lech["san_luong_tan"] * 10 / lech["dien_tich_ha"]; lech.loc[5, "nang_suat_ta_ha"] *= 1.5
    d2, l2, c2 = bdl.kiem_tra_va_chuan_hoa(lech)
    kt("nang suat lech > 2% -> chap nhan nhung canh bao, dung nang suat nguoi dung", d2 is not None
       and any("lệch" in c for c in c2) and abs(d2["nang_suat_ta_ha"].iloc[5] - lech["nang_suat_ta_ha"].iloc[5]) < 1e-9, c2)
    nhay = bang_tong_hop(); nhay.loc[6, "san_luong_tan"] *= 2
    kt("nang suat nhay > 30% -> canh bao", any("30%" in c for c in bdl.kiem_tra_va_chuan_hoa(nhay)[2]))
    tt = bang_tong_hop(); tt["mua_tong_mm"] = 1000.0; tt["nhiet_tb_c"] = 27.0; tt["ngay_nong"] = 3.0; tt.loc[4, "ngay_nong"] = np.nan
    kt("thoi tiet thieu 1 nam -> canh bao khong dung duoc du bao theo thoi tiet", any("không dùng được" in c for c in bdl.kiem_tra_va_chuan_hoa(tt)[2]))
    xau = bang_tong_hop(); xau["nhiet_tb_c"] = 80.0; xau["mua_tong_mm"] = 1000.0; xau["ngay_nong"] = 3.0
    kt("nhiet do vo ly -> loi", any("nhiet_tb_c" in x for x in loi_cua(xau)))

    # ---- thoi tiet tu Open-Meteo (gia lap mang, so tay) ----
    that_urlopen = bdl.urllib.request.urlopen
    bdl.urllib.request.urlopen = lambda url, timeout=0: PhanHoiGia(thoi_tiet_gia(2013, 2022))
    r = bdl.thoi_tiet_lich_su(10.0, 105.0, 2013, 2022, 5, 11)
    nam_2016 = r["du_lieu"][2016]
    kt("thoi tiet: mua mua vu thang 5-11 = 214 ngay x 1mm", nam_2016["mua_tong_mm"] == 214.0, nam_2016)
    kt("thoi tiet: nhiet TB 28,0 va 7 ngay nong (ngay mung 1 moi thang)", nam_2016["nhiet_tb_c"] == 28.0 and nam_2016["ngay_nong"] == 7, nam_2016)
    kt("thoi tiet: du 10 nam", sorted(r["du_lieu"]) == list(range(2013, 2023)))
    bdl.urllib.request.urlopen = lambda url, timeout=0: (_ for _ in ()).throw(urllib.error.URLError("mat mang"))
    kt("mat mang -> loi, khong nem ngoai le", "loi" in bdl.thoi_tiet_lich_su(10.0, 105.0, 2013, 2022, 5, 11))
    kt("nam hien tai chua day du -> loi", "loi" in bdl.thoi_tiet_lich_su(10.0, 105.0, 2020, datetime.date.today().year, 5, 11))
    bdl.urllib.request.urlopen = that_urlopen

    # ---- them / doc / xoa trong co so du lieu ----
    db.khoi_tao()
    base = bang_tong_hop()
    kt("nguon qua ngan -> loi", "loi" in bdl.them_bo("Ngô", "Sơn La", "abc", base))
    kt("thieu ten cay -> loi", "loi" in bdl.them_bo("", "Sơn La", "Niên giám Sơn La 2024", base))
    kt("chi nhap vi do -> loi", "loi" in bdl.them_bo("Ngô", "Sơn La", "Niên giám Sơn La 2024", base, lat=21.3))
    kt("thang mua vu sai thu tu -> loi", "loi" in bdl.them_bo("Ngô", "Sơn La", "Niên giám Sơn La 2024", base, thang_bat_dau=9, thang_ket_thuc=3))
    kt("trung bo co san lua An Giang -> loi 'Da co'", bdl.them_bo("Lúa", "An Giang", "Niên giám An Giang 2024", base).get("loi", "").startswith("Da co bo du lieu"))
    kt("du lieu loi (thieu nam) -> khong luu", "loi" in bdl.them_bo("Ngô", "Sơn La", "Niên giám Sơn La 2024", base.drop(index=3)) and bdl.ds_bo().__len__() == 1)
    kq = bdl.them_bo("Ngô", "Sơn La", "Niên giám thống kê tỉnh Sơn La 2024 (giả lập để test)", base)
    kt("them bo hop le", kq.get("ma") == "ngo_son_la" and kq["so_nam"] == 10 and kq["co_thoi_tiet"] is False, kq)
    meta, d = bdl.lay_bo("ngo_son_la")
    kt("doc lai khop du lieu da luu", list(d["nam"]) == list(range(2013, 2023)) and abs(d["nang_suat_ta_ha"].iloc[3] - 51.5) < 1e-9
       and abs(d["san_luong_tan"].iloc[0] - base["san_luong_tan"].iloc[0]) < 1e-6, d.head(4))
    kt("co NaN o cot thoi tiet khi doc lai", d[bdl.COT_THOI_TIET].isna().all().all())
    kt("ds_bo co 2 bo, bo moi khong phai co san", [b["ma"] for b in bdl.ds_bo()] == ["lua_an_giang", "ngo_son_la"]
       and bdl.ds_bo()[1]["co_san"] is False and bdl.ds_bo()[1]["co_thoi_tiet"] is False)
    kt("them lai cung cay-tinh -> loi", bdl.them_bo("Ngô", "Sơn La", "Niên giám thống kê tỉnh Sơn La 2024", base).get("loi", "").startswith("Da co"))
    try:
        bdl.lay_bo("khong_ton_tai"); kt("bo khong ton tai -> KhongCoBo", False)
    except bdl.KhongCoBo as e:
        kt("bo khong ton tai -> KhongCoBo kem danh sach bo co", "lua_an_giang" in str(e) and "ngo_son_la" in str(e), str(e))

    # tu lay thoi tiet
    bdl.urllib.request.urlopen = lambda url, timeout=0: PhanHoiGia(thoi_tiet_gia(2013, 2022))
    kq = bdl.them_bo("Chè", "Thái Nguyên", "Niên giám thống kê Thái Nguyên (giả lập để test)", base, lat=21.6, lon=105.8,
                     thang_bat_dau=5, thang_ket_thuc=11, tu_lay_thoi_tiet=True)
    d_che = bdl.lay_bo("che_thai_nguyen")[1]
    kt("tu lay thoi tiet: dien du 3 cot cho 10 nam", kq.get("co_thoi_tiet") is True and (d_che["mua_tong_mm"] == 214.0).all()
       and (d_che["ngay_nong"] == 7).all(), kq)
    kt("tu lay thoi tiet: ghi chu nguon Open-Meteo", any("Open-Meteo" in c for c in kq["canh_bao"]), kq)
    kt("tu lay thoi tiet nhung thieu toa do -> loi", "loi" in bdl.them_bo("Cao su", "Bình Phước", "Niên giám Bình Phước (giả lập để test)", base, tu_lay_thoi_tiet=True))
    bdl.urllib.request.urlopen = lambda url, timeout=0: (_ for _ in ()).throw(urllib.error.URLError("mat mang"))
    kq = bdl.them_bo("Tiêu", "Gia Lai", "Niên giám Gia Lai 2024 (giả lập để test)", base, lat=13.9, lon=108.0,
                     thang_bat_dau=5, thang_ket_thuc=11, tu_lay_thoi_tiet=True)
    kt("lay thoi tiet that bai -> loi va KHONG luu bo", "loi" in kq and "tieu_gia_lai" not in [b["ma"] for b in bdl.ds_bo()], kq)
    bdl.urllib.request.urlopen = that_urlopen

    # nguyen tu: loi giua chung thi khong luu gi
    meta_xau = {"ma": "bo_loi", "cay": "X", "tinh": "Y", "nguon": "nguon test dai du", "lat": None, "lon": None,
                "thang_bat_dau": None, "thang_ket_thuc": None, "tao_luc": "2026-01-01 00:00:00"}
    dong_xau = [dict(nam=2020, dien_tich_ha=1.0, san_luong_tan=1.0, nang_suat_ta_ha=10.0, mua_tong_mm=None, nhiet_tb_c=None, ngay_nong=None)] * 2
    try:
        db.them_bo_du_lieu_db(meta_xau, dong_xau); kt("trung (bo, nam) bi chan", False)
    except sa.exc.IntegrityError:
        kt("trung (bo, nam) bi chan boi rang buoc", True)
    kt("giao dich hoan tac: khong con bo 'bo_loi'", db.doc_bo_du_lieu_db("bo_loi") is None)

    # xoa
    so_dong_truoc = db._doc("SELECT COUNT(*) AS n FROM du_lieu_nam WHERE ma = :m", {"m": "ngo_son_la"})[0]["n"]
    kt("truoc khi xoa co 10 dong nam", so_dong_truoc == 10, so_dong_truoc)
    kt("xoa bo -> da_xoa", bdl.xoa_bo("ngo_son_la") == {"da_xoa": "ngo_son_la"})
    kt("xoa bo -> cac dong nam bi xoa theo (CASCADE)", db._doc("SELECT COUNT(*) AS n FROM du_lieu_nam WHERE ma = :m", {"m": "ngo_son_la"})[0]["n"] == 0)
    kt("xoa bo khong ton tai -> loi", "loi" in bdl.xoa_bo("ngo_son_la"))
    kt("khong xoa duoc bo co san", "loi" in bdl.xoa_bo("lua_an_giang") and len(bdl.lay_bo()[1]) == 10)


if __name__ == "__main__":
    chay()
    print("\nKET QUA:", "TAT CA PASS" if not LOI else f"CO {len(LOI)} LOI: {LOI}")
    sys.exit(1 if LOI else 0)
