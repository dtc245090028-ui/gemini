# NHẬT KÝ TIẾN ĐỘ DỰ ÁN (PROJECT PROGRESS TRACKER)

## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

---

### QUY ĐỊNH VỀ RANH GIỚI TÀI LIỆU

- **`docs/plans/` (Kế hoạch & Nhiệm vụ)**: Chứa 11 file kế hoạch độc lập (`Buoc-01-...md` đến `Buoc-11-...md`) và file nhật ký tiến độ này. Đây là tài liệu điều phối quá trình phát triển (Internal Execution Plans).
- **`docs/SDLC/` (Sản phẩm bàn giao thật - Deliverables)**: Chứa toàn bộ hồ sơ kỹ thuật, báo cáo, thiết kế dùng để nộp bài và chấm thi theo 4 mốc của giảng viên (`KT1/`, `KT2/`, `KT3/`, `final/`).

---

### BẢNG THEO DÕI TIẾN ĐỘ CHUẨN (PROGRESS MATRIX)

> **Hướng dẫn cập nhật:**
>
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
| 2026-09-23 | Bước 08 | Module AI Trợ lý & Fallback Engine | Hoàn thành | `backend/app/services/ai_service.py`, `services/fallback_service.py`, `api/v1/endpoints/ai.py` | Hoàn thiện 3 tính năng AI (Báo cáo tháng, Gợi ý nhập, Biến động bất thường), Gemini API + Heuristic Fallback offline |
| 2026-09-23 | Bước 09 | Xây dựng Frontend Web (React + Tailwind) | Hoàn thành | `frontend/src/App.jsx`, `components/`, `pages/`, `api/client.js` | Hoàn thiện SPA React 18 + Tailwind CSS + Lucide Icons cho 7 phân hệ, Defensive UI chống tồn âm, Demo Role Switcher |
| 2026-09-23 | Bước 10 | Viết Bộ Test Tự động (Pytest) & Seed Data | Hoàn thành | `backend/tests/test_ai.py`, `backend/seed_data.py`, `docs/SDLC/KT3/*.md` | Bộ test 30/30 passed 100%, Seed Data 60 ngày kịch bản SP001/SP002/SP003, bàn giao KT3 |
| 2026-09-25 | Bước 11 | Đóng gói, Tài liệu SDLC & Kịch bản Demo | Hoàn thành | `README.md`, `run.bat`, `docs/SDLC/final/...`, `Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`, `Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx` | Hoàn thành 100% toàn bộ đồ án, trọn bộ SDLC 4 mốc, văn bản Báo cáo kỹ thuật Word, Slide PowerPoint, script run.bat và Pytest 60/60 passed 100% |

---

### CHANGELOG

#### [2026-09-25] Hoàn thành Bước 11: Đóng gói toàn diện dự án, Hồ sơ SDLC Cuối kỳ, Báo cáo kỹ thuật Word & Slide PowerPoint Thuyết trình

- **Đóng gói & Khởi chạy 1-Click:**
  - `run.bat`: Tạo script tự động khởi chạy đồng thời Backend FastAPI (cổng 8000) và Frontend React Vite (cổng 5173) trên Windows.
  - `README.md`: Hướng dẫn vận hành, danh mục tài khoản mẫu và các lối tắt chấm thi.
- **Hồ sơ bàn giao giai đoạn Cuối kỳ (`docs/SDLC/final/` & `docs/submissions/final/`):**
  - `01_Final_Technical_Report.md`: Báo cáo kỹ thuật tổng kết toàn diện 10 chương: kiến trúc Clean Architecture 3 tầng, CSDL chuẩn 3NF (9 bảng), giao dịch ACID, cỗ máy trạng thái xuất kho 3 bước, chốt chặn kép chống tồn âm, phân hệ AI Copilot và kiểm thử.
  - `02_User_Guide_and_Demo_Script.md`: Cẩm nang hướng dẫn sử dụng 7 phân hệ và Kịch bản Demo 5 phút chuẩn chấm thi phân vai từng phút.
  - `03_Presentation_Slides.md`: Bản ghi chép nội dung và kịch bản thuyết minh chi tiết cho 16 slide bảo vệ đồ án.
  - `Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`: Văn bản Báo cáo đặc tả yêu cầu & thiết kế kiến trúc hệ thống phiên bản in ấn chính thức (10 chương hoàn chỉnh).
  - `Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx`: Bộ slide trình chiếu 16 trang định dạng PowerPoint chuẩn đồ họa phục vụ bảo vệ đồ án trước Hội đồng.
- **Kiểm định chất lượng toàn diện:**
  - Toàn bộ 11/11 bước trong kế hoạch phát triển đã hoàn thành 100%.
  - Bộ kiểm thử tự động Pytest nâng cấp lên quy mô **60 / 60 ca test PASS 100%** (bao gồm test auth, master data, ACID transaction, AI pipeline, heuristic fallback và blackbox integration).
  - Đồng bộ đầy đủ dữ liệu bàn giao sang `docs/submissions/` (KT1, KT2, KT3, final).

#### [2026-09-23] Hoàn thành Bước 09: Xây dựng Frontend Web React 18 & Tailwind CSS (Ứng dụng giao diện người dùng)

- **Kiến trúc & Cơ chế nền tảng:**
  - `frontend/src/api/client.js`: Cấu hình Axios client tập trung với JWT interceptor, tự động gắn `Authorization: Bearer <token>`, bắt mã 401 tự động điều hướng về Login, đóng gói 9 nhóm API service chuẩn mực.
  - `frontend/src/context/AuthContext.jsx`: Quản lý phiên làm việc JWT, tự động khôi phục từ `localStorage`, tích hợp hàm `switchDemoRole` hỗ trợ chuyển đổi 1-click giữa `ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT` phục vụ thuyết trình hội đồng.
  - `frontend/src/components/Layout.jsx`: Giao diện Sidebar chuẩn mực với nhận diện SmartKho AI + Header hiển thị thông tin người dùng và thanh công cụ chuyển vai trò Demo.
  - `frontend/src/components/Badge.jsx` & `Modal.jsx`: Bộ component dùng chung tái sử dụng với quản lý trạng thái trực quan và hỗ trợ phím Escape.
- **7 Phân hệ nghiệp vụ hoàn chỉnh (Pages):**
  - `pages/Login.jsx`: Đăng nhập tiêu chuẩn kèm 3 nút 1-click đăng nhập nhanh (Admin, Thủ kho, Kế toán).
  - `pages/Dashboard.jsx`: Thống kê KPI tồn kho, bảng cảnh báo hàng dưới mức tối thiểu và lối tắt thao tác nhanh.
  - `pages/Products.jsx`: CRUD sản phẩm, tìm kiếm tức thời, lọc nhóm hàng, lọc `is_low_stock`, phân quyền thao tác theo vai trò và nút nhảy nhanh sang Thẻ kho.
  - `pages/Suppliers.jsx`: Quản lý danh sách nhà cung cấp, tìm kiếm, thêm/sửa đối tác, bảo toàn lịch sử giao dịch.
  - `pages/ImportNotes.jsx`: Lập phiếu nhập kho đa dòng, tự động tra cứu đơn giá chuẩn, tính tổng tiền, xem chi tiết và hủy phiếu hoàn trừ tồn kho.
  - `pages/ExportNotes.jsx`: Lập phiếu xuất kho với cơ chế **Defensive UI chống xuất âm** (cảnh báo đỏ, khóa nút tạo phiếu nếu số lượng vượt quá tồn hiện có) kết hợp chặt chẽ với ACID Backend.
  - `pages/StockLedger.jsx`: Sổ cái thẻ kho chi tiết theo mặt hàng, lọc theo loại giao dịch (`IMPORT`, `EXPORT`, `ADJUSTMENT`), hỗ trợ modal điều chỉnh kiểm kê thực tế.
  - `pages/AIAssistant.jsx`: Màn hình 3 phân hệ AI (Báo cáo tháng điều hành, Gợi ý nhập hàng theo vận tốc bán 30 ngày, Nhận diện biến động bất thường `SURGE_EXPORT` / `DEAD_STOCK`) với cờ thông báo Fallback Engine rõ ràng.
- **Kiểm định đóng gói:**
  - Đã cài đặt toàn bộ `node_modules` và chạy `npm run build` thành công rực rỡ (`✓ 1551 modules transformed`, built in 4.23s, 0 lỗi).

#### [2026-09-23] Hoàn thành Mốc KT3 (Bước 08 & Bước 10: Tích hợp AI, Prompt Engineering, Fallback Engine & Test Suite 30/30)

- **Module AI Trợ lý & Heuristic Fallback (Bước 08):**
  - `backend/app/services/ai_service.py`: Xây dựng SQL Aggregation Pipeline tiền xử lý dữ liệu và **loại bỏ 100% giá mua nhạy cảm** (`unit_price`). Tích hợp Google Gemini API (`gemini-1.5-flash`) qua structured JSON schema.
  - `backend/app/services/fallback_service.py`: Xây dựng Heuristic Fallback Engine hoạt động độc lập offline (< 50ms), tính toán chính xác số lượng đề xuất nhập (`suggested_qty = 2*min - stock`) và nhận diện biến động bất thường (`SURGE_EXPORT`, `DEAD_STOCK`).
  - `backend/app/schemas/ai.py`: Khởi tạo đầy đủ Pydantic schemas cho 3 bài toán AI.
  - `backend/app/ai/prompts/`: Quản lý 3 prompt templates độc lập (`inventory_report_prompt.txt`, `reorder_suggestion_prompt.txt`, `anomaly_detection_prompt.txt`).
  - `backend/app/api/v1/endpoints/ai.py`: Đăng ký 3 endpoints: `/api/v1/ai/monthly-report`, `/api/v1/ai/restock-suggestions`, `/api/v1/ai/anomalies`.
- **Kiểm thử tự động & Seed Data (Bước 10):**
  - `backend/tests/test_ai.py`: Bổ sung 6 bài test kiểm tra bảo mật giá mua, fallback dữ liệu rỗng, gợi ý nhập hàng, biến động bất thường, mock Gemini API và RBAC.
  - Kết quả kiểm thử toàn dự án: **30 / 30 test cases PASS 100%**.
  - `backend/seed_data.py`: Script nạp 22 mặt hàng, 3 users, 3 NCC và lịch sử 60 ngày nhập xuất theo 3 kịch bản cốt lõi (SP001 bán chạy sắp hết, SP002 xuất đột biến tuần này, SP003 tồn chết 55 ngày).
- **Hồ sơ bàn giao mốc KT3:**
  - `docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md`: Báo cáo so sánh định lượng 3 phiên bản Prompt (v1, v2, v3).
  - `docs/SDLC/KT3/02_Test_Plan_and_Results.md`: Ma trận 30 ca kiểm thử tự động và nhật ký thực thi 100% Pass.
  - `docs/SDLC/KT3/03_AI_Integration_Architecture.md`: Kiến trúc phân tầng AI và sơ đồ luồng chuyển mạch Fallback.

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
