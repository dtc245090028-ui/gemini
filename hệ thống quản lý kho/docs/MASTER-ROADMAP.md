# MASTER ROADMAP

## Đề tài 07 — Hệ thống quản lý kho có tích hợp AI

> **Vai trò của file này:** Bức tranh toàn cảnh — điều hướng sang từng kế hoạch chi tiết.
> Xem `CLAUDE.md §11` để hiểu quy ước nguồn sự thật và khi nào cập nhật file này.

---

## Phân cấp nguồn sự thật

```text
docs/plans/TIEN-DO.md          ← Trạng thái thực tế (tick ✅ ở đây là chính thức)
    ↑ đồng bộ
MASTER-ROADMAP.md   ← Bức tranh toàn cảnh + điều hướng (file này)
    ↓ link sang
Buoc-NN.md          ← Spec thực thi chi tiết cho từng bước
```

**Khi hai file mâu thuẫn:** TIEN-DO.md thắng về trạng thái; Buoc-NN.md thắng về cách làm.

---

## Trạng thái tổng quan

| Giai đoạn | Mô tả | Mốc SDLC | Tiến độ |
| :---: | --- | :---: | :---: |
| **0** | Nền tảng dự án | — | ✅ Hoàn thành |
| **1** | Tài liệu KT1 + DB Models | KT1 | ✅ Hoàn thành |
| **2** | Backend Auth + CRUD | KT2 | ✅ Hoàn thành |
| **3** | Transaction ACID + Stock Ledger | KT2 | ✅ Hoàn thành |
| **4** | Tích hợp AI + Fallback Engine | KT3 | ✅ Hoàn thành |
| **5** | Kiểm thử tự động (Pytest) | KT3 | ✅ Hoàn thành |
| **6** | Frontend React + Tailwind | Cuối kỳ | ✅ Hoàn thành |
| **7** | Đóng gói + Tài liệu cuối | Cuối kỳ | ✅ Hoàn thành |

> **Quy ước trạng thái ô:** ⬜ Chưa bắt đầu · 🔄 Đang thực hiện · ✅ Hoàn thành · ⚠️ Cần xem xét

---

## Chi tiết từng giai đoạn

---

### GIAI ĐOẠN 0 — Nền tảng dự án

> **Mục tiêu:** Dựng khung chạy được trước khi viết bất kỳ nghiệp vụ nào.
> **Dependency:** Không có — thực hiện đầu tiên.

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 0.1 | Tạo cấu trúc thư mục đầy đủ theo `Prompt.md §6` | 🔴 P0 | [Buoc-03](plans/Buoc-03-Cau-hinh-Moi-truong-Docker-va-CSDL.md) | Cây thư mục khớp đặc tả | ✅ |
| 0.2 | `requirements.txt` + `.env.example` | 🔴 P0 | [Buoc-03](plans/Buoc-03-Cau-hinh-Moi-truong-Docker-va-CSDL.md) | `backend/requirements.txt`, `backend/.env.example` | ✅ |
| 0.3 | FastAPI app khung: `main.py`, `core/config.py`, `core/database.py` | 🔴 P0 | [Buoc-04](plans/Buoc-04-Cau-truc-Backend-Cau-hinh-va-Database-Session.md) | Backend khởi động được tại `uvicorn app.main:app` | ✅ |
| 0.4 | React + Vite + Tailwind CSS khởi tạo | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | Frontend chạy được tại `localhost:5173` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 0:** Backend trả `200 OK` tại `/health`, frontend hiển thị trang trắng không lỗi.

---

### GIAI ĐOẠN 1 — Tài liệu KT1 + DB Models

> **Mục tiêu:** Hoàn thiện thiết kế trên giấy TRƯỚC khi viết model — tránh thiết kế sai phải đập lại.
> **Dependency:** Giai đoạn 0 (môi trường chạy được).
> **Mốc nộp bài:** KT1

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 1.1 | Tài liệu SRS + Use Case (3 Actor, 8 luồng nghiệp vụ) | 🔴 P0 | [Buoc-01](plans/Buoc-01-Dac-ta-yeu-cau-va-Phan-tich-nghiep-vu.md) | `docs/SDLC/KT1/01_SRS_and_UseCases.md` | ✅ |
| 1.2 | Thiết kế ERD + Data Dictionary (9 bảng) | 🔴 P0 | [Buoc-02](plans/Buoc-02-Thiet-ke-CSDL-va-So-do-ERD.md) | `docs/SDLC/KT1/02_Database_Design_ERD.md` | ✅ |
| 1.3 | Kiến trúc AI + Prompt mẫu (Gemini 3.5 Flash Lite) | 🔴 P0 | [Buoc-01](plans/Buoc-01-Dac-ta-yeu-cau-va-Phan-tich-nghiep-vu.md) | `docs/SDLC/KT1/03_AI_Architecture_and_Prompts.md` | ✅ |
| 1.4 | Wireframes: Dashboard, Phiếu nhập/xuất, Trợ lý AI, Dark/Light mode | 🔴 P0 | [Buoc-01](plans/Buoc-01-Dac-ta-yeu-cau-va-Phan-tich-nghiep-vu.md) | `docs/SDLC/KT1/04_Wireframes.md` | ✅ |
| 1.5 | 9 SQLAlchemy Models (`users`, `categories`, `products`, `suppliers`, `import_notes`, `import_note_details`, `export_notes`, `export_note_details`, `stock_ledger`) | 🔴 P0 | [Buoc-02](plans/Buoc-02-Thiet-ke-CSDL-va-So-do-ERD.md) | `backend/app/models/*.py` | ✅ |
| 1.6 | `Base.metadata.create_all()` — tạo bảng khi khởi động | 🔴 P0 | [Buoc-04](plans/Buoc-04-Cau-truc-Backend-Cau-hinh-va-Database-Session.md) | DB schema khớp ERD, `CHECK (current_stock >= 0)` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 1:** 4 file deliverable KT1 tồn tại và có nội dung; chạy backend tạo đúng 9 bảng trong SQLite.

---

### GIAI ĐOẠN 2 — Backend Auth + CRUD

> **Mục tiêu:** API có xác thực và CRUD master data hoạt động — nền cho nghiệp vụ kho.
> **Dependency:** Giai đoạn 1 (models đã có).

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 2.1 | Pydantic Schemas cho tất cả models | 🔴 P0 | [Buoc-04](plans/Buoc-04-Cau-truc-Backend-Cau-hinh-va-Database-Session.md) | `backend/app/schemas/*.py` | ✅ |
| 2.2 | Auth: bcrypt + JWT + endpoint `/auth/login` | 🔴 P0 | [Buoc-05](plans/Buoc-05-Xac-thuc-Dang-nhap-va-Phan-quyen-RBAC.md) | `backend/app/core/security.py`, `api/v1/endpoints/auth.py` | ✅ |
| 2.3 | RBAC dependency `require_roles(["ADMIN", ...])` & Rate Limiting | 🔴 P0 | [Buoc-05](plans/Buoc-05-Xac-thuc-Dang-nhap-va-Phan-quyen-RBAC.md) | Tích hợp vào tất cả protected endpoints | ✅ |
| 2.4 | CRUD: Categories, Products (với `min_stock`, `current_stock`, upload ảnh) | 🔴 P0 | [Buoc-06](plans/Buoc-06-Module-Hang-hoa-Nhom-hang-va-Nha-cung-cap.md) | `api/v1/endpoints/products.py` + Swagger OK | ✅ |
| 2.5 | CRUD: Suppliers | 🔴 P0 | [Buoc-06](plans/Buoc-06-Module-Hang-hoa-Nhom-hang-va-Nha-cung-cap.md) | `api/v1/endpoints/suppliers.py` + Swagger OK | ✅ |
| 2.6 | Tài liệu API Spec KT2 (Mở rộng 44 endpoints) | 🔴 P0 | [Buoc-06](plans/Buoc-06-Module-Hang-hoa-Nhom-hang-va-Nha-cung-cap.md) | `docs/SDLC/KT2/01_API_Specifications.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 2:** Login trả JWT; CRUD products/suppliers pass test; Swagger UI hiển thị đủ endpoints.

---

### GIAI ĐOẠN 3 — Transaction ACID + Stock Ledger ⭐ Tâm điểm đề tài

> **Mục tiêu:** Nghiệp vụ kho cốt lõi — phải đúng 100%, không được thỏa hiệp.
> **Dependency:** Giai đoạn 2 (CRUD master data xong).
> **Mốc nộp bài:** KT2

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 3.1 | `InventoryService.create_import()` — Transaction ACID nhập hàng + ghi Stock Ledger + Idempotency Key | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `backend/app/services/inventory_service.py` | ✅ |
| 3.2 | `InventoryService.create_export()` & Cỗ máy xuất kho 3 bước (`CONFIRMED` -> `SHIPPING` -> `COMPLETED`) | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `backend/app/services/inventory_service.py` | ✅ |
| 3.3 | API endpoints nhập/xuất kho (`/import-notes`, `/export-notes`, xóa phiếu CONFIRMED) | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `api/v1/endpoints/import_notes.py`, `export_notes.py` | ✅ |
| 3.4 | State Machine phiếu xuất & Guard-check hủy phiếu an toàn | 🟡 P1 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | Logic trong `inventory_service.py` | ✅ |
| 3.5 | API Báo cáo Nhập-Xuất-Tồn theo kỳ + tra cứu Stock Ledger + Xuất Excel | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `api/v1/endpoints/reports.py`, `stock_ledger.py` | ✅ |
| 3.6 | API cảnh báo hàng dưới tồn tối thiểu (`@computed_field is_low_stock`) | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | Tích hợp vào `/products` | ✅ |
| 3.7 | Tài liệu Transaction Design KT2 | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md` | ✅ |
| 3.8 | Minh chứng dùng AI trong SDLC KT2 | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `docs/SDLC/KT2/03_AI_Assisted_Development_Evidence.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 3:** Xuất quá tồn → HTTP 400, `current_stock` không đổi; mỗi nhập/xuất tạo bản ghi `stock_ledger`; công thức `Tồn đầu + Nhập - Xuất = Tồn cuối` khớp.

---

### GIAI ĐOẠN 4 — Tích hợp AI + Fallback Engine

> **Mục tiêu:** 5 chức năng AI hoạt động, offline-safe, không bịa số liệu.
> **Dependency:** Giai đoạn 3 (có dữ liệu kho thực để AI phân tích).
> **Mốc nộp bài:** KT3

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 4.1 | Data Aggregation Pipeline (SQL tổng hợp, loại bỏ 100% giá mua) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `backend/app/services/ai_service.py` | ✅ |
| 4.2 | Kết nối Gemini 3.5 Flash Lite — Báo cáo tháng | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `ai_service.generate_monthly_report()` | ✅ |
| 4.3 | Kết nối Gemini 3.5 Flash Lite — Gợi ý nhập hàng (kèm velocity 30 ngày) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `ai_service.generate_restock_suggestions()` | ✅ |
| 4.4 | Kết nối Gemini 3.5 Flash Lite — Biến động bất thường (xuất >200%, tồn >30 ngày) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `ai_service.generate_anomaly_detection()` | ✅ |
| 4.5 | Prompt Templates tập trung & AI In-Day Cache (`ai_cache.py`) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `backend/app/ai/prompts/*.txt`, `ai_cache.py` | ✅ |
| 4.6 | Heuristic Fallback Engine (offline-safe, trả cùng cấu trúc JSON) | 🟡 P1 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `backend/app/services/fallback_service.py` | ✅ |
| 4.7 | API endpoints AI (`/monthly-report`, `/restock-suggestions`, `/anomalies`, `/ask`, `/generate-order`) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `api/v1/endpoints/ai.py` | ✅ |
| 4.8 | Tài liệu KT3: Prompt Engineering + AI Integration Architecture | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md`, `03_AI_Integration_Architecture.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 4:** 5 endpoint AI trả kết quả đúng cấu trúc; khi `GEMINI_API_KEY` trống hoặc 429, Fallback Engine kích hoạt tự động và giao diện không vỡ.

---

### GIAI ĐOẠN 5 — Kiểm thử tự động (Pytest)

> **Mục tiêu:** Bộ test đủ mạnh để phát hiện regression và minh chứng cho KT3.
> **Dependency:** Giai đoạn 3 + 4 (có code để test).
> **Mốc nộp bài:** KT3

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 5.1 | `conftest.py` — Pytest fixtures (SQLite in-memory, test client, JWT tokens) | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | Tích hợp trong các test modules | ✅ |
| 5.2 | `test_auth.py` — 12 tests xác thực, RBAC, Rate Limiting | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_auth.py` | ✅ |
| 5.3 | `test_master_data.py` — 5 tests CRUD danh mục, upload ảnh | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_master_data.py` | ✅ |
| 5.4 | `test_stock_transactions.py` — 18 tests luồng xuất 3 bước, ACID, chặn tồn âm, Thẻ kho, Idempotency | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_stock_transactions.py` | ✅ |
| 5.5 | `test_ai_service.py` — 31 tests AI pipeline, heuristic fallback, AI cache, Gemini mock | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_ai_service.py` | ✅ |
| 5.6 | `test_ai_empty_data.py` — 4 tests an toàn khi kho hoàn toàn rỗng | 🟡 P1 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_ai_empty_data.py` | ✅ |
| 5.7 | Seed Data thực tế: 76 sản phẩm, 7 nhóm, 10 NCC, giao dịch 5 tháng (150 ngày) | 🟡 P1 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/seed_data.py` | ✅ |
| 5.8 | Báo cáo kết quả test KT3 (70 tests pass 100%, 83% coverage) | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `docs/SDLC/KT3/02_Test_Plan_and_Results.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 5:** `pytest` đạt 70/70 tests PASS 100%, độ bao phủ code 83%.

---

### GIAI ĐOẠN 6 — Frontend React + Tailwind CSS

> **Mục tiêu:** Giao diện đầy đủ, sinh viên demo được toàn bộ nghiệp vụ.
> **Dependency:** Giai đoạn 2+3+4 (API backend ổn định).
> **Mốc nộp bài:** Cuối kỳ

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 6.1 | Auth Context + Axios client (`api/client.js`) + Trang Login | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/context/AuthContext.jsx`, `src/api/client.js`, `src/pages/Login.jsx` | ✅ |
| 6.2 | Dashboard: KPIs tổng quan + badge cảnh báo tồn kho | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/Dashboard.jsx` | ✅ |
| 6.3 | Trang Hàng hóa + Nhóm hàng (CRUD + lọc tìm kiếm + upload ảnh) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/Products.jsx` | ✅ |
| 6.4 | Trang Nhà cung cấp (CRUD) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/Suppliers.jsx` | ✅ |
| 6.5 | Trang Lập phiếu Nhập kho (chọn hàng, tự tính tổng, hủy phiếu) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/ImportNotes.jsx` | ✅ |
| 6.6 | Trang Lập phiếu Xuất kho (luồng 3 bước, xóa phiếu CONFIRMED, kiểm tra tồn) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/ExportNotes.jsx` | ✅ |
| 6.7 | Trang Tra cứu Thẻ kho + Xuất Excel | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/StockLedger.jsx` | ✅ |
| 6.8 | Trang Trợ lý AI & Báo cáo NXT 4 tabs (Báo cáo NXT + Xuất Excel, Gợi ý, Bất thường, Copilot Chat) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/AIAssistant.jsx` | ✅ |
| 6.9 | Giao diện Sáng/Tối (Dark/Light mode), ConfirmModal bắt buộc lý do $\ge 5$ ký tự, Role Switcher | 🟢 P2 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `Layout.jsx`, `tokens.css`, `ConfirmContext.jsx` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 6:** Demo được toàn bộ luồng: Đăng nhập → Nhập kho → Xuất kho 3 bước → Thẻ kho → Báo cáo NXT & Trợ lý AI. Build thành công 100%.

---

### GIAI ĐOẠN 7 — Đóng gói + Tài liệu cuối

> **Mục tiêu:** Giảng viên nhận repo, chạy được trong 5 phút, sinh viên thuyết trình được.
> **Dependency:** Giai đoạn 6 (toàn bộ app hoàn chỉnh).
> **Mốc nộp bài:** Cuối kỳ

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 7.1 | `README.md` hướng dẫn Docker Compose 2 containers + `run.bat` + kịch bản demo | 🔴 P0 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `README.md`, `docker-compose.yml`, `run.bat` | ✅ |
| 7.2 | Báo cáo kỹ thuật tổng kết đồ án (Markdown & Word) | 🔴 P0 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `docs/SDLC/final/01_Final_Technical_Report.md`, `Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx` | ✅ |
| 7.3 | Hướng dẫn sử dụng + kịch bản demo chấm thi 5 phút | 🔴 P0 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `docs/SDLC/final/02_User_Guide_and_Demo_Script.md` | ✅ |
| 7.4 | Slide thuyết trình bảo vệ đồ án (Markdown & PowerPoint) | 🟡 P1 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `docs/SDLC/final/03_Presentation_Slides.md`, `Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx` | ✅ |
| 7.5 | Kiểm tra bảo mật & toàn vẹn: 44 endpoints, 70 tests pass 100%, 83% coverage | 🟡 P1 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | Toàn bộ 70 Pytest cases pass 100%, ghi chú trong báo cáo | ✅ |

**Tiêu chí hoàn thành Giai đoạn 7:** Khởi chạy 1-Click qua Docker Compose hoặc `run.bat` trong ≤5 phút; trọn bộ hồ sơ SDLC 4 mốc sẵn sàng nộp và thuyết trình. Đã hoàn thành 100%.

---

## Lịch sử cập nhật MASTER-ROADMAP

| Ngày | Phiên | Nội dung thay đổi |
| :---: | :---: | --- |
| 2026-09-20 | #1 | Tạo mới — thiết lập toàn bộ 8 giai đoạn |
| 2026-09-21 | #2 | Hoàn thành Giai đoạn 0 (Scaffolding Backend/Frontend) và Giai đoạn 1 (Tài liệu KT1 + 9 DB Models) |
| 2026-09-22 | #3 | Hoàn thành phần Auth & RBAC (Bước 05 / Nhiệm vụ 2.2, 2.3) thuộc Giai đoạn 2: Tích hợp bcrypt thuần, PyJWT HS256, idempotent seed 3 tài khoản, SQLite FK và 14/14 tests pass |
| 2026-09-22 | #4 | Hoàn thành toàn bộ Giai đoạn 2 (Bước 06 & Tài liệu KT2 API Spec): Hoàn thiện CRUD Category, Product, Supplier, cảnh báo tồn kho, RBAC và 18/18 tests pass |
| 2026-09-22 | #5 | Hoàn thành toàn bộ Giai đoạn 3 (Bước 07 & 3 tài liệu KT2/Architecture): Transaction ACID, Chống tồn âm, Guard-check Hủy phiếu, Thẻ kho, Báo cáo Nhập-Xuất-Tồn và 24/24 tests pass |
| 2026-09-23 | #6 | Hoàn thành toàn bộ Giai đoạn 4 & 5 (Mốc KT3): Tích hợp AI Gemini + Heuristic Fallback offline, 3 prompt templates độc lập, seed data 60 ngày 3 kịch bản cốt lõi và 30/30 tests pass 100% |
| 2026-09-23 | #7 | Hoàn thành toàn bộ Giai đoạn 6 (Bước 09): Xây dựng hoàn chỉnh ứng dụng Frontend Web React 18 + Tailwind CSS + Lucide Icons cho 7 phân hệ, Defensive UI chống xuất âm, Demo Role Switcher 1-click, build thành công 1551 modules |
| 2026-09-25 | #8 | Hoàn thành toàn bộ Giai đoạn 7 (Bước 11 & Mốc Cuối kỳ): Đóng gói dự án 1-click (run.bat), trọn bộ hồ sơ SDLC 4 mốc tại docs/SDLC/final/, Báo cáo kỹ thuật Word 10 chương, Slide PowerPoint bảo vệ đồ án 16 trang, đồng bộ docs/submissions/final/ và bộ test Pytest đạt 60/60 tests pass 100% |
| 2026-10-28 | #9 | Đồng bộ toàn diện hồ sơ dự án theo mã nguồn thực tế: Chuẩn hóa 44 endpoints, Gemini 3.5 Flash Lite + AI In-Day Cache, 70 tests pass 100% (83% coverage), seed data 76 sản phẩm / 5 tháng, cỗ máy xuất kho 3 bước, xóa phiếu CONFIRMED, gộp Báo cáo NXT vào AIAssistant, xuất Excel và Dark mode |

---

## CHANGELOG

### [2026-10-28] Đồng bộ Toàn diện Hồ sơ Dự án theo Mã nguồn Thực tế (Audit 09)

- **Chuẩn hóa số lượng endpoint:** Cập nhật 44 endpoints (42 API v1 + 2 root/health).
- **Chuẩn hóa mô hình AI:** Nâng cấp sang `gemini-3.5-flash-lite`, chuỗi fallback chain 3.1 $\rightarrow$ 3.6, bổ sung `ai_cache.py`, endpoint `/ai/ask` và `/ai/generate-order`.
- **Cỗ máy xuất kho 3 bước:** Cập nhật luồng `CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`, trừ kho nguyên tử bằng Atomic SQL `RETURNING current_stock`, bảo toàn quyền xóa phiếu `CONFIRMED` (`DELETE /export-notes/{id}`).
- **Bộ kiểm thử tự động:** Mở rộng thành **70 ca test PASS 100%** (bổ sung 4 ca test kho rỗng tại `test_ai_empty_data.py`), độ bao phủ mã nguồn đạt **83%**.
- **Dữ liệu mẫu thực tế:** Cập nhật quy mô trong `seed_data.py` lên **76 sản phẩm**, **7 nhóm hàng**, **10 nhà cung cấp** và dữ liệu liên tục **5 tháng (150 ngày)**.
- **Frontend & Tiện ích:** Bổ sung giao diện Sáng / Tối (Dark / Light mode qua `tokens.css`), hộp thoại `ConfirmModal` bắt buộc lý do $\ge 5$ ký tự, tích hợp Báo cáo Nhập-Xuất-Tồn và xuất file Excel vào trang `AIAssistant.jsx`.
