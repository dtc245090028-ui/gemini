# BẢN KIỂM KÊ MODULE & ENDPOINTS THỰC TẾ (MODULE INVENTORY)

> **Mã phiên kiểm thử:** `2026-09-23_20-05-00`  
> **Dự án:** Hệ thống Quản lý Kho Thông minh tích hợp AI (Đề tài 07)  
> **Phương pháp kiểm kê:** Quét mã nguồn tĩnh thực tế (Static Code Audit) tại `backend/app/` và `frontend/src/`.  
> **Nguyên tắc:** Chỉ ghi nhận hiện trạng thực tế, không đánh giá đúng/sai theo tài liệu.

---

## 1. Kiểm Kê Endpoints Backend (RESTful APIs)

### 1.1. Module Hệ Thống (`app/main.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/` | Công khai (Public) | None | `dict` (Thông tin dự án) |
| `GET` | `/health` | Công khai (Public) | None | `dict` (Trạng thái healthy) |

---

### 1.2. Module Xác Thực & Tài Khoản (`app/api/v1/endpoints/auth.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `POST` | `/api/v1/auth/login` | Công khai (Public) | `LoginRequest` | `TokenResponse` |
| `GET` | `/api/v1/auth/me` | Người dùng đã đăng nhập | None | `UserResponse` |
| `POST` | `/api/v1/auth/users` | `ADMIN` | `UserCreate` | `UserResponse` |
| `GET` | `/api/v1/auth/users` | `ADMIN` | Query: `skip`, `limit` | `List[UserResponse]` |

---

### 1.3. Module Nhóm Hàng Hóa (`app/api/v1/endpoints/categories.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/categories/` & `/api/v1/categories` | Người dùng đã đăng nhập | Query: `search`, `skip`, `limit` | `List[CategoryResponse]` |
| `GET` | `/api/v1/categories/{category_id}` | Người dùng đã đăng nhập | Path: `category_id: int` | `CategoryResponse` |
| `POST` | `/api/v1/categories/` & `/api/v1/categories` | `ADMIN`, `WAREHOUSE_KEEPER` | `CategoryCreate` | `CategoryResponse` |
| `PUT` | `/api/v1/categories/{category_id}` | `ADMIN`, `WAREHOUSE_KEEPER` | `CategoryUpdate` | `CategoryResponse` |
| `DELETE` | `/api/v1/categories/{category_id}` | `ADMIN` | Path: `category_id: int` | `dict` (thông báo xóa) |

---

### 1.4. Module Hàng Hóa & Tồn Kho (`app/api/v1/endpoints/products.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/products/` & `/api/v1/products` | Người dùng đã đăng nhập | Query: `search`, `category_id`, `is_low_stock`, `status`, `skip`, `limit` | `List[ProductResponse]` |
| `GET` | `/api/v1/products/{product_id}` | Người dùng đã đăng nhập | Path: `product_id: int` | `ProductResponse` |
| `POST` | `/api/v1/products/` & `/api/v1/products` | `ADMIN`, `WAREHOUSE_KEEPER` | `ProductCreate` | `ProductResponse` |
| `PUT` | `/api/v1/products/{product_id}` | `ADMIN`, `WAREHOUSE_KEEPER` | `ProductUpdate` | `ProductResponse` |
| `DELETE` | `/api/v1/products/{product_id}` | `ADMIN` | Path: `product_id: int` | `dict` (thông báo ngưng kinh doanh) |

---

### 1.5. Module Nhà Cung Cấp (`app/api/v1/endpoints/suppliers.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/suppliers/` & `/api/v1/suppliers` | Người dùng đã đăng nhập | Query: `search`, `is_active`, `skip`, `limit` | `List[SupplierResponse]` |
| `GET` | `/api/v1/suppliers/{supplier_id}` | Người dùng đã đăng nhập | Path: `supplier_id: int` | `SupplierResponse` |
| `POST` | `/api/v1/suppliers/` & `/api/v1/suppliers` | `ADMIN`, `WAREHOUSE_KEEPER` | `SupplierCreate` | `SupplierResponse` |
| `PUT` | `/api/v1/suppliers/{supplier_id}` | `ADMIN`, `WAREHOUSE_KEEPER` | `SupplierUpdate` | `SupplierResponse` |
| `DELETE` | `/api/v1/suppliers/{supplier_id}` | `ADMIN` | Path: `supplier_id: int` | `dict` (ngừng hợp tác) |

---

### 1.6. Module Phiếu Nhập Kho (`app/api/v1/endpoints/import_notes.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/import-notes/` & `/api/v1/import-notes` | Người dùng đã đăng nhập | Query: `search`, `supplier_id`, `status`, `skip`, `limit` | `List[ImportNoteResponse]` |
| `GET` | `/api/v1/import-notes/{import_note_id}` | Người dùng đã đăng nhập | Path: `import_note_id: int` | `ImportNoteResponse` |
| `POST` | `/api/v1/import-notes/` & `/api/v1/import-notes` | `ADMIN`, `WAREHOUSE_KEEPER` | `ImportNoteCreate` | `ImportNoteResponse` |
| `POST` | `/api/v1/import-notes/{import_note_id}/cancel` | `ADMIN`, `WAREHOUSE_KEEPER` | Path: `import_note_id: int` | `ImportNoteResponse` |

---

### 1.7. Module Phiếu Xuất Kho (`app/api/v1/endpoints/export_notes.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/export-notes/` & `/api/v1/export-notes` | Người dùng đã đăng nhập | Query: `search`, `status`, `skip`, `limit` | `List[ExportNoteResponse]` |
| `GET` | `/api/v1/export-notes/{export_note_id}` | Người dùng đã đăng nhập | Path: `export_note_id: int` | `ExportNoteResponse` |
| `POST` | `/api/v1/export-notes/` & `/api/v1/export-notes` | `ADMIN`, `WAREHOUSE_KEEPER` | `ExportNoteCreate` | `ExportNoteResponse` |
| `POST` | `/api/v1/export-notes/{export_note_id}/cancel` | `ADMIN`, `WAREHOUSE_KEEPER` | Path: `export_note_id: int` | `ExportNoteResponse` |

---

### 1.8. Module Thẻ Kho & Kiểm Kê (`app/api/v1/endpoints/stock_ledger.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/stock-ledger/` & `/api/v1/stock-ledger` | Người dùng đã đăng nhập | Query: `product_id`, `transaction_type`, `from_date`, `to_date`, `skip`, `limit` | `List[StockLedgerResponse]` |
| `POST` | `/api/v1/stock-ledger/adjust` | `ADMIN`, `WAREHOUSE_KEEPER` | `StockAdjustmentRequest` | `StockLedgerResponse` |

---

### 1.9. Module Báo Cáo Nhập - Xuất - Tồn (`app/api/v1/endpoints/reports.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/reports/inventory-summary` | Người dùng đã đăng nhập | Query: `from_date`, `to_date` | `InventorySummaryReportResponse` |

---

### 1.10. Module Trợ Lý AI (`app/api/v1/endpoints/ai.py`)

| Phương thức | Đường dẫn URL | Yêu cầu xác thực / Phân quyền | Schema đầu vào | Schema đầu ra |
| :---: | --- | :---: | :---: | :---: |
| `GET` | `/api/v1/ai/monthly-report` | Người dùng đã đăng nhập | Query: `month: int`, `year: int` | `MonthlyReportResponse` |
| `GET` | `/api/v1/ai/restock-suggestions` | Người dùng đã đăng nhập | Query: `lookback_days: int` (1..180) | `RestockSuggestionResponse` |
| `GET` | `/api/v1/ai/anomalies` | Người dùng đã đăng nhập | Query: `lookback_days: int` (1..180) | `AnomalyReportResponse` |

---

## 2. Kiểm Kê Bảng Dữ Liệu & Models (`app/models/`)

Hệ thống quản lý 9 bảng dữ liệu quan hệ với ràng buộc ACID và khoá ngoại SQLite Foreign Keys:

| Tên Model Python | Tên Bảng CSDL | Khoá chính | Các trường khoá ngoại (FK) | Ràng buộc toàn vẹn đặc thù |
| --- | --- | --- | --- | --- |
| `User` | `users` | `id` | Không có | `username` UNIQUE; Role: `ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT` |
| `Category` | `categories` | `id` | Không có | `code` UNIQUE |
| `Product` | `products` | `id` | `category_id -> categories.id` | `code` UNIQUE; `CheckConstraint('current_stock >= 0')` |
| `Supplier` | `suppliers` | `id` | Không có | `code` UNIQUE |
| `ImportNote` | `import_notes` | `id` | `supplier_id -> suppliers.id`, `created_by -> users.id` | `code` UNIQUE |
| `ImportNoteDetail` | `import_note_details` | `id` | `import_note_id -> import_notes.id`, `product_id -> products.id` | `quantity > 0`, `unit_price >= 0` |
| `ExportNote` | `export_notes` | `id` | `created_by -> users.id` | `code` UNIQUE |
| `ExportNoteDetail` | `export_note_details` | `id` | `export_note_id -> export_notes.id`, `product_id -> products.id` | `quantity > 0` |
| `StockLedger` | `stock_ledger` | `id` | `product_id -> products.id`, `created_by -> users.id` | `transaction_type`: `IMPORT`, `EXPORT`, `ADJUSTMENT` |

---

## 3. Kiểm Kê Phía Frontend Web (`frontend/src/`)

- **Context & Client:**
  - `context/AuthContext.jsx`: Quản lý JWT token, lưu `localStorage`, cung cấp hàm `switchDemoRole` hỗ trợ chuyển đổi 1-click giữa `ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT`.
  - `api/client.js`: Axios instance tập trung kết nối 9 cụm dịch vụ Backend, interceptor tự động bắt lỗi 401.
- **Components Dùng Chung:**
  - `components/Layout.jsx`: Khung điều hướng Sidebar + Header hiển thị vai trò và bộ chuyển đổi vai trò Demo.
  - `components/Badge.jsx`: Huy hiệu trạng thái nhiều biến thể màu sắc.
  - `components/Modal.jsx`: Hộp thoại tương tác hỗ trợ phím Escape.
- **7 Trang Nghiệp Vụ (Pages):**
  - `pages/Login.jsx`: Đăng nhập tiêu chuẩn + 3 nút 1-click tài khoản mẫu.
  - `pages/Dashboard.jsx`: KPIs tồn kho, bảng cảnh báo hàng sắp hết, thao tác nhanh.
  - `pages/Products.jsx`: CRUD sản phẩm, tìm kiếm tức thì, lọc danh mục & `is_low_stock`, chuyển nhanh sang Thẻ kho.
  - `pages/Suppliers.jsx`: Quản lý thông tin nhà cung cấp.
  - `pages/ImportNotes.jsx`: Lập phiếu nhập đa dòng, tra giá tự động, hủy phiếu hoàn trừ tồn.
  - `pages/ExportNotes.jsx`: Lập phiếu xuất với Defensive UI kiểm tra tồn kho realtime, khóa nút submit khi xuất vượt tồn, hủy phiếu hoàn kho.
  - `pages/StockLedger.jsx`: Sổ cái thẻ kho chi tiết, lọc giao dịch, modal điều chỉnh kiểm kê thực tế.
  - `pages/AIAssistant.jsx`: 3 bài toán AI kết nối API Backend (`monthly-report`, `restock-suggestions`, `anomalies`).
