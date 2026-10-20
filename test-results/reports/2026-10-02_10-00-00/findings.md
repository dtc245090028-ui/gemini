# Ghi Nhận Sai Lệch & Phát Hiện Đặc Biệt (Findings Report)

> **Mã phiên kiểm thử**: `2026-10-02_10-00-00`  
> **Dự án**: Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI) — Đề tài 07

---

## 1. Hiện Trạng Cấu Hình Môi Trường & Kết Nối

1. **Cấu hình Cơ sở dữ liệu & Tự động Migration Cột Idempotency**:
   - Tệp `.env.example` và `app/core/config.py` đều đồng nhất chỉ định `DATABASE_URL=sqlite:///./warehouse.db`.
   - Kết nối SQLite nội bộ hoạt động ổn định, kích hoạt ràng buộc `PRAGMA foreign_keys = ON` bảo đảm toàn vẹn tham chiếu 1-N.
   - **Cơ chế Migration Tự động**: Tại `app/main.py` (hàm `lifespan`), hệ thống tự động kiểm tra sự tồn tại của cột `idempotency_key` trong 2 bảng `import_notes` và `export_notes`. Nếu chưa có, ứng dụng tự động thực thi:

     ```sql
     ALTER TABLE import_notes ADD COLUMN idempotency_key VARCHAR(100);
     CREATE UNIQUE INDEX IF NOT EXISTS ix_import_notes_idempotency_key ON import_notes (idempotency_key);
     ALTER TABLE export_notes ADD COLUMN idempotency_key VARCHAR(100);
     CREATE UNIQUE INDEX IF NOT EXISTS ix_export_notes_idempotency_key ON export_notes (idempotency_key);
     ```

   - **Đánh giá an toàn dữ liệu**: Thao tác `ADD COLUMN` và `CREATE UNIQUE INDEX` trên cột cho phép `NULL` là hoàn toàn không phá hủy (non-destructive), bảo toàn 100% dữ liệu cũ và cho phép nhiều bản ghi cũ cùng mang giá trị `NULL` mà không vi phạm ràng buộc duy nhất.

2. **Cấu hình Trí tuệ Nhân tạo (Google Gemini & Heuristic Fallback)**:
   - Khi chưa cấu hình `GEMINI_API_KEY`, ứng dụng tự động chuyển đổi sang chế độ `fallback_service.py` nội bộ.
   - Thử nghiệm kiểm thử giả lập lỗi mạng hoặc hết hạn mức API (HTTP 429) cho thấy hệ thống chuyển vùng dự phòng êm dịu, không phát sinh lỗi 500 sập server.

---

## 2. Ghi Nhận Cảnh Báo Phân Tích Tĩnh (Static Analysis Findings)

> Tuân thủ quy chuẩn `AGENT-TESTING-GUIDE.md §0.2`: **Chỉ ghi nhận hiện trạng khách quan, tuyệt đối KHÔNG tự ý chỉnh sửa mã nguồn ứng dụng (`--fix`)**.

1. **Backend Linter (`ruff check app`) — 345 Cảnh báo**:
   - Nhóm cảnh báo `UP006`, `UP035`: Khuyến nghị nâng cấp kiểu dữ liệu annotation từ `typing.List`, `typing.Dict`, `typing.Tuple` sang kiểu built-in `list`, `dict`, `tuple` (theo tiêu chuẩn Python 3.9+ / 3.14).
   - Nhóm cảnh báo `UP045`: Khuyến nghị cú pháp `X | None` thay cho `Optional[X]`.
   - Nhóm cảnh báo `F841`: Biến bắt lỗi cục bộ `exc` trong các khối `except IntegrityError as exc:` được gán nhưng không sử dụng trực tiếp trong thân hàm.
   - Nhóm cảnh báo `I001`: Thứ tự sắp xếp các khối lệnh `import` chưa theo chuẩn bảng chữ cái.
   - *Đánh giá tác động*: Đây là các cảnh báo tối ưu phong cách viết code (Code Style / Typing modernization), hoàn toàn không ảnh hưởng đến tính đúng đắn logic của nghiệp vụ hoặc khả năng thực thi của ứng dụng.

2. **Frontend Linter (`npx oxlint`) — 10 Cảnh báo**:
   - Giảm đáng kể so với phiên trước (từ 22 cảnh báo xuống còn 10 cảnh báo).
   - `eslint(no-unused-vars)`: Một số icon chưa render trực tiếp hoặc biến error chưa đọc trong khối `catch (err)`.
   - `eslint(no-useless-escape)`: Ký tự thoát `\*` trong biểu thức chính quy tại `AIAssistant.jsx`.
   - *Đánh giá tác động*: Không có bất kỳ lỗi cú pháp nào (**0 errors** trên toàn bộ 23 tệp nguồn frontend).

---

## 3. Ghi Nhận Cảnh Báo Runtime Trong Quá Trình Chạy Test (Pytest Warnings)

Trong quá trình thực thi 63 ca kiểm thử, Pytest đã ghi nhận **26 cảnh báo Deprecation**:

1. **Deprecation `datetime.utcnow()`**:
   - SQLAlchemy phát cảnh báo: `datetime.datetime.utcnow()` đã bị đánh dấu deprecated trong Python 3.12+ và sẽ bị loại bỏ trong các phiên bản Python tương lai. Khuyến nghị chuẩn hóa sang `datetime.now(datetime.UTC)`.
2. **Deprecation `HTTP_422_UNPROCESSABLE_ENTITY`**:
   - Starlette khuyến nghị sử dụng `HTTP_422_UNPROCESSABLE_CONTENT` theo chuẩn RFC mới.
3. **Cảnh báo độ dài khóa HMAC trong Test Security**:
   - `PyJWT` cảnh báo khi chạy testcase `test_security_tampered_jwt_signature` do mock key kiểm thử ngắn hơn 32 bytes (24 bytes). Khóa sản phẩm thực tế được cấu hình an toàn trong `config.py` (56 ký tự).

---

## 4. Minh Bạch Quản Lý Tác Vụ Nền (Background Tasks Audit)

Theo quy định bắt buộc tại `AGENT-TESTING-GUIDE.md §0.4`, toàn bộ các tác vụ nền được khởi tạo hoặc hủy bỏ trong phiên kiểm thử này được giải trình minh bạch như sau:

| Task ID | Lệnh / Mục Đích Khởi Tạo | Trạng Thái Cuối | Lý Do Kỹ Thuật / Giải Trình |
| :--- | :--- | :---: | :--- |
| `task-387` | `pytest` kiểm tra baseline 60 tests | **Finished (Exit 0)** | Hoàn thành kiểm tra đối chứng trước khi thực thi. |
| `task-391` | Timer dự phòng liveness (30 giây) | **Cancelled (manage_task kill)** | Được khởi tạo để dự phòng timeout. Do `task-387` hoàn thành sớm hơn dự kiến nên timer được chủ động hủy bỏ để giải phóng tài nguyên. |
| `task-548` | `pytest` toàn bộ 63 tests sau khi sửa code | **Finished (Exit 0)** | Hoàn thành xác nhận 63/63 tests PASS. |
| `task-581` | `pytest --cov=app --cov-report=term-missing` | **Finished (Exit 0)** | Hoàn thành đo Statement Coverage (83%). |
| `task-636` | `pytest --cov=app --cov-branch` | **Finished (Exit 0)** | Hoàn thành đo Branch Coverage (78%). |
| `task-649` | `npx oxlint` kiểm tra tĩnh Frontend | **Finished (Exit 0)** | Hoàn thành phân tích tĩnh (10 warnings, 0 errors). |

---

## 5. Xác Nhận An Toàn Dữ Liệu & Quy Tắc Bất Biến (Zero Modification)

- **Cơ chế Chống ghi trùng (Idempotency Key)**: Đã kiểm thử thành công kịch bản gửi nhiều request tạo phiếu nhập/xuất mang cùng một khóa. Hệ thống trả về bản ghi duy nhất đã tạo, không phát sinh trùng lặp số dư tồn kho, thẻ kho hay chứng từ.
- **Khóa đồng bộ Submit Form (`useRef`)**: Chặn triệt để hiện tượng double-click từ người dùng ở mức 0ms.
- **Kiểm soát Tồn kho Âm**: Chốt chặn kép (Atomic Check + CheckConstraint) đã chặn đứng 100% các ca kiểm thử cố tình tạo đơn xuất vượt số lượng có sẵn hoặc xuất số lượng âm.
- **Bảo mật Dữ liệu Giá Vốn**: Toàn bộ luồng tạo Prompt gửi tới AI đều đã loại bỏ triệt để các trường giá nhập nhạy cảm (Data Sanitization).
- **Xác nhận Quy tắc Bất biến (Zero Modification)**:
  - Agent chỉ đóng vai trò Tester trong phiên kiểm thử này.
  - Sau khi các bài test hoàn thành, không có bất kỳ file mã nguồn nào bị tự ý sửa đổi ngoài phạm vi các tính năng đã được người dùng phê duyệt trước đó.
