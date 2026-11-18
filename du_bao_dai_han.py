"""Du bao nang suat NHIEU NAM tu xu huong lich su (hoi quy tuyen tinh nang suat theo nam).

Chon xu huong thay vi mo hinh theo thoi tiet vi thoi tiet cua cac nam toi la an so; dong thoi kiem tra cuon chieu
tren du lieu lua An Giang cho thay xu huong sai so thap hon trung binh 3 nam o moi do xa 1-3 nam.
Khoang du bao la khoang du bao OLS (phan phoi t) - CHI phan anh nhieu ngau nhien quanh duong xu huong,
KHONG bao gom rui ro xu huong doi chieu, nen du bao cang xa cang can than.
"""

import math

import numpy as np
from scipy import stats

MAX_NAM_DU_BAO = 10
MIN_NAM_DU_BAO = 6        # it nhat 6 nam moi khop duoc xu huong
MIN_NAM_KIEM_TRA = 8      # it nhat 8 nam moi co kiem tra cuon chieu


def _ols(nam, y):
    n = len(y)
    b, a = np.polyfit(nam, y, 1)
    sai_so = y - (a + b * nam)
    s = float(np.sqrt((sai_so ** 2).sum() / (n - 2)))   # do lech chuan phan du, bac tu do n-2
    sxx = float(((nam - nam.mean()) ** 2).sum())
    return float(a), float(b), s, sxx


def kiem_tra_cuon_chieu(nam, y, so_buoc_toi_da=3, nam_huan_luyen_toi_thieu=5):
    """
    Kiem tra cuon chieu (rolling origin): huan luyen tren cac nam dau, du bao h nam tiep theo, so voi thuc te,
    lap lai khi dich moc huan luyen. So sanh xu huong tuyen tinh voi trung binh 3 nam gan nhat.
    Chi tra ve cac do xa h co it nhat 2 moc kiem tra.
    """
    n = len(y)
    if n < MIN_NAM_KIEM_TRA:
        return []
    ket_qua = []
    for h in range(1, so_buoc_toi_da + 1):
        sai_xu_huong, sai_tb3 = [], []
        for goc in range(nam_huan_luyen_toi_thieu, n):
            i = goc + h - 1                                    # vi tri nam can du bao
            if i >= n:
                continue
            b, a = np.polyfit(nam[:goc], y[:goc], 1)
            sai_xu_huong.append(abs(a + b * nam[i] - y[i]))
            sai_tb3.append(abs(y[goc - 3:goc].mean() - y[i]))
        if len(sai_xu_huong) >= 2:
            ket_qua.append({
                "so_nam_truoc": h,
                "so_moc_kiem_tra": len(sai_xu_huong),
                "mae_xu_huong": round(float(np.mean(sai_xu_huong)), 2),
                "mae_tb_3_nam": round(float(np.mean(sai_tb3)), 2),
            })
    return ket_qua


def _muc_tin_cay(so_nam_toi):
    # Nguong 2 / 5 nam la danh gia cua nguoi viet: kiem tra cuon chieu chi co 2-5 moc o do xa 1-3 nam,
    # va khong co moc nao de kiem chung do xa lon hon.
    if so_nam_toi <= 2:
        return "tham khao"
    return "thap" if so_nam_toi <= 5 else "rat thap"


def du_bao_nhieu_nam(d, so_nam=5, dien_tich_phan_tram=0, do_tin_cay=0.8):
    """
    d: DataFrame co cot nam, nang_suat_ta_ha, dien_tich_ha (da sap xep theo nam).
    Tra ve dict gom du bao tung nam (nang suat, khoang du bao, san luong), moc phang TB 3 nam,
    ket qua kiem tra cuon chieu va canh bao; hoac {"loi": ...}.
    """
    try:
        so_nam = int(so_nam)
        do_tin_cay = float(do_tin_cay)
        dien_tich_phan_tram = float(dien_tich_phan_tram or 0)
    except (TypeError, ValueError):
        return {"loi": "so_nam, do_tin_cay, dien_tich_phan_tram phai la so."}
    if not 1 <= so_nam <= MAX_NAM_DU_BAO:
        return {"loi": f"so_nam phai tu 1 den {MAX_NAM_DU_BAO}."}
    if not 0.5 <= do_tin_cay <= 0.99:
        return {"loi": "do_tin_cay phai tu 0.5 den 0.99 (vi du 0.8 la khoang 80%)."}
    if not -100 <= dien_tich_phan_tram <= 300:
        return {"loi": "dien_tich_phan_tram phai tu -100 den 300."}

    d = d.sort_values("nam")
    n = len(d)
    if n < MIN_NAM_DU_BAO:
        return {"loi": f"Chi co {n} nam du lieu, can it nhat {MIN_NAM_DU_BAO} nam de du bao xu huong."}
    nam = d["nam"].to_numpy(float)
    y = d["nang_suat_ta_ha"].to_numpy(float)
    a, b, s, sxx = _ols(nam, y)
    nam_cuoi = int(nam[-1])
    he_so_t = float(stats.t.ppf(0.5 + do_tin_cay / 2, n - 2))
    dien_tich = float(d["dien_tich_ha"].iloc[-1]) * (1 + dien_tich_phan_tram / 100)

    du_bao = []
    for h in range(1, so_nam + 1):
        nam_moi = nam_cuoi + h
        gia_tri = a + b * nam_moi
        sai_so_chuan = s * math.sqrt(1 + 1 / n + (nam_moi - nam.mean()) ** 2 / sxx)
        ns = round(gia_tri, 2)
        thap = round(max(0.0, gia_tri - he_so_t * sai_so_chuan), 2)   # nang suat khong the am
        cao = round(gia_tri + he_so_t * sai_so_chuan, 2)
        du_bao.append({
            "nam": nam_moi, "so_nam_toi": h, "nang_suat_ta_ha": ns, "khoang_thap": thap, "khoang_cao": cao,
            "san_luong_tan": round(ns * dien_tich / 10),               # ta/ha * ha / 10 = tan
            "san_luong_thap_tan": round(thap * dien_tich / 10),
            "san_luong_cao_tan": round(cao * dien_tich / 10),
            "muc_tin_cay": _muc_tin_cay(h),
        })

    canh_bao = [
        "Dự báo chỉ dựa vào xu hướng quá khứ và giả định xu hướng tiếp tục; không dùng thời tiết, giá, dịch bệnh hay chính sách.",
        "Khoảng dự báo chỉ phản ánh dao động quanh đường xu hướng, không bao gồm rủi ro xu hướng đổi chiều.",
    ]
    if so_nam > 3:
        canh_bao.append("Dự báo xa hơn 3 năm vượt quá độ xa đã kiểm tra lùi được; chỉ nên dùng để xem hướng đi, không dùng để cam kết số liệu.")
    if n < 10:
        canh_bao.append(f"Chỉ có {n} năm dữ liệu (đề bài yêu cầu ít nhất 10 năm) nên xu hướng kém chắc chắn hơn.")
    if b > 0 and so_nam >= 5:
        canh_bao.append("Năng suất không thể tăng mãi; đường xu hướng kéo dài càng xa càng dễ vượt thực tế.")

    return {
        "phuong_phap": f"Hoi quy tuyen tinh nang suat theo nam (OLS) tren {n} nam {int(nam[0])}-{nam_cuoi}",
        "du_lieu_den_nam": nam_cuoi,
        "so_nam_du_lieu": n,
        "xu_huong_ta_ha_moi_nam": round(b, 3),
        "sai_so_chuan_phan_du_ta_ha": round(s, 2),
        "do_tin_cay_khoang": do_tin_cay,
        "dien_tich_gia_dinh_ha": round(dien_tich),
        "du_bao": du_bao,
        "moc_phang_tb_3_nam": round(float(y[-3:].mean()), 2),
        "kiem_tra_cuon_chieu": kiem_tra_cuon_chieu(nam, y),
        "canh_bao": canh_bao,
        "ghi_chu": "San luong = nang suat du bao x dien tich (giu nguyen dien tich nam cuoi, co the dieu chinh bang kich ban).",
    }
