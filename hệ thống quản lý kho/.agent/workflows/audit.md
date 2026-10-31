# Workflow: Audit Mode — Hệ Thống Quản Lý Kho Tích Hợp AI

## 1. Mục Tiêu
Rà soát độc lập, đánh giá chất lượng mã nguồn, kiến trúc Clean Architecture 3 tầng, an toàn CSDL ACID, chốt chặn chống tồn âm và an toàn AI mà TUYỆT ĐỐI KHÔNG chỉnh sửa bất kỳ dòng mã nguồn nào của hệ thống kho (CHẾ ĐỘ CHỈ ĐỌC).

---

## 2. Khi Nào Kích Hoạt
- Định kỳ kiểm toán mã nguồn, kiểm tra an toàn kỹ thuật trước các mốc nộp bài và chấm thi đồ án môn học (KT1, KT2, KT3, Final).
- Khi cần rà soát tuân thủ các quy tắc cốt lõi: bảo vệ CSDL, chốt chặn tồn âm kép, tính toàn vẹn thẻ kho (`stock_ledger`), an toàn AI và phòng chống rò rỉ secret.

---

## 3. Thang Đánh Giá Mức Độ Rủi Ro (Severity Rubric)

- **Critical (Nghiêm trọng):**
  - Rò rỉ API key / Secret (`GEMINI_API_KEY`, `SECRET_KEY`, `.env`).
  - Phá vỡ chốt chặn chống tồn âm (cho phép xuất quá số lượng tồn kho gây âm kho).
  - Bypass phân quyền RBAC (cho phép vai trò thấp thực hiện chức năng quản trị).
  - Mất tính toàn vẹn ACID (cập nhật tồn kho thành công nhưng không ghi Thẻ kho, hoặc ngược lại).
- **High (Cao):**
  - Thiếu khóa đồng thời hoặc giao dịch cách ly gây race condition khi nhiều thủ kho cùng xuất hàng.
  - Thiếu Fallback Heuristic Engine khiến server/giao diện sập khi Gemini API timeout hoặc hết quota (429).
  - Thiếu cơ chế Idempotency Key trên các endpoint tạo phiếu dẫn đến nguy cơ trừ kho trùng lặp.
- **Medium (Trung bình):**
  - Rò rỉ thông tin nhạy cảm (giá mua/giá vốn) vào prompt AI khi không phục vụ phân tích chi phí.
  - Thiếu validate dữ liệu đầu vào trong Pydantic schemas (cho phép số lượng <= 0, chuỗi rỗng).
  - Nuốt ngoại lệ (`try...except: pass`) mà không ghi log truy vết.
  - Giao diện thiếu ConfirmModal bắt buộc nhập lý do (>= 5 ký tự) khi hủy/xóa phiếu kho.
- **Low (Thấp):**
  - Vi phạm quy ước đặt tên file/hàm hoặc cấu trúc thư mục.
  - Thiếu docstring/comment bằng tiếng Việt giải thích logic cho sinh viên bảo vệ trước hội đồng.
  - Định dạng mã nguồn, linting hoặc style CSS chưa đồng bộ.

---

## 4. Được Làm Gì / Không Được Làm Gì

- **ĐƯỢC:**
  - CHỈ ĐỌC toàn bộ mã nguồn (`backend/app/`, `frontend/src/`), tài liệu, file cấu hình và test suites.
  - Chạy lệnh test ở chế độ kiểm toán để đo lường trạng thái pass/fail.
  - Tạo và ghi báo cáo đánh giá vào thư mục `docs/SDLC/` hoặc `docs/Audit/` (tự tạo thư mục nếu chưa có).
- **KHÔNG ĐƯỢC:**
  - TUYỆT ĐỐI KHÔNG CHỈNH SỬA, THÊM, XÓA bất kỳ file source code nào trong hệ thống (`backend/app/`, `frontend/src/`, `backend/tests/`).
  - Không thay đổi file cấu hình môi trường hoặc cơ sở dữ liệu `warehouse.db`.

---

## 5. Quy Trình Làm Việc Từng Bước

1. **Rà soát An Ninh & Bí Mật:**
   - Quét mã nguồn tìm kiếm API key, secret, mật khẩu hardcoded.
   - Kiểm tra nguy cơ SQL Injection (SQLAlchemy parameter binding) và phân quyền RBAC tại `backend/app/api/v1/endpoints/`.
2. **Rà soát Nghiệp Vụ Kho & Giao Dịch ACID:**
   - Kiểm tra ràng buộc `CheckConstraint("current_stock >= 0")` trong model `Product`.
   - Kiểm tra logic trừ kho trong `inventory_service.py`: Có bọc `db.begin()` không? Có kiểm tra số lượng khả dụng trước khi trừ không?
   - Kiểm tra tính đồng bộ của Thẻ kho (`stock_ledger`): Có ghi nhận tức thời cùng transaction không?
   - Kiểm tra cỗ máy trạng thái xuất kho 3 bước (`CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`).
3. **Rà soát Độ Ổn Định & An Toàn AI:**
   - Kiểm tra cơ chế tự động chuyển sang `FallbackService` trong `ai_service.py` khi Gemini API timeout (>10s) hoặc lỗi HTTP 429.
   - Kiểm tra prompt templates tại `backend/app/ai/prompts/` để đảm bảo không rò rỉ dữ liệu nhạy cảm.
   - Kiểm tra cache in-day (`ai_cache.py`) để tối ưu chi phí và tốc độ phản hồi.
4. **Rà soát Kiểm Thử:**
   - Chạy lệnh kiểm thử ở chế độ chỉ đọc: `cd backend; pytest` để ghi nhận trạng thái kiểm thử hiện hành.
5. **Tổng Hợp Báo Cáo Kiểm Toán:**
   - Phân loại các phát hiện theo thang đánh giá (Mục 3).
   - Xuất báo cáo chi tiết vào `docs/SDLC/` hoặc `docs/Audit/`.

---

## 6. Định Dạng Output Bắt Buộc

- **Phạm vi kiểm toán:** Danh sách các module và file đã rà soát.
- **Bảng tổng hợp phát hiện:**
  | Mã phát hiện | Mức độ | Vị trí file / Dòng | Tóm tắt rủi ro |
  | :--- | :--- | :--- | :--- |
- **Chi tiết từng phát hiện:** Phân tích bối cảnh, bằng chứng vi phạm cụ thể tại từng file/dòng.
- **Khuyến nghị khắc phục:** Đề xuất hướng xử lý kỹ thuật cho Dev/Architect mà không tự động sửa code.

---

## 7. Checklist Tự Kiểm Tra Trước Khi Hoàn Tất Mode

- [ ] Đã xác nhận TUYỆT ĐỐI KHÔNG có file source code nào bị thay đổi (`git status` sạch sẽ ngoài tài liệu báo cáo)?
- [ ] Phân loại mức độ rủi ro tuân thủ đúng Thang Đánh Giá tại Mục 3?
- [ ] Báo cáo kiểm toán hoàn chỉnh đã được xuất đúng thư mục quy định?
