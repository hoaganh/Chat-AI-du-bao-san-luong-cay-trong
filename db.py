"""Luu tru du lieu quan ly nong trai bang SQLAlchemy.

Chon co so du lieu bang bien moi truong:
  DATABASE_URL = postgresql://user:matkhau@host:5432/ten_db   -> PostgreSQL (khi trien khai)
  (khong dat)  -> SQLite, file agfarm.db (hoac duong dan trong AGFARM_DB) - de chay may ca nhan / test
"""

import datetime
import json
import os

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger, Column, Float, ForeignKey, Integer, MetaData, String, Table, Text, UniqueConstraint, event, text,
)

THU_MUC = os.path.dirname(os.path.abspath(__file__))
TINH_TRANG = ["Tốt", "Cần theo dõi", "Cần xử lý"]
LOAI_CHI_PHI = ["Giống", "Phân bón", "Thuốc BVTV", "Nhân công", "Khác"]
NHAN_MAU = "[MẪU]"


def _lay_url():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgres://"):  # kieu cu cua mot so dich vu; SQLAlchemy can 'postgresql://'
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            # chi dinh ro driver psycopg2: cac ban SQLAlchemy khac nhau chon driver mac dinh khac nhau
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url
    duong_dan = os.environ.get("AGFARM_DB") or os.path.join(THU_MUC, "agfarm.db")
    return f"sqlite:///{duong_dan}"


DB_URL = _lay_url()
engine = sa.create_engine(DB_URL, pool_pre_ping=True)
LA_SQLITE = engine.dialect.name == "sqlite"

if LA_SQLITE:
    @event.listens_for(engine, "connect")
    def _bat_khoa_ngoai(ket_noi, _):
        con_tro = ket_noi.cursor()
        con_tro.execute("PRAGMA foreign_keys = ON")  # SQLite mac dinh khong kiem tra khoa ngoai
        con_tro.close()

metadata = MetaData()
_thua = Table(
    "thua", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ten", Text, nullable=False),
    Column("cay_trong", Text, server_default="Lúa"),
    Column("giong", Text, server_default=""),
    Column("dien_tich_ha", Float, nullable=False),
    Column("ngay_gieo", Text, server_default=""),
    Column("tinh_trang", Text, server_default="Tốt"),
    Column("ghi_chu", Text, server_default=""),
    Column("la_mau", Integer, server_default="0"),
)
_mua_vu = Table(
    "mua_vu", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("thua_id", Integer, ForeignKey("thua.id", ondelete="CASCADE"), nullable=False),
    Column("nam", Integer, nullable=False),
    Column("ten_vu", Text, server_default=""),
    Column("san_luong_tan", Float, nullable=False),
    Column("gia_ban_dong_kg", Float, nullable=False),
    Column("ghi_chu", Text, server_default=""),
)
_chi_phi = Table(
    "chi_phi", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("thua_id", Integer, ForeignKey("thua.id", ondelete="CASCADE"), nullable=False),
    Column("nam", Integer, nullable=False),
    Column("loai", Text, nullable=False),
    Column("so_tien", BigInteger, nullable=False),  # dong VND, co the vuot 2 ty nen dung BigInteger
    Column("ngay", Text, server_default=""),
    Column("ghi_chu", Text, server_default=""),
)
_chan_doan = Table(
    "chan_doan", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("thua_id", Integer, ForeignKey("thua.id", ondelete="SET NULL"), nullable=True),
    Column("ngay", Text, nullable=False),
    Column("ten_anh", Text, server_default=""),
    Column("mo_ta", Text, server_default=""),
    Column("ket_qua", Text, nullable=False),
)
_phien_chat = Table(
    "phien_chat", metadata,
    Column("phien_id", String(64), primary_key=True),
    Column("lich_su", Text, nullable=False),  # JSON lich su hoi thoai gui Gemini
    Column("cap_nhat", Text, nullable=False),
)

_bo_du_lieu = Table(
    "bo_du_lieu", metadata,
    Column("ma", String(80), primary_key=True),
    Column("cay", Text, nullable=False),
    Column("tinh", Text, nullable=False),
    Column("nguon", Text, nullable=False),          # nguon du lieu: bat buoc (de bai: khong ro nguon = 0 diem)
    Column("lat", Float, nullable=True),            # toa do de lay thoi tiet; khong co thi khong dung thoi tiet
    Column("lon", Float, nullable=True),
    Column("thang_bat_dau", Integer, nullable=True),
    Column("thang_ket_thuc", Integer, nullable=True),
    Column("tao_luc", Text, nullable=False),
)
_du_lieu_nam = Table(
    "du_lieu_nam", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ma", String(80), ForeignKey("bo_du_lieu.ma", ondelete="CASCADE"), nullable=False),
    Column("nam", Integer, nullable=False),
    Column("dien_tich_ha", Float, nullable=False),
    Column("san_luong_tan", Float, nullable=False),
    Column("nang_suat_ta_ha", Float, nullable=False),
    Column("mua_tong_mm", Float, nullable=True),
    Column("nhiet_tb_c", Float, nullable=True),
    Column("ngay_nong", Float, nullable=True),
    UniqueConstraint("ma", "nam"),
)


def _doc(sql, tham_so=None):
    with engine.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), tham_so or {})]


def _ghi(sql, tham_so=None):
    """Chay cau lenh ghi, tra ve so dong bi anh huong."""
    with engine.begin() as c:
        return c.execute(text(sql), tham_so or {}).rowcount


def _them(bang, gia_tri):
    with engine.begin() as c:
        return c.execute(sa.insert(bang).values(**gia_tri)).inserted_primary_key[0]


def khoi_tao():
    metadata.create_all(engine)


# ---------- Thua ruong ----------
def them_thua(ten, cay_trong, giong, dien_tich_ha, ngay_gieo, tinh_trang, ghi_chu="", la_mau=0):
    return _them(_thua, dict(
        ten=ten, cay_trong=cay_trong, giong=giong, dien_tich_ha=float(dien_tich_ha),
        ngay_gieo=str(ngay_gieo), tinh_trang=tinh_trang, ghi_chu=ghi_chu, la_mau=int(la_mau),
    ))


def ds_thua():
    return _doc("SELECT * FROM thua ORDER BY id")


def xoa_thua(thua_id):
    return _ghi("DELETE FROM thua WHERE id = :id", {"id": thua_id})


def cap_nhat_tinh_trang(thua_id, tinh_trang):
    return _ghi("UPDATE thua SET tinh_trang = :tt WHERE id = :id", {"tt": tinh_trang, "id": thua_id})


# ---------- Mua vu / doanh thu ----------
def them_mua_vu(thua_id, nam, ten_vu, san_luong_tan, gia_ban_dong_kg, ghi_chu=""):
    return _them(_mua_vu, dict(
        thua_id=thua_id, nam=int(nam), ten_vu=ten_vu, san_luong_tan=float(san_luong_tan),
        gia_ban_dong_kg=float(gia_ban_dong_kg), ghi_chu=ghi_chu,
    ))


def ds_mua_vu():
    return _doc(
        "SELECT m.*, t.ten AS ten_thua FROM mua_vu m JOIN thua t ON t.id = m.thua_id "
        "ORDER BY m.nam DESC, m.id DESC"
    )


def xoa_mua_vu(mua_vu_id):
    return _ghi("DELETE FROM mua_vu WHERE id = :id", {"id": mua_vu_id})


# ---------- Chi phi ----------
def them_chi_phi(thua_id, nam, loai, so_tien, ngay="", ghi_chu=""):
    return _them(_chi_phi, dict(
        thua_id=thua_id, nam=int(nam), loai=loai, so_tien=int(so_tien), ngay=str(ngay), ghi_chu=ghi_chu,
    ))


def ds_chi_phi():
    return _doc(
        "SELECT c.*, t.ten AS ten_thua FROM chi_phi c JOIN thua t ON t.id = c.thua_id "
        "ORDER BY c.nam DESC, c.id DESC"
    )


def xoa_chi_phi(chi_phi_id):
    return _ghi("DELETE FROM chi_phi WHERE id = :id", {"id": chi_phi_id})


# ---------- Chan doan benh ----------
def them_chan_doan(thua_id, ten_anh, mo_ta, ket_qua):
    return _them(_chan_doan, dict(
        thua_id=thua_id, ngay=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        ten_anh=ten_anh, mo_ta=mo_ta, ket_qua=ket_qua,
    ))


def ds_chan_doan(gioi_han=50):
    return _doc(
        "SELECT d.*, t.ten AS ten_thua FROM chan_doan d LEFT JOIN thua t ON t.id = d.thua_id "
        "ORDER BY d.id DESC LIMIT :gh",
        {"gh": int(gioi_han)},
    )


def dem_chan_doan():
    """Tong so ban ghi chan doan da luu (khong gioi han 50 dong nhu ds_chan_doan)."""
    return int(_doc("SELECT COUNT(*) AS n FROM chan_doan")[0]["n"])


# ---------- Hoi thoai chat (luu phien de nho ngu canh giua cac lan goi API) ----------
def doc_phien(phien_id):
    rows = _doc("SELECT lich_su FROM phien_chat WHERE phien_id = :p", {"p": phien_id})
    return json.loads(rows[0]["lich_su"]) if rows else None


def luu_phien(phien_id, lich_su):
    noi_dung = json.dumps(lich_su, ensure_ascii=False)
    bay_gio = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as c:
        da_cap_nhat = c.execute(
            text("UPDATE phien_chat SET lich_su = :l, cap_nhat = :t WHERE phien_id = :p"),
            {"l": noi_dung, "t": bay_gio, "p": phien_id},
        ).rowcount
        if not da_cap_nhat:
            c.execute(sa.insert(_phien_chat).values(phien_id=phien_id, lich_su=noi_dung, cap_nhat=bay_gio))


def xoa_phien(phien_id):
    return _ghi("DELETE FROM phien_chat WHERE phien_id = :p", {"p": phien_id})


# ---------- Bo du lieu (cay + tinh) do nguoi dung them ----------
def ds_bo_du_lieu_db():
    return _doc("SELECT * FROM bo_du_lieu ORDER BY ma")


def doc_bo_du_lieu_db(ma):
    """Tra ve (meta, danh sach dong theo nam) hoac None neu khong co."""
    meta = _doc("SELECT * FROM bo_du_lieu WHERE ma = :m", {"m": ma})
    if not meta:
        return None
    dong = _doc(
        "SELECT nam, dien_tich_ha, san_luong_tan, nang_suat_ta_ha, mua_tong_mm, nhiet_tb_c, ngay_nong "
        "FROM du_lieu_nam WHERE ma = :m ORDER BY nam", {"m": ma})
    return meta[0], dong


def them_bo_du_lieu_db(meta, dong):
    """Luu bo du lieu va cac nam trong MOT giao dich (loi giua chung thi khong luu gi)."""
    with engine.begin() as c:
        c.execute(sa.insert(_bo_du_lieu).values(**meta))
        if dong:
            c.execute(sa.insert(_du_lieu_nam), [dict(ma=meta["ma"], **d) for d in dong])


def xoa_bo_du_lieu_db(ma):
    return _ghi("DELETE FROM bo_du_lieu WHERE ma = :m", {"m": ma})


# ---------- Tong hop (moi con so tinh o day, khong de AI tu tinh) ----------
def ds_nam():
    rows = _doc("SELECT nam FROM mua_vu UNION SELECT nam FROM chi_phi ORDER BY nam DESC")
    return [r["nam"] for r in rows]


_SQL_TONG_HOP = """
SELECT t.id, t.ten, t.dien_tich_ha,
  COALESCE((SELECT SUM(m.san_luong_tan * 1000 * m.gia_ban_dong_kg) FROM mua_vu m
            WHERE m.thua_id = t.id AND (CAST(:nam AS INTEGER) IS NULL OR m.nam = CAST(:nam AS INTEGER))), 0) AS doanh_thu,
  COALESCE((SELECT SUM(c.so_tien) FROM chi_phi c
            WHERE c.thua_id = t.id AND (CAST(:nam AS INTEGER) IS NULL OR c.nam = CAST(:nam AS INTEGER))), 0) AS chi_phi
FROM thua t ORDER BY t.id
"""


def tong_hop(nam=None):
    rows = _doc(_SQL_TONG_HOP, {"nam": nam})
    for r in rows:
        # PostgreSQL tra Decimal cho SUM cua so nguyen lon -> doi ve kieu Python thong thuong
        r["doanh_thu"] = float(r["doanh_thu"])
        r["chi_phi"] = int(r["chi_phi"])
        r["loi_nhuan"] = r["doanh_thu"] - r["chi_phi"]
        r["loi_nhuan_tren_ha"] = r["loi_nhuan"] / r["dien_tich_ha"] if r["dien_tich_ha"] else 0.0
    tong = {
        "dien_tich_ha": sum(r["dien_tich_ha"] for r in rows),
        "doanh_thu": sum(r["doanh_thu"] for r in rows),
        "chi_phi": sum(r["chi_phi"] for r in rows),
    }
    tong["loi_nhuan"] = tong["doanh_thu"] - tong["chi_phi"]
    return {"theo_thua": rows, "tong": tong}


def co_du_lieu_mau():
    return _doc("SELECT COUNT(*) AS n FROM thua WHERE la_mau = 1")[0]["n"] > 0


def bao_cao_loi_nhuan(nam=None):
    """Ham cho chat goi: doanh thu, chi phi, loi nhuan (dong VND) tu du lieu quan ly mua vu."""
    try:
        nam = int(nam) if nam not in (None, "", 0) else None
    except (TypeError, ValueError):
        nam = None
    if not ds_thua():
        return {"loi": "Chua co du lieu quan ly mua vu (chua co thua ruong nao)."}
    th = tong_hop(nam)
    return {
        "nam": nam if nam else "tat ca cac nam",
        "don_vi": "dong (VND)",
        "so_thua": len(th["theo_thua"]),
        "tong_doanh_thu": round(th["tong"]["doanh_thu"]),
        "tong_chi_phi": round(th["tong"]["chi_phi"]),
        "loi_nhuan": round(th["tong"]["loi_nhuan"]),
        "theo_thua": [
            {
                "thua": r["ten"],
                "dien_tich_ha": r["dien_tich_ha"],
                "doanh_thu": round(r["doanh_thu"]),
                "chi_phi": round(r["chi_phi"]),
                "loi_nhuan": round(r["loi_nhuan"]),
            }
            for r in th["theo_thua"]
        ],
        "co_du_lieu_mau": co_du_lieu_mau(),
    }


# ---------- Du lieu mau (chi de xem thu giao dien, la gia dinh) ----------
def nap_mau():
    """Nap 3 thua + mua vu + chi phi MAU. Tra ve False neu da co du lieu mau."""
    if co_du_lieu_mau():
        return False
    mau = [
        ("Thửa A1", 2.5, "Tốt", 15.5, 7200, [3_000_000, 10_500_000, 4_200_000, 12_000_000]),
        ("Thửa A2", 1.8, "Cần theo dõi", 10.4, 7200, [2_200_000, 7_600_000, 3_000_000, 8_500_000]),
        ("Thửa B1", 3.2, "Cần xử lý", 18.9, 7200, [3_800_000, 13_400_000, 6_100_000, 15_000_000]),
    ]
    loai = ["Giống", "Phân bón", "Thuốc BVTV", "Nhân công"]
    for ten, ha, tt, san_luong, gia, chi in mau:
        tid = them_thua(f"{ten} {NHAN_MAU}", "Lúa", "Giống mẫu", ha, "2025-05-10", tt,
                        f"{NHAN_MAU} dữ liệu giả định để xem thử", la_mau=1)
        them_mua_vu(tid, 2025, "Hè Thu", san_luong, gia, f"{NHAN_MAU} giả định")
        for lo, tien in zip(loai, chi):
            them_chi_phi(tid, 2025, lo, tien, "2025-06-01", f"{NHAN_MAU} giả định")
    return True


def xoa_mau():
    return _ghi("DELETE FROM thua WHERE la_mau = 1")
