# BẰNG CHỨNG D2 & D3: SMOKE TEST VÀ SO SÁNH HỢP ĐỒNG API (HEAD VS dd5be3f)

## 1. Kết Quả Smoke Test và Đối Chiếu Hợp Đồng API

| Endpoint | Method | HEAD Status | dd5be3f Status | HEAD Keys | dd5be3f Keys | Status Match | Keys Match | 500 Error |
|---|---|---|---|---|---|---|---|---|
| /api/v1/auth/me | GET | 200 | 200 | created_at, full_name, id, is_active, role... | created_at, full_name, id, is_active, role... | DUNG | DUNG | KHONG |
| /api/v1/categories/ | GET | 200 | 200 | code, description, id, name | code, description, id, name | DUNG | DUNG | KHONG |
| /api/v1/categories/ | POST | 201 | 201 | code, description, id, name | code, description, id, name | DUNG | DUNG | KHONG |
| /api/v1/products/ | GET | 200 | 200 | category, category_id, category_name, code, created_at... | category, category_id, category_name, code, created_at... | DUNG | KHAC (Mở rộng) | KHONG |
| /api/v1/products/1 | GET | 200 | 200 | category, category_id, category_name, code, created_at... | category, category_id, category_name, code, created_at... | DUNG | KHAC (Mở rộng) | KHONG |
| /api/v1/suppliers/ | GET | 200 | 200 | address, code, email, id, is_active... | address, code, email, id, is_active... | DUNG | DUNG | KHONG |
| /api/v1/suppliers/1 | GET | 200 | 200 | address, code, email, id, is_active... | address, code, email, id, is_active... | DUNG | DUNG | KHONG |
| /api/v1/import-notes/ | GET | 200 | 200 | code, created_by, creator_name, details, id... | code, created_by, creator_name, details, id... | DUNG | DUNG | KHONG |
| /api/v1/import-notes/1 | GET | 200 | 200 | code, created_by, creator_name, details, id... | code, created_by, creator_name, details, id... | DUNG | DUNG | KHONG |
| /api/v1/export-notes/ | GET | 200 | 200 | code, created_by, creator_name, details, id... | code, created_by, creator_name, details, id... | DUNG | DUNG | KHONG |
| /api/v1/export-notes/1 | GET | 200 | 200 | code, created_by, creator_name, details, id... | code, created_by, creator_name, details, id... | DUNG | DUNG | KHONG |
| /api/v1/stock-ledger/ | GET | 200 | 200 | balance_after, balance_before, created_by, creator_name, id... | balance_after, created_by, creator_name, id, note... | DUNG | KHAC (Thêm balance_before) | KHONG |
| /api/v1/reports/kpi-summary | GET | 200 | 404 | low_stock_count, total_export_notes, total_import_notes, total_products, total_stock | detail, error_code, success | KHAC (Endpoint mới) | KHAC | KHONG |
| /api/v1/reports/low-stock | GET | 200 | 200 | category, category_id, category_name, code, created_at... | category, category_id, category_name, code, created_at... | DUNG | KHAC (Mở rộng) | KHONG |
| /api/v1/reports/inventory-summary | GET | 200 | 200 | from_date, items, to_date, total_adjustment, total_closing... | from_date, items, to_date, total_adjustment, total_closing... | DUNG | DUNG | KHONG |
| /api/v1/reports/write-metrics | GET | 200 | 404 | avg_retry_sleep_ms, enabled, max_concurrent_writes, max_waiting_threads, retry_count... | detail, error_code, success | KHAC (Endpoint mới) | KHAC | KHONG |
| /api/v1/reports/write-gate | GET | 200 | 404 | concurrency_limit, current_in_flight, enabled, max_queue_size, timeout_seconds... | detail, error_code, success | KHAC (Endpoint mới) | KHAC | KHONG |
| /api/v1/ai/monthly-report | GET | 200 | 200 | cached_at, end_date, executive_summary, is_cached, is_fallback... | cached_at, end_date, executive_summary, is_cached, is_fallback... | DUNG | DUNG | KHONG |
| /api/v1/ai/restock-suggestions | GET | 200 | 200 | cached_at, end_date, executive_summary, is_cached, is_fallback... | cached_at, end_date, executive_summary, is_cached, is_fallback... | DUNG | DUNG | KHONG |
| /api/v1/products/ (POST) | POST | 201 | 201 | category_name, code, current_stock, id, name... | category_name, code, current_stock, id, name... | DUNG | DUNG | KHONG |
| /api/v1/import-notes/ (POST) | POST | 201 | 201 | code, created_by, details, id, status... | code, created_by, details, id, status... | DUNG | DUNG | KHONG |
| /api/v1/export-notes/ (POST) | POST | 201 | 201 | code, created_by, details, id, status... | code, created_by, details, id, status... | DUNG | DUNG | KHONG |
| /api/v1/stock-ledger/adjust (POST)| POST | 200 | 200 | balance_after, balance_before, change_amount, id... | balance_after, change_amount, id... | DUNG | KHAC (Thêm balance_before) | KHONG |

## 2. Tổng Kết
- Số lỗi HTTP 500: **0 lỗi** trên Server HEAD.
- Hợp đồng API cũ (`dd5be3f`) được bảo toàn 100% về tính tương thích ngược: toàn bộ các trường JSON cũ đều được giữ nguyên; các trường mới (`balance_before`, `standard_price`, `initial_supplier_id`) chỉ là mở rộng không phá vỡ client.
- 3 endpoint mới (`/reports/kpi-summary`, `/reports/write-metrics`, `/reports/write-gate`) phục vụ tính năng giám sát quản trị và kiểm toán.
