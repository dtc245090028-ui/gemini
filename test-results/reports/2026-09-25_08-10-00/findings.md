# Ghi Nhận Sai Lệch & Phát Hiện Đặc Biệt (Findings Report)

> **Mã phiên kiểm thử**: `2026-09-25_08-10-00`  
> **Dự án**: Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI) — Đề tài 07

---

## 1. Hiện Trạng Cấu Hình Môi Trường & Kết Nối

1. **Cấu hình Cơ sở dữ liệu**:
   - Tệp `.env.example` và `app/core/config.py` đều đồng nhất chỉ định `DATABASE_URL=sqlite:///./warehouse.db`.
   - Kết nối SQLite nội bộ hoạt động ổn định, kích hoạt ràng buộc `PRAGMA foreign_keys = ON` bảo đảm toàn vẹn tham chiếu 1-N.
   - Khi chuyển đổi sang Docker hoặc PostgreSQL production, hệ thống đã hỗ trợ sẵn sàng qua biến môi trường mà không cần sửa đổi mã nguồn.

2. **Cấu hình Trí tuệ Nhân tạo (Google Gemini & Heuristic Fallback)**:
   - Khi chưa cấu hình `GEMINI_API_KEY`, ứng dụng tự động chuyển đổi sang chế độ `fallback_service.py` nội bộ.
   - Thử nghiệm kiểm thử giả lập lỗi mạng hoặc hết hạn mức API (HTTP 429) cho thấy hệ thống chuyển vùng dự phòng êm dịu, không phát sinh lỗi 500 sập server.

---

## 2. Ghi Nhận Cảnh Báo Phân Tích Tĩnh (Static Analysis Findings)

> Tuân thủ quy chuẩn `AGENT-TESTING-GUIDE.md §0.2`: **Chỉ ghi nhận hiện trạng khách quan, tuyệt đối KHÔNG tự ý chỉnh sửa mã nguồn ứng dụng (`--fix`)**.

1. **Backend Linter (`ruff check app`) — 339 Cảnh báo**:
   - Nhóm cảnh báo `UP006`, `UP035`: Khuyến nghị nâng cấp kiểu dữ liệu annotation từ `typing.List`, `typing.Dict`, `typing.Tuple` sang kiểu built-in `list`, `dict`, `tuple` (theo tiêu chuẩn Python 3.9+ / 3.14).
   - Nhóm cảnh báo `UP045`: Khuyến nghị cú pháp `X | None` thay cho `Optional[X]`.
   - Nhóm cảnh báo `F841`: Biến bắt lỗi cục bộ `exc` trong các khối `except IntegrityError as exc:` được gán nhưng không sử dụng trực tiếp trong thân hàm.
   - Nhóm cảnh báo `I001`: Thứ tự sắp xếp các khối lệnh `import` chưa theo chuẩn bảng chữ cái.
   - *Đánh giá tác động*: Đây là các cảnh báo tối ưu phong cách viết code (Code Style/Typing modernization), hoàn toàn không ảnh hưởng đến tính đúng đắn logic của nghiệp vụ hoặc khả năng thực thi của ứng dụng.

2. **Frontend Linter (`npx oxlint`) — 22 Cảnh báo**:
   - `eslint(no-unused-vars)`: Phát hiện một số biến và component icons nhập khẩu từ thư viện `lucide-react` nhưng chưa được render trên giao diện (ví dụ: `ArrowDownToLine`, `CheckCircle`, `FileText`, `Truck`, `Package`, `ClipboardList`).
   - `eslint(no-useless-escape)`: Ký tự thoát `\*` trong biểu thức chính quy xử lý markdown tại `AIAssistant.jsx`.
   - *Đánh giá tác động*: Không có lỗi cú pháp (0 errors), bản build Vite hoàn tất đạt chuẩn và tối ưu kích thước bundle.

---

## 3. Ghi Nhận Cảnh Báo Runtime Trong Quá Trình Chạy Test (Pytest Warnings)

Trong quá trình thực thi 60 ca kiểm thử, Pytest đã ghi nhận **26 cảnh báo Deprecation**:

1. **Deprecation `datetime.utcnow()`**:
   - SQLAlchemy phát cảnh báo: `datetime.datetime.utcnow()` đã bị đánh dấu deprecated trong Python 3.12+ và sẽ bị loại bỏ trong các phiên bản Python tương lai. Khuyến nghị chuẩn hóa sang `datetime.now(datetime.UTC)`.
2. **Deprecation `HTTP_422_UNPROCESSABLE_ENTITY`**:
   - Starlette khuyến nghị sử dụng `HTTP_422_UNPROCESSABLE_CONTENT` theo chuẩn RFC mới.
3. **Cảnh báo độ dài khóa HMAC trong Test Security**:
   - `PyJWT` cảnh báo khi chạy testcase `test_security_tampered_jwt_signature` do mock key kiểm thử ngắn hơn 32 bytes (24 bytes). Khóa sản phẩm thực tế được cấu hình an toàn trong `config.py` (56 ký tự).

---

## 4. Xác Nhận An Toàn Dữ Liệu & Quy Tắc Bất Biến (Zero Modification)

- **Kiểm soát Tồn kho Âm**: Chốt chặn kép (Atomic Check + CheckConstraint) đã chặn đứng 100% các ca kiểm thử cố tình tạo đơn xuất vượt số lượng có sẵn hoặc xuất số lượng âm.
- **Bảo mật Dữ liệu Giá Vốn**: Toàn bộ luồng tạo Prompt gửi tới AI đều đã loại bỏ triệt để các trường giá nhập nhạy cảm (Data Sanitization).
- **Xác nhận Quy tắc Bất biến (Zero Modification)**:
  - Agent chỉ đóng vai trò Tester.
  - Không có bất kỳ tệp mã nguồn ứng dụng nào trong `backend/app/` hoặc `frontend/src/` bị chỉnh sửa trong toàn bộ phiên kiểm thử này.
