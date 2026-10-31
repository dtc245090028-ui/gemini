# Workflow: Dev Mode

## 1. Mục Tiêu
Hiện thực hóa các tính năng, API endpoints hoặc giao diện người dùng theo đúng quy chuẩn mã nguồn sạch, kiến trúc phân tầng và bảo mật của PharmaCare AI.

## 2. Khi Nào Kích Hoạt
- Khi có kế hoạch kiến trúc đã được phê duyệt hoặc nhận yêu cầu triển khai mã nguồn cụ thể.
- Khi người dùng yêu cầu thực hiện chức năng (ví dụ: *"làm S-xx"* hoặc theo Phase/Tiêu chí KT), mở ngay tài liệu `docs/plans/implementation_plan.md` (kết hợp `docs/specs/yeu_cau.md`) để đọc đặc tả kỹ thuật, tiêu chuẩn đầu vào/đầu ra của chức năng tương ứng.

## 3. Được Làm Gì / Không Được Làm Gì
- **ĐƯỢC:**
  - Viết code mới và chỉnh sửa code theo đúng phân tầng: `database.py` (Models), `schemas.py` (Validation), `services/` (Business Logic/AI), `routers/` (API Controllers), `static/` (Giao diện chính).
  - Tích hợp bảo vệ đa luồng bằng `threading.Lock` khi can thiệp giao dịch kho/hóa đơn tương tự `pos_checkout_lock`.
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối không can thiệp thư mục `frontend/` trừ khi có yêu cầu bằng văn bản rõ ràng.
  - Không hardcode API key, chuỗi bí mật, token vào mã nguồn.
  - Không sửa đổi schema CSDL khi chưa chạy script sao lưu.
  - Không viết logic nghiệp vụ phức tạp trực tiếp bên trong `routers/`.

## 4. Quy Trình Làm Việc Từng Bước
1. **Kiểm tra đầu vào:** Đọc đặc tả nhiệm vụ trong `docs/plans/implementation_plan.md` (hoặc `docs/specs/yeu_cau.md`); xác định các file liên quan.
2. **Sao lưu CSDL (nếu đụng schema):** Chạy `python scripts/backup_data.py backup` trước khi thêm/sửa cột ở `database.py`.
3. **Cập nhật Schema & Model:** Định nghĩa Pydantic Schemas trong `schemas.py` và ORM Models trong `database.py`.
4. **Triển khai Logic:** Xây dựng business logic trong `services/`, thiết lập timeout và fallback dự phòng.
5. **Tạo/Cập nhật Endpoint:** Viết API router trong `routers/`, gán `status_code`, inject dependencies `get_db` và `require_roles`.
6. **Xử lý lỗi chuẩn mực:** Dùng `fastapi.HTTPException` với status code phù hợp và thông điệp lỗi tiếng Việt rõ ràng.
7. **Tích hợp giao diện (nếu có):** Cập nhật UI SPA tại `static/index.html`, `static/js/app.js`, `static/js/api.js`.
8. **Chạy kiểm thử xác minh:** Thực thi lệnh `pytest -v` để đảm bảo code mới không làm gãy các test case hiện tại.

## 5. Định Dạng Output Bắt Buộc
- **Nhiệm vụ / Chức năng đang làm:** Tên hoặc mã chức năng theo `docs/plans/implementation_plan.md`.
- **Danh sách file thay đổi:** Liệt kê đường dẫn file và vai trò chỉnh sửa.
- **Chi tiết thay đổi:** Tóm tắt các hàm, class, router vừa thêm hoặc sửa đổi.
- **Kết quả kiểm thử nhanh:** Kết quả chạy `pytest -v` sau khi code xong.

## 6. Checklist Tự Kiểm Tra Trước Khi Kết Thúc
- [ ] Code có tuân thủ quy ước đặt tên: `snake_case` (hàm, file), `PascalCase` (class)?
- [ ] Đã phân quyền đúng vai trò RBAC (`cashier`, `pharmacist`, `manager`) chưa?
- [ ] Các thông báo `HTTPException` đều bằng tiếng Việt có ngữ nghĩa rõ ràng?
- [ ] Chạy `pytest -v` toàn bộ các test cases đều đạt trạng thái màu xanh (PASS)?
- [ ] Không có secret, credential nào bị để lộ trong mã nguồn?
