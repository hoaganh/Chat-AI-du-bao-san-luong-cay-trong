# Model card – dự báo năng suất lúa An Giang

- Phiên bản: `lua_forecast_v1`; mô hình đã chọn theo validation: **LinearRegression[default]**
- Đầu vào: nam, dien_tich_ha, mua_tong_mm, nhiet_tb_c, ngay_nong của năm t. Đầu ra: năng suất năm t+1 (tạ/ha).
- Chia thời gian: train [2016, 2019], validation [2020, 2021], test [2022, 2024].
- Bộ dữ liệu chỉ gồm 2015–2024; project không chứa số liệu 2025–2026.

## Kết quả test
MAE 2.039, RMSE 2.117, MAPE 3.11%, bias +2.039 tạ/ha.
Last Value baseline MAE 0.680. **Mô hình KHÔNG hơn baseline Last Value trên test** – chưa nên dùng thay baseline.

## Đánh giá cuốn chiếu (walk-forward) 2019–2024
Mỗi năm đích chỉ train trên quá khứ, cấu hình khai báo trước. MAE (tạ/ha): LastValue_baseline 1.025, LinearRegression 1.255, MovingAverage3_baseline 1.421, RandomForest(60,3,2) 2.108.
Mô hình tốt nhất theo MAE cuốn chiếu: LastValue_baseline. Chỉ 6 điểm, đọc thận trọng.
Bỏ thời tiết: MAE 1.683 so với đầy đủ 1.255 (thời tiết giúp giảm sai số trong thí nghiệm này).

## Giới hạn
- Chỉ 4 dòng train, 2 validation, 3 test; ước lượng sai số rất không ổn định.
- R² trên test rất âm vì năng suất 2022–2024 gần như đi ngang (phương sai nhỏ); ưu tiên đọc MAE/MAPE.
- Không phải LSTM/deep learning: với 9–10 điểm dữ liệu, mô hình sâu không có cơ sở huấn luyện.
- Không dùng thời tiết thực tế của năm đích; dự báo từ 2025 trở đi là ngoại suy của chuỗi An Giang cũ, không phải số liệu thực tế.

## An toàn
Dự báo chỉ là tín hiệu khuyến nghị, không phải lệnh tự động. Cần người có chuyên môn xác nhận trước khi thay đổi kế hoạch sản xuất.