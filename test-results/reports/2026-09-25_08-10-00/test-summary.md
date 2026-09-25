# Báo Cáo Tổng Quan Kết Quả Kiểm Thử (Test Summary)

> **Mã phiên kiểm thử**: `2026-09-25_08-10-00`  
> **Thời gian thực hiện**: 25/09/2026 08:10:00 (GMT+7)  
> **Dự án**: Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI) — Đề tài 07  
> **Môi trường thực thi**: Python 3.14.6, pytest 8.2.2, Node.js v24.18.1, Vite 5.4.21, SQLite (PRAGMA foreign_keys = ON)

---

## 1. Thống Kê Phân Loại Trạng Thái Kiểm Thử

| Trạng Thái Kiểm Thử | Số Lượng Ca Kiểm Thử | Tỷ Lệ (%) | Ghi Chú Kỹ Thuật |
| :--- | :---: | :---: | :--- |
| **PASSED** (Thành công) | **60** | **100%** | Toàn bộ 60 ca kiểm thử vượt qua xác thực assertions tuyệt đối. |
| **FAILED** (Lỗi nghiệp vụ) | **0** | **0%** | Không có lỗi logic hoặc sai lệch assertion trong thân hàm test. |
| **ERRORS** (Lỗi hạ tầng/Fixture) | **0** | **0%** | Không có lỗi fixture, database session hay môi trường khởi tạo. |
| **TỔNG CỘNG** | **60** | **100%** | **Toàn bộ bộ test suite đạt trạng thái PASS hoàn hảo.** |

### 1.1. Chi tiết phân bổ theo tập tin kiểm thử

1. `tests/test_agent_comprehensive_blackbox.py`: **20/20 passed** (Blackbox API contracts, boundary values, RBAC matrix, IDOR security, AI negative inputs, data consistency).
2. `tests/test_ai.py`: **13/13 passed** (Google Gemini prompts, heuristic fallback engine, monthly reports, restock suggestions, anomaly alerts, prompt sanitization).
3. `tests/test_auth.py`: **11/11 passed** (Bcrypt password hashing, JWT Bearer generation, login JSON/form, role-based access control, expired tokens).
4. `tests/test_foundation.py`: **3/3 passed** (Database engine initialization, seed data completeness, health check endpoint).
5. `tests/test_master_data.py`: **5/5 passed** (CRUD danh mục Category, Product lifecycle, Supplier management, filtering).
6. `tests/test_stock_transactions.py`: **8/8 passed** (Quy trình Nhập kho ACID, Cỗ máy xuất kho 3 bước CONFIRMED -> SHIPPING -> COMPLETED, Chặn tồn âm ở 2 tầng, Hủy đơn & Hoàn kho 100%, Sổ cái thẻ kho kiểm kê cân đối).

---

## 2. Đối Chiếu Kết Nối Dịch Vụ Ngoài & Môi Trường

- **Cơ sở dữ liệu (Database)**:
  - Cấu hình kết nối: `sqlite:///./warehouse.db`.
  - Kiểm tra tính toàn vẹn: Đã kích hoạt cơ chế `PRAGMA foreign_keys = ON` cho SQLite session.
  - Toàn bộ các giao dịch ACID (nhập kho, xuất kho 3 bước, kiểm kê bù trừ thẻ kho) đã thực hiện rollback tự động thành công khi gặp lỗi cố ý trong test suite.
- **Phân hệ Trí tuệ Nhân tạo (Google Gemini API & Heuristic Fallback)**:
  - Khi không có `GEMINI_API_KEY` hoặc khi giả lập timeout/lỗi 429 quota: Bộ động cơ `FallbackService` nội tại tự động kích hoạt mượt mà, trả kết quả phân tích thống kê chính xác kèm cờ cảnh báo `[Chế độ Heuristic Offline]`.

---

## 3. Đối Chiếu So Sánh Biến Động Số Liệu (Baseline Run)

- **Trích dẫn nguồn số liệu**: Đây là **Phiên kiểm thử chuẩn hóa đầu tiên (Baseline Benchmark Run)** được khởi tạo và lưu vết chính thức vào thư mục `test-results/reports/` theo quy chuẩn `AGENT-TESTING-GUIDE.md`.
- **Hiện trạng trước phiên**: Thư mục `test-results/reports/` chưa có phiên kiểm thử trước đó.
- **Kết luận cơ sở**: Thiết lập mốc tham chiếu cơ sở vững chắc: **60/60 tests passed, 0 failed, 0 errors, Coverage đạt 79% toàn hệ thống (Statement coverage 83.8%)**.

---

## 4. Bảng Đo Độ Bao Phủ Mã Nguồn (Code Coverage Table)

> Lệnh thực thi: `pytest --cov=app --cov-branch --cov-report=term-missing tests/`

| Tên Module / Tệp Nguồn | Số Dòng (Stmts) | Bỏ Sót (Miss) | Nhánh (Branch) | Nhánh Thiếu (BrPart) | Tỷ Lệ Độ Phủ (Cover) | Các Dòng Chưa Bao Phủ (Missing) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `app/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/ai/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/api/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/api/deps.py` | 28 | 2 | 10 | 2 | **89%** | 42, 49 |
| `app/api/v1/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/api/v1/api.py` | 12 | 0 | 0 | 0 | **100%** | — |
| `app/api/v1/endpoints/ai.py` | 24 | 0 | 0 | 0 | **100%** | — |
| `app/api/v1/endpoints/auth.py` | 39 | 4 | 10 | 4 | **84%** | 34, 60, 67, 107 |
| `app/api/v1/endpoints/categories.py` | 63 | 13 | 22 | 6 | **71%** | 30->35, 50-56, 105, 112-120, 122->124, 125, 145 |
| `app/api/v1/endpoints/export_notes.py` | 59 | 10 | 12 | 1 | **79%** | 72-89, 191, 216-217 |
| `app/api/v1/endpoints/import_notes.py` | 42 | 8 | 10 | 3 | **75%** | 78, 80, 82, 99-114, 150 |
| `app/api/v1/endpoints/products.py` | 127 | 46 | 52 | 4 | **59%** | 47, 53, 121, 198-230, 245-275, 291 |
| `app/api/v1/endpoints/reports.py` | 27 | 7 | 6 | 2 | **67%** | 42, 44, 66-78 |
| `app/api/v1/endpoints/stock_ledger.py` | 30 | 3 | 10 | 4 | **82%** | 46->48, 49, 51, 53 |
| `app/api/v1/endpoints/suppliers.py` | 74 | 16 | 30 | 10 | **69%** | 32->41, 42, 59-65, 117, 123-131, 134, 135->137, 138, 139->141, 142, 162 |
| `app/core/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/core/config.py` | 17 | 0 | 0 | 0 | **100%** | — |
| `app/core/database.py` | 21 | 0 | 4 | 2 | **92%** | 10->13, 20->27 |
| `app/core/security.py` | 29 | 3 | 2 | 1 | **87%** | 25-26, 37 |
| `app/core/seed.py` | 14 | 0 | 6 | 0 | **100%** | — |
| `app/main.py` | 47 | 9 | 0 | 0 | **81%** | 24-33, 84, 96, 119 |
| `app/models/ (Toàn bộ 8 models)` | 146 | 0 | 0 | 0 | **100%** | — |
| `app/schemas/ (Toàn bộ 9 schemas)` | 219 | 0 | 0 | 0 | **100%** | — |
| `app/services/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/services/ai_cache.py` | 58 | 9 | 6 | 2 | **83%** | 34, 38-40, 48-49, 65-67 |
| `app/services/ai_service.py` | 336 | 88 | 94 | 24 | **71%** | Chi tiết các nhánh fallback, gemini stream và prompt formatters |
| `app/services/fallback_service.py` | 90 | 15 | 28 | 9 | **78%** | 27-35, 38-46, 58->65, 78->82, 82->86, 110, 122-131, 159, 231 |
| `app/services/inventory_service.py` | 227 | 52 | 86 | 25 | **71%** | Các nhánh xử lý retry concurrency, error handlers và lọc ngày |
| **TỔNG CỘNG HỆ THỐNG** | **1757** | **285** | **388** | **99** | **79%** | **Statement: 83.8% (1472/1757 dòng được thực thi thật)** |

---

## 5. Kết Quả Kiểm Tra Frontend & Tĩnh Học

1. **Kiểm tra Frontend Build (`npm run build`)**:
   - Công nghệ: Vite 5.4.21, React 18, Tailwind CSS.
   - Kết quả: **Exit Code 0** (Build thành công trong 4.24 giây).
   - Bundle Metrics:
     - `dist/index.html`: 1.01 kB (gzip: 0.63 kB).
     - `dist/assets/index-BmbfUsTP.css`: 42.91 kB (gzip: 7.26 kB).
     - `dist/assets/index-CNzsWlO_.js`: 341.01 kB (gzip: **95.78 kB**).
   - Đánh giá: Kích thước tải nén Gzip chỉ ~95.78 kB, hoàn toàn đáp ứng mục tiêu kiến trúc tải siêu tốc (< 100KB).

2. **Kiểm tra Phân tích Tĩnh (Static Analysis)**:
   - **Backend (`python -m ruff check app`)**: Phát hiện 339 warnings (chủ yếu là hiện đại hóa cú pháp type annotation Python 3.14 như `list` thay vì `List`, `dict` thay vì `Dict`, và unused error variables `exc`). Tuân thủ quy tắc Zero Modification: **Không chạy cờ `--fix`**.
   - **Frontend (`npx oxlint`)**: 22 warnings (các import icon chưa dùng từ `lucide-react`), **0 lỗi cú pháp (0 errors)** trên toàn bộ 20 tệp nguồn.

3. **Kiểm tra Định dạng Markdown (`npx markdownlint-cli "test-results/**/*.md"`)**:
   - Đã kiểm tra toàn bộ cây tài liệu `test-results/`.
   - Kết quả: **Exit Code 0** (Không có bất kỳ vi phạm cú pháp hay khoảng trắng markdown nào).

---

## 6. Nhật Ký Tác Vụ Nền (Background Tasks Disclosure)

| Mã Task ID | Lệnh Thực Thi | Mục Đích Khởi Tạo | Trạng Thái Kết Thúc | Lý Do & Giải Trình |
| :--- | :--- | :--- | :---: | :--- |
| `task-83` | `node -v; npm -v` | Kiểm tra môi trường Node.js & npm | **DONE (0)** | Xác nhận Node v24.18.1 & npm 11.16.0 sẵn sàng. |
| `task-88` | `pytest --cov=app ...` | Chạy toàn bộ 60 test cases với đo lường Coverage | **DONE (0)** | Chạy xong 60/60 tests passed trong 29.05 giây. |
| `task-96` | `npm run build` | Kiểm tra khả năng đóng gói Vite SPA & đo kích thước Gzip | **DONE (0)** | Build thành công, bundle js gzip 95.78 kB. |
| `task-103` | `npx oxlint` | Quét phân tích tĩnh mã nguồn React | **DONE (0)** | Hoàn thành trong 22ms, 0 errors, 22 warnings. |
| `task-117` | `npx markdownlint-cli ...` | Kiểm tra định dạng tài liệu markdown | **DONE (0)** | Exit code 0, tài liệu đạt chuẩn 100%. |
