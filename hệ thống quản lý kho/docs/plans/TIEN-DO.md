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
| 2026-09-21 | Bước 01 | Đặc tả Yêu cầu & Phân tích Nghiệp vụ | Hoàn thành | `docs/SDLC/KT1/01_SRS_and_UseCases.md`, `03_AI_Architecture_and_Prompts.md`, `04_Wireframes.md` | Hoàn thiện SRS 3 Actor, Use Case, ma trận RBAC, luồng xuất 3 bước, báo cáo gộp vào AIAssistant |
| 2026-09-21 | Bước 02 | Thiết kế CSDL & Sơ đồ ERD Chuẩn | Hoàn thành | `docs/SDLC/KT1/02_Database_Design_ERD.md`, `backend/app/models/*.py` | Thiết kế 9 bảng CSDL, Mermaid ERD, CheckConstraint chống âm, bổ sung `image_url` và `idempotency_key` |
| 2026-09-21 | Bước 03 | Cấu hình Môi trường, Docker & CSDL | Hoàn thành | `.env.example`, `docker-compose.yml`, `Dockerfile` | Chuẩn hóa Docker Compose 2 services (`warehouse_backend`, `warehouse_frontend`), SQLite embedded |
| 2026-09-21 | Bước 04 | Cấu trúc Backend & Database Session | Hoàn thành | `backend/app/main.py`, `core/database.py`, `core/config.py` | FastAPI 3 tầng, 44 endpoints, middleware Rate Limiting, Exception handler IntegrityError & DB Busy |
| 2026-09-22 | Bước 05 | Xác thực, Đăng nhập & Phân quyền RBAC | Hoàn thành | `backend/app/api/v1/endpoints/auth.py`, `core/security.py`, `core/seed.py` | JWT auth, bcrypt thuần, RBAC 3 vai trò, SlidingWindowRateLimiter 10 req/min, 12 ca test auth pass |
| 2026-09-22 | Bước 06 | Module Hàng hóa, Nhóm hàng & Nhà cung cấp | Hoàn thành | `backend/app/schemas/*.py`, `backend/app/api/v1/endpoints/*.py`, `docs/SDLC/KT2/01_API_Specifications.md` | CRUD Nhóm hàng, Hàng hóa (upload ảnh, khởi tạo phiếu nhập), Nhà cung cấp, 5 ca test master data |
| 2026-09-22 | Bước 07 | Module Nhập/Xuất kho & Thẻ kho (Transaction) | Hoàn thành | `backend/app/services/inventory_service.py`, `backend/app/api/v1/endpoints/*.py`, `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md` | Transaction ACID, luồng xuất 3 bước (`CONFIRMED` -> `SHIPPING` -> `COMPLETED`), xóa phiếu chưa xuất, Thẻ kho, xuất Excel |
| 2026-09-23 | Bước 08 | Module AI Trợ lý & Fallback Engine | Hoàn thành | `backend/app/services/ai_service.py`, `services/fallback_service.py`, `api/v1/endpoints/ai.py` | Gemini 3.5 Flash Lite + Fallback chain, 5 endpoints AI, Heuristic Fallback offline, AI In-Day Cache |
| 2026-09-23 | Bước 09 | Xây dựng Frontend Web (React + Tailwind) | Hoàn thành | `frontend/src/App.jsx`, `components/`, `pages/`, `api/client.js` | SPA React 18, Tailwind CSS, Dark/Light mode, ConfirmModal kèm lý do >= 5 ký tự, Toast notification |
| 2026-09-23 | Bước 10 | Viết Bộ Test Tự động (Pytest) & Seed Data | Hoàn thành | `backend/tests/`, `backend/seed_data.py`, `docs/SDLC/KT3/02_Test_Plan_and_Results.md` | Bộ test 70/70 passed 100%, 83% coverage (thêm 4 ca test kho rỗng), Seed Data 76 SP / 5 tháng |
| 2026-09-25 | Bước 11 | Đóng gói, Tài liệu SDLC & Kịch bản Demo | Hoàn thành | `README.md`, `docker-compose.yml`, `docs/SDLC/final/...`, `docs/submissions/...` | Đóng gói hoàn chỉnh, 4 mốc SDLC, văn bản Word 10 chương, Slide PowerPoint 16 trang, kịch bản demo 5 phút |

---

### CHANGELOG

#### [2026-10-28] Đồng bộ Toàn diện Hồ sơ Dự án theo Mã nguồn Thực tế (PR #1 & Audit 09)

- **Đồng bộ số liệu và kiến trúc thực tế:**
  - Chuẩn hóa tổng số endpoint toàn hệ thống: **44 endpoints** (42 endpoints API v1 + 2 endpoints root/health).
  - Chuẩn hóa mô hình AI chính thức: `gemini-3.5-flash-lite`, chuỗi fallback chain (`gemini-3.1-flash-lite` $\rightarrow$ `gemini-3.6-flash`), bổ sung `ai_cache.py` và 2 endpoint nâng cao (`/ai/ask`, `/ai/generate-order`).
  - Chuẩn hóa quy mô bộ dữ liệu thử nghiệm trong `seed_data.py`: **76 sản phẩm**, **7 nhóm hàng**, **10 nhà cung cấp**, lịch sử nhập xuất **5 tháng (150 ngày)**.
  - Chuẩn hóa bộ kiểm thử tự động Pytest: **70 ca test pass 100%** (bao gồm 66 ca test PR #1 và 4 ca test mới tại `test_ai_empty_data.py` bảo vệ endpoint AI dữ liệu rỗng), độ bao phủ code đạt **83%**.
  - Chuẩn hóa kiến trúc Docker: **2 containers** (`warehouse_backend` & `warehouse_frontend`), sử dụng SQLite nhúng với khóa ngoại (`PRAGMA foreign_keys=ON;`).
  - Đồng bộ nghiệp vụ: Cỗ máy trạng thái xuất kho 3 bước (`CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`), bảo toàn quyền xóa phiếu `CONFIRMED`, gộp phân hệ Báo cáo NXT vào `AIAssistant.jsx` (kèm xuất Excel), Thẻ kho hiển thị số lượng và tồn sau giao dịch, cơ chế Idempotency Key chống trùng lặp.
  - Cập nhật toàn bộ tài liệu 11 bước `docs/plans/`, 4 mốc `docs/SDLC/`, hồ sơ nộp bài `docs/submissions/`, `Prompt.md`, `MASTER-ROADMAP.md`, `architecture.md`, `codebase-map.md`, `README.md`, và bộ Prompt suy đoán `docs_evidence/08_bo_prompt_sdlc_suy_doan.md`.

#### [2026-09-25] Hoàn thành Bước 11: Đóng gói toàn diện dự án, Hồ sơ SDLC Cuối kỳ, Báo cáo kỹ thuật Word & Slide PowerPoint Thuyết trình

- **Đóng gói & Khởi chạy:**
  - `docker-compose.yml`: Triển khai 2 dịch vụ độc lập backend và frontend.
  - `README.md`: Hướng dẫn vận hành, danh mục tài khoản mẫu và các lối tắt chấm thi.
- **Hồ sơ bàn giao giai đoạn Cuối kỳ (`docs/SDLC/final/` & `docs/submissions/final/`):**
  - `01_Final_Technical_Report.md`: Báo cáo kỹ thuật tổng kết toàn diện 10 chương: kiến trúc Clean Architecture 3 tầng, CSDL chuẩn 3NF (9 bảng), giao dịch ACID, cỗ máy trạng thái xuất kho 3 bước, chốt chặn kép chống tồn âm, phân hệ AI Copilot và kiểm thử.
  - `02_User_Guide_and_Demo_Script.md`: Cẩm nang hướng dẫn sử dụng 7 phân hệ và Kịch bản Demo 5 phút chuẩn chấm thi phân vai từng phút.
  - `03_Presentation_Slides.md`: Bản ghi chép nội dung và kịch bản thuyết minh chi tiết cho 16 slide bảo vệ đồ án.
  - `Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`: Văn bản Báo cáo đặc tả yêu cầu & thiết kế kiến trúc hệ thống phiên bản in ấn chính thức (10 chương hoàn chỉnh).
  - `Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx`: Bộ slide trình chiếu 16 trang định dạng PowerPoint chuẩn đồ họa phục vụ bảo vệ đồ án trước Hội đồng.

#### [2026-09-23] Hoàn thành Bước 09: Xây dựng Frontend Web React 18 & Tailwind CSS

- `frontend/src/api/client.js`: Axios client tập trung với JWT interceptor.
- `frontend/src/context/AuthContext.jsx`: Quản lý phiên làm việc JWT, hàm `switchDemoRole` hỗ trợ chuyển đổi vai trò 1-click.
- Dark / Light mode toggle với hệ thống Design Tokens (`tokens.css`).
- Hộp thoại `ConfirmModal` bắt buộc lý do $\ge 5$ ký tự khi hủy/xóa phiếu.

#### [2026-09-23] Hoàn thành Mốc KT3 (Bước 08 & Bước 10: Tích hợp AI, Prompt Engineering, Fallback Engine & Test Suite)

- `backend/app/services/ai_service.py`: Pipeline tiền xử lý loại bỏ 100% giá mua nhạy cảm. Tích hợp Gemini 3.5 Flash Lite và chuỗi fallback.
- `backend/app/services/fallback_service.py`: Heuristic Fallback Engine hoạt động offline độc lập (< 50ms).
- Bộ kiểm thử tự động Pytest, Script nạp dữ liệu mẫu lớn.

#### [2026-09-22] Hoàn thành Bước 07: Module Nhập/Xuất kho & Thẻ kho (Transaction ACID)

- Giao dịch ACID cho Nhập/Xuất kho, cỗ máy trạng thái xuất kho 3 bước, trừ tồn kho nguyên tử bằng SQL RETURNING, kiểm tra chống tồn âm, cơ chế Idempotency Key.

#### [2026-09-22] Hoàn thành Bước 06: Module Hàng hóa, Nhóm hàng & Nhà cung cấp

- CRUD Nhóm hàng, Sản phẩm (upload ảnh, tự động sinh phiếu nhập ban đầu), Nhà cung cấp, kiểm tra ràng buộc toàn vẹn.

#### [2026-09-22] Hoàn thành Bước 05: Xác thực, Đăng nhập & Phân quyền RBAC

- JWT Authentication, bcrypt thuần, phân quyền RBAC 3 vai trò, SlidingWindowRateLimiter chống brute-force.
