"""
AgFarm AI - he thong quan ly nong trai tich hop AI (Streamlit).
Chay: streamlit run app.py
"""

import copy
import datetime
import os
from pathlib import Path

import altair as alt
import pandas as pd

import streamlit as st

import db
import ham_xu_ly as hx
import chat_logic
from chat_store import nap_phien, luu_phien, xoa_phien
from gemini_client import co_api_key

st.set_page_config(page_title="AgFarm AI", page_icon=":material/eco:", layout="wide")
os.environ.setdefault("AGRI_CHAT_LOG", str(Path(__file__).parent / "outputs" / "chat_log.jsonl"))  # nhat ky moi luot chat
db.khoi_tao()

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root { --forest:#123c2b; --leaf:#16834c; --mint:#e9f5ed; --ink:#183328; --muted:#718177; --line:#e4ece6; }
html, body, [class*="css"] { font-family:'DM Sans', sans-serif; color:var(--ink); }
.stApp { background:linear-gradient(180deg,#f7faf8 0%,#f4f8f5 100%); }
.block-container {padding:1.35rem 2.25rem 3.5rem; max-width:1500px;}
h1,h2,h3 {font-family:'Manrope','DM Sans',sans-serif !important; letter-spacing:-.035em; color:var(--forest);}
h1 {font-size:2rem !important; font-weight:800 !important; margin:.35rem 0 .2rem !important;}
h2 {font-size:1.35rem !important; font-weight:750 !important;}
h3 {font-size:1.05rem !important; font-weight:700 !important;}
p, label, .stCaption {color:var(--ink);}
[data-testid="stAppDeployButton"], .stAppDeployButton {display:none;}
[data-testid="stHeader"] {background:rgba(247,250,248,.88);}
[data-testid="stSidebar"] {background:#f0f6f2; border-right:1px solid #e3ece5;}
[data-testid="stSidebar"] > div:first-child {padding:1.15rem .95rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] > label {display:none;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {padding:9px 12px; border-radius:12px; width:100%; margin:3px 0; transition:all .18s ease;}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {background:#e5f0e8;}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) {background:#fff; box-shadow:0 4px 14px rgba(18,60,43,.08); outline:1px solid #dce9df;}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:checked) p {font-weight:700;color:var(--forest);}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > span:first-child {display:none;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {font-size:.84rem;}
[data-testid="stMetric"] {background:linear-gradient(145deg,#fff,#fbfdfb); border:1px solid var(--line); border-radius:18px; padding:14px 16px; box-shadow:0 5px 18px rgba(21,60,43,.035);}
[data-testid="stMetricValue"] {color:var(--forest);font-weight:800;}
[data-testid="stMetricLabel"] p {color:var(--muted);font-weight:600;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color:var(--line) !important; border-radius:18px !important; background:rgba(255,255,255,.78); box-shadow:0 5px 20px rgba(21,60,43,.035);}
[data-testid="stAlert"] {border-radius:14px;}
.stButton > button, .stDownloadButton > button {border-radius:11px;border:1px solid #d9e7dd;font-weight:650;transition:all .18s ease;}
.stButton > button[kind="primary"] {background:linear-gradient(135deg,#16834c,#11683c);border:0;color:#fff;box-shadow:0 5px 12px rgba(22,131,76,.18);}
.stButton > button:hover, .stDownloadButton > button:hover {border-color:#16834c;color:#11683c;transform:translateY(-1px);}
input, textarea, [data-baseweb="select"] > div {border-radius:12px !important;}
[data-testid="stChatMessage"] {border:1px solid #e7eee9;border-radius:18px;padding:1rem 1.1rem;background:#fff;box-shadow:0 5px 18px rgba(21,60,43,.035);}
[data-testid="stChatInput"] {border:1px solid #b8d8c2;border-radius:18px;box-shadow:0 8px 24px rgba(21,60,43,.08);background:#fff;}
details {border-color:var(--line) !important;border-radius:14px !important;}
[data-testid="stDataFrame"] {border:1px solid var(--line);border-radius:14px;overflow:hidden;}
.topbar {display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:0 0 1.15rem;padding:.8rem 1rem;border:1px solid #e5eee7;border-radius:16px;background:rgba(255,255,255,.82);box-shadow:0 4px 16px rgba(21,60,43,.035);}
.topbar-title {font:700 .9rem 'Manrope',sans-serif;color:var(--forest);}
.topbar-sub {font-size:.74rem;color:var(--muted);margin-top:2px;}
.status-pill {display:inline-flex;align-items:center;gap:7px;border:1px solid #d8eadc;background:#eff8f1;color:#247247;border-radius:999px;padding:7px 11px;font-size:.75rem;font-weight:650;white-space:nowrap;}
.status-dot {width:7px;height:7px;border-radius:50%;background:#25a45e;box-shadow:0 0 0 3px #d9f0df;}
.brand {padding:.35rem .4rem 1rem;margin-bottom:.3rem;border-bottom:1px solid #dce8df;}
.brand-mark {display:flex;align-items:center;gap:10px;font:800 1.24rem 'Manrope',sans-serif;letter-spacing:-.04em;color:var(--forest);}
.brand-icon {display:grid;place-items:center;width:37px;height:37px;border-radius:12px;color:#fff;background:linear-gradient(140deg,#27a565,#11633b);box-shadow:0 5px 12px #16834c35;}
.brand-caption {margin:6px 0 0 47px;font-size:.71rem;color:var(--muted);}
@media (max-width:800px) {.block-container{padding:1rem 1rem 2.5rem}.topbar{padding:.7rem}.status-pill{font-size:.68rem}}
</style>
""",
    unsafe_allow_html=True,
)
PAGES = [
    "Tổng quan",
    "Dự báo năng suất",
    "Mô hình AI",
    "Trợ lý AI",
]
ICON_VAI = {"user": ":material/person:", "assistant": ":material/smart_toy:"}

# ---------------- Tien ich ----------------
def so(v, chu_so=0):
    """Dinh dang so kieu Viet Nam: 1.234,5"""
    return f"{v:,.{chu_so}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def bieu_do_nang_suat(nam_du_bao=None, gia_tri_du_bao=None):
    """Bieu do nang suat: duong xanh = thuc te, duong vang net dut = du bao. Truc Y khong bat buoc tu 0."""
    nam = [str(n) for n in hx.df["nam"]]
    thuc_te = [float(v) for v in hx.df["nang_suat_ta_ha"]]
    d = pd.DataFrame({"nam": nam, "thuc_te": thuc_te})
    bd = alt.Chart(d).mark_line(point=alt.OverlayMarkDef(color="#1f8a4c"), color="#1f8a4c").encode(
        x=alt.X("nam:N", title="Năm"),
        y=alt.Y("thuc_te:Q", title="Năng suất (tạ/ha)", scale=alt.Scale(zero=False)),
        tooltip=["nam", "thuc_te"],
    )
    if gia_tri_du_bao is not None:
        dd = pd.DataFrame({"nam": [nam[-1], str(nam_du_bao)], "du_bao": [thuc_te[-1], float(gia_tri_du_bao)]})
        bd = bd + alt.Chart(dd).mark_line(
            point=alt.OverlayMarkDef(color="#e0a800"), color="#e0a800", strokeDash=[6, 4]
        ).encode(x="nam:N", y=alt.Y("du_bao:Q", scale=alt.Scale(zero=False)), tooltip=["nam", "du_bao"])
    return bd.properties(height=300, width="container")


def the(cot, nhan, gia_tri, ghi_chu=None):
    """The KPI. gia_tri=None nghia la CHUA CO DU LIEU (khong hien so 0 de tranh hieu nham la da co thong ke)."""
    with cot.container(border=True):
        if gia_tri is None:
            st.metric(nhan, "—")
            st.caption("Chưa có dữ liệu")
        else:
            st.metric(nhan, gia_tri)
            if ghi_chu:
                st.caption(ghi_chu)


# ---------------- Trang: Tong quan ----------------
def trang_tong_quan():
    st.title("Tổng quan dữ liệu lúa An Giang")
    st.caption("Số liệu lịch sử lúa An Giang có nguồn (Niên giám Thống kê + Open-Meteo); con số dự báo là ngoại suy một bước.")
    du_lieu = hx.df
    dong_cuoi = du_lieu.iloc[-1]
    nam_cuoi = int(dong_cuoi["nam"])
    ns_cuoi = float(dong_cuoi["nang_suat_ta_ha"])
    dbao = hx.du_bao(nam_cuoi + 1)

    h1 = st.columns(4)
    the(h1[0], "Số năm dữ liệu", str(len(du_lieu)),
        f"{int(du_lieu['nam'].min())}–{nam_cuoi} · năm liên tục")
    the(h1[1], f"Diện tích {nam_cuoi} (ha)", so(float(dong_cuoi["dien_tich_ha"])),
        "Niên giám Thống kê An Giang")
    the(h1[2], f"Năng suất {nam_cuoi} (tạ/ha)", so(ns_cuoi, 2),
        "Số liệu lịch sử")
    nhan_du_bao = (f"Ước tính {nam_cuoi + 1} (tạ/ha)"
                   if nam_cuoi + 1 <= datetime.date.today().year
                   else f"Dự báo {nam_cuoi + 1} (tạ/ha)")
    the(h1[3], nhan_du_bao, so(dbao["nang_suat_du_bao"], 2),
        f"Chuỗi cũ, ngoại suy một bước từ {nam_cuoi}; MAE kiểm tra {so(dbao['sai_so_uoc_tinh'], 3)} tạ/ha")

    h2 = st.columns(4)
    the(h2[0], f"Sản lượng thực tế {nam_cuoi} (tấn)", so(float(dong_cuoi["san_luong_tan"])),
        "Niên giám Thống kê An Giang")
    the(h2[1], f"Mưa mùa vụ {nam_cuoi} (mm)", so(float(dong_cuoi["mua_tong_mm"]), 1),
        "Open-Meteo Historical · tháng 5–11")
    the(h2[2], f"Nhiệt độ TB mùa vụ {nam_cuoi}", so(float(dong_cuoi["nhiet_tb_c"]), 2) + " °C",
        "Open-Meteo Historical")
    the(h2[3], f"Ngày nóng trên 35 °C · {nam_cuoi}", so(float(dong_cuoi["ngay_nong"])) + " ngày",
        "Open-Meteo Historical · mùa vụ")
    st.caption(
        "Nguồn chuỗi cũ: Niên giám Thống kê tỉnh An Giang 2024 (biểu 127–129, trang 366–368); "
        "thời tiết Open-Meteo Historical Weather API. Con số mô hình bên trên là ngoại suy một bước cho chuỗi địa giới cũ, "
        "không phải kết quả thực tế năm 2025 hay dự báo cho tỉnh mới. Chi phí và doanh thu nông hộ chỉ có khi người dùng tự nhập."
    )

# ---------------- Trang: Du bao nang suat ----------------
def khoi_rui_ro_do_tin_cay(nam_du_bao, mua_pct, dt_pct):
    """Mô hình dự báo: dự báo + mức rủi ro + sai số kiểm tra + so với baseline + đánh giá cuốn chiếu."""
    st.subheader("Mức rủi ro và độ tin cậy của mô hình")
    try:
        import mo_hinh_du_bao as mhdb
        cuoi = hx.df.iloc[-1]
        kq4 = mhdb.forecast_with_decision(
            nam_du_bao,
            mua_tong_mm=float(cuoi["mua_tong_mm"]) * (1 + mua_pct / 100) if mua_pct else None,
            dien_tich_ha=float(cuoi["dien_tich_ha"]) * (1 + dt_pct / 100) if dt_pct else None,
        )
    except Exception:
        st.info("Chưa có mô hình dự báo. Chạy `python mo_hinh_du_bao.py` rồi tải lại trang.", icon=":material/info:")
        return
    mo, qd = kq4["model_output"], kq4["decision"]
    muc = {"NORMAL": "Bình thường", "WARNING": "Cảnh báo", "HIGH": "Cao", "CRITICAL": "Nghiêm trọng", "UNKNOWN": "Chưa xác định"}
    hien = {"NORMAL": st.success, "WARNING": st.warning, "HIGH": st.error, "CRITICAL": st.error}.get(qd["risk_level"], st.info)
    hien(f"Mức rủi ro: {muc.get(qd['risk_level'], qd['risk_level'])}. {qd.get('recommendation_text', qd['reason'])}")
    itv = mo.get("prediction_interval")
    if itv:
        st.caption(
            f"Khoảng sai số tham khảo {so(itv['low'], 2)} – {so(itv['high'], 2)} tạ/ha (± độ lệch cuốn chiếu lớn nhất, "
            f"chỉ 6 phần dư gồm cả năm test; KHÔNG phải khoảng tin cậy hay xác suất bao phủ). "
            f"Mức rủi ro nếu rơi vào cận thấp: {muc.get(qd.get('risk_level_if_low_bound'), '—')}."
        )
    st.caption(qd["safety_note"])
    st.caption("Bảng so sánh mô hình, chỉ số đánh giá và đánh giá cuốn chiếu nằm ở trang Mô hình AI.")


def trang_du_bao():
    st.title("Dự báo năng suất lúa · chuỗi An Giang cũ")
    nam_du_bao = hx.NAM_CUOI_CO_DU_LIEU + 1
    st.caption(
        f"Mô hình một bước từ dữ liệu đến {hx.NAM_CUOI_CO_DU_LIEU}, đang ước tính năm {nam_du_bao}. "
        "Chuỗi này dùng địa giới An Giang cũ, không đại diện tỉnh mới sau hợp nhất."
    )
    if nam_du_bao <= datetime.date.today().year:
        st.warning(f"Năm {nam_du_bao} đã qua. Đây là ước tính mô hình tạo từ dữ liệu đến {hx.NAM_CUOI_CO_DU_LIEU}, "
                   "không phải số liệu thực tế của năm đó.")
    c1, c2 = st.columns(2)
    mua = c1.slider("Thay đổi lượng mưa (%)", -50, 50, 0, step=5, key="du_bao_mua")
    dt = c2.slider("Thay đổi diện tích gieo trồng (%)", -30, 30, 0, step=5, key="du_bao_dt")

    kq = hx.du_bao(nam_du_bao, mua, dt)
    baseline = float(hx.df["nang_suat_ta_ha"].tail(3).mean())
    dien_tich = float(hx.df.iloc[-1]["dien_tich_ha"]) * (1 + dt / 100)
    san_luong_tan = kq["nang_suat_du_bao"] * dien_tich / 10  # tạ/ha * ha / 10 = tấn

    m = st.columns(4)
    ghi = f"Sai số kiểm tra (MAE) {so(kq['sai_so_uoc_tinh'], 3)} tạ/ha"
    if kq["chenh_lech_so_voi_co_so"] != 0:
        ghi += f"  \nKhông kịch bản: {so(kq['nang_suat_co_so'], 2)} (chênh {so(kq['chenh_lech_so_voi_co_so'], 2)})"
    ten_mo_hinh = str(kq.get("model_id", "LinearRegression")).split("/")[-1].split("[")[0]
    ten_mo_hinh = {"LinearRegression": "Linear Regression", "RandomForest": "Random Forest",
                   "GradientBoosting": "Gradient Boosting"}.get(ten_mo_hinh, ten_mo_hinh)
    the(m[0], f"Dự báo ({ten_mo_hinh})", so(kq["nang_suat_du_bao"], 2) + " tạ/ha", ghi)
    the(m[1], "Mốc baseline (tạ/ha)", so(baseline, 2), "Trung bình 3 năm gần nhất, để đối chiếu với mô hình")
    the(m[2], "Sản lượng (triệu tấn)", so(san_luong_tan / 1_000_000, 2), f"Diện tích {so(dien_tich)} ha")
    the(m[3], "Dữ liệu đến năm", str(kq["du_lieu_den_nam"]), "Số liệu mới nhất đã nạp")

    st.altair_chart(bieu_do_nang_suat(nam_du_bao, kq["nang_suat_du_bao"]))
    st.caption("Đường xanh: năng suất thực tế · Đường vàng nét đứt: dự báo")

    dg = hx.MAE_KIEM_TRA
    ket_luan = "mô hình Linear Regression tốt hơn mốc baseline" if dg["mae_linear"] < dg["mae_baseline"] else "mốc baseline tốt hơn Linear Regression"
    st.info(
        f"Lưu ý trung thực: trên tập kiểm tra {dg['nam_kiem_tra'][0]}–{dg['nam_kiem_tra'][1]} "
        f"(huấn luyện {dg['nam_huan_luyen'][0]}–{dg['nam_huan_luyen'][1]}), {ket_luan}: "
        f"MAE baseline {so(dg['mae_baseline'], 3)} so với Linear Regression {so(dg['mae_linear'], 3)} tạ/ha. "
        "Cả hai dùng cùng tập huấn luyện/kiểm tra; baseline lấy trung bình 3 năm cuối của tập huấn luyện. "
        "MAE đo trên chỉ vài năm nên chỉ là ước lượng gần đúng, không phải "
        "khoảng tin cậy; mô hình dùng để dự báo được huấn luyện lại trên toàn bộ dữ liệu.",
        icon=":material/info:",
    )
    khoi_rui_ro_do_tin_cay(nam_du_bao, mua, dt)

    with st.expander("Dữ liệu lịch sử đã dùng"):
        st.dataframe(hx.df, hide_index=True)


def _csv_mo_hinh(ten):
    try:
        return pd.read_csv(Path(__file__).resolve().parent / "outputs" / ten)
    except Exception:
        return None


_TEN_DAC_TRUNG = {"nam": "Năm (xu hướng)", "mua_tong_mm": "Tổng mưa", "nhiet_tb_c": "Nhiệt độ TB",
                  "ngay_nong": "Số ngày nóng", "dien_tich_ha": "Diện tích gieo trồng"}


def trang_mo_hinh_ai():
    import json
    st.title("Mô hình AI và chỉ số đánh giá")
    st.caption("Mô hình nhỏ chạy bên trong hệ thống. Trợ lý Gemini chỉ gọi nó và diễn đạt kết quả, không tự tính số. "
               "Dữ liệu 2015–2024 (An Giang cũ), dự báo một năm tiếp theo.")
    out = Path(__file__).resolve().parent / "outputs"
    try:
        ms = json.loads((out / "forecast_metrics.json").read_text(encoding="utf-8"))
        so_sanh = pd.read_csv(out / "model_comparison.csv")
        du_doan = pd.read_csv(out / "predictions_test.csv")
    except Exception:
        st.info("Chưa có mô hình dự báo. Chạy `python mo_hinh_du_bao.py` rồi tải lại trang.", icon=":material/info:")
        return

    chon = ms["selected_model_by_validation_mae"]
    ho, tham_so = chon.split("[")[0], chon[chon.find("[") + 1:-1] if "[" in chon else "mặc định"
    kt_ = ms["selected_model_test_metrics"]
    sp = ms["split"]
    hon = ms["selected_model_beats_last_value_on_test"]
    mae_lv = ms["last_value_baseline_test_mae"]

    # ---- 1. Tổng quan mô hình đang dùng
    c = st.columns(4)
    the(c[0], "Mô hình đang dùng", {"LinearRegression": "Linear", "RandomForest": "Rừng cây", "GradientBoosting": "Boosting"}.get(ho, ho),
        f"{ho}, tham số: {tham_so}. Chọn theo MAE trên validation.")
    the(c[1], "Train / validation / test",
        f"{sp['train_rows']} / {sp['validation_rows']} / {sp['test_rows']}",
        f"Số năm mỗi tập. Train {sp['train_target_years'][0]}–{sp['train_target_years'][1]}, validation "
        f"{sp['validation_target_years'][0]}–{sp['validation_target_years'][1]}, test "
        f"{sp['test_target_years'][0]}–{sp['test_target_years'][1]}")
    the(c[2], "MAE tập kiểm tra", so(kt_["mae"], 3), f"tạ/ha. Baseline Last Value: {so(mae_lv, 3)} tạ/ha")
    the(c[3], "So với baseline", "Hơn" if hon else "Chưa hơn",
        "Baseline = dùng năng suất năm trước làm dự báo")
    if not hon:
        st.warning(
            f"Trên tập kiểm tra, mô hình sai nhiều hơn baseline Last Value ({so(kt_['mae'], 3)} so với {so(mae_lv, 3)} tạ/ha). "
            "Với chỉ vài năm dữ liệu và năng suất gần như đi ngang, mô hình phức tạp hơn không mặc nhiên tốt hơn. "
            "Hãy dùng dự báo như tín hiệu tham khảo.", icon=":material/warning:")

    # ---- 2. So sánh mô hình + giải thích chỉ số
    st.subheader("So sánh mô hình trên tập kiểm tra")
    t = so_sanh.copy()
    t["Mô hình"] = t["model"].str.split("[").str[0]
    t["Vai trò"] = ["Baseline" if b else ("Đang dùng" if sel else "Mô hình khác")
                    for b, sel in zip(t["is_baseline"], t["is_selected"])]
    hien = t[["Mô hình", "Vai trò", "mae", "rmse", "mape_percent", "r2", "bias_pred_minus_actual",
              "mae_improvement_vs_last_value_percent"]].rename(columns={
        "mae": "MAE", "rmse": "RMSE", "mape_percent": "MAPE (%)", "r2": "R²",
        "bias_pred_minus_actual": "Độ lệch", "mae_improvement_vs_last_value_percent": "So với Last Value (%)"})
    st.dataframe(hien, hide_index=True, column_config={
        "MAE": st.column_config.NumberColumn(format="%.3f"), "RMSE": st.column_config.NumberColumn(format="%.3f"),
        "MAPE (%)": st.column_config.NumberColumn(format="%.2f"), "R²": st.column_config.NumberColumn(format="%.2f"),
        "Độ lệch": st.column_config.NumberColumn(format="%+.3f"),
        "So với Last Value (%)": st.column_config.NumberColumn(format="%+.1f")})
    st.caption("Sắp theo MAE tăng dần. Số dương ở cột cuối nghĩa là tốt hơn Last Value. "
               "Mô hình được chọn bằng validation, không chọn theo test.")
    st.subheader("Giải thích các chỉ số")
    giai_thich = [
        ("MAE", f"{so(kt_['mae'], 3)} tạ/ha", "Sai số tuyệt đối trung bình giữa dự báo và thực tế. Càng thấp càng tốt."),
        ("RMSE", f"{so(kt_['rmse'], 3)} tạ/ha", "Phạt nặng sai số lớn. RMSE cao hơn MAE nhiều nghĩa là có vài năm lệch mạnh."),
        ("MAPE", f"{so(kt_['mape_percent'], 2)}%", "Sai số phần trăm so với giá trị thực, dễ so giữa các bộ dữ liệu."),
        ("R²", so(kt_["r2"], 2), "Mức giải thích biến thiên. Âm là kém hơn dự báo bằng trung bình"
                                  + (": năng suất 2022–2024 gần đi ngang nên R² rất âm, ưu tiên đọc MAE." if kt_["r2"] < 0 else ".")),
        ("Độ lệch (bias)", so(kt_["bias_pred_minus_actual"], 3) + " tạ/ha",
         "Dự báo − thực tế. Dương: hay dự báo cao; âm: hay dự báo thấp. Gần 0 là tốt."),
    ]
    cot = st.columns(len(giai_thich))
    for cc, (ten, gia_tri, ghi) in zip(cot, giai_thich):
        with cc.container(border=True):
            st.markdown(f"**{ten}**")
            st.markdown(f"**{gia_tri}**")
            st.caption(ghi)

    # ---- 3. Thực tế và dự báo
    st.subheader("Thực tế và dự báo trên tập kiểm tra")
    cot_mo_hinh = chon if chon in du_doan.columns else next(c_ for c_ in du_doan.columns if c_.startswith(ho))
    d = du_doan.rename(columns={"actual": "Thực tế", cot_mo_hinh: "Mô hình đang dùng", "LastValue_baseline": "Baseline Last Value"})
    dai = d.melt(id_vars="nam", value_vars=["Thực tế", "Mô hình đang dùng", "Baseline Last Value"],
                 var_name="Chuỗi", value_name="Năng suất (tạ/ha)")
    dai["Năm"] = dai["nam"].astype(str)
    mau = alt.Scale(domain=["Thực tế", "Mô hình đang dùng", "Baseline Last Value"], range=["#1f8a4c", "#e0a800", "#7a8b82"])
    bd = alt.Chart(dai).mark_line(point=True).encode(
        x=alt.X("Năm:N"), y=alt.Y("Năng suất (tạ/ha):Q", scale=alt.Scale(zero=False)),
        color=alt.Color("Chuỗi:N", scale=mau), strokeDash=alt.StrokeDash("Chuỗi:N"),
        tooltip=["Năm", "Chuỗi", alt.Tooltip("Năng suất (tạ/ha):Q", format=".2f")])
    sai = d.assign(sai_so=d["Mô hình đang dùng"] - d["Thực tế"])
    lon = sai.loc[sai["sai_so"].abs().idxmax()]
    nhan = alt.Chart(pd.DataFrame({"Năm": [str(int(lon["nam"]))], "y": [float(lon["Mô hình đang dùng"])],
                                   "nhan": [f"sai số lớn nhất {lon['sai_so']:+.2f}"]})).mark_text(dy=-14, color="#c0392b", fontWeight="bold").encode(
        x="Năm:N", y=alt.Y("y:Q", scale=alt.Scale(zero=False)), text="nhan:N")
    st.altair_chart((bd + nhan).properties(height=320, width="container"))
    st.caption("Dự báo − thực tế: mô hình dự báo cao hơn thực tế ở mọi năm kiểm tra." if (sai["sai_so"] > 0).all()
               else "Dự báo − thực tế: có năm cao hơn, có năm thấp hơn thực tế.")

    # ---- 4. Cuốn chiếu
    wf = _csv_mo_hinh("walk_forward_summary.csv")
    wfp = _csv_mo_hinh("walk_forward_predictions.csv")
    if wf is not None and wfp is not None:
        st.subheader("Đánh giá cuốn chiếu (walk-forward)")
        w = ms.get("walk_forward", {})
        yrs = w.get("target_years", [wfp["nam"].min(), wfp["nam"].max()])
        st.write(f"Mỗi năm đích {yrs[0]}–{yrs[1]} chỉ huấn luyện trên các năm trước đó, cấu hình khai báo trước. "
                 f"Có {len(wfp)} điểm thay vì {sp['test_rows']} nên ổn định hơn một chút, nhưng vẫn rất ít.")
        hien_wf = wf.rename(columns={"model": "Mô hình", "n_years": "Số năm", "mae": "MAE", "rmse": "RMSE",
                                     "mape_percent": "MAPE (%)", "bias_pred_minus_actual": "Độ lệch",
                                     "years_better_than_last_value": "Số năm hơn Last Value",
                                     "mae_vs_last_value_percent": "So với Last Value (%)"})
        st.dataframe(hien_wf, hide_index=True, column_config={
            "MAE": st.column_config.NumberColumn(format="%.3f"), "RMSE": st.column_config.NumberColumn(format="%.3f"),
            "MAPE (%)": st.column_config.NumberColumn(format="%.2f"), "Độ lệch": st.column_config.NumberColumn(format="%+.3f"),
            "So với Last Value (%)": st.column_config.NumberColumn(format="%+.1f")})
    # ---- 5. Mô hình dựa vào gì
    he_so = _csv_mo_hinh("linear_coefficients.csv")
    abl = _csv_mo_hinh("ablation_features.csv")
    if he_so is not None and abl is not None:
        st.subheader("Mô hình dựa vào đặc trưng nào")
        g1, g2 = st.columns(2)
        with g1:
            h = he_so.assign(**{"Đặc trưng": he_so["feature"].map(_TEN_DAC_TRUNG).fillna(he_so["feature"])})
            st.altair_chart(alt.Chart(h).mark_bar(color="#16834c").encode(
                y=alt.Y("Đặc trưng:N", sort="-x"), x=alt.X("ridge_std_coef:Q", title="Hệ số chuẩn hoá (Ridge)"),
                tooltip=["Đặc trưng", alt.Tooltip("ridge_std_coef:Q", format="+.3f")]).properties(height=220, width="container"))
            st.caption("Dương: tăng thì năng suất dự báo tăng. Chỉ có vài dòng dữ liệu nên hệ số chỉ để tham khảo, không phải quan hệ nhân quả.")
        with g2:
            a = abl.assign(**{"Bộ đặc trưng": abl["feature_set"].str.split(" \\(").str[0].replace({"day_du": "Đầy đủ", "khong_thoi_tiet": "Không thời tiết", "chi_thoi_tiet": "Chỉ thời tiết", "chi_nam": "Chỉ năm", "chi_dien_tich": "Chỉ diện tích", "LastValue_baseline": "Last Value"})})
            st.altair_chart(alt.Chart(a).mark_bar(color="#457b9d").encode(
                y=alt.Y("Bộ đặc trưng:N", sort="x"), x=alt.X("mae:Q", title="MAE cuốn chiếu (tạ/ha)"),
                tooltip=["Bộ đặc trưng", alt.Tooltip("mae:Q", format=".3f")]).properties(height=220, width="container"))
            ab = ms.get("ablation", {})
            if ab:
                st.caption(f"Giữ đủ đặc trưng: MAE {so(ab['mae_full_features'], 3)}; bỏ thời tiết: {so(ab['mae_without_weather'], 3)}. "
                           + ("Thời tiết giúp giảm sai số trong thí nghiệm này." if ab["weather_helps"] else "Thời tiết không giúp giảm sai số."))

    # ---- 6. Nhật ký tinh chỉnh
    tl = _csv_mo_hinh("tuning_log.csv")
    if tl is not None:
        with st.expander("Nhật ký tinh chỉnh tham số (chọn theo validation)"):
            st.dataframe(tl.rename(columns={"model": "Mô hình", "params": "Tham số", "train_mae": "MAE train", "val_mae": "MAE validation",
                                            "selected": "Được chọn"})[["Mô hình", "Tham số", "MAE train", "MAE validation", "Được chọn"]],
                         hide_index=True)
            st.caption("MAE train gần 0 nhưng MAE validation lớn cho thấy mô hình ghi nhớ dữ liệu huấn luyện (quá khớp) vì chỉ có vài dòng.")

    st.info(ms.get("caveat", "") + " Dự báo là tín hiệu khuyến nghị, không phải lệnh điều khiển tự động. "
            "Dự báo năm tới và mức rủi ro nằm ở trang Dự báo năng suất.", icon=":material/info:")


# ---------------- Trang: Tro ly AI ----------------
def hien_nhat_ky(nhat_ky):
    """Hien thi cac ham he thong da goi, ket qua dua cho Gemini va nguon cua cau tra loi."""
    goi = [e for e in (nhat_ky or []) if e.get("ham")]
    nguon = next((e for e in (nhat_ky or []) if e.get("nguon_tra_loi")), None)
    if not goi and not nguon:
        return
    with st.expander(f"Hệ thống đã gọi {len(goi)} hàm và đưa kết quả cho Gemini"):
        for e in goi:
            tham_so = ", ".join(f"{k}={v}" for k, v in (e.get("tham_so") or {}).items())
            st.markdown(f"**`{e['ham']}({tham_so})`**")
            if e.get("ket_qua"):
                st.code(e["ket_qua"], language="json")
        if nguon and nguon["nguon_tra_loi"] == "gemini":
            st.caption("Câu trả lời do Gemini viết từ kết quả hàm; mọi con số đã được đối chiếu với kết quả hàm.")
        elif nguon:
            st.caption(f"Câu trả lời dựng sẵn từ kết quả hàm, không phải Gemini viết ({nguon.get('ly_do', '')}).")


def trang_tro_ly():
    st.title("Trợ lý AI nông nghiệp")
    st.caption(
        "Mọi con số do hàm Python tính từ dữ liệu thật; AI chỉ chọn hàm và diễn đạt lại. "
        "Câu hỏi ngoài dữ liệu sẽ được trả lời “chưa có dữ liệu”."
    )
    st.caption("Lịch sử hội thoại được lưu trong cơ sở dữ liệu cục bộ và khôi phục khi mở lại cùng đường dẫn chat.")
    if not co_api_key():
        st.warning("Chưa có API key Gemini nên chưa chat được. Xem hướng dẫn trong README_HETHONG.md.")
    nap_phien(st, "tin_nhan", "lich_su_gemini")

    with st.expander("Ví dụ câu hỏi"):
        st.markdown(
            "- Năm tới năng suất lúa khoảng bao nhiêu? Nếu mưa ít hơn 20% thì sao?\n"
            "- Năm nào năng suất thấp nhất trong 10 năm qua?\n"
            "- So sánh năng suất năm 2019 và 2022\n"
            "- Thống kê năng suất 5 năm gần nhất: trung bình, cao nhất, thấp nhất\n"
            "- Năng suất 2020 là bao nhiêu? (số liệu thực tế)\n"
            "- Có những bộ dữ liệu nào?\n"
            "- Năm tới chắc chắn được mùa đúng không?"
        )
    if st.button("Xóa lịch sử chat", icon=":material/delete:", key="chat_xoa"):
        xoa_phien(st, "tin_nhan", "lich_su_gemini")
        st.rerun()

    for m in st.session_state["tin_nhan"]:
        with st.chat_message(m["role"], avatar=ICON_VAI[m["role"]]):
            st.markdown(m["noi_dung"])
            if m["role"] == "assistant":
                hien_nhat_ky(m.get("chi_tiet"))

    cau_hoi = st.chat_input("Hỏi về năng suất lúa: lịch sử, dự báo năm tới, so sánh năm, thống kê...")
    if cau_hoi:
        st.session_state["tin_nhan"].append({"role": "user", "noi_dung": cau_hoi})
        with st.chat_message("user", avatar=ICON_VAI["user"]):
            st.markdown(cau_hoi)
        nhat_ky = []
        chi_tiet = []
        with st.chat_message("assistant", avatar=ICON_VAI["assistant"]):
            with st.spinner("Đang trả lời..."):
                lich_su_truoc = copy.deepcopy(st.session_state["lich_su_gemini"])
                try:
                    tra_loi, st.session_state["lich_su_gemini"] = chat_logic.hoi(
                        cau_hoi, st.session_state["lich_su_gemini"], nhat_ky=nhat_ky, chi_tiet=chi_tiet
                    )
                except Exception as e:  # noqa: BLE001
                    tra_loi = f"Xin lỗi, có lỗi khi gọi AI: {e}. Bạn thử lại nhé."
                    st.session_state["lich_su_gemini"] = lich_su_truoc
            st.markdown(tra_loi)
            hien_nhat_ky(chi_tiet)
        st.session_state["tin_nhan"].append({"role": "assistant", "noi_dung": tra_loi, "nhat_ky": nhat_ky, "chi_tiet": chi_tiet})
        luu_phien(st, "tin_nhan", "lich_su_gemini")


# ---------------- Dieu huong ----------------
st.sidebar.markdown(
    """
<div class="brand">
  <div class="brand-mark"><span class="brand-icon">✳</span><span>AgFarm <span style="color:#24965b">AI</span></span></div>
  <div class="brand-caption">Nông nghiệp thông minh · An Giang</div>
</div>
""",
    unsafe_allow_html=True,
)
trang = st.sidebar.radio("Điều hướng", PAGES, key="trang", label_visibility="collapsed")
st.sidebar.divider()
if co_api_key():
    st.sidebar.success("Gemini AI đang sẵn sàng", icon=":material/check_circle:")
else:
    st.sidebar.warning("Chưa cấu hình Gemini API", icon=":material/key_off:")
st.sidebar.caption(
    f"DỮ LIỆU NỀN  ·  {int(hx.df['nam'].min())}–{hx.NAM_CUOI_CO_DU_LIEU}\n\n"
    "Lúa An Giang · Niên giám Thống kê 2024 · Open-Meteo"
)
st.markdown(
    f"""
<div class="topbar">
  <div><div class="topbar-title">AgFarm AI <span style="color:#8aa092;font-weight:500">/ {trang}</span></div>
  <div class="topbar-sub">Trung tâm điều hành nông trại · Dữ liệu có nguồn, dự báo có căn cứ</div></div>
  <div class="status-pill"><span class="status-dot"></span>{'Gemini đã kết nối' if co_api_key() else 'Chế độ dữ liệu cục bộ'}</div>
</div>
""",
    unsafe_allow_html=True,
)
{
    "Tổng quan": trang_tong_quan,
    "Dự báo năng suất": trang_du_bao,
    "Mô hình AI": trang_mo_hinh_ai,
    "Trợ lý AI": trang_tro_ly,
}[trang]()
