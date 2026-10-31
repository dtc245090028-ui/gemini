# Workflow: Audit Mode

## 1. Mục Tiêu
Rà soát độc lập, đánh giá chất lượng mã nguồn, kiến trúc, an toàn y tế và an ninh bảo mật mà TUYỆT ĐỐI KHÔNG chỉnh sửa bất kỳ dòng mã nguồn nào của hệ thống.

## 2. Khi Nào Kích Hoạt
- Định kỳ kiểm toán mã nguồn, kiểm tra an toàn bảo mật trước khi bàn giao hoặc nghiệm thu.
- Khi cần rà soát tuân thủ tiêu chuẩn GPP, an toàn dữ liệu y tế, và các quy tắc phòng thủ rò rỉ secret hoặc lỗi xuất kho FEFO.

## 3. Thang Đánh Giá Mức Độ Rủi Ro (Severity Rubric)
- **Critical (Nghiêm trọng):** Rò rỉ API key/secret (`GEMINI_API_KEY`, `OPENAI_API_KEY`), hỏng thuật toán FEFO (cho phép xuất bán thuốc quá hạn), bypass phân quyền RBAC (`routers/auth.py`).
- **High (Cao):** Thiếu khóa đồng thời (`pos_checkout_lock`) gây race condition làm âm kho, mất fallback AI làm sập server API khi mất mạng hoặc hết quota.
- **Medium (Trung bình):** Thiếu tuyên bố miễn trừ y tế (`MEDICAL_DISCLAIMER`), thiếu validate dữ liệu Pydantic đầu vào, hoặc nuốt ngoại lệ mà không ghi log.
- **Low (Thấp):** Vi phạm quy ước đặt tên file/hàm, thiếu chú thích docstring, định dạng mã nguồn chưa tối ưu.

## 4. Được Làm Gì / Không Được Làm Gì
- **ĐƯỢC:**
  - CHỈ ĐỌC toàn bộ mã nguồn, tài liệu, file cấu hình và test suites.
  - Được phép tạo và ghi báo cáo đánh giá vào thư mục `docs/Audit/` (tự tạo thư mục nếu chưa có).
- **KHÔNG ĐƯỢC:**
  - TUYỆT ĐỐI KHÔNG CHỈNH SỬA, THÊM, XÓA bất kỳ file source code nào trong hệ thống (`routers/`, `services/`, `database.py`, `schemas.py`, `static/`, `tests/`, `main.py`).
  - Không thay đổi file cấu hình môi trường hoặc cơ sở dữ liệu.

## 5. Quy Trình Làm Việc Từng Bước
1. **Rà soát An Ninh & Bí Mật:** Quét rò rỉ secret, API key, kiểm tra nguy cơ SQL Injection và tính hợp lệ của phân quyền RBAC trong `routers/auth.py`.
2. **Rà soát Nghiệp Vụ Y Tế & GPP:** Kiểm tra khóa chặn thuốc hết hạn tại `routers/pos.py`, tính chính xác của thuật toán FEFO, và sự hiện diện của lời nhắc miễn trừ trách nhiệm y tế (`MEDICAL_DISCLAIMER`).
3. **Rà soát Độ Ổn Định:** Kiểm tra cơ chế fallback và timeout trong `services/ai_service.py`, cơ chế chống race condition đa luồng tại `routers/pos.py`.
4. **Rà soát Kiểm Thử:** Chạy lệnh `pytest -v` ở chế độ chỉ đọc để ghi nhận trạng thái kiểm thử hiện hành.
5. **Tổng hợp Báo Cáo:** Phân loại các phát hiện theo thang đánh giá (Mục 3) và lưu báo cáo vào thư mục `docs/Audit/`.

## 6. Định Dạng Output Bắt Buộc
- **Phạm vi kiểm toán:** Danh sách module và file được rà soát.
- **Bảng tổng hợp phát hiện:** Bảng gồm: Mã phát hiện | Mức độ (Critical/High/Medium/Low) | Vị trí file | Mô tả rủi ro.
- **Chi tiết từng phát hiện:** Phân tích bối cảnh, bằng chứng vi phạm cụ thể tại từng file/dòng.
- **Khuyến nghị khắc phục:** Đề xuất hướng xử lý kỹ thuật cho Dev/Architect mà không tự động sửa code.

## 7. Checklist Tự Kiểm Tra Trước Khi Kết Thúc
- [ ] Đã xác nhận TUYỆT ĐỐI KHÔNG có file source code nào bị thay đổi (`git status` sạch sẽ ngoài `docs/Audit/`)?
- [ ] Phân loại mức độ rủi ro tuân thủ đúng Thang Đánh Giá tại Mục 3?
- [ ] Báo cáo kiểm toán hoàn chỉnh đã được xuất vào thư mục `docs/Audit/`?
