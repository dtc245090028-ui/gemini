# Kiểm Kê Hiện Trạng Module & Endpoint (Module Inventory)

> **Mã phiên kiểm thử**: `2026-10-02_10-00-00`  
> **Dự án**: Hệ thống Quản lý Kho Thông minh tích hợp Trí tuệ Nhân tạo (WMS AI) — Đề tài 07

---

## 1. Danh Sách Endpoints Backend Thực Tế (API Inventory)

Hệ thống có **31 endpoints API nghiệp vụ** (cùng các route hệ thống) được đăng ký tập trung qua `app/api/v1/api.py`. Tất cả đều đang hoạt động 100% và được bảo vệ bằng cơ chế xác thực JWT Bearer cùng phân quyền RBAC đa cấp độ.

| STT | Phương Thức | Đường Dẫn URL API | Tên Hàm Xử Lý | Quyền Yêu Cầu (`@roles`) | Ghi Chú Tính Năng Mới | Trạng Thái |
| :---: | :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | `POST` | `/api/v1/auth/login` | `login_json` | Public / Khách | Đăng nhập JWT | **Hoạt động** |
| 2 | `POST` | `/api/v1/auth/login-form` | `login_oauth2_form` | Public / Khách | Swagger UI OAuth2 | **Hoạt động** |
| 3 | `GET` | `/api/v1/auth/me` | `get_me` | Authenticated | Profile người dùng | **Hoạt động** |
| 4 | `POST` | `/api/v1/auth/users` | `create_user` | `admin` | Tạo tài khoản nội bộ | **Hoạt động** |
| 5 | `GET` | `/api/v1/categories/` | `get_categories` | Authenticated | Cache 60s phía client | **Hoạt động** |
| 6 | `GET` | `/api/v1/categories/{id}` | `get_category_by_id` | Authenticated | Chi tiết nhóm hàng | **Hoạt động** |
| 7 | `POST` | `/api/v1/categories/` | `create_category` | `admin`, `warehouse_keeper` | Auto-invalidation cache | **Hoạt động** |
| 8 | `PUT` | `/api/v1/categories/{id}` | `update_category` | `admin`, `warehouse_keeper` | Auto-invalidation cache | **Hoạt động** |
| 9 | `DELETE` | `/api/v1/categories/{id}` | `delete_category` | `admin` | Chặn xóa nếu có SP | **Hoạt động** |
| 10 | `GET` | `/api/v1/products/` | `get_products` | Authenticated | Phân trang, lọc `is_low_stock` | **Hoạt động** |
| 11 | `GET` | `/api/v1/products/{id}` | `get_product_by_id` | Authenticated | Chi tiết sản phẩm | **Hoạt động** |
| 12 | `POST` | `/api/v1/products/` | `create_product` | `admin`, `warehouse_keeper` | Hỗ trợ nhập kho ban đầu | **Hoạt động** |
| 13 | `PUT` | `/api/v1/products/{id}` | `update_product` | `admin`, `warehouse_keeper` | Cập nhật thông tin | **Hoạt động** |
| 14 | `POST` | `/api/v1/products/{id}/image` | `upload_product_image` | `admin`, `warehouse_keeper` | Tải ảnh đại diện | **Hoạt động** |
| 15 | `DELETE` | `/api/v1/products/{id}` | `delete_product` | `admin` | Ngừng kinh doanh | **Hoạt động** |
| 16 | `GET` | `/api/v1/suppliers/` | `get_suppliers` | Authenticated | Cache 60s phía client | **Hoạt động** |
| 17 | `GET` | `/api/v1/suppliers/{id}` | `get_supplier_by_id` | Authenticated | Chi tiết nhà cung cấp | **Hoạt động** |
| 18 | `POST` | `/api/v1/suppliers/` | `create_supplier` | `admin`, `warehouse_keeper` | Auto-invalidation cache | **Hoạt động** |
| 19 | `PUT` | `/api/v1/suppliers/{id}` | `update_supplier` | `admin`, `warehouse_keeper` | Auto-invalidation cache | **Hoạt động** |
| 20 | `DELETE` | `/api/v1/suppliers/{id}` | `delete_supplier` | `admin` | Ngừng hợp tác | **Hoạt động** |
| 21 | `GET` | `/api/v1/import-notes/` | `get_import_notes` | Authenticated | Lịch sử phiếu nhập | **Hoạt động** |
| 22 | `GET` | `/api/v1/import-notes/{id}` | `get_import_note_by_id` | Authenticated | Chi tiết phiếu nhập | **Hoạt động** |
| 23 | `POST` | `/api/v1/import-notes/` | `create_new_import_note` | `admin`, `warehouse_keeper` | **Hỗ trợ Header `X-Idempotency-Key`** | **Hoạt động** |
| 24 | `POST` | `/api/v1/import-notes/{id}/cancel` | `cancel_existing_import_note` | `admin`, `warehouse_keeper` | Guard-check chống âm | **Hoạt động** |
| 25 | `GET` | `/api/v1/export-notes/` | `get_export_notes` | Authenticated | Lịch sử phiếu xuất | **Hoạt động** |
| 26 | `GET` | `/api/v1/export-notes/{id}` | `get_export_note_by_id` | Authenticated | Chi tiết phiếu xuất | **Hoạt động** |
| 27 | `POST` | `/api/v1/export-notes/` | `create_new_export_note` | `admin`, `warehouse_keeper` | **Hỗ trợ Header `X-Idempotency-Key`** | **Hoạt động** |
| 28 | `POST` | `/api/v1/export-notes/{id}/ship` | `ship_existing_export_note` | `admin`, `warehouse_keeper` | Trừ tồn kho & ghi Thẻ kho | **Hoạt động** |
| 29 | `POST` | `/api/v1/export-notes/{id}/complete` | `complete_existing_export_note` | `admin`, `warehouse_keeper` | Chốt giao thành công | **Hoạt động** |
| 30 | `POST` | `/api/v1/export-notes/{id}/cancel` | `cancel_existing_export_note` | `admin`, `warehouse_keeper` | Hoàn tồn nếu đang giao | **Hoạt động** |
| 31 | `DELETE` | `/api/v1/export-notes/{id}` | `delete_existing_export_note` | `admin`, `warehouse_keeper` | Xóa sạch khi chưa giao | **Hoạt động** |
| 32 | `GET` | `/api/v1/stock-ledger/` | `get_stock_ledger_entries` | Authenticated | Sổ cái Thẻ kho bất biến | **Hoạt động** |
| 33 | `POST` | `/api/v1/stock-ledger/adjust` | `create_stock_adjustment` | `admin`, `warehouse_keeper` | Cân đối kiểm kê kho | **Hoạt động** |
| 34 | `GET` | `/api/v1/reports/inventory-summary` | `get_inventory_summary` | Authenticated | Báo cáo Nhập-Xuất-Tồn | **Hoạt động** |
| 35 | `GET` | `/api/v1/reports/low-stock` | `get_low_stock_alerts` | Authenticated | Cảnh báo dưới tồn an toàn | **Hoạt động** |
| 36 | `GET` | `/api/v1/ai/monthly-report` | `get_ai_monthly_report` | `admin`, `warehouse_keeper`, `accountant` | Báo cáo AI tháng + Cache | **Hoạt động** |
| 37 | `GET` | `/api/v1/ai/restock-suggestions` | `get_ai_restock_suggestions` | `admin`, `warehouse_keeper` | Gợi ý nhập hàng AI | **Hoạt động** |
| 38 | `GET` | `/api/v1/ai/anomalies` | `get_ai_anomalies` | `admin`, `warehouse_keeper`, `accountant` | Bất thường xuất/tồn chết | **Hoạt động** |
| 39 | `POST` | `/api/v1/ai/generate-order` | `generate_ai_order` | `admin`, `warehouse_keeper` | Tạo đơn gợi ý AI | **Hoạt động** |
| 40 | `POST` | `/api/v1/ai/ask` | `ask_ai_question` | `admin`, `warehouse_keeper`, `accountant` | Chatbot hỏi đáp kho | **Hoạt động** |
| 41 | `GET` | `/health` | `health_check` | Public | Kiểm tra dịch vụ sống | **Hoạt động** |

---

## 2. Danh Sách Màn Hình Giao Diện & Thành Phần Frontend

Hệ thống giao diện Single Page Application (SPA) gồm **8 màn hình nghiệp vụ** và **6 thành phần giao diện dùng chung**:

| Tên Màn Hình / Thành Phần | Đường Dẫn Tệp Nguồn | Vai Trò & Chức Năng Nghiệp Vụ | Cải Tiến Mới | Trạng Thái |
| :--- | :--- | :--- | :--- | :---: |
| **Login** | `src/pages/Login.jsx` | Xác thực đăng nhập, lưu token JWT, chuyển nhanh vai trò demo | Nút Demo 1-click có loading disable | **Hoạt động** |
| **Dashboard** | `src/pages/Dashboard.jsx` | Bảng điều khiển tổng quan, thẻ số liệu kho tức thời, biểu đồ | Bỏ remount tree, giữ state khi chuyển tab | **Hoạt động** |
| **Products** | `src/pages/Products.jsx` | Quản lý danh mục hàng hóa, lọc theo nhóm, cảnh báo tồn tối thiểu | Khóa `isSubmittingRef`, Debounce 300ms tìm kiếm | **Hoạt động** |
| **Suppliers** | `src/pages/Suppliers.jsx` | Quản lý danh bạ nhà cung cấp, thông tin liên lạc | Khóa `isSubmittingRef` chống click kép | **Hoạt động** |
| **ImportNotes** | `src/pages/ImportNotes.jsx` | Lập phiếu nhập kho, bảng chi tiết nhập hàng, lưu giá vốn | **Khóa `isSubmittingRef` + Header `X-Idempotency-Key`** | **Hoạt động** |
| **ExportNotes** | `src/pages/ExportNotes.jsx` | Cỗ máy xuất kho 3 bước (`CONFIRMED` -> `SHIPPING` -> `COMPLETED`) | **Khóa `isSubmittingRef` + Header `X-Idempotency-Key`** | **Hoạt động** |
| **StockLedger** | `src/pages/StockLedger.jsx` | Sổ cái thẻ kho kiểm toán bất biến & Modal kiểm kê kho bù trừ | Chống lặp truy vấn qua In-flight Dedupe | **Hoạt động** |
| **AIAssistant** | `src/pages/AIAssistant.jsx` | Trung tâm AI Copilot: Báo cáo tháng, Gợi ý nhập hàng, Bất thường | Debounce, caching ngầm, không lặp request | **Hoạt động** |
| **ProductSelect** | `src/components/ProductSelect.jsx` | Component dropdown gõ tắt chữ cái đầu (`blv`), khử dấu NFD, ẩn SKU | Dùng dữ liệu cache từ API client | **Hoạt động** |
| **Layout** | `src/components/Layout.jsx` | Khung điều hướng công thái học Warm Wood & Slate, Sidebar, Header | Khóa chuyển tab khi đang pending request | **Hoạt động** |
| **Modal** | `src/components/Modal.jsx` | Hộp thoại tương tác tạo phiếu, xem chi tiết và xác nhận hủy đơn | Chuẩn hóa onClose và reset submit ref | **Hoạt động** |
| **Badge** | `src/components/Badge.jsx` | Hiển thị trạng thái màu sắc chuẩn hóa (Xanh, Vàng, Đỏ, Xám) | Chuẩn hóa giao diện trực quan | **Hoạt động** |
| **Loader** | `src/components/Loader.jsx` | Hiệu ứng tải động thân thiện Warm Wood | Tích hợp vào table và button loading | **Hoạt động** |
| **ErrorBoundary** | `src/components/ErrorBoundary.jsx` | Bắt lỗi giao diện runtime bảo đảm trang web không bị crash | Bảo vệ toàn diện cây DOM React | **Hoạt động** |

---

## 3. Rà Soát Mã Chết (Dead Code Detection)

Đã thực hiện quét chéo toàn bộ các tệp nguồn trong `backend/app/` và `frontend/src/`:

- **Kết quả Backend**: 100% các file models, schemas, services, endpoints, core utilities đều được tham chiếu và sử dụng trực tiếp trong luồng thực thi của FastAPI router hoặc Pytest test suite. **Không phát hiện bất kỳ file mã chết (Unreferenced Dead Code) nào.**
- **Kết quả Frontend**: Toàn bộ các pages và components đều được định tuyến và nạp vào cây `App.jsx` và `Layout.jsx`. **Không phát hiện bất kỳ component mồ côi nào.**

---

## 4. Rà Soát Mã Nhân Bản Kiến Trúc (Duplicate Logic Detection)

- **Xác thực & Phân quyền**: Được tập trung duy nhất tại `backend/app/api/deps.py` (`get_current_user`, `require_roles`) và `backend/app/core/security.py`.
- **Tính toán Tồn kho & Sổ cái**: Được cô lập hoàn toàn tại `backend/app/services/inventory_service.py` (Single Source of Truth).
- **Bộ nhớ đệm API Client**: Tập trung toàn bộ logic Cache TTL 60s và In-flight Deduplication tại `frontend/src/api/client.js`, các page không cần tự viết cache riêng.
- **Cơ chế Idempotency**: Quản lý tập trung trong transaction ACID tại `inventory_service.py`, không viết tản mát ở tầng endpoint.
