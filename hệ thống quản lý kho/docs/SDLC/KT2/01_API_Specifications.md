# ĐẶC TẢ CHI TIẾT RESTFUL APIS (BÀI KT2)

## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

---

## 1. TỔNG QUAN HỆ THỐNG API

- **Base URL**: `http://localhost:8000/api/v1`
- **Format dữ liệu**: `JSON` (UTF-8)
- **Tổng số endpoint**: **44 endpoints** (42 endpoints API v1 + 2 endpoints root & health check)
- **Cơ chế xác thực**: JSON Web Token (JWT) thông qua HTTP Header:
  ```http
  Authorization: Bearer <access_token>
  ```
- **Thời hạn Token**: 60 phút (HS256).
- **Cơ chế Rate Limiting**: `SlidingWindowRateLimiter` áp dụng:
  - 10 requests / phút / IP cho endpoint đăng nhập (`/auth/login`).
  - 10 requests / phút / user cho các endpoint AI (`/ai/*`).
- **Phân quyền người dùng (RBAC)**:
  - `ADMIN`: Quản trị viên toàn quyền hệ thống.
  - `WAREHOUSE_KEEPER`: Thủ kho (quản lý danh mục, hàng hóa, upload ảnh, lập phiếu nhập/xuất kho, tra cứu thẻ kho).
  - `ACCOUNTANT`: Kế toán (quyền Read-Only đối soát danh mục, chứng từ, thẻ kho, báo cáo NXT và xuất Excel).

---

## 2. MA TRẬN PHÂN QUYỀN TOÀN DIỆN (RBAC MATRIX)

| Phân hệ | Endpoint | Thao tác | ADMIN | WAREHOUSE_KEEPER | ACCOUNTANT |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Auth** | `POST /auth/login` | Đăng nhập JSON | ✅ | ✅ | ✅ |
| | `POST /auth/login-form` | Đăng nhập OAuth2 Form | ✅ | ✅ | ✅ |
| | `GET /auth/me` | Lấy thông tin user | ✅ | ✅ | ✅ |
| | `POST /auth/users` | Tạo tài khoản người dùng | ✅ | ❌ (403) | ❌ (403) |
| **Categories** | `GET /categories` | Danh sách nhóm hàng | ✅ | ✅ | ✅ |
| | `POST /categories` | Thêm mới nhóm hàng | ✅ | ✅ | ❌ (403) |
| | `PUT /categories/{id}` | Cập nhật nhóm hàng | ✅ | ✅ | ❌ (403) |
| | `DELETE /categories/{id}` | Xóa nhóm hàng (nếu rỗng) | ✅ | ❌ (403) | ❌ (403) |
| **Products** | `GET /products` | Danh sách & lọc hàng hóa | ✅ | ✅ | ✅ |
| | `POST /products` | Thêm mặt hàng mới | ✅ | ✅ | ❌ (403) |
| | `GET /products/{id}` | Chi tiết mặt hàng | ✅ | ✅ | ✅ |
| | `PUT /products/{id}` | Cập nhật mặt hàng | ✅ | ✅ | ❌ (403) |
| | `DELETE /products/{id}` | Xóa / Ngừng kinh doanh | ✅ | ❌ (403) | ❌ (403) |
| | `POST /products/{id}/image` | Tải ảnh mặt hàng lên | ✅ | ✅ | ❌ (403) |
| **Suppliers** | `GET /suppliers` | Danh sách nhà cung cấp | ✅ | ✅ | ✅ |
| | `POST /suppliers` | Thêm nhà cung cấp mới | ✅ | ✅ | ❌ (403) |
| | `PUT /suppliers/{id}` | Cập nhật nhà cung cấp | ✅ | ✅ | ❌ (403) |
| | `DELETE /suppliers/{id}` | Xóa / Ngừng hợp tác NCC | ✅ | ❌ (403) | ❌ (403) |
| **Import** | `GET /import-notes` | Danh sách phiếu nhập | ✅ | ✅ | ✅ |
| | `POST /import-notes` | Lập phiếu nhập kho (ACID) | ✅ | ✅ | ❌ (403) |
| | `GET /import-notes/{id}` | Chi tiết phiếu nhập | ✅ | ✅ | ✅ |
| | `POST /import-notes/{id}/cancel` | Hủy phiếu nhập (Guard-check) | ✅ | ✅ | ❌ (403) |
| **Export** | `GET /export-notes` | Danh sách phiếu xuất | ✅ | ✅ | ✅ |
| | `POST /export-notes` | Tạo phiếu xuất (CONFIRMED) | ✅ | ✅ | ❌ (403) |
| | `GET /export-notes/{id}` | Chi tiết phiếu xuất | ✅ | ✅ | ✅ |
| | `PUT /export-notes/{id}/status` | Chuyển trạng thái xuất kho | ✅ | ✅ | ❌ (403) |
| | `DELETE /export-notes/{id}` | Xóa phiếu xuất CONFIRMED | ✅ | ✅ | ❌ (403) |
| **Stock Ledger**| `GET /stock-ledger` | Tra cứu lịch sử thẻ kho | ✅ | ✅ | ✅ |
| | `POST /stock-ledger/adjust` | Điều chỉnh kiểm kê thực tế | ✅ | ✅ | ❌ (403) |
| **Reports** | `GET /reports/inventory-summary` | Báo cáo Nhập-Xuất-Tồn | ✅ | ✅ | ✅ |
| | `GET /reports/stock-ledger-excel/{product_id}` | Xuất Thẻ kho Excel | ✅ | ✅ | ✅ |
| | `GET /reports/inventory-summary-excel` | Xuất Báo cáo NXT Excel | ✅ | ✅ | ✅ |
| **AI Copilot** | `POST /ai/monthly-report` | AI Báo cáo NXT tháng | ✅ | ✅ | ✅ |
| | `POST /ai/restock-suggestions` | AI Gợi ý nhập hàng tối ưu | ✅ | ✅ | ✅ |
| | `POST /ai/anomalies` | AI Phát hiện biến động lạ | ✅ | ✅ | ✅ |
| | `POST /ai/ask` | AI Trợ lý hỏi đáp SmartKho | ✅ | ✅ | ✅ |
| | `POST /ai/generate-order` | AI Sinh đơn hàng xuất kho | ✅ | ✅ | ✅ |

---

## 3. CHI TIẾT CÁC ENDPOINTS

### 3.1. Phân hệ Xác thực (`/auth`)

- `POST /auth/login`: Nhận JSON `{username, password}`, trả về JWT token và thông tin profile. Giới hạn 10 lần/phút/IP.
- `POST /auth/login-form`: Nhận form urlencoded tương thích chuẩn OAuth2 password request của Swagger UI.
- `GET /auth/me`: Trả về thông tin người dùng hiện tại từ Bearer token.
- `POST /auth/users`: Tạo người dùng mới trong hệ thống (Chỉ dành cho ADMIN).

### 3.2. Phân hệ Nhóm hàng (`/categories`)

- `GET /categories`: Lấy danh sách nhóm hàng, hỗ trợ `search`, `skip`, `limit`.
- `POST /categories`: Thêm mới nhóm hàng (`code`, `name`, `description`).
- `PUT /categories/{id}`: Cập nhật thông tin nhóm hàng.
- `DELETE /categories/{id}`: Xóa nhóm hàng. Chặn xóa nếu đang có sản phẩm thuộc nhóm (HTTP 400).

### 3.3. Phân hệ Hàng hóa (`/products`)

- `GET /products`: Danh sách hàng hóa, lọc theo `search`, `category_id`, `is_low_stock` (boolean tính toán), `status`, `skip`, `limit`.
- `POST /products`: Tạo mặt hàng mới (`code`, `name`, `category_id`, `unit`, `min_stock`, `current_stock`, `standard_price`). Nếu có khai báo `current_stock > 0`, hệ thống tự động tạo một phiếu nhập ban đầu.
- `GET /products/{id}`: Chi tiết mặt hàng.
- `PUT /products/{id}`: Cập nhật thông tin mặt hàng. Không cho phép sửa trực tiếp `current_stock`.
- `DELETE /products/{id}`: Xóa mặt hàng nếu chưa có phát sinh giao dịch, hoặc chuyển sang `DISCONTINUED` nếu đã có chứng từ.
- `POST /products/{id}/image`: Tải file ảnh đại diện sản phẩm (`.jpg`, `.png`, `.webp`), lưu tại thư mục `uploads/` và cập nhật trường `image_url`.

### 3.4. Phân hệ Nhà cung cấp (`/suppliers`)

- `GET /suppliers`: Lấy danh sách nhà cung cấp, hỗ trợ `search`, `is_active`.
- `POST /suppliers`: Thêm mới đối tác cung ứng.
- `PUT /suppliers/{id}`: Cập nhật thông tin đối tác.
- `DELETE /suppliers/{id}`: Chuyển `is_active = false` nếu đã có phiếu nhập, hoặc xóa khỏi CSDL nếu chưa phát sinh chứng từ.

### 3.5. Phân hệ Phiếu Nhập Kho (`/import-notes`)

- `GET /import-notes`: Danh sách phiếu nhập, hỗ trợ lọc theo ngày, nhà cung cấp `supplier_id`, trạng thái.
- `POST /import-notes`: Lập phiếu nhập kho đa dòng kèm `idempotency_key`. Tự động tăng tồn kho `current_stock` và ghi bản ghi `stock_ledger` (loại `IMPORT`) trong một Transaction ACID duy nhất.
- `GET /import-notes/{id}`: Xem chi tiết phiếu nhập và các dòng hàng.
- `POST /import-notes/{id}/cancel`: Hủy phiếu nhập kho với Guard-check chống tồn kho âm. Nếu hàng đã xuất khiến tồn hiện tại nhỏ hơn số lượng hủy $\rightarrow$ Từ chối hủy (HTTP 400).

### 3.6. Phân hệ Phiếu Xuất Kho (`/export-notes`)

- `GET /export-notes`: Danh sách phiếu xuất kèm trạng thái và khách hàng.
- `POST /export-notes`: Lập phiếu xuất mới với trạng thái ban đầu là `CONFIRMED` (Chờ xuất). Hỗ trợ `idempotency_key`. **Chưa trừ tồn kho vật lý**.
- `GET /export-notes/{id}`: Chi tiết phiếu xuất.
- `PUT /export-notes/{id}/status`: Chuyển dịch trạng thái phiếu xuất:
  - Chuyển sang `SHIPPING`: Thực hiện trừ tồn kho nguyên tử bằng Atomic SQL `RETURNING current_stock`. Nếu không đủ hàng $\rightarrow$ Rollback và trả HTTP 400. Ghi nhận Thẻ kho `stock_ledger` (loại `EXPORT`).
  - Chuyển sang `COMPLETED`: Giao hàng thành công.
  - Chuyển sang `CANCELLED`: Nếu hủy từ `SHIPPING`, hoàn lại tồn kho và ghi thẻ kho hoàn trả.
- `DELETE /export-notes/{id}`: Xóa phiếu xuất khỏi hệ thống. **Chỉ cho phép xóa khi phiếu đang ở trạng thái `CONFIRMED`** (chưa xuất kho).

### 3.7. Phân hệ Thẻ Kho & Kiểm kê (`/stock-ledger`)

- `GET /stock-ledger`: Tra cứu dòng thời gian biến động thẻ kho theo `product_id`, khoảng thời gian `from_date` / `to_date`, và loại giao dịch (`IMPORT`, `EXPORT`, `ADJUSTMENT`). Bảng trả về chỉ hiển thị số lượng thay đổi và số tồn sau giao dịch `balance_after` (không hiển thị đơn giá).
- `POST /stock-ledger/adjust`: Lập phiếu điều chỉnh kiểm kê thực tế (`actual_stock`, `reason`), cân bằng số lượng tồn tức thời và ghi thẻ kho loại `ADJUSTMENT`.

### 3.8. Phân hệ Báo cáo Kho (`/reports`)

- `GET /reports/inventory-summary`: Tính toán bảng cân đối Nhập - Xuất - Tồn theo công thức chuẩn kế toán (`Tồn cuối = Tồn đầu + Nhập - Xuất`).
- `GET /reports/stock-ledger-excel/{product_id}`: Xuất toàn bộ lịch sử Thẻ kho của sản phẩm ra file Excel (`.xlsx`).
- `GET /reports/inventory-summary-excel`: Xuất Báo cáo Nhập - Xuất - Tồn theo kỳ ra file Excel (`.xlsx`).

### 3.9. Phân hệ Trợ lý AI (`/ai`)

- `POST /ai/monthly-report`: Gọi Gemini 3.5 Flash Lite sinh báo cáo nhận xét tình hình luân chuyển kho tháng. Hỗ trợ Heuristic Fallback khi offline.
- `POST /ai/restock-suggestions`: Phân tích vận tốc bán 30 ngày và đưa ra gợi ý số lượng đặt hàng tối ưu kèm lý do.
- `POST /ai/anomalies`: Phát hiện biến động bất thường (xuất tăng $>200\%$ hoặc tồn ứ đọng $>30$ ngày).
- `POST /ai/ask`: Chat hỏi đáp tự do với trợ lý SmartKho Copilot về trạng thái hàng hóa và kho hàng.
- `POST /ai/generate-order`: Tự động soạn thảo đơn hàng xuất kho theo yêu cầu bằng ngôn ngữ tự nhiên.

---

## 4. LỊCH SỬ ĐỒNG BỘ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Mở rộng toàn diện đặc tả API:** Bổ sung đầy đủ 44 endpoints (trước đây tài liệu chỉ mới ghi nhận 4 modules cơ bản).
  - **Bổ sung Phân hệ Nhập / Xuất / Thẻ kho / Báo cáo / AI:** Đặc tả chi tiết các tham số request, response và quy tắc bảo vệ dữ liệu.
  - **Bổ sung nghiệp vụ xuất kho 3 bước:** Đặc tả endpoint chuyển trạng thái `PUT /export-notes/{id}/status` và quyền xóa phiếu `DELETE /export-notes/{id}` khi ở trạng thái `CONFIRMED`.
  - **Bổ sung xuất file Excel:** Thêm 2 endpoints xuất báo cáo Excel cho Thẻ kho và Báo cáo Nhập-Xuất-Tồn.
  - **Bổ sung Rate Limiter:** Ghi nhận cơ chế chống brute-force đăng nhập và spam gọi AI qua `SlidingWindowRateLimiter`.
