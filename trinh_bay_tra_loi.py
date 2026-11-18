"""Dựng phần SỐ LIỆU của câu trả lời chat trực tiếp từ JSON của hàm Python (không qua LLM).

Thứ tự trình bày: căn cứ (cây, vùng, năm, nguồn) -> cách tính -> bảng dẫn chứng -> kết luận -> nhận định/gợi ý
(do Gemini viết, không có số) -> độ chính xác ở CUỐI CÙNG (chỉ với dự báo).
Mọi con số ở đây lấy từ kết quả hàm; LLM không được sửa.
"""
from __future__ import annotations

_DON_VI = {"ta/ha": "tạ/ha", "tan": "tấn", "ha": "ha", "mm": "mm", "do C": "°C", "ngay": "ngày"}
_TEN_CHI_TIEU = {"nang_suat": "Năng suất", "dien_tich": "Diện tích", "san_luong": "Sản lượng", "mua": "Tổng mưa mùa vụ",
                 "nhiet_do": "Nhiệt độ trung bình", "ngay_nong": "Số ngày nóng (trên 35 °C)"}
_TEN_THUONG = {"nang_suat": "năng suất", "dien_tich": "diện tích", "san_luong": "sản lượng", "mua": "tổng mưa mùa vụ",
               "nhiet_do": "nhiệt độ trung bình", "ngay_nong": "số ngày nóng"}


def vn(x, nd=2, dau=False):
    """Định dạng kiểu Việt Nam: 67,46 / 4.362.330; dau=True thêm dấu +/− cho độ chênh."""
    if x is None:
        return "—"
    s = f"{abs(float(x)):,.{nd}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if float(x) < 0:
        s = "−" + s
    elif dau and float(x) > 0:
        s = "+" + s
    return s


def _dv(ma):
    return _DON_VI.get(ma, ma or "")


def thong_tin_bo(ma_bo=None):
    """(cây, vùng, nguồn, năm đầu, năm cuối) của bộ dữ liệu; None nếu không tra được."""
    try:
        import bo_du_lieu as bdl
        from ham_xu_ly import MAC_DINH
        meta, d = bdl.lay_bo(ma_bo or MAC_DINH)
        return (meta.get("cay"), meta.get("tinh"), meta.get("nguon"), int(d["nam"].min()), int(d["nam"].max()))
    except Exception:  # noqa: BLE001
        return None, None, None, None, None


def _dau_de(cay, vung, nam_dau=None, nam_cuoi=None):
    s = f"{(cay or 'cây trồng').lower()} {vung or ''}".strip()
    return s


def _nguon(ma_bo):
    cay, vung, nguon, d0, d1 = thong_tin_bo(ma_bo)
    dong = []
    if cay or vung:
        dong.append(f"- Cây trồng và vùng: **{cay or '—'}**, **{vung or '—'}** (địa giới cũ, chưa tính hợp nhất)")
    if d0:
        dong.append(f"- Dữ liệu thực tế: năm {d0}–{d1} ({d1 - d0 + 1} năm)")
    if nguon:
        dong.append(f"- Nguồn: {nguon}")
    return dong, (cay, vung, d0, d1)


# ----------------------------------------------------------------------------------- dự báo
def khoi_du_bao(kq, tham_so):
    nam = (tham_so or {}).get("nam")
    cay, vung = kq.get("cay"), kq.get("vung")
    nam_cuoi = kq.get("nam_cuoi_du_lieu") or kq.get("du_lieu_den_nam")
    nguon_dong, _ = _nguon(kq.get("bo_du_lieu"))
    L = [f"### Dự báo năng suất {_dau_de(cay, vung)} năm {nam} (số liệu tham khảo)", "", "**1. Căn cứ dữ liệu**"]
    L += nguon_dong
    ten_mh = str(kq.get("model_id", "")).split("/")[-1].split("[")[0]
    ten_mh = {"LinearRegression": "hồi quy tuyến tính", "RandomForest": "Random Forest"}.get(ten_mh, ten_mh or "mô hình")
    L.append(f"- Mô hình: {ten_mh}, học từ số liệu các năm trước; lấy số liệu năm {nam_cuoi} làm đầu vào để dự báo năm {nam}")
    L += ["", "**2. Cách ra con số**"]
    dv = kq.get("dau_vao_goc") or {}
    if dv:
        L.append(f"- Đầu vào (năm {nam_cuoi}): diện tích {vn(dv.get('dien_tich_ha'), 0)} ha; tổng mưa mùa vụ "
                 f"{vn(dv.get('mua_tong_mm'), 1)} mm; nhiệt độ trung bình {vn(dv.get('nhiet_tb_c'), 2)} °C; "
                 f"{vn(dv.get('ngay_nong'), 0)} ngày nóng trên 35 °C")
    kb = kq.get("kich_ban") or {}
    mua, dt = kb.get("rain_change_percent", 0) or 0, kb.get("area_change_percent", 0) or 0
    if mua or dt:
        du = kq.get("dau_vao_nam_truoc") or {}
        phan = []
        if mua:
            phan.append(f"mưa {vn(mua, 0, True)}% (còn {vn(du.get('mua_tong_mm'), 1)} mm)")
        if dt:
            phan.append(f"diện tích {vn(dt, 0, True)}% (còn {vn(du.get('dien_tich_ha'), 0)} ha)")
        L.append("- Kịch bản giả định: " + "; ".join(phan) + ". Đây là giả định để mô phỏng, không phải dự báo thời tiết")
    L.append(f"- Mốc so sánh đơn giản: trung bình 3 năm gần nhất của {_dau_de(cay, vung)} là "
             f"**{vn(kq.get('baseline_tb_3_nam'))} tạ/ha**")
    # kiểm chứng
    kc = kq.get("kiem_chung") or []
    L += ["", "**3. Dẫn chứng: kiểm chứng trên các năm đã biết kết quả** (mô hình chưa thấy các năm này khi học)"]
    if kc:
        L += ["", "| Năm | Thực tế (tạ/ha) | Mô hình dự báo (tạ/ha) | Lệch (tạ/ha) | Lệch (%) |", "|---|---|---|---|---|"]
        for k in kc:
            L.append(f"| {k['nam']} | {vn(k['thuc_te'])} | {vn(k['du_bao'])} | {vn(k['lech'], 2, True)} | {vn(k['lech_phan_tram'])}% |")
        L.append("")
        chieu = "cao hơn" if all(k["lech"] > 0 for k in kc) else "thấp hơn" if all(k["lech"] < 0 for k in kc) else "lệch cả hai phía so với"
        L.append(f"- Sai số trung bình {vn(kq.get('sai_so_uoc_tinh'), 2)} tạ/ha ({vn(kq.get('mape_kiem_tra_phan_tram'))}%); "
                 f"mô hình dự báo {chieu} thực tế" + (" cả " + str(len(kc)) + " năm." if chieu != "lệch cả hai phía so với" else "."))
        if kq.get("mo_hinh_hon_baseline_last_value") is False:
            L.append(f"- Mốc \"lấy năng suất năm trước\" chỉ lệch trung bình {vn(kq.get('baseline_last_value_mae'))} tạ/ha, "
                     "nên mô hình **chưa tốt hơn** mốc đơn giản này trên 3 năm kiểm chứng.")
    else:
        L.append("- Chưa có bảng kiểm chứng cho bộ dữ liệu này.")
    # kết quả
    L += ["", "**4. Kết quả (tham khảo)**"]
    ns = kq.get("nang_suat_du_bao")
    khoang = kq.get("khoang_kiem_chung")
    if khoang:
        L.append(f"- Khoảng tham khảo: **{vn(khoang['low'])} – {vn(khoang['high'])} tạ/ha** "
                 f"(giá trị giữa khoảng {vn(ns)} tạ/ha; khoảng = giá trị giữa ± sai lệch lớn nhất {vn(abs(kq.get('lech_lon_nhat_kiem_chung')))} tạ/ha trong bảng dẫn chứng)")
    else:
        L.append(f"- Giá trị dự báo: **{vn(ns)} tạ/ha**")
    if kq.get("san_luong_uoc_tinh_tan") is not None:
        L.append(f"- Sản lượng tham khảo khoảng {vn(kq['san_luong_uoc_tinh_tan'], 0)} tấn, nếu diện tích là "
                 f"{vn(kq.get('dien_tich_gia_dinh_ha'), 0)} ha (giữ như năm {nam_cuoi} hoặc theo kịch bản)")
    if mua or dt:
        L.append(f"- So với không kịch bản: {vn(kq.get('nang_suat_co_so'))} tạ/ha (chênh {vn(kq.get('chenh_lech_so_voi_co_so'), 2, True)} tạ/ha)")
    L.append("- Lưu ý: số cụ thể gần như chắc chắn lệch ít nhiều; chỉ nên dùng để tham khảo, "
             "không dùng làm căn cứ ký hợp đồng.")
    cuoi = None
    if kq.get("do_chinh_xac_phan_tram") is not None:
        cuoi = (f"**Độ chính xác tham khảo: khoảng {vn(kq['do_chinh_xac_phan_tram'], 1)}%** "
                f"(= 100% − sai số trung bình {vn(kq.get('mape_kiem_tra_phan_tram'))}% trên {len(kc)} năm kiểm chứng; "
                f"{kq.get('so_nam_lech_duoi_5_phan_tram')}/{len(kc)} năm lệch dưới 5%). "
                f"Chỉ có {len(kc)} năm kiểm chứng nên chưa đủ căn cứ để khẳng định"
                + ("; kịch bản giả định chưa được kiểm chứng riêng." if (mua or dt) else "."))
    return "\n".join(L), cuoi


# ----------------------------------------------------------------------------------- so sánh hai năm
def khoi_so_sanh(kq, tham_so):
    a, b = kq["nam_a"], kq["nam_b"]
    nguon_dong, (cay, vung, d0, d1) = _nguon((tham_so or {}).get("bo_du_lieu"))
    ct = kq["chi_tieu"]
    L = [f"### So sánh {_dau_de(cay, vung)} năm {a} và năm {b}", "", "**Căn cứ dữ liệu**"] + nguon_dong
    L += ["", f"**Bảng so sánh** (chênh = năm {b} − năm {a})", "",
          f"| Chỉ tiêu | Năm {a} | Năm {b} | Chênh | Thay đổi (%) |", "|---|---|---|---|---|"]
    for ma, v in ct.items():
        dv = _dv(v.get("don_vi"))
        nd = 0 if ma in ("dien_tich", "san_luong", "ngay_nong") else 2
        nd_mua = 1 if ma == "mua" else nd
        L.append(f"| {_TEN_CHI_TIEU.get(ma, ma)} ({dv}) | {vn(v['nam_a'], nd_mua)} | {vn(v['nam_b'], nd_mua)} | "
                 f"{vn(v['chenh_lech'], nd_mua, True)} | {vn(v['phan_tram_thay_doi'], 2, True)}% |")
    ns = ct.get("nang_suat")
    L += ["", "**Kết luận (từ bảng trên)**"]
    if ns:
        huong = "cao hơn" if ns["chenh_lech"] > 0 else "thấp hơn" if ns["chenh_lech"] < 0 else "bằng"
        L.append(f"- Năng suất năm {b} {huong} năm {a}: **{vn(abs(ns['chenh_lech']))} tạ/ha** "
                 f"({vn(ns['phan_tram_thay_doi'], 2, True)}%).")
    mua = ct.get("mua")
    if mua:
        L.append(f"- Thời tiết cùng hai năm: mưa năm {b} {'nhiều hơn' if mua['chenh_lech'] > 0 else 'ít hơn'} "
                 f"{vn(abs(mua['chenh_lech']), 1)} mm ({vn(mua['phan_tram_thay_doi'], 2, True)}%).")
    L.append("- Đây chỉ là so sánh số liệu của 2 năm; chưa đủ căn cứ để kết luận thời tiết là nguyên nhân của chênh lệch.")
    return "\n".join(L), None


# ----------------------------------------------------------------------------------- thống kê
def _canh_bao_thieu(kq):
    """Dòng cảnh báo khi người dùng hỏi các năm không có trong dữ liệu (hàm trả thieu_nam)."""
    th = kq.get("thieu_nam")
    if not th:
        return []
    cum, i = [], 0
    while i < len(th):
        j = i
        while j + 1 < len(th) and th[j + 1] == th[j] + 1:
            j += 1
        cum.append(str(th[i]) if i == j else f"{th[i]}–{th[j]}")
        i = j + 1
    return [f"**Lưu ý: không có dữ liệu cho năm {', '.join(cum)}.** Kết quả dưới đây chỉ tính trên các năm có số liệu; "
            "hệ thống không đoán số cho các năm thiếu.", ""]


def khoi_thong_ke(kq, tham_so):
    ma = kq.get("chi_tieu", "nang_suat")
    dv = _dv(kq.get("don_vi"))
    ten = _TEN_THUONG.get(ma, ma)
    nd = 0 if ma in ("dien_tich", "san_luong") else 2
    nguon_dong, (cay, vung, d0, d1) = _nguon((tham_so or {}).get("bo_du_lieu"))
    t0, t1, n = kq["tu_nam"], kq["den_nam"], kq["so_nam"]
    L = [f"### Thống kê {ten} {_dau_de(cay, vung)}, giai đoạn {t0}–{t1} ({n} năm)", ""] + _canh_bao_thieu(kq) + ["**Căn cứ dữ liệu**"] + nguon_dong
    L += ["", "| Chỉ số | Giá trị | Năm / phạm vi |", "|---|---|---|",
          f"| Trung bình {n} năm | {vn(kq['trung_binh'], nd)} {dv} | cả giai đoạn {t0}–{t1}, {vung or 'toàn vùng'} |",
          f"| Thấp nhất | {vn(kq['nho_nhat']['gia_tri'], nd)} {dv} | năm {kq['nho_nhat']['nam']} |",
          f"| Cao nhất | {vn(kq['lon_nhat']['gia_tri'], nd)} {dv} | năm {kq['lon_nhat']['nam']} |"]
    if "gia_tri_dau" in kq:
        L += [f"| Năm đầu | {vn(kq['gia_tri_dau']['gia_tri'], nd)} {dv} | năm {kq['gia_tri_dau']['nam']} |",
              f"| Năm cuối | {vn(kq['gia_tri_cuoi']['gia_tri'], nd)} {dv} | năm {kq['gia_tri_cuoi']['nam']} |"]
    if "thay_doi_dau_cuoi" in kq:
        L.append(f"| Thay đổi từ năm đầu đến năm cuối | {vn(kq['thay_doi_dau_cuoi'], nd, True)} {dv} | {t0} → {t1} |")
    if "xu_huong_moi_nam" in kq:
        L.append(f"| Xu hướng (đường thẳng qua {n} điểm) | {vn(kq['xu_huong_moi_nam'], 3, True)} {dv}/năm | {t0}–{t1} |")
    if "do_lech_chuan" in kq:
        L.append(f"| Độ lệch chuẩn | {vn(kq['do_lech_chuan'], nd)} {dv} | {t0}–{t1} |")
    for nhan, tieu in (("thoi_tiet_nam_nho_nhat", "thấp nhất"), ("thoi_tiet_nam_lon_nhat", "cao nhất")):
        w = kq.get(nhan)
        if w:
            L.append(f"| Thời tiết cùng năm {w['nam']} (năm {tieu}) | mưa {vn(w.get('mua_tong_mm'), 1)} mm; "
                     f"{vn(w.get('nhiet_tb_c'), 2)} °C; {vn(w.get('ngay_nong'), 0)} ngày nóng | năm {w['nam']} |")
    L += ["", "**Kết luận (từ bảng trên)**"]
    x = kq.get("xu_huong_moi_nam")
    if x is not None:
        huong = "TĂNG" if x > 0.1 else "GIẢM" if x < -0.1 else "gần như KHÔNG ĐỔI"
        tb = kq["trung_binh"] or 1
        L.append(f"- {ten.capitalize()} {huong} trong {t0}–{t1}: khoảng {vn(abs(x), 3)} {dv} mỗi năm "
                 f"(≈ {vn(abs(x) / tb * 100, 2)}% mỗi năm so với trung bình).")
    L.append(f"- Thấp nhất là năm {kq['nho_nhat']['nam']}, cao nhất là năm {kq['lon_nhat']['nam']}.")
    if kq.get("luu_y_nguyen_nhan"):
        L.append("- Thời tiết cùng năm chỉ là thông tin đi kèm; chuỗi ngắn không chứng minh thời tiết là nguyên nhân.")
    L.append(f"- Chuỗi chỉ có {n} năm nên xu hướng chỉ mô tả giai đoạn này, không dùng để dự báo.")
    return "\n".join(L), None


# ----------------------------------------------------------------------------------- lịch sử
def khoi_lich_su(kq, tham_so):
    dl = kq.get("du_lieu") or []
    if not dl or not all(x in dl[0] for x in ("nam", "nang_suat_ta_ha", "dien_tich_ha", "san_luong_tan")):
        return None, None
    nguon_dong, (cay, vung, d0, d1) = _nguon((tham_so or {}).get("bo_du_lieu"))
    L = [f"### Số liệu thực tế {_dau_de(cay, vung)}, năm {dl[0]['nam']}" + (f"–{dl[-1]['nam']}" if len(dl) > 1 else ""), ""] \
        + _canh_bao_thieu(kq) + ["**Căn cứ dữ liệu**"] + nguon_dong
    L += ["", "| Năm | Năng suất (tạ/ha) | Diện tích (ha) | Sản lượng (tấn) |", "|---|---|---|---|"]
    for r in dl:
        L.append(f"| {r['nam']} | {vn(r['nang_suat_ta_ha'])} | {vn(r['dien_tich_ha'], 0)} | {vn(r['san_luong_tan'], 0)} |")
    L += ["", "**Kết luận (từ bảng trên)**"]
    if kq.get("xu_huong_moi_nam") is not None:
        x = kq["xu_huong_moi_nam"]
        huong = "TĂNG" if x > 0.1 else "GIẢM" if x < -0.1 else "gần như KHÔNG ĐỔI"
        L.append(f"- Năng suất {huong} giai đoạn {dl[0]['nam']}–{dl[-1]['nam']}: khoảng {vn(abs(x), 3)} tạ/ha mỗi năm; "
                 f"thay đổi từ năm đầu đến năm cuối {vn(kq.get('thay_doi_dau_cuoi_nang_suat'), 2, True)} tạ/ha.")
        L.append(f"- Chuỗi chỉ có {kq.get('so_nam', len(dl))} năm nên xu hướng chỉ mô tả giai đoạn này, không dùng để dự báo.")
    else:
        L.append("- Đây là số liệu thực tế đã được thống kê, không phải dự báo.")
    return "\n".join(L), None


# ----------------------------------------------------------------------------------- ghép
_GOI_Y_MAC_DINH = ("Số liệu trên chỉ để tham khảo. Nên theo dõi diễn biến thời tiết từng vụ, chủ động nguồn nước và lịch xuống giống, "
                   "và hỏi thêm cán bộ khuyến nông địa phương trước khi quyết định canh tác hay ký hợp đồng.")


def dung_tra_loi(ket_qua_cong_cu, nhan_dinh=None):
    """Ghép: các khối số liệu -> Nhận định và gợi ý (Gemini, không số) -> độ chính xác ở cuối.
    Trả None nếu không có kết quả hàm nào cần dựng khối (vd ds_bo_du_lieu, lỗi)."""
    khoi, cuoi = [], None
    for k in ket_qua_cong_cu:
        kq = k.get("ket_qua") if isinstance(k, dict) else None
        if not isinstance(kq, dict) or "loi" in kq:
            continue
        ts = k.get("tham_so") or {}
        than = c = None
        if "nang_suat_du_bao" in kq:
            than, c = khoi_du_bao(kq, ts)
        elif "chi_tieu" in kq and "nam_a" in kq and "nam_b" in kq:
            than, c = khoi_so_sanh(kq, ts)
        elif "nho_nhat" in kq and "lon_nhat" in kq and "trung_binh" in kq:
            than, c = khoi_thong_ke(kq, ts)
        elif isinstance(kq.get("du_lieu"), list) and kq["du_lieu"]:
            than, c = khoi_lich_su(kq, ts)
        if than:
            khoi.append(than)
            cuoi = c or cuoi
    if not khoi:
        return None
    ket = "\n\n---\n\n".join(khoi[-2:])
    nd = (nhan_dinh or "").strip() or _GOI_Y_MAC_DINH
    s = ket + "\n\n**Nhận định và gợi ý canh tác (tham khảo, không phải số liệu)**\n\n" + nd
    if cuoi:
        s += "\n\n---\n\n" + cuoi
    return s
