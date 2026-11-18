# Thay đổi theo báo cáo review Nhóm 02 (05/11/2026)

ZIP được sửa là bản MỚI HƠN bản mà báo cáo review kiểm tra: đã có sẵn CSV, model, outputs, README. Phần dưới ghi những gì đã sửa.

| Mục | Việc đã làm | Nơi sửa |
|---|---|---|
| P0 bí mật | Bỏ `api_key.txt` (chứa key thật) và `agfarm.db` (lịch sử chat) khỏi ZIP; thêm `.env.example`; key đọc theo thứ tự env → Streamlit secrets → file | `gemini_client.py`, `.gitignore`, `.env.example` |
| P0 chạy lại | `requirements.txt` có cận dưới, `requirements-tested.txt` là bộ đã chạy; README thêm lệnh test, nhật ký, nguồn dự báo | `README.md` |
| P1 hai engine | Thêm `predict_yield()` làm nguồn duy nhất; `du_bao()` (bộ lúa) gọi hàm này; chat, trang Dự báo, API ra cùng số + `model_id` + `data_version`. Bộ dữ liệu phụ gắn nhãn engine riêng | `mo_hinh_du_bao.py`, `ham_xu_ly.py`, `api_forecast.py`, `app.py` |
| P1 chính sách năm | `forecast_with_decision` chỉ nhận [năm đầu+1, năm cuối+1]; ngoài đó raise `NamNgoaiPhamVi`; API trả 422; chat trả "loi" | `mo_hinh_du_bao.py`, `api_forecast.py` |
| P1 chống bịa số | `_so_chua_xac_nhan` đối chiếu theo loại trường + đơn vị; câu sai được thay bằng câu dựng từ JSON | `chat_logic.py` |
| P1 khoảng dự báo | Bỏ nhãn "conformal" và "mức danh nghĩa 85,7%"; đổi thành "khoảng sai số tham khảo" kèm giải thích | `mo_hinh_du_bao.py`, `app.py` |
| P1 10 năm | `MIN_NAM = 10`: bộ 8–9 năm bị từ chối khi nhập | `bo_du_lieu.py` |
| Nhật ký | `outputs/chat_log.jsonl`: question, route, tool_name, args, model_id, data_version, result_fields, final_answer, error | `chat_logic.py`, `app.py` |
| Test | Test API không còn ép "đổi mưa thì số phải đổi"; thêm `tests/test_nguon_du_bao_duy_nhat.py`; cập nhật test 9 năm | `tests/` |

## Đợt 2: đổi tên, thu gọn, dọn file
| Mục | Việc đã làm |
|---|---|
| Đổi tên | `forecast_lab4.py` thành `mo_hinh_du_bao.py`; `tests/test_lab4_phan_tich.py` thành `tests/test_mo_hinh_phan_tich.py`; bỏ chữ "Lab 4" trong code, giao diện, README, biểu đồ |
| Thu gọn mô hình | 11 cấu hình thành 2 mô hình (Linear Regression, Random Forest 60/3/2) + 2 baseline; bỏ Ridge và Gradient Boosting khỏi so sánh. Kết quả chính KHÔNG đổi: vẫn chọn Linear, test MAE 2,039, dự báo 2025 = 67,46 tạ/ha. Chỉ bảng so sánh mô hình, `tuning_log.csv`, hình MAE và walk-forward có ít dòng hơn nên phần mô tả trong báo cáo Word cần cập nhật |
| Rút công cụ chat | 15 công cụ thành 5: `du_bao`, `lich_su`, `so_sanh_nam`, `thong_ke`, `ds_bo_du_lieu`. Các chức năng thời tiết, lợi nhuận, kiến thức, chẩn đoán ảnh vẫn ở các trang riêng của app. Câu hỏi năm xa và 2022–2024 đi nhánh rule-based nội bộ |
| Bộ nghiệm thu | `docs/test_cases.csv` (10 câu cơ bản + 6 câu khó) và `tests/test_test_cases.py` kiểm tra đáp án khớp số thật |
| File đã xóa | `.agents/`, `.claude/` (hướng dẫn công cụ AI), `so_sanh_appliances.py` + `du_lieu_doi_chung/` + `outputs/so_sanh_hai_bo_du_lieu.*` (bộ dữ liệu ngoài đề), `ve_bieu_do.py` + `figures/kiem_tra_xu_huong.png`, `docs/BO_10_CAU_KIEM_THU.md` (số liệu lỗi thời, thay bằng test_cases.csv), `docs/BAO_CAO_DU_LIEU.md` (trùng bản .docx), `README_MO_HINH.md` (gộp vào README), `outputs/api_test_result.json` (sinh lại khi chạy test) |

## Đợt 3: sửa câu 4, 5, 6 của bộ 10 câu không qua
- **Nguyên nhân câu 5 và 6:** bộ kiểm số mới xếp nhầm trường `xu_huong_moi_nam` (câu 5) và `nam_a`/`nam_b` (câu 6) vào loại "năm", nên chặn các con số đúng (0,528 tạ/ha; 62,6 tạ/ha...) và chat trả câu "đã ẩn".
- **Nguyên nhân câu 4:** công cụ `giai_thich` đã bị bỏ nên phần "vì sao" không còn thời tiết.
- **Đã sửa:** trường con kế thừa loại đơn vị của trường cha; tách riêng trường đếm (`so_nam`) và `ngay_nong` để số lạ vẫn bị chặn (ví dụ "5 tạ/ha" không lọt nhờ trùng `so_nam = 5`); chấp nhận làm tròn đúng (0,53 cho 0,528); `thong_ke` trả thêm thời tiết cùng năm của năm thấp nhất/cao nhất kèm lưu ý không chứng minh nguyên nhân.
- **Test mới:** chạy trọn luồng chat (Gemini giả, công cụ thật) cho câu 4, 5, 6 và kiểm số cho câu 1, 2, 3, 8 trong `tests/test_nguon_du_bao_duy_nhat.py`.

- **Bổ sung sau ảnh chụp màn hình:** `thong_ke` trả thêm `gia_tri_dau`/`gia_tri_cuoi` (Gemini hay nêu 62,99 → 65,77); khi Gemini viết số sai, backend dựng câu đúng từ JSON của `thong_ke` thay vì câu cụt "đã ẩn".

- **Câu 5 khi Gemini gọi `lich_su` (ảnh chụp lần 2):** `lich_su` trả thêm `xu_huong_moi_nam`, `thay_doi_dau_cuoi_nang_suat`, `so_nam`; có câu dựng từ JSON cho `lich_su` khi Gemini viết số sai.

## Đợt 4: gỡ phần ngoài phạm vi Đề 2
- **Đã gỡ 5 trang khỏi `app.py`** (1.022 xuống ~500 dòng): Chẩn đoán bệnh (ảnh), Thời tiết và cảnh báo, Quản lý mùa vụ, Kho kiến thức, Bộ dữ liệu; Tổng quan bỏ phần nông trại và cảnh báo thời tiết.
- **Đã xóa file:** `ai_vision.py`, `canh_bao.py`, `tinh_toan.py`, `kien_thuc.py`, thư mục `kien_thuc/`, `tests/test_tinh_toan.py`; `tests/test_he_thong.py` chỉ còn phần kiểm 4 trang còn lại. Bỏ Pillow, openpyxl, requests khỏi `requirements.txt`.
- **Giữ lại vì còn được dùng:** `db.py` (lưu lịch sử chat), `bo_du_lieu.py` (nạp dữ liệu và kiểm tra tối thiểu 10 năm, `ham_xu_ly` và `mo_hinh_du_bao` gọi), `ham_xu_ly.thoi_tiet_du_bao`, `api_forecast.py`, `giam_sat_drift.py`.

## Đợt 5: sửa theo nhận xét về câu trả lời của chat
| Nhận xét | Đã làm |
|---|---|
| Sai số/khoảng thiếu căn cứ | Khoảng cũ (±1,98) không bao phủ nổi sai lệch năm 2024 (2,77). Khoảng mới = giá trị giữa ± sai lệch lớn nhất của 3 năm kiểm chứng, kèm bảng dẫn chứng |
| Phải nêu vì sao ra số, lấy căn cứ ở đâu | Khối "Căn cứ dữ liệu" (cây, vùng, năm, nguồn) + "Cách ra con số" (đầu vào năm trước, kịch bản, mốc TB 3 năm) |
| Dẫn chứng rồi mới kết luận; so sánh làm bảng | Mọi câu trả lời: bảng dẫn chứng trước, kết luận sau; so sánh có cột Chênh và % thay đổi |
| Phải có % chính xác, để cuối | Dòng cuối: độ chính xác tham khảo ≈ 96,9% (= 100% − MAPE 3,1% trên 3 năm), kèm lưu ý chỉ 3 mẫu |
| Không đưa số cụ thể vì dễ sai; lời khuyên canh tác | Kết quả trả dạng khoảng, nói rõ "chỉ tham khảo, không dùng ký hợp đồng"; phần Nhận định/gợi ý canh tác do Gemini viết, không kèm số |
| Thiếu trung bình của năm nào, vùng nào | Bảng thống kê ghi rõ giai đoạn và vùng ("Trung bình 5 năm, cả giai đoạn 2020–2024, An Giang") |
| Không đưa câu hỏi hạ tầng model vào câu hỏi | Bỏ "Hệ thống dùng model AI gì?" khỏi câu hỏi mẫu; câu trả lời về AI được viết đầy đủ hơn (dữ liệu, cách chia, bảng so sánh, độ chính xác, giới hạn) |
| Số liệu do backend dựng | Module `trinh_bay_tra_loi.py` dựng bảng từ JSON; Gemini không sửa được số |

## Đợt 6: nhật ký làm sạch, bộ chạy 16 câu, khung bổ sung dữ liệu
- **`kiem_tra_du_lieu.py` + `docs/NHAT_KY_LAM_SACH_DU_LIEU.md`:** nguồn, cách lấy từng cột, 9 phép kiểm (cấu trúc, ô trống, năm trùng/thiếu, đơn vị, khoảng hợp lý, ngoại lệ IQR, biến động năm, thời tiết), giới hạn dữ liệu.
- **`chay_bo_cau_hoi.py`:** chạy 16 câu qua chat thật, kiểm tra tự động theo chuỗi, ghi CSV/MD để điền cột `nguoi_cham`; `tests/test_chay_bo_cau_hoi.py` kiểm bằng Gemini giả (cả việc bộ kiểm tra BẮT được câu sai).
- **Hai lỗi định tuyến tìm thấy khi viết bộ chạy:** (1) mọi câu có "sản lượng" + năm ≥ 2025 bị trả lời "chưa có số liệu", kể cả câu kịch bản "mưa ít hơn 20% và diện tích tăng 10%" (câu khó số 1 của đề); nay câu kịch bản đi tới hàm dự báo. (2) "Năng suất lúa năm 2030 là bao nhiêu?" (không có chữ "dự báo") nay đi nhánh xu hướng, không rơi vào Gemini.
- **Bổ sung dữ liệu 2010–2014:** chưa thêm được vì không tìm được bảng lúa An Giang theo từng năm có nguồn rõ ràng (không dùng số cả nước/cả vùng). Đã chuẩn bị `data/bo_sung_lua_an_giang_2010_2014_MAU.csv` (thời tiết điền sẵn), `them_nam_truoc_2015.py` (kiểm tra rồi mới ghép, sao lưu) và `docs/HUONG_DAN_BO_SUNG_DU_LIEU.md`; pipeline đã thử chạy thông với 15 năm bằng số giả trong thư mục tạm.

## Đợt 7: sửa theo kết quả chạy Gemini thật (TC09, TC14, TC16)
- **TC14, TC16:** bộ kiểm số coi số năm trong câu từ chối là số lạ khi Gemini không gọi hàm; nay chấp nhận số NĂM hợp lệ (từ câu hỏi và phạm vi dữ liệu), vẫn chặn số khác (100 tạ/ha, 2031 là 70 tạ/ha). Khi bị chặn mà chưa gọi hàm: trả lời hướng dẫn hỏi lại thay vì "đã ẩn".
- **TC09:** `lich_su` và `thong_ke` âm thầm cắt khoảng năm (hỏi 2012–2015 chỉ trả 2015). Nay trả `thieu_nam`/`luu_y_thieu_nam` và câu trả lời hiển thị "Không có dữ liệu cho năm 2012–2014"; tiêu chí TC09 chỉ cấm số năng suất gắn với năm 2012.
- **`chay_bo_cau_hoi.py --chi`** gộp vào kết quả cũ thay vì ghi đè; thêm kiểm tra đường API key.

## Chưa làm (cần nhóm quyết định)
- Ví dụ cây khác ở vùng khác (nhận xét "đưa vài ví dụ cây gì trồng ở đâu"): hệ thống chỉ có dữ liệu lúa An Giang, thêm ví dụ khi chưa có dữ liệu có nguồn sẽ là số bịa. Cần thêm bộ dữ liệu thật trước.
- Câu hỏi năm xa (2026 trở đi, nhánh xu hướng) chưa có bảng và % chính xác như dự báo 1 năm.
- Video demo 3 phút và điền cột `ket_qua_thuc_te_dung_sai` trong `docs/test_cases.csv` (cần chạy với Gemini thật).
- Kiểm thử với Gemini API thật và giao diện trên trình duyệt thật.
- Đối chiếu CSV với Niên giám Thống kê bản gốc (cần tài liệu gốc, không làm được từ ZIP).
- Cập nhật báo cáo Word (`docs/BAO_CAO_DO_AN.docx`): tên file mới, bảng so sánh 2 mô hình, 5 công cụ chat.
