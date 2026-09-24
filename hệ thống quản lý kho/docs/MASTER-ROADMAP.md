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
| **6** | Frontend React + Tailwind | Cuối kỳ | ⬜ Chưa bắt đầu |
| **7** | Đóng gói + Tài liệu cuối | Cuối kỳ | ⬜ Chưa bắt đầu |

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
| 1.3 | Kiến trúc AI + Prompt mẫu (anti-hallucination) | 🔴 P0 | [Buoc-01](plans/Buoc-01-Dac-ta-yeu-cau-va-Phan-tich-nghiep-vu.md) | `docs/SDLC/KT1/03_AI_Architecture_and_Prompts.md` | ✅ |
| 1.4 | Wireframes: Dashboard, Phiếu nhập/xuất, Trợ lý AI | 🔴 P0 | [Buoc-01](plans/Buoc-01-Dac-ta-yeu-cau-va-Phan-tich-nghiep-vu.md) | `docs/SDLC/KT1/04_Wireframes.md` | ✅ |
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
| 2.3 | RBAC dependency `require_role(["ADMIN", ...])` | 🔴 P0 | [Buoc-05](plans/Buoc-05-Xac-thuc-Dang-nhap-va-Phan-quyen-RBAC.md) | Tích hợp vào tất cả protected endpoints | ✅ |
| 2.4 | CRUD: Categories, Products (với `min_stock`, `current_stock`) | 🔴 P0 | [Buoc-06](plans/Buoc-06-Module-Hang-hoa-Nhom-hang-va-Nha-cung-cap.md) | `api/v1/endpoints/products.py` + Swagger OK | ✅ |
| 2.5 | CRUD: Suppliers | 🔴 P0 | [Buoc-06](plans/Buoc-06-Module-Hang-hoa-Nhom-hang-va-Nha-cung-cap.md) | `api/v1/endpoints/suppliers.py` + Swagger OK | ✅ |
| 2.6 | Tài liệu API Spec KT2 | 🔴 P0 | [Buoc-06](plans/Buoc-06-Module-Hang-hoa-Nhom-hang-va-Nha-cung-cap.md) | `docs/SDLC/KT2/01_API_Specifications.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 2:** Login trả JWT; CRUD products/suppliers pass test; Swagger UI hiển thị đủ endpoints.

---

### GIAI ĐOẠN 3 — Transaction ACID + Stock Ledger ⭐ Tâm điểm đề tài

> **Mục tiêu:** Nghiệp vụ kho cốt lõi — phải đúng 100%, không được thỏa hiệp.
> **Dependency:** Giai đoạn 2 (CRUD master data xong).
> **Mốc nộp bài:** KT2

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 3.1 | `InventoryService.create_import()` — Transaction ACID nhập hàng + ghi Stock Ledger | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `backend/app/services/inventory_service.py` | ✅ |
| 3.2 | `InventoryService.create_export()` — Atomic check tồn + Rollback nếu âm + ghi Stock Ledger | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `backend/app/services/inventory_service.py` | ✅ |
| 3.3 | API endpoints nhập/xuất kho (`/import-notes`, `/export-notes`) | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `api/v1/endpoints/import_notes.py`, `export_notes.py` | ✅ |
| 3.4 | State Machine phiếu: `DRAFT → COMPLETED → CANCELLED` (hoàn trả tồn kho khi hủy) | 🟡 P1 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | Logic trong `inventory_service.py` | ✅ |
| 3.5 | API Báo cáo Nhập-Xuất-Tồn theo kỳ + tra cứu Stock Ledger | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `api/v1/endpoints/reports.py`, `stock_ledger.py` | ✅ |
| 3.6 | API cảnh báo hàng dưới tồn tối thiểu | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | Tích hợp vào `/products` hoặc `/reports/alerts` | ✅ |
| 3.7 | Tài liệu Transaction Design KT2 | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md` | ✅ |
| 3.8 | Minh chứng dùng AI trong SDLC KT2 | 🔴 P0 | [Buoc-07](plans/Buoc-07-Module-Nhap-xuat-kho-va-The-kho-Transaction-ACID.md) | `docs/SDLC/KT2/03_AI_Assisted_Development_Evidence.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 3:** Xuất quá tồn → HTTP 400, `current_stock` không đổi; mỗi nhập/xuất tạo bản ghi `stock_ledger`; công thức `Tồn đầu + Nhập - Xuất = Tồn cuối` khớp.

---

### GIAI ĐOẠN 4 — Tích hợp AI + Fallback Engine

> **Mục tiêu:** 3 chức năng AI hoạt động, offline-safe, không bịa số liệu.
> **Dependency:** Giai đoạn 3 (có dữ liệu kho thực để AI phân tích).
> **Mốc nộp bài:** KT3

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 4.1 | Data Aggregation Pipeline (SQL tổng hợp, loại bỏ giá mua) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `backend/app/services/ai_service.py` — hàm `tong_hop_du_lieu()` | ✅ |
| 4.2 | Kết nối Gemini API — Báo cáo tháng | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `ai_service.generate_monthly_report()` | ✅ |
| 4.3 | Kết nối Gemini API — Gợi ý nhập hàng (kèm velocity 30 ngày) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `ai_service.generate_restock_suggestions()` | ✅ |
| 4.4 | Kết nối Gemini API — Biến động bất thường (xuất >200%, tồn >30 ngày) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `ai_service.generate_anomaly_detection()` | ✅ |
| 4.5 | Prompt Templates tập trung (không hardcode trong router) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `backend/app/ai/prompts/*.txt` | ✅ |
| 4.6 | Heuristic Fallback Engine (offline-safe, trả cùng cấu trúc JSON) | 🟡 P1 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `backend/app/services/fallback_service.py` | ✅ |
| 4.7 | API endpoints AI (`/ai/monthly-report`, `/ai/restock-suggestions`, `/ai/anomalies`) | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `api/v1/endpoints/ai.py` | ✅ |
| 4.8 | Tài liệu KT3: Prompt Engineering + AI Architecture | 🔴 P0 | [Buoc-08](plans/Buoc-08-Module-AI-Tro-ly-va-Scheduler-Quet-ton-kho.md) | `docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md`, `03_AI_Integration_Architecture.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 4:** 3 endpoint AI trả kết quả đúng cấu trúc; khi `GEMINI_API_KEY` trống, Fallback Engine kích hoạt tự động và giao diện không vỡ.

---

### GIAI ĐOẠN 5 — Kiểm thử tự động (Pytest)

> **Mục tiêu:** Bộ test đủ mạnh để phát hiện regression và minh chứng cho KT3.
> **Dependency:** Giai đoạn 3 + 4 (có code để test).
> **Mốc nộp bài:** KT3

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 5.1 | `conftest.py` — Pytest fixtures (SQLite in-memory, test client) | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | Tích hợp trong các test modules | ✅ |
| 5.2 | `test_import_stock` — Nhập kho tăng đúng tồn + ghi đúng Stock Ledger | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_stock_transactions.py` | ✅ |
| 5.3 | `test_prevent_negative_stock` — Xuất > tồn → HTTP 400, tồn không đổi | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_stock_transactions.py` | ✅ |
| 5.4 | `test_stock_ledger_balance` — `balance_after` khớp `current_stock` sau mỗi giao dịch | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_stock_transactions.py` | ✅ |
| 5.5 | `test_ai_pipeline` — Mock Gemini, kiểm tra dữ liệu đầu vào không chứa giá mua | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_ai.py` | ✅ |
| 5.6 | `test_ai_fallback` — Khi API lỗi, fallback trả đúng cấu trúc | 🟡 P1 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/tests/test_ai.py` | ✅ |
| 5.7 | Seed Data thực tế: 20+ SP, 3 user, giao dịch 60 ngày | 🟡 P1 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `backend/seed_data.py` | ✅ |
| 5.8 | Báo cáo kết quả test KT3 | 🔴 P0 | [Buoc-10](plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md) | `docs/SDLC/KT3/02_Test_Plan_and_Results.md` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 5:** `pytest` chạy không có test đỏ; các test không mock chính layer đang test (xem `CLAUDE.md §7`).

---

### GIAI ĐOẠN 6 — Frontend React + Tailwind CSS

> **Mục tiêu:** Giao diện đầy đủ, sinh viên demo được toàn bộ nghiệp vụ.
> **Dependency:** Giai đoạn 2+3+4 (API backend ổn định).
> **Mốc nộp bài:** Cuối kỳ

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 6.1 | Auth Context + Axios client + Trang Login | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/context/AuthContext.jsx`, `src/api/client.js`, `src/pages/Login.jsx` | ✅ |
| 6.2 | Dashboard: KPIs tổng quan + badge cảnh báo tồn kho | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/Dashboard.jsx` | ✅ |
| 6.3 | Trang Hàng hóa + Nhóm hàng (CRUD + lọc tìm kiếm) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/Products.jsx` | ✅ |
| 6.4 | Trang Nhà cung cấp (CRUD) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/Suppliers.jsx` | ✅ |
| 6.5 | Trang Lập phiếu Nhập kho (form chọn hàng, tự tính tổng, hủy phiếu) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/ImportNotes.jsx` | ✅ |
| 6.6 | Trang Lập phiếu Xuất kho (kiểm tra tồn realtime trước khi submit) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/ExportNotes.jsx` | ✅ |
| 6.7 | Trang Báo cáo Nhập-Xuất-Tồn + tra cứu Thẻ kho | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/StockLedger.jsx` | ✅ |
| 6.8 | Trang Trợ lý AI (3 nút 1-click: Báo cáo tháng · Gợi ý nhập · Bất thường) | 🔴 P0 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | `src/pages/AIAssistant.jsx` | ✅ |
| 6.9 | Biểu đồ trực quan trên Dashboard & Bộ chuyển đổi Demo Role | 🟢 P2 | [Buoc-09](plans/Buoc-09-Xay-dung-Frontend-Web-React-Tailwind.md) | Tích hợp trong `Dashboard.jsx`, `Layout.jsx` | ✅ |

**Tiêu chí hoàn thành Giai đoạn 6:** Demo được toàn bộ luồng: Đăng nhập → Nhập kho → Xuất kho → Xem cảnh báo → Xem báo cáo AI. Đã hoàn thành 100% build thành công.

---

### GIAI ĐOẠN 7 — Đóng gói + Tài liệu cuối

> **Mục tiêu:** Giảng viên nhận repo, chạy được trong 5 phút, sinh viên thuyết trình được.
> **Dependency:** Giai đoạn 6 (toàn bộ app hoàn chỉnh).
> **Mốc nộp bài:** Cuối kỳ

| # | Nhiệm vụ | Ưu tiên | Kế hoạch chi tiết | Deliverable | Trạng thái |
| --- | --- | :---: | --- | --- | :---: |
| 7.1 | `README.md` hướng dẫn cài đặt 1-click + kịch bản demo | 🔴 P0 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `README.md` ở gốc dự án | ⬜ |
| 7.2 | Báo cáo kỹ thuật tổng kết đồ án | 🔴 P0 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `docs/SDLC/final/01_Final_Technical_Report.md` | ⬜ |
| 7.3 | Hướng dẫn sử dụng + kịch bản demo chấm thi | 🔴 P0 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `docs/SDLC/final/02_User_Guide_and_Demo_Script.md` | ⬜ |
| 7.4 | Slide thuyết trình bảo vệ đồ án | 🟡 P1 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | `docs/SDLC/final/03_Presentation_Slides.md` | ⬜ |
| 7.5 | Kiểm tra bảo mật cuối: CORS, JWT expiry, không lộ key | 🟡 P1 | [Buoc-11](plans/Buoc-11-Dong-goi-Tai-lieu-SDLC-va-Kich-ban-Demo.md) | Review code + ghi chú trong báo cáo | ⬜ |

**Tiêu chí hoàn thành Giai đoạn 7:** `git clone` + `pip install` + `npm install` + `python seed_data.py` → app chạy được trong ≤5 phút.

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

> **Quy ước ghi lịch sử:** Mỗi lần cập nhật file này (thay đổi trạng thái, thêm/sửa nhiệm vụ, điều chỉnh kế hoạch), thêm 1 dòng vào bảng trên với ngày và lý do. Không xóa dòng cũ.

---

## CHANGELOG

### [2026-09-23] Hoàn thành Giai đoạn 6 (Bước 09: Frontend Web React 18 & Tailwind CSS)

- **Kiến trúc Single Page Application:**
  - Hoàn thiện bộ khung React 18 + Vite + Tailwind CSS + Lucide Icons.
  - Tích hợp `AuthContext` quản lý phiên JWT, lưu `localStorage`, cung cấp hàm `switchDemoRole` chuyển vai trò tức thời (`ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT`) phục vụ thuyết trình đồ án.
  - Xây dựng `apiClient` tập trung với interceptor tự động xử lý token và mã lỗi 401.
- **7 Phân hệ giao diện chức năng:**
  - `Dashboard`: Thẻ KPI tồn kho, cảnh báo hàng sắp hết, lối tắt nghiệp vụ và giới thiệu tính năng AI.
  - `Products`: CRUD hàng hóa, tìm kiếm tức thì, lọc danh mục & `is_low_stock`, bảo vệ quyền hạn RBAC.
  - `Suppliers`: Quản lý thông tin nhà cung cấp và bảo toàn đối tác.
  - `ImportNotes`: Lập phiếu nhập đa dòng, tra giá mẫu tự động, tính tổng tiền, hủy phiếu hoàn trừ kho.
  - `ExportNotes`: Lập phiếu xuất với Defensive UI kiểm tra tồn kho realtime, khóa nút tạo phiếu nếu xuất vượt tồn, hủy phiếu hoàn kho.
  - `StockLedger`: Sổ cái thẻ kho chi tiết, lọc theo giao dịch, modal điều chỉnh kiểm kê cân bằng tồn.
  - `AIAssistant`: 3 bài toán AI kết nối API Backend (Báo cáo tháng, Gợi ý nhập hàng, Biến động bất thường) kèm nhãn nhận biết Fallback Engine.
- **Chất lượng đóng gói:**
  - `npm run build` PASS: 1551 modules compile trong 4.23s, 0 cảnh báo hay lỗi cú pháp.
  - Backend test suite tiếp tục duy trì 30/30 test cases PASS 100%.

### [2026-09-23] Hoàn thành Giai đoạn 4 & 5 (Mốc KT3: Tích hợp AI, Tối ưu Prompt & Kiểm thử tự động)

- **Tích hợp AI & Heuristic Fallback Engine (Giai đoạn 4 - Bước 08):**
  - Xây dựng `backend/app/services/ai_service.py` với SQL Aggregation Pipeline tiền xử lý và **loại bỏ hoàn toàn thông tin giá mua nhạy cảm** (`unit_price`).
  - Tích hợp Google Gemini API (`gemini-1.5-flash`) qua Structured JSON Output.
  - Xây dựng `backend/app/services/fallback_service.py` (Heuristic Fallback Engine) đảm bảo hệ thống phản hồi $< 50$ms khi offline hoặc thiếu API Key.
  - Quản lý 3 Prompt Templates tập trung tại `backend/app/ai/prompts/*.txt`.
  - Khởi tạo 3 endpoints API tại `backend/app/api/v1/endpoints/ai.py` (`/monthly-report`, `/restock-suggestions`, `/anomalies`).
- **Bộ kiểm thử tự động & Dữ liệu mẫu 60 ngày (Giai đoạn 5 - Bước 10):**
  - Viết `backend/tests/test_ai.py` (6 bài test kiểm tra bảo mật dữ liệu, fallback rỗng, gợi ý nhập, biến động bất thường, mock Gemini, RBAC). Toàn bộ **30/30 test cases PASS 100%**.
  - Xây dựng `backend/seed_data.py` nạp 22 mặt hàng, 3 users, 3 NCC và lịch sử 60 ngày theo 3 kịch bản: SP001 (bán chạy cạn kho), SP002 (xuất đột biến), SP003 (tồn chết).
- **Hồ sơ bàn giao mốc KT3:**
  - Hoàn thiện đầy đủ 3 tài liệu tại `docs/SDLC/KT3/`: `01_Prompt_Engineering_and_Evaluation.md`, `02_Test_Plan_and_Results.md`, `03_AI_Integration_Architecture.md`.

### [2026-09-22] Hoàn thành Giai đoạn 3 (Bước 07: Module Nhập/Xuất kho & Thẻ kho Transaction ACID)

- **Nghiệp vụ cốt lõi (Core Inventory Service):**
  - `backend/app/services/inventory_service.py`: Transaction ACID cho Nhập/Xuất kho, kiểm tra chống tồn âm, sinh mã tự động với Retry Pattern, Guard-check hủy phiếu (Phương án B), điều chỉnh kiểm kê (Phương án A) và báo cáo Nhập-Xuất-Tồn chuẩn kế toán.
  - `backend/app/schemas/`: Đầy đủ schemas cho ImportNote, ExportNote, StockLedger, Report.
  - `backend/app/api/v1/endpoints/`: Đăng ký các endpoints `/import-notes`, `/export-notes`, `/stock-ledger`, `/reports`.
- **Tài liệu bàn giao KT2:**
  - `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md`: Tài liệu thiết kế Transaction và chống tồn âm.
  - `docs/SDLC/KT2/03_AI_Assisted_Development_Evidence.md`: Minh chứng sinh viên ứng dụng AI trong quy trình SDLC.
  - `docs/architecture.md`: Tài liệu kiến trúc hệ thống 3 tầng và các sơ đồ luồng dữ liệu.
- **Kiểm thử tự động:**
  - `backend/tests/test_stock_transactions.py` (6 bài test lớn kiểm tra trọn vẹn mọi luồng).
  - Kết quả toàn dự án: **24/24 test cases PASS 100%**.

### [2026-09-22] Hoàn thành Giai đoạn 2 (Bước 06: Module Hàng hóa, Nhóm hàng & Nhà cung cấp)

- **Hoàn thành các nhiệm vụ Giai đoạn 2:**
  - `backend/app/schemas/`: Toàn bộ Schemas cho Category, Product, Supplier và User.
  - `backend/app/api/v1/endpoints/categories.py`: CRUD nhóm hàng hóa, chặn xóa khi có sản phẩm liên kết.
  - `backend/app/api/v1/endpoints/products.py`: CRUD hàng hóa, tìm kiếm theo tên/SKU, lọc theo nhóm hàng, lọc cảnh báo tồn `is_low_stock`, soft delete `DISCONTINUED`.
  - `backend/app/api/v1/endpoints/suppliers.py`: CRUD nhà cung cấp, chuyển `is_active=False` khi đã có phiếu nhập.
  - Phân quyền RBAC chặt chẽ: `ACCOUNTANT` chỉ đọc, `WAREHOUSE_KEEPER` thêm/sửa, `ADMIN` toàn quyền.
- **Tài liệu bàn giao KT2:**
  - Hoàn thành `docs/SDLC/KT2/01_API_Specifications.md` đặc tả toàn bộ RESTful APIs và RBAC Matrix.
- **Kiểm thử tự động:**
  - `backend/tests/test_master_data.py`: Đạt 4/4 test suites lớn. Tổng cộng 18/18 tests toàn dự án PASS 100%.

### [2026-09-22] Cập nhật Giai đoạn 2 (Bước 05: Auth & RBAC)

- **Hoàn thành các mục trong Bước 05:**
  - `backend/app/core/security.py`: Sử dụng `bcrypt` thuần (loại bỏ phụ thuộc `passlib` để tương thích hoàn toàn Python 3.14) và `pyjwt` (HS256).
  - Chuẩn hóa JWT tối thiểu: `ACCESS_TOKEN_EXPIRE_MINUTES = 60` (được đọc từ `.env`).
  - `backend/app/schemas/user.py`: Cung cấp các Pydantic schema cho đăng nhập, thông tin người dùng và token.
  - `backend/app/api/deps.py`: Dependency `get_current_user` và `require_roles` phân quyền 3 vai trò (`ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT`).
  - `backend/app/api/v1/endpoints/auth.py`: Đăng ký router `/api/v1/auth` gồm các endpoint `/login`, `/login-form`, `/me`, `/users`.
- **Cải tiến kỹ thuật & 2 đề xuất của người dùng:**
  - **SQLite Foreign Keys:** Kích hoạt `PRAGMA foreign_keys = ON;` qua SQLAlchemy connection listener tại `database.py`.
  - **Exception Handler:** Bắt riêng `IntegrityError` trả về HTTP 400 trong `main.py`.
  - **Idempotent Seed:** Thêm `backend/app/core/seed.py` tự động nạp 3 tài khoản mẫu (`admin`, `thukho`, `ketoan`) an toàn trong `lifespan`.
- **Chất lượng kiểm thử:**
  - `backend/tests/test_auth.py` đạt 11/11 tests. Tổng cộng bộ test hiện tại 14/14 tests PASS 100%.
