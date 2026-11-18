"""
Kiem thu tu dong cho AgFarm AI. Chay:  python test_he_thong.py   (hoac: pytest test_he_thong.py)
Khong can mang, khong can API key: Gemini va Open-Meteo duoc gia lap, DB dung thu muc tam.
"""
import os
import sys
import tempfile
import urllib.error

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)
_TMP = tempfile.mkdtemp(prefix="agfarm_test_")
os.environ["AGFARM_DB"] = os.path.join(_TMP, "test.db")

import chat_logic  # noqa: E402
import ham_xu_ly as hx  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

LOI = []


def kt(ten, dieu_kien, chi_tiet=""):
    print(("PASS  " if dieu_kien else "FAIL  ") + ten + ("" if dieu_kien or not chi_tiet else f"  -> {chi_tiet}"))
    if not dieu_kien:
        LOI.append(ten)


_NGAY = [("2026-10-11", 36.2, 26.0, 0.0), ("2026-10-12", 33.0, 25.5, 62.0), ("2026-10-13", 31.0, 25.0, 3.5)]
THOI_TIET_GIA = {
    "tong_mua_mm": 65.5, "nhiet_cao_trung_binh_c": 33.4, "so_ngay_nong_tren_35c": 1,
    "chi_tiet": [{"ngay": a, "nhiet_cao_c": b, "nhiet_thap_c": c, "mua_mm": d} for a, b, c, d in _NGAY],
}


def app_moi():
    hx.thoi_tiet_du_bao = lambda so_ngay=7: THOI_TIET_GIA
    at = AppTest.from_file(os.path.join(THU_MUC, "app.py"), default_timeout=60)
    at.run()
    return at


def nhan(at):
    return {m.label: m.value for m in at.metric}


def chay_tat_ca():
    # ---------- Giao dien khi CHUA co du lieu quan ly: khong duoc hien so 0 gia ----------
    at = app_moi()
    kt("trang chu chay khong loi", not at.exception, [e.value for e in at.exception])

    # ---------- Mo hinh va ham tinh toan ----------
    mae = hx.MAE_KIEM_TRA
    kt("MAE baseline 3 nam walk-forward = 0,846", abs(mae["mae_baseline"] - 0.846) < 0.0015, mae)
    kt("MAE Linear Regression target nam ke tiep = 2,039", abs(mae["mae_linear"] - 2.039) < 0.0015, mae)
    co_so = hx.du_bao(2025)
    kb = hx.du_bao(2025, -20)
    kt("khong kich ban: muc co so = muc du bao", co_so["nang_suat_co_so"] == co_so["nang_suat_du_bao"], co_so)
    kt("kich ban mua -20%: thap hon muc co so", kb["nang_suat_du_bao"] < kb["nang_suat_co_so"], kb)
    kt("chenh lech do code tinh dung", kb["chenh_lech_so_voi_co_so"] == round(kb["nang_suat_du_bao"] - kb["nang_suat_co_so"], 2), kb)
    kt("ghi chu noi dung nam huan luyen 2015-2024", "2015-2024" in kb["ghi_chu"] and "2018" not in kb["ghi_chu"], kb["ghi_chu"])
    kt("nam truoc du lieu (2012) -> loi, khong du bao", "loi" in hx.du_bao(2012))
    kt("nam xa (2030) -> loi, khong du bao", "loi" in hx.du_bao(2030))
    kt("nam co so lieu thuc (2020) = 62,99", hx.du_bao(2020)["nang_suat_du_bao"] == 62.99)
    kt("xu huong 2020-2024 la TANG", "TANG" in hx.lich_su(2020, 2024)["xu_huong_nang_suat"])
    kt("giai_thich nam ngoai du lieu -> loi", "loi" in hx.giai_thich(2030))

    def mat_mang(*a, **k):
        raise urllib.error.URLError("mat mang gia lap")
    thuc = hx.__dict__.pop("thoi_tiet_du_bao")  # bo ban gia lap de test ham that
    import importlib
    importlib.reload(hx)
    bak, hx.urllib.request.urlopen = hx.urllib.request.urlopen, mat_mang
    try:
        kt("Open-Meteo loi mang -> tra {'loi'}, khong crash", "loi" in hx.thoi_tiet_du_bao(3))
    finally:
        hx.urllib.request.urlopen = bak

    # ---------- Dieu phoi chat (Gemini gia lap): chi goi duoc ham trong danh sach cho phep ----------
    kich_ban = [
        {"candidates": [{"content": {"parts": [{"functionCall": {"name": "du_bao", "args": {"nam": 2025, "kich_ban_mua_phan_tram": -20}}}]}}]},
        {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
    ]
    chat_logic.goi_gemini = lambda ls: kich_ban.pop(0)
    nk = []
    tra_loi, ls = chat_logic.hoi("kich ban mua", nhat_ky=nk, in_nhat_ky=False)
    ket_qua_ham = ls[2]["parts"][0]["functionResponse"]["response"]["result"]
    kt("chat: ham that duoc chay voi dung tham so", nk == [{"ham": "du_bao", "tham_so": {"nam": 2025, "kich_ban_mua_phan_tram": -20}}], nk)
    kt("chat: ket qua ham (co ca muc co so) duoc gui lai cho AI",
       ket_qua_ham["nang_suat_du_bao"] == 65.58 and ket_qua_ham["nang_suat_co_so"] == 67.46, ket_qua_ham)
    for ten_ham, tham_so in [("xoa_het_du_lieu", {}), ("du_bao", {"tham_so_la": 1})]:
        kich_ban = [
            {"candidates": [{"content": {"parts": [{"functionCall": {"name": ten_ham, "args": tham_so}}]}}]},
            {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        ]
        _, ls = chat_logic.hoi("x", in_nhat_ky=False)
        kt(f"chat: goi sai '{ten_ham}' bi chan, tra loi thay vi crash", "loi" in ls[2]["parts"][0]["functionResponse"]["response"]["result"])
    kt("moi cong cu khai bao deu co ham tuong ung",
       sorted(t["name"] for t in chat_logic.KHAI_BAO_HAM) == sorted(chat_logic.CAC_HAM))

    kich_ban = [
        {"candidates": [{"content": {"parts": [{"functionCall": {"name": "du_bao", "args": {"nam": 2025}}}]}}]},
        {"candidates": [{"content": {"parts": [{"text": "Năng suất năm 2025 chắc chắn là 999 tạ/ha."}]}}]},
    ]
    chat_logic.goi_gemini = lambda ls: kich_ban.pop(0)
    tra_loi, _ = chat_logic.hoi("Dự báo năng suất", in_nhat_ky=False)
    ns_that = hx.du_bao(2025)["nang_suat_du_bao"]
    kt("chat chan con so khong co trong ket qua ham, backend dung cau tu JSON cua ham du bao",
       "999" not in tra_loi and f"{str(ns_that).replace('.', ',')} tạ/ha" in tra_loi, tra_loi)

    # ---------- Giao dien: moi trang chay khong loi ----------
    at = app_moi()
    for trang in ["Tổng quan", "Dự báo năng suất", "Mô hình AI", "Trợ lý AI"]:
        at.sidebar.radio(key="trang").set_value(trang).run()
        kt(f"trang '{trang}' chay khong loi", not at.exception, [e.value for e in at.exception])
    at.sidebar.radio(key="trang").set_value("Dự báo năng suất").run()
    at.slider(key="du_bao_mua").set_value(-20).run()
    n = nhan(at)
    kt("trang du bao -20% mua: hien 65,58", n.get("Dự báo (Linear Regression)") == "65,58 tạ/ha", n)
    def hoi_loi(*a, **k):
        raise RuntimeError("loi gia lap")
    chat_logic.hoi = hoi_loi
    at = app_moi()
    at.sidebar.radio(key="trang").set_value("Trợ lý AI").run()
    at.chat_input[0].set_value("xin chao").run()
    kt("chat gap loi -> hien thong bao than thien, khong crash",
       not at.exception and any("Xin lỗi" in m.value for m in at.markdown))

    print("\nKET QUA:", "TAT CA PASS" if not LOI else f"{len(LOI)} LOI: {LOI}")
    return len(LOI)


def test_he_thong():
    assert chay_tat_ca() == 0


if __name__ == "__main__":
    sys.exit(1 if chay_tat_ca() else 0)

