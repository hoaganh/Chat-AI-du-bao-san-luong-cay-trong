# Hướng dẫn bổ sung dữ liệu lúa An Giang 2010–2014 (từ 10 lên 15 năm)

**Vì sao nên làm:** chỉ 10 năm (4 năm train, 2 năm validation, 3 năm test) nên so sánh mô hình rất bất định. Thêm 5 năm làm
tập train gần gấp đôi. Thời tiết 2010–2014 **đã có sẵn** trong `data/thoi_tiet_an_giang.csv` (Open-Meteo), nên chỉ thiếu số liệu lúa.

## Cần điền gì
File `data/bo_sung_lua_an_giang_2010_2014_MAU.csv`: với mỗi năm 2010–2014, điền 3 cột còn trống
`dien_tich_ha`, `san_luong_tan`, `nang_suat_ta_ha` (lúa cả năm, ranh giới An Giang cũ).

- **Nguồn nên dùng:** Niên giám Thống kê tỉnh An Giang các năm 2011–2015 (Cục Thống kê An Giang), cùng loại nguồn với số liệu 2015–2024 hiện có.
  Chỉ dùng số có trong niên giám; **không tự suy số**, không lấy số cả nước hay cả vùng thay cho tỉnh.
- **Đơn vị:** diện tích ha, sản lượng tấn, năng suất tạ/ha. Niên giám thường ghi *nghìn ha* và *nghìn tấn*: nhớ nhân 1.000.
- **Ghi nguồn:** ghi tên niên giám, năm, biểu, trang vào `docs/NHAT_KY_LAM_SACH_DU_LIEU.md` (mục 1) hoặc báo cáo.

## Ghép và chạy lại
```
python them_nam_truoc_2015.py --thu     # chỉ kiểm tra: ô trống, sai đơn vị, năng suất không khớp sản lượng/diện tích
python them_nam_truoc_2015.py           # ghi thật; file cũ được sao lưu thành lua_an_giang.csv.bak
python mo_hinh_du_bao.py                # train lại trên 15 năm
python kiem_tra_du_lieu.py              # sinh lại docs/NHAT_KY_LAM_SACH_DU_LIEU.md
python tests/test_nguon_du_bao_duy_nhat.py
```

## Điều sẽ thay đổi (cần cập nhật tay sau khi ghép)
- Mô hình học trên nhiều năm hơn nên **mọi con số dự báo, MAE, % chính xác đều đổi** (đây là lẽ thường, không phải lỗi).
- Một số test và `docs/test_cases.csv` ghi cứng số hiện tại (67,46; 2,039; 96,9%...). Chúng sẽ báo FAIL: hãy chạy lại, đọc số mới rồi
  cập nhật đáp án; **không** sửa code cho khớp số cũ.
- Báo cáo Word cần cập nhật bảng so sánh mô hình và phần giới hạn "chỉ có 10 năm".
- Các năm kiểm tra vẫn là 2022–2024 (hằng `TEST_START`), các năm thêm vào được dùng để huấn luyện.
