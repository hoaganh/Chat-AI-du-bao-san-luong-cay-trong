# Nhật ký làm sạch và kiểm tra dữ liệu — Lúa An Giang 2015–2024

File này do `python kiem_tra_du_lieu.py` sinh ra; chạy lại sau khi đổi `data/lua_an_giang.csv`.

## 1. Nguồn và cách lấy
| Nhóm số liệu | Nguồn | Cách lấy / định nghĩa |
|---|---|---|
| Diện tích, sản lượng, năng suất lúa theo năm | Niên giám Thống kê tỉnh An Giang 2024, biểu 127–129, trang 366–368 | Lấy từ bảng niên giám, đơn vị: diện tích ha; sản lượng tấn; năng suất tạ/ha (cách nhập do nhóm ghi lại trong báo cáo) |
| Tổng mưa mùa vụ (`mua_tong_mm`) | Open-Meteo Historical Weather API (`archive-api.open-meteo.com`) | Tổng `precipitation_sum` hằng ngày, 01/05–30/11 mỗi năm, tọa độ 10,38 Bắc, 105,43 Đông (gần Long Xuyên) |
| Nhiệt độ trung bình (`nhiet_tb_c`) | Open-Meteo | Trung bình `temperature_2m_mean` hằng ngày cùng giai đoạn |
| Số ngày nóng (`ngay_nong`) | Open-Meteo | Số ngày có `temperature_2m_max` > 35 °C cùng giai đoạn |

## 2. Các bước xử lý (script trong dự án)
1. `lay_thoi_tiet.py`: gọi Open-Meteo từng năm, tính 3 chỉ số thời tiết, ghi `data/thoi_tiet_an_giang.csv`; năm nào lỗi thì để trống, không điền giả.
2. `ghep_du_lieu.py`: ghép thời tiết vào số liệu lúa theo cột `nam`; **dừng và báo lỗi** nếu thiếu năm, thiếu cột hoặc có năm trùng, không ghi file kết quả.
3. `bo_du_lieu.py`: khi nạp dữ liệu, **từ chối** bộ dưới 10 năm hoặc năm không liên tục; **cảnh báo** (không từ chối) khi năng suất lệch hơn 2% so với sản lượng × 10 ÷ diện tích.
4. `kiem_tra_du_lieu.py` (file này): kiểm tra độc lập sau khi ghép, kết quả ở mục 3.

## 3. Kết quả kiểm tra (9/9 mục Đạt)
| Mục | Cách kiểm | Kết quả thật | Đánh giá | Ghi chú |
|---|---|---|---|---|
| 1. Cấu trúc bảng | Đủ 7 cột đúng tên; mọi cột là số | Thiếu cột: không; kiểu số: True | **Đạt** |  |
| 2. Ô trống | Đếm ô trống (NaN) trong 7 cột | 0 ô trống | **Đạt** |  |
| 3. Năm trùng | Kiểm tra cột nam có giá trị lặp | Năm trùng: không | **Đạt** |  |
| 4. Năm liên tục và đủ 10 năm | So sánh với dãy năm đầu–năm cuối; đếm số năm (đề yêu cầu ≥ 10) | 2015–2024, 10 năm; năm thiếu: không | **Đạt** |  |
| 5. Nhất quán đơn vị | Sản lượng (tấn) so với năng suất (tạ/ha) × diện tích (ha) ÷ 10, từng năm | Lệch lớn nhất 0,007% (năm 2018); lệch trung bình 0,005% | **Đạt** | Lệch rất nhỏ, phù hợp với việc làm tròn năng suất ở 2 chữ số |
| 6. Khoảng giá trị hợp lý | Mỗi cột nằm trong ngưỡng hợp lý (ngưỡng do nhóm đặt: dien_tich_ha 300000–900000; san_luong_tan 2e+06–6e+06; nang_suat_ta_ha 40–80; mua_tong_mm 800–3000; nhiet_tb_c 24–31; ngay_nong 0–120) | Ngoài ngưỡng: không | **Đạt** |  |
| 7. Giá trị bất thường (IQR) | Quy tắc 1,5×IQR cho năng suất, diện tích, mưa, nhiệt độ | Ngoại lệ: không | **Đạt** |  |
| 8. Biến động năm này so với năm trước | Đổi quá 8% giữa hai năm liền kề (năng suất, diện tích) | Vượt ngưỡng: không | **Đạt** |  |
| 9. Thời tiết có thật cho mọi năm | Mưa > 0 và nhiệt độ > 0 ở mọi dòng (không điền giả) | Mưa nhỏ nhất 1.250,7 mm; nhiệt độ nhỏ nhất 26,71 °C | **Đạt** |  |

## 4. Bảng số liệu sau kiểm tra

| Năm | Diện tích (ha) | Sản lượng (tấn) | Năng suất (tạ/ha) | Mưa (mm) | Nhiệt độ TB (°C) | Ngày nóng |
|---|---|---|---|---|---|---|
| 2015 | 644.258 | 4.073.742 | 63,23 | 1.250,7 | 27,63 | 8 |
| 2016 | 669.011 | 3.974.745 | 59,41 | 1.613,4 | 27,3 | 15 |
| 2017 | 641.104 | 3.879.505 | 60,51 | 1.896,9 | 26,98 | 0 |
| 2018 | 623.070 | 3.926.874 | 63,02 | 1.533,6 | 27,08 | 0 |
| 2019 | 626.123 | 3.919.253 | 62,6 | 1.418,9 | 27,33 | 1 |
| 2020 | 637.228 | 4.014.080 | 62,99 | 1.997,3 | 27,33 | 6 |
| 2021 | 624.959 | 4.143.032 | 66,29 | 2.058,1 | 27,08 | 0 |
| 2022 | 604.380 | 3.943.771 | 65,25 | 1.944,7 | 26,71 | 0 |
| 2023 | 616.206 | 4.067.658 | 66,01 | 1.903,1 | 27,35 | 3 |
| 2024 | 618.586 | 4.068.224 | 65,77 | 2.049,9 | 27,48 | 5 |

## 5. Giới hạn dữ liệu (cần nêu trong báo cáo)
- **Chưa đối chiếu lại từng số với bản gốc Niên giám**: bản kiểm tra này chỉ bắt lỗi nhất quán, không thay việc đối chiếu nguồn.
- **Lệch kỳ**: thời tiết tính trong 01/05–30/11, còn năng suất niên giám là số cả năm (có thể gồm cả vụ Đông Xuân). Mưa và nhiệt của mùa vụ có thể không phản ánh hết điều kiện cả năm.
- **Địa giới cũ**: số liệu theo ranh giới An Giang trước hợp nhất (2025); không đại diện tỉnh sau hợp nhất.
- **Một điểm quan trắc**: thời tiết lấy tại một tọa độ gần Long Xuyên, không phải trung bình toàn tỉnh.
- **Chỉ 10 năm**: đủ mức tối thiểu của đề nhưng ít cho việc so sánh mô hình; nên bổ sung các năm trước 2015 khi có nguồn.
