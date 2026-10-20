# Báo Cáo Tổng Quan Kết Quả Kiểm Thử (Test Summary)

> **Mã phiên kiểm thử**: `2026-10-02_10-00-00`  
> **Thời gian thực hiện**: 02/10/2026 10:00:00 (GMT+7)  
> **Dự án**: Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI) — Đề tài 07  
> **Môi trường thực thi**: Python 3.14.6, pytest 8.2.2, Node.js v24.18.1, Vite 5.4.21, SQLite (PRAGMA foreign_keys = ON)

---

## 1. Thống Kê Phân Loại Trạng Thái Kiểm Thử

| Trạng Thái Kiểm Thử | Số Lượng Ca Kiểm Thử | Tỷ Lệ (%) | Ghi Chú Kỹ Thuật |
| :--- | :---: | :---: | :--- |
| **PASSED** (Thành công) | **63** | **100%** | Toàn bộ 63 ca kiểm thử vượt qua xác thực assertions tuyệt đối. |
| **FAILED** (Lỗi nghiệp vụ) | **0** | **0%** | Không có lỗi logic hoặc sai lệch assertion trong thân hàm test. |
| **ERRORS** (Lỗi hạ tầng/Fixture) | **0** | **0%** | Không có lỗi fixture, database session hay môi trường khởi tạo. |
| **TỔNG CỘNG** | **63** | **100%** | **Toàn bộ bộ test suite đạt trạng thái PASS hoàn hảo (63/63).** |

### 1.1. Chi tiết phân bổ theo tập tin kiểm thử

1. `tests/test_agent_comprehensive_blackbox.py`: **20/20 passed** (Blackbox API contracts, boundary values, RBAC matrix, IDOR security, SQL injection defense, boundary negative inputs, data consistency).
2. `tests/test_ai.py`: **13/13 passed** (Google Gemini prompts, heuristic fallback engine, monthly reports, restock suggestions, anomaly alerts, prompt data privacy sanitization, in-day cache).
3. `tests/test_auth.py`: **11/11 passed** (Bcrypt password hashing, JWT Bearer generation, login JSON/form, role-based access control, expired tokens, foreign key enforcement).
4. `tests/test_foundation.py`: **3/3 passed** (Database engine initialization, 9 tables completeness, health check endpoint).
5. `tests/test_master_data.py`: **5/5 passed** (CRUD danh mục Category, Product lifecycle, Supplier management, filtering, initial import note linking).
6. `tests/test_stock_transactions.py`: **11/11 passed** (+3 tests mới hôm nay):
   - Quy trình Nhập kho ACID: tăng tồn + sinh thẻ kho.
   - Cỗ máy xuất kho 3 bước: `CONFIRMED` -> `SHIPPING` -> `COMPLETED`.
   - Chặn tồn âm ở 2 tầng: rollback 100%, mã lỗi HTTP 400.
   - Hủy đơn & Hoàn kho 100% an toàn.
   - Sổ cái thẻ kho kiểm kê cân đối theo công thức kế toán.
   - **Mới**: `test_import_note_idempotency_key` — chống ghi trùng phiếu nhập kho qua header `X-Idempotency-Key`.
   - **Mới**: `test_export_note_idempotency_key` — chống ghi trùng phiếu xuất kho qua header `X-Idempotency-Key`.
   - **Mới**: `test_notes_without_idempotency_key_are_backward_compatible` — tương thích ngược khi client cũ không gửi header.

---

## 2. Đối Chiếu Kết Nối Dịch Vụ Ngoài & Môi Trường

- **Cơ sở dữ liệu (Database)**:
  - Cấu hình kết nối: `sqlite:///./warehouse.db`.
  - Tính toàn vẹn: Ràng buộc `PRAGMA foreign_keys = ON` cho SQLite session.
  - Schema Migration: Đã tự động bổ sung cột `idempotency_key VARCHAR(100)` và `UNIQUE INDEX` cho 2 bảng `import_notes` và `export_notes` mà không làm thay đổi hoặc mất mát dữ liệu hiện có.
  - Toàn bộ các giao dịch ACID (nhập kho, xuất kho 3 bước, kiểm kê bù trừ thẻ kho) đã thực hiện rollback tự động thành công khi gặp lỗi cố ý trong test suite.
- **Phân hệ Trí tuệ Nhân tạo (Google Gemini API & Heuristic Fallback)**:
  - Khi không có `GEMINI_API_KEY` hoặc khi giả lập timeout/lỗi 429 quota: Bộ động cơ `FallbackService` nội tại tự động kích hoạt mượt mà, trả kết quả phân tích thống kê chính xác kèm cờ cảnh báo `[Chế độ Heuristic Offline]`.

---

## 3. Đối Chiếu So Sánh Biến Động Số Liệu Giữa Các Phiên

- **Trích dẫn nguồn số liệu phiên trước**: `test-results/reports/2026-09-25_08-10-00/test-summary.md`.
- **Biến động số lượng ca kiểm thử**:
  - Phiên `2026-09-25_08-10-00`: **60 tests passed** (100%).
  - Phiên `2026-10-02_10-00-00`: **63 tests passed** (100%).
  - **Tăng trưởng**: **+3 test cases mới** tập trung xác thực cơ chế Idempotency Key bảo đảm chống ghi trùng lặp dữ liệu trên toàn bộ giao dịch nhập xuất kho.
- **Biến động độ bao phủ (Coverage)**:
  - Statement Coverage: **83%** (1.484 / 1.791 statements được thực thi).
  - Branch Coverage: **78%** (316 / 414 branches được bao phủ).
- **Biến động cảnh báo Frontend**:
  - Phiên trước: 22 warnings.
  - Phiên hôm nay: **10 warnings (giảm 12 cảnh báo)**, duy trì 0 errors.

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
| `app/api/v1/endpoints/export_notes.py` | 59 | 10 | 12 | 1 | **79%** | 73-90, 198, 223-224 |
| `app/api/v1/endpoints/import_notes.py` | 42 | 8 | 10 | 3 | **75%** | 79, 81, 83, 100-115, 157 |
| `app/api/v1/endpoints/products.py` | 127 | 46 | 52 | 4 | **59%** | 47, 53, 121, 198-230, 245-275, 291 |
| `app/api/v1/endpoints/reports.py` | 27 | 7 | 6 | 2 | **67%** | 42, 44, 66-78 |
| `app/api/v1/endpoints/stock_ledger.py` | 30 | 3 | 10 | 4 | **82%** | 46->48, 49, 51, 53 |
| `app/api/v1/endpoints/suppliers.py` | 74 | 16 | 30 | 10 | **69%** | 32->41, 42, 59-65, 117, 123-131, 134, 135->137, 138, 139->141, 142, 162 |
| `app/core/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/core/config.py` | 17 | 0 | 0 | 0 | **100%** | — |
| `app/core/database.py` | 21 | 0 | 4 | 2 | **92%** | 10->13, 20->27 |
| `app/core/security.py` | 29 | 3 | 2 | 1 | **87%** | 25-26, 37 |
| `app/core/seed.py` | 14 | 0 | 6 | 0 | **100%** | — |
| `app/main.py` | 57 | 19 | 6 | 0 | **60%** | 24-45, 96, 108, 131 |
| `app/models/ (Toàn bộ 8 models)` | 178 | 0 | 0 | 0 | **100%** | — |
| `app/schemas/ (Toàn bộ 9 schemas)` | 215 | 0 | 0 | 0 | **100%** | — |
| `app/services/__init__.py` | 0 | 0 | 0 | 0 | **100%** | — |
| `app/services/ai_cache.py` | 58 | 9 | 6 | 2 | **83%** | 34, 38-40, 48-49, 65-67 |
| `app/services/ai_service.py` | 336 | 89 | 94 | 23 | **70%** | 49->58, 76, 318-320, 347, 349, 351-357, 432-438, 456->462, 459-460, 479-540, 558->564, 561-562, 579-636, 662->669, 666-667, 670, 702, 712->724, 726, 737-742, 790-791, 796, 831-833, 881, 891-893, 925-938, 976, 986-988 |
| `app/services/fallback_service.py` | 90 | 18 | 28 | 9 | **75%** | 27-35, 38-46, 59-60, 78->82, 83, 110, 122-131, 159, 231 |
| `app/services/inventory_service.py` | 247 | 60 | 106 | 25 | **70%** | 37-38, 70, 80, 85, 97->exit, 100-103, 155-163, 195, 200, 223->exit, 226-229, 266-274, 297, 303, 312->310, 324-345, 366, 372, 381, 386, 437, 443, 471, 477, 519-533, 544, 594->596, 596->599, 601 |
| **TỔNG CỘNG HỆ THỐNG** | **1791** | **307** | **414** | **98** | **78% (Branch) / 83% (Stmt)** | **Statement Coverage: 83% (1.484 / 1.791 dòng lệnh được thực thi)** |

---

## 5. Kết Quả Kiểm Tra Frontend & Tĩnh Học

1. **Kiểm tra Frontend Production Build (`npm run build`)**:
   - Công cụ: Vite 5.4.21, React 18.2.0, Tailwind CSS.
   - Kết quả: **Exit Code 0** (Build thành công trong 4.36 giây, 1.557 modules).
   - Bundle Metrics:
     - `dist/index.html`: 1.47 kB (gzip: 0.82 kB).
     - `dist/assets/index-DJ3jQpl1.css`: 38.98 kB (gzip: 8.02 kB).
     - `dist/assets/index-nnZfPfVw.js`: 372.98 kB (gzip: **100.84 kB**).
   - Đánh giá: Bundle nén đạt chuẩn hiệu năng cao, tích hợp in-flight dedupe, cache 60s và cơ chế khóa đồng bộ `useRef` chống click kép.

2. **Kiểm tra Phân tích Tĩnh (Static Analysis)**:
   - **Backend (`python -m ruff check app`)**: Phát hiện 345 warnings (chủ yếu là hiện đại hóa cú pháp type annotation Python 3.9+ như `list` thay vì `List`, và unused error variables `exc`). Tuân thủ quy tắc Zero Modification: **Không chạy cờ `--fix`**.
   - **Frontend (`npx oxlint`)**: 10 warnings (các import icon hoặc biến cục bộ chưa sử dụng), **0 lỗi cú pháp (0 errors)** trên 23 tệp nguồn.
