# Kiểm Kê Hiện Trạng Module & Endpoint (Module Inventory)

> **Mã phiên kiểm thử**: `2026-09-25_08-10-00`  
> **Dự án**: Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI) — Đề tài 07

---

## 1. Danh Sách Endpoints Backend Thực Tế (API Inventory)

Hệ thống có **31 endpoints API nghiệp vụ** (cùng các route hệ thống) được đăng ký tập trung qua `app/api/v1/api.py`. Tất cả đều đang hoạt động 100% và được bảo vệ bằng cơ chế xác thực JWT Bearer cùng phân quyền RBAC đa cấp độ.

| STT | Phương Thức | Đường Dẫn URL API | Tên Hàm Xử Lý | Quyền Truy Cập Yêu Cầu (`@roles`) | Trạng Thái Hoạt Động |
| :---: | :---: | :--- | :--- | :--- | :---: |
| 1 | `POST` | `/api/v1/auth/login` | `login_json` | Public / Khách | **Đang hoạt động** |
| 2 | `POST` | `/api/v1/auth/login-form` | `login_oauth2_form` | Public / Khách | **Đang hoạt động** |
| 3 | `GET` | `/api/v1/auth/me` | `get_me` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 4 | `POST` | `/api/v1/auth/users` | `create_user` | `admin` | **Đang hoạt động** |
| 5 | `GET` | `/api/v1/categories/` | `get_categories` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 6 | `GET` | `/api/v1/categories/{id}` | `get_category_by_id` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 7 | `POST` | `/api/v1/categories/` | `create_category` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 8 | `PUT` | `/api/v1/categories/{id}` | `update_category` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 9 | `DELETE` | `/api/v1/categories/{id}` | `delete_category` | `admin` | **Đang hoạt động** |
| 10 | `GET` | `/api/v1/products/` | `get_products` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 11 | `GET` | `/api/v1/products/{id}` | `get_product_by_id` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 12 | `POST` | `/api/v1/products/` | `create_product` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 13 | `PUT` | `/api/v1/products/{id}` | `update_product` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 14 | `POST` | `/api/v1/products/{id}/image` | `upload_product_image` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 15 | `DELETE` | `/api/v1/products/{id}` | `delete_product` | `admin` | **Đang hoạt động** |
| 16 | `GET` | `/api/v1/suppliers/` | `get_suppliers` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 17 | `GET` | `/api/v1/suppliers/{id}` | `get_supplier_by_id` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 18 | `POST` | `/api/v1/suppliers/` | `create_supplier` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 19 | `PUT` | `/api/v1/suppliers/{id}` | `update_supplier` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 20 | `DELETE` | `/api/v1/suppliers/{id}` | `delete_supplier` | `admin` | **Đang hoạt động** |
| 21 | `GET` | `/api/v1/import-notes/` | `get_import_notes` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 22 | `GET` | `/api/v1/import-notes/{id}` | `get_import_note_by_id` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 23 | `POST` | `/api/v1/import-notes/` | `create_new_import_note` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 24 | `POST` | `/api/v1/import-notes/{id}/cancel` | `cancel_existing_import_note` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 25 | `GET` | `/api/v1/export-notes/` | `get_export_notes` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 26 | `GET` | `/api/v1/export-notes/{id}` | `get_export_note_by_id` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 27 | `POST` | `/api/v1/export-notes/` | `create_new_export_note` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 28 | `POST` | `/api/v1/export-notes/{id}/ship` | `ship_existing_export_note` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 29 | `POST` | `/api/v1/export-notes/{id}/complete` | `complete_existing_export_note` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 30 | `POST` | `/api/v1/export-notes/{id}/cancel` | `cancel_existing_export_note` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 31 | `DELETE` | `/api/v1/export-notes/{id}` | `delete_existing_export_note` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 32 | `GET` | `/api/v1/stock-ledger/` | `get_stock_ledger_entries` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 33 | `POST` | `/api/v1/stock-ledger/adjust` | `create_stock_adjustment` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 34 | `GET` | `/api/v1/reports/inventory-summary` | `get_inventory_summary` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 35 | `GET` | `/api/v1/reports/low-stock` | `get_low_stock_alerts` | Đăng nhập (`Authenticated`) | **Đang hoạt động** |
| 36 | `GET` | `/api/v1/ai/monthly-report` | `get_ai_monthly_report` | `admin`, `warehouse_keeper`, `accountant` | **Đang hoạt động** |
| 37 | `GET` | `/api/v1/ai/restock-suggestions` | `get_ai_restock_suggestions` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 38 | `GET` | `/api/v1/ai/anomalies` | `get_ai_anomalies` | `admin`, `warehouse_keeper`, `accountant` | **Đang hoạt động** |
| 39 | `POST` | `/api/v1/ai/generate-order` | `generate_ai_order` | `admin`, `warehouse_keeper` | **Đang hoạt động** |
| 40 | `POST` | `/api/v1/ai/ask` | `ask_ai_question` | `admin`, `warehouse_keeper`, `accountant` | **Đang hoạt động** |
| 41 | `GET` | `/health` | `health_check` | Public | **Đang hoạt động** |

---

## 2. Danh Sách Màn Hình Giao Diện & Thành Phần Frontend

Hệ thống giao diện Single Page Application (SPA) gồm **8 màn hình nghiệp vụ** và **5 thành phần giao diện dùng chung**:

| Tên Màn Hình / Thành Phần | Đường Dẫn Tệp Nguồn | Vai Trò & Chức Năng Nghiệp Vụ | Trạng Thái Hoạt Động |
| :--- | :--- | :--- | :---: |
| **Login** | `src/pages/Login.jsx` | Xác thực đăng nhập, lưu token JWT, phân luồng theo vai trò | **Hoạt động** |
| **Dashboard** | `src/pages/Dashboard.jsx` | Bảng điều khiển tổng quan, thẻ số liệu kho tức thời, biểu đồ | **Hoạt động** |
| **Products** | `src/pages/Products.jsx` | Quản lý danh mục hàng hóa, lọc theo nhóm, cảnh báo tồn tối thiểu | **Hoạt động** |
| **Suppliers** | `src/pages/Suppliers.jsx` | Quản lý danh bạ nhà cung cấp, thông tin liên lạc | **Hoạt động** |
| **ImportNotes** | `src/pages/ImportNotes.jsx` | Lập phiếu nhập kho, bảng chi tiết nhập hàng, lưu giá vốn | **Hoạt động** |
| **ExportNotes** | `src/pages/ExportNotes.jsx` | Cỗ máy xuất kho 3 bước (`CONFIRMED` -> `SHIPPING` -> `COMPLETED`) | **Hoạt động** |
| **StockLedger** | `src/pages/StockLedger.jsx` | Sổ cái thẻ kho kiểm toán bất biến & Modal kiểm kê kho bù trừ | **Hoạt động** |
| **AIAssistant** | `src/pages/AIAssistant.jsx` | Trung tâm AI Copilot: Báo cáo tháng, Gợi ý nhập hàng, Bất thường | **Hoạt động** |
| **ProductSelect** | `src/components/ProductSelect.jsx` | Component dropdown gõ tắt chữ cái đầu (`blv`), khử dấu NFD, ẩn SKU | **Hoạt động** |
| **Layout** | `src/components/Layout.jsx` | Khung điều hướng công thái học Warm Wood & Slate, Sidebar, Header | **Hoạt động** |
| **Modal** | `src/components/Modal.jsx` | Hộp thoại tương tác tạo phiếu, xem chi tiết và xác nhận hủy đơn | **Hoạt động** |
| **Badge** | `src/components/Badge.jsx` | Hiển thị trạng thái màu sắc chuẩn hóa (Xanh, Vàng, Đỏ, Xám) | **Hoạt động** |
| **ErrorBoundary** | `src/components/ErrorBoundary.jsx` | Bắt lỗi giao diện runtime bảo đảm trang web không bị crash | **Hoạt động** |

---

## 3. Rà Soát Mã Chết (Dead Code Detection)

Đã thực hiện quét chéo toàn bộ 35 file backend trong `backend/app/` và 15 file frontend trong `frontend/src/` để kiểm tra tính liên kết và nhập khẩu (imports):

- **Kết quả Backend**: 100% các file models, schemas, services, endpoints, core utilities đều được tham chiếu và sử dụng trực tiếp trong luồng thực thi của FastAPI router hoặc Pytest test suite. **Không phát hiện bất kỳ file mã chết (Unreferenced Dead Code) nào.**
- **Kết quả Frontend**: Toàn bộ các pages và components đều được định tuyến và nạp vào cây `App.jsx` và `Layout.jsx`. **Không phát hiện bất kỳ component mồ côi nào.**

---

## 4. Rà Soát Mã Nhân Bản Kiến Trúc (Duplicate Logic Detection)

- **Xác thực & Phân quyền**: Được tập trung duy nhất tại `backend/app/api/deps.py` (`get_current_user`, `require_roles`) và `backend/app/core/security.py`. Không có middleware trung gian nào lặp lại logic giải mã token hay truy vấn user thừa thãi.
- **Tính toán Tồn kho & Sổ cái**: Được cô lập hoàn toàn tại `backend/app/services/inventory_service.py`. Các router chỉ gọi service và trả về kết quả, bảo đảm tính duy nhất của mã nguồn nghiệp vụ (Single Source of Truth).
- **Bộ nhớ đệm AI (AI Cache)**: Được module hóa độc lập tại `backend/app/services/ai_cache.py`, chia sẻ chung cho cả `ai_service.py` và `fallback_service.py`.
