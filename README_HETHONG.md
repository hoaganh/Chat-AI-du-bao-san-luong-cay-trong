# AgFarm AI - Chat AI dự báo năng suất lúa An Giang

Chạy cả hệ thống bằng 1 lệnh trong thư mục dự án:

```
pip install -r requirements.txt
python mo_hinh_du_bao.py      # train mô hình (lần đầu hoặc khi đổi máy)
streamlit run app.py
```

Giao diện sáng nằm trong `.streamlit/config.toml` (thư mục `.streamlit` cạnh `app.py`). Thiếu file này thì app vẫn chạy nhưng theo màu hệ thống.

Đặt biến môi trường `GEMINI_API_KEY` (khuyên dùng) hoặc Streamlit secrets; xem `.env.example` và README.md. Không nộp `api_key.txt`.
Không có key thì các trang khác vẫn chạy, chỉ Trợ lý AI báo "chưa có API key".

## 4 trang

| Trang | Làm gì | Số liệu đến từ đâu |
|---|---|---|
| Tổng quan | KPI dữ liệu lúa An Giang 2015–2024, năng suất năm gần nhất, dự báo năm kế tiếp | `data/lua_an_giang.csv` + `mo_hinh_du_bao.predict_yield` |
| Dự báo năng suất | Dự báo 1 năm tới, kịch bản mưa/diện tích, so với baseline, mức rủi ro | `mo_hinh_du_bao.predict_yield` (qua hàm `du_bao`) |
| Mô hình AI | Bảng so sánh mô hình và baseline, MAE theo năm, đánh giá cuốn chiếu, hệ số | `outputs/` do `python mo_hinh_du_bao.py` sinh ra |
| Trợ lý AI | Chat tiếng Việt về năng suất lúa (5 công cụ: dự báo, lịch sử, so sánh năm, thống kê, danh sách bộ dữ liệu); khôi phục lịch sử theo phiên | Hàm Python tính số liệu; Gemini diễn đạt câu trả lời; SQLite lưu lịch sử chat |

## Giới hạn cần biết (nói thẳng trong báo cáo)
- Trang **Dự báo năng suất** dùng hồi quy để dự báo năng suất năm kế tiếp. Dòng dữ liệu được căn thời gian: diện tích/thời tiết năm t dự báo năng suất năm t+1. Train target 2016–2019, validation 2020–2021, test cuối 2022–2024; mô hình được chọn bằng validation. Test MAE: Linear Regression 2,039, baseline trung bình 3 năm 0,846, Last Value 0,680 tạ/ha; mô hình thua baseline ở test và điều này được nêu rõ.
- Chỉ có 10 năm dữ liệu (mức tối thiểu của đề), nên kết quả so sánh mô hình rất bất định.
- Chat chỉ trả lời về lúa An Giang; cây/vùng khác trả lời "chưa có dữ liệu".
- Chưa có: dự báo cho tỉnh An Giang mới sau hợp nhất (dữ liệu dùng ranh giới cũ).
