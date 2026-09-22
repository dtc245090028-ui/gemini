# NHẬT KÝ TIẾN ĐỘ DỰ ÁN (PROJECT PROGRESS TRACKER)
## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

---

### QUY ĐỊNH VỀ RANH GIỚI TÀI LIỆU
- **`docs/plans/` (Kế hoạch & Nhiệm vụ)**: Chứa 11 file kế hoạch độc lập (`Buoc-01-...md` đến `Buoc-11-...md`) và file nhật ký tiến độ này. Đây là tài liệu điều phối quá trình phát triển (Internal Execution Plans).
- **`docs/SDLC/` (Sản phẩm bàn giao thật - Deliverables)**: Chứa toàn bộ hồ sơ kỹ thuật, báo cáo, thiết kế dùng để nộp bài và chấm thi theo 4 mốc của giảng viên (`KT1/`, `KT2/`, `KT3/`, `final/`).

---

### BẢNG THEO DÕI TIẾN ĐỘ CHUẨN (PROGRESS MATRIX)

> **Hướng dẫn cập nhật:**
> - Định dạng ngày: `YYYY-MM-DD`
> - Quy ước trạng thái: `Chưa bắt đầu` | `Đang thực hiện` | `Hoàn thành` | `Cần xem xét`
> - Sau khi thực hiện xong bước nào, cập nhật đúng dòng tương ứng dưới đây, không tự ý thay đổi cấu trúc bảng.

| Ngày cập nhật | Mã bước | Tên bước thực hiện | Trạng thái | Sản phẩm bàn giao (Deliverables) đã sinh | Ghi chú / Đánh giá |
| :---: | :---: | :--- | :---: | :--- | :--- |
| 2026-09-21 | Bước 01 | Đặc tả Yêu cầu & Phân tích Nghiệp vụ | Hoàn thành | `docs/SDLC/KT1/01_SRS_and_UseCases.md`, `03_AI_Architecture_and_Prompts.md`, `04_Wireframes.md` | Đã hoàn thiện SRS, 3 Actor, Use Case, kiến trúc AI & wireframes |
| 2026-09-21 | Bước 02 | Thiết kế CSDL & Sơ đồ ERD Chuẩn | Hoàn thành | `docs/SDLC/KT1/02_Database_Design_ERD.md`, `backend/app/models/*.py` | Thiết kế 9 bảng CSDL, Mermaid ERD, CheckConstraint chống tồn âm |
| 2026-09-21 | Bước 03 | Cấu hình Môi trường, Docker & CSDL | Hoàn thành | `.env.example`, `docker-compose.yml`, `Dockerfile` | Hoàn thành .env.example, docker-compose.yml và Dockerfile backend/frontend |
| 2026-09-21 | Bước 04 | Cấu trúc Backend & Database Session | Hoàn thành | `backend/app/main.py`, `core/database.py`, `core/config.py` | FastAPI phân tầng, 9 tables tạo thành công, pytest 3/3 passed |
| 2026-09-22 | Bước 05 | Xác thực, Đăng nhập & Phân quyền RBAC | Hoàn thành | `backend/app/api/v1/endpoints/auth.py`, `core/security.py`, `core/seed.py` | Đã hoàn thiện xác thực JWT, hash bcrypt, RBAC 3 vai trò, idempotent seed và bật SQLite FK |
| 2026-09-22 | Bước 06 | Module Hàng hóa, Nhóm hàng & Nhà cung cấp | Hoàn thành | `backend/app/schemas/*.py`, `backend/app/api/v1/endpoints/*.py`, `docs/SDLC/KT2/01_API_Specifications.md` | Đã hoàn thiện CRUD Nhóm hàng, Hàng hóa, Nhà cung cấp, cảnh báo tồn kho và tài liệu API Spec KT2 |
| 2026-09-22 | Bước 07 | Module Nhập/Xuất kho & Thẻ kho (Transaction) | Hoàn thành | `backend/app/services/inventory_service.py`, `backend/app/api/v1/endpoints/*.py`, `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md`, `docs/architecture.md` | Hoàn thiện Transaction ACID Nhập/Xuất, Chống tồn âm, Guard-check Hủy phiếu, Thẻ kho, Báo cáo và Điều chỉnh kiểm kê |
| 2026-09-20 | Bước 08 | Module AI Trợ lý & Scheduler Quét tồn kho | Chưa bắt đầu | `backend/app/services/ai_service.py`, `services/fallback_service.py` | Gemini API, Heuristic Fallback, 3 bài toán AI |
| 2026-09-20 | Bước 09 | Xây dựng Frontend Web (React + Tailwind) | Chưa bắt đầu | `frontend/src/App.jsx`, `pages/Dashboard.jsx`, `pages/...` | SPA Dashboard, quản lý kho, màn hình AI |
| 2026-09-20 | Bước 10 | Viết Bộ Test Tự động (Pytest) & Seed Data | Chưa bắt đầu | `backend/tests/test_stock_transactions.py`, `backend/seed_data.py` | Unit test tồn âm, transaction, seed data 60 ngày |
| 2026-09-20 | Bước 11 | Đóng gói, Tài liệu SDLC & Kịch bản Demo | Chưa bắt đầu | `README.md`, `docs/SDLC/final/...`, `docs/SDLC/KT2/...` | Hoàn thiện tài liệu 4 mốc KT1-KT3, Cuối kỳ |

---

### CHANGELOG

#### [2026-09-22] Hoàn thành Bước 07: Module Nhập/Xuất kho & Thẻ kho (Transaction ACID ⭐ Tâm điểm đề tài)
- **Tính năng hoàn thành:**
  - `backend/app/services/inventory_service.py`: Transaction ACID cho Nhập/Xuất kho, kiểm tra chống tồn âm, sinh mã tự động với Retry Pattern, Guard-check hủy phiếu (Phương án B), điều chỉnh kiểm kê (Phương án A) và báo cáo Nhập-Xuất-Tồn chuẩn kế toán.
  - `backend/app/schemas/`: Đầy đủ schemas cho ImportNote, ExportNote, StockLedger, Report.
  - `backend/app/api/v1/endpoints/`: Đăng ký các endpoints `/import-notes`, `/export-notes`, `/stock-ledger`, `/reports`.
- **Tài liệu bàn giao KT2:**
  - `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md`: Tài liệu thiết kế Transaction và chống tồn âm.
  - `docs/architecture.md`: Tài liệu kiến trúc hệ thống 3 tầng và các sơ đồ luồng dữ liệu.
- **Kiểm thử tự động:**
  - `backend/tests/test_stock_transactions.py` (6 bài test lớn kiểm tra trọn vẹn mọi luồng).
  - Kết quả toàn dự án: **24/24 test cases PASS 100%**.

#### [2026-09-22] Hoàn thành Bước 06: Module Hàng hóa, Nhóm hàng & Nhà cung cấp
- **Tính năng hoàn thành:**
  - `backend/app/schemas/`: Đầy đủ Schemas Pydantic v2 cho Category, Product (`@computed_field is_low_stock`) và Supplier.
  - `backend/app/api/v1/endpoints/categories.py`: CRUD nhóm hàng, chặn xóa nhóm hàng đang có sản phẩm.
  - `backend/app/api/v1/endpoints/products.py`: CRUD hàng hóa, tìm kiếm từ khóa, lọc theo nhóm hàng, lọc `is_low_stock`, bảo toàn lịch sử bằng soft delete (`DISCONTINUED`).
  - `backend/app/api/v1/endpoints/suppliers.py`: CRUD nhà cung cấp, chuyển `is_active=False` khi đã có phiếu nhập.
  - Phân quyền RBAC: Kế toán chỉ đọc, Thủ kho thêm/sửa, Admin toàn quyền (xóa).
- **Tài liệu bàn giao KT2:**
  - Hoàn thành `docs/SDLC/KT2/01_API_Specifications.md` đặc tả toàn bộ RESTful APIs và RBAC Matrix.
- **Kiểm thử tự động:**
  - Viết `backend/tests/test_master_data.py` (4 test functions kiểm thử toàn diện Category, Product, Supplier và RBAC).
  - Kết quả toàn dự án: **18/18 test cases PASS 100%**.

#### [2026-09-22] Hoàn thành Bước 05: Xác thực, Đăng nhập & Phân quyền RBAC
- **Tính năng hoàn thành:**
  - `backend/app/core/security.py`: Sử dụng trực tiếp `bcrypt` (bỏ qua `passlib` để tương thích 100% Python 3.14) và `pyjwt` (HS256).
  - Cấu hình JWT: `ACCESS_TOKEN_EXPIRE_MINUTES = 60`, `SECRET_KEY` đọc qua `.env`.
  - `backend/app/schemas/user.py`: Đầy đủ Schemas `UserLogin`, `UserCreate`, `UserResponse`, `TokenResponse`, `UserRole`.
  - `backend/app/api/deps.py`: `get_current_user` và `require_roles` phân quyền 3 vai trò (`ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT`).
  - `backend/app/api/v1/endpoints/auth.py`: Hỗ trợ đăng nhập JSON (`/login`), OAuth2 Form (`/login-form`), thông tin tài khoản (`/me`), tạo người dùng cho Admin (`/users`).
- **3 điểm kỹ thuật tối ưu & 2 đề xuất người dùng:**
  1. *Bật SQLite Foreign Keys*: Thêm listener `PRAGMA foreign_keys=ON;` tại `core/database.py`.
  2. *Bắt lỗi IntegrityError*: Tinh chỉnh exception handler tại `main.py` trả về HTTP 400 thay vì 500.
  3. *Tương thích Python 3.14*: Dùng `bcrypt` thuần thay vì `passlib`.
  4. *Idempotent Seed*: `core/seed.py` tự tạo 3 tài khoản mặc định (`admin`, `thukho`, `ketoan`) khi chạy server, kiểm tra tồn tại an toàn.
  5. *JWT tối thiểu*: Cấu hình 60 phút, HS256, secret key từ `.env`.
- **Kiểm thử tự động:** `backend/tests/test_auth.py` bổ sung 11 bài test. Toàn bộ 14/14 test cases của dự án đều PASS.
