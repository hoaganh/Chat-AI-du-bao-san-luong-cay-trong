# Đề 2: Chat AI dự báo sản lượng cây trồng (lúa An Giang)

Chat hỏi đáp tiếng Việt về **năng suất và sản lượng lúa tỉnh An Giang**. Mô hình ngôn ngữ (Gemini) chỉ *hiểu câu hỏi và viết nhận định*; **mọi con số do hàm Python tính** từ dữ liệu có nguồn (Niên giám Thống kê tỉnh An Giang + thời tiết Open-Meteo). Mỗi câu trả lời nêu căn cứ, bảng dẫn chứng, khoảng sai số và độ chính xác tham khảo; hỏi cây hoặc vùng khác thì trả lời "chưa có dữ liệu".

> Đồ án học tập. Số liệu và mô hình chỉ có giá trị tham khảo, không dùng làm căn cứ ký hợp đồng hay quyết định sản xuất.

## Kết quả chính

| Hạng mục | Kết quả |
|---|---|
| Dữ liệu | Lúa An Giang 2015–2024 (10 năm), 9/9 phép kiểm tra chất lượng đạt (`docs/NHAT_KY_LAM_SACH_DU_LIEU.md`) |
| Mô hình | Hồi quy tuyến tính (chọn bằng validation). Test 2022–2024: MAE 2,04 tạ/ha |
| Mốc so sánh | Lấy năm trước: MAE 0,68; trung bình 3 năm: MAE 0,85 → **mô hình thua cả hai mốc** (báo cáo trung thực, xem lý do trong báo cáo) |
| Dự báo 2025 | Khoảng tham khảo quanh 67,46 tạ/ha, kèm bảng kiểm chứng và độ chính xác ≈ 96,9% (chỉ 3 năm kiểm chứng) |
| Chat | 16/16 câu nghiệm thu đạt kiểm tra tự động với Gemini thật (câu hỏi: `docs/test_cases.csv`; kết quả chạy 12/11/2026: `outputs/chinh_thuc/ket_qua_16_cau.md`) |
| Kiểm thử bằng mã | 298 phép kiểm tra tự động, 0 lỗi (Gemini giả lập, không cần API key) |

## Cách hoạt động

```
Câu hỏi → [nhánh rule-based: năm xa] hoặc [Gemini chọn 1 trong 5 công cụ]
        → hàm Python tính số (du_bao / lich_su / so_sanh_nam / thong_ke / ds_bo_du_lieu)
        → mọi dự báo đi qua một hàm duy nhất: predict_yield()
        → bộ kiểm số: mỗi số trong câu trả lời phải khớp đúng trường và đơn vị của kết quả hàm
        → backend dựng bảng căn cứ + dẫn chứng; Gemini chỉ viết phần nhận định (không số)
        → độ chính xác tham khảo ở dòng cuối; ghi nhật ký route/công cụ/tham số
```

## Cấu trúc thư mục

| Đường dẫn | Nội dung |
|---|---|
| `app.py` | Giao diện Streamlit, 4 trang: Tổng quan, Dự báo năng suất, Mô hình AI, Trợ lý AI |
| `chat_logic.py`, `trinh_bay_tra_loi.py` | Bộ điều phối chat, kiểm soát số liệu, dựng câu trả lời |
| `ham_xu_ly.py`, `mo_hinh_du_bao.py`, `bo_du_lieu.py` | Hàm công cụ; huấn luyện và `predict_yield`; kiểm tra bộ dữ liệu |
| `gemini_client.py`, `db.py`, `chat_store.py` | Gọi Gemini API; lưu lịch sử chat (SQLite) |
| `api_forecast.py`, `giam_sat_drift.py` | API FastAPI; giám sát sai lệch dự báo so với thực tế |
| `lay_thoi_tiet.py`, `ghep_du_lieu.py`, `kiem_tra_du_lieu.py`, `them_nam_truoc_2015.py` | Chuỗi công cụ dữ liệu |
| `chay_bo_cau_hoi.py` | Chạy tự động bộ 16 câu nghiệm thu với Gemini thật |
| `data/`, `models/`, `outputs/`, `figures/` | Dữ liệu CSV; mô hình đã train; kết quả huấn luyện; biểu đồ |
| `tests/` | 15 tệp kiểm thử tự động |
| `docs/` | `test_cases.csv` (16 câu nghiệm thu), nhật ký làm sạch dữ liệu, hướng dẫn bổ sung dữ liệu, báo cáo |

## Cài đặt

Yêu cầu: Python 3.10 trở lên.

**Git Bash (Windows):**
```bash
git clone https://github.com/hoaganh/Chat-AI-du-bao-san-luong-cay-trong.git
cd Chat-AI-du-bao-san-luong-cay-trong
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```
**Linux / macOS:** dùng `source .venv/bin/activate` thay cho dòng `source .venv/Scripts/activate`.

`requirements.txt` là cận dưới phiên bản; bộ phiên bản đã chạy đủ kiểm thử nằm trong `requirements-tested.txt`.

## Đặt API key Gemini (không bao giờ đưa key vào Git)

Repo này **không chứa key**. Mỗi người dùng tự lấy key miễn phí tại <https://aistudio.google.com/api-keys> và đặt theo một trong hai cách (ứng dụng **không tự đọc file `.env`**):

```bash
# Cách 1 (khuyên dùng): biến môi trường, chỉ có hiệu lực trong cửa sổ terminal hiện tại
export GEMINI_API_KEY="dán-key-của-bạn"          # Git Bash / Linux / macOS
# PowerShell:  $env:GEMINI_API_KEY="dán-key-của-bạn"
```
```toml
# Cách 2: Streamlit secrets, tạo file .streamlit/secrets.toml (đã nằm trong .gitignore)
GEMINI_API_KEY = "dán-key-của-bạn"
```
Ngoài ra ứng dụng còn đọc file `api_key.txt` (một dòng) cho máy cá nhân; file này cũng nằm trong `.gitignore`. Nếu key của bạn từng bị lộ ở bất cứ đâu, hãy thu hồi và tạo key mới.

Không có key thì phần dữ liệu, mô hình và các kiểm thử bằng mã vẫn chạy; chỉ trang **Trợ lý AI** và `chay_bo_cau_hoi.py` cần key.

## Chạy chương trình

```bash
python mo_hinh_du_bao.py        # huấn luyện + đánh giá, ghi outputs/ và models/ (chạy lại nếu báo lỗi nạp model do khác phiên bản scikit-learn)
streamlit run app.py            # giao diện, mở http://localhost:8501, vào trang "Trợ lý AI"
uvicorn api_forecast:app --reload   # API (tùy chọn): http://127.0.0.1:8000/docs
```

### Kiểm thử
```bash
for t in tests/test_*.py; do python "$t"; done      # không cần API key; các tệp có đếm kiểm tra kết thúc bằng "TAT CA PASS"
python kiem_tra_du_lieu.py                           # kiểm tra chất lượng dữ liệu, sinh lại nhật ký làm sạch
python chay_bo_cau_hoi.py                            # bộ 16 câu với Gemini thật (cần key); thêm --chi TC04,TC05 để chạy lại vài câu
```
Một số kiểm thử tạo `agfarm.db` (lịch sử chat) và `outputs/chat_log.jsonl`; hai tệp này không được đưa lên Git.

## Dữ liệu và nguồn

- **Sản xuất lúa** (diện tích, sản lượng, năng suất): Niên giám Thống kê tỉnh An Giang 2024, biểu 127–129, trang 366–368.
- **Thời tiết** (tổng mưa, nhiệt độ trung bình, số ngày nóng trên 35 °C, mùa vụ 01/05–30/11): [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), tại một điểm gần Long Xuyên.
- Số liệu theo địa giới An Giang trước hợp nhất.

## Giới hạn đã biết

- Chỉ 10 năm dữ liệu của một cây ở một tỉnh; mô hình thua mốc đơn giản; chọn giữa hai mô hình dựa trên 2 năm validation nên rất bất định.
- Chưa đối chiếu lại từng con số với bản gốc niên giám; thời tiết chỉ tính trong mùa vụ và tại một điểm quan trắc.
- Kịch bản mưa vượt miền dữ liệu (ví dụ mưa +15%) là ngoại suy và chưa có cảnh báo riêng.
- Gemini không trả lời giống hệt nhau giữa các lần chạy; hệ thống đảm bảo con số, không đảm bảo cách diễn đạt.

## Bổ sung dữ liệu

Thời tiết 2010–2014 đã có sẵn; cần điền số liệu lúa các năm này từ niên giám để có 15 năm. Xem `docs/HUONG_DAN_BO_SUNG_DU_LIEU.md` và dùng `python them_nam_truoc_2015.py --thu` để kiểm tra trước khi ghép. Sau khi thêm dữ liệu, mọi con số dự báo và một số kiểm thử ghi cứng số hiện tại sẽ cần cập nhật.

## Tài liệu khác

thư mục `docs/` (báo cáo Word), `docs/NHAT_KY_LAM_SACH_DU_LIEU.md`, `docs/test_cases.csv`, `outputs/chinh_thuc/ket_qua_16_cau.md` (kết quả chạy Gemini thật), `outputs/model_card_lua.md`, `CHANGELOG_SUA_THEO_REVIEW.md` (lịch sử các thay đổi và lỗi đã sửa).
