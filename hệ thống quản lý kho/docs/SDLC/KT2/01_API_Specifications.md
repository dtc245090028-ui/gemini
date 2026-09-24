# ĐẶC TẢ CHI TIẾT RESTFUL APIS (BÀI KT2)

## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

---

## 1. TỔNG QUAN HỆ THỐNG API

- **Base URL**: `http://localhost:8000/api/v1`
- **Format dữ liệu**: `JSON` (UTF-8)
- **Cơ chế xác thực**: JSON Web Token (JWT) thông qua HTTP Header:

  ```http
  Authorization: Bearer <access_token>
  ```

- **Thời hạn Token**: 60 phút (HS256).
- **Phân quyền người dùng (RBAC)**:
  - `ADMIN`: Quản trị viên toàn quyền hệ thống.
  - `WAREHOUSE_KEEPER`: Thủ kho (tạo/sửa danh mục, hàng hóa, nhập/xuất kho).
  - `ACCOUNTANT`: Kế toán (chỉ đọc master data, tra cứu báo cáo, kiểm tra thẻ kho).

---

## 2. MA TRẬN PHÂN QUYỀN (RBAC MATRIX)

| Endpoint | Thao tác | ADMIN | WAREHOUSE_KEEPER | ACCOUNTANT |
| --- | --- | :---: | :---: | :---: |
| `POST /auth/login` | Đăng nhập hệ thống | ✅ | ✅ | ✅ |
| `GET /auth/me` | Xem thông tin tài khoản | ✅ | ✅ | ✅ |
| `POST /auth/users` | Tạo người dùng mới | ✅ | ❌ (403) | ❌ (403) |
| `GET /categories` | Xem danh sách nhóm hàng | ✅ | ✅ | ✅ |
| `POST /categories` | Thêm mới nhóm hàng | ✅ | ✅ | ❌ (403) |
| `PUT /categories/{id}` | Cập nhật nhóm hàng | ✅ | ✅ | ❌ (403) |
| `DELETE /categories/{id}` | Xóa nhóm hàng | ✅ | ❌ (403) | ❌ (403) |
| `GET /products` | Xem & lọc danh sách hàng hóa | ✅ | ✅ | ✅ |
| `POST /products` | Thêm mặt hàng mới | ✅ | ✅ | ❌ (403) |
| `PUT /products/{id}` | Cập nhật hàng hóa | ✅ | ✅ | ❌ (403) |
| `DELETE /products/{id}` | Xóa / Ngừng kinh doanh hàng | ✅ | ❌ (403) | ❌ (403) |
| `GET /suppliers` | Xem danh sách nhà cung cấp | ✅ | ✅ | ✅ |
| `POST /suppliers` | Thêm mới nhà cung cấp | ✅ | ✅ | ❌ (403) |
| `PUT /suppliers/{id}` | Cập nhật nhà cung cấp | ✅ | ✅ | ❌ (403) |
| `DELETE /suppliers/{id}` | Xóa / Vô hiệu hóa NCC | ✅ | ❌ (403) | ❌ (403) |

---

## 3. CHI TIẾT CÁC ENDPOINTS

### 3.1. Module Xác thực & Tài khoản (`/auth`)

#### `POST /auth/login`

- **Mục đích:** Đăng nhập bằng tài khoản và nhận JWT access token (Dùng cho Frontend React).
- **Request Body:**

  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```

- **Response 200 OK:**

  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "full_name": "Quản trị viên Hệ thống",
      "role": "ADMIN",
      "is_active": true,
      "created_at": "2026-09-22T07:43:00"
    }
  }
  ```

- **Lỗi:** 401 Unauthorized khi sai username/password; 403 khi tài khoản bị khóa.

#### `GET /auth/me`

- **Mục đích:** Trả về thông tin người dùng hiện tại dựa trên Bearer token.
- **Headers:** `Authorization: Bearer <token>`
- **Response 200 OK:** Trả về đối tượng `user`.

#### `POST /auth/users`

- **Mục đích:** Tạo người dùng mới trong hệ thống (Chỉ dành cho ADMIN).
- **Request Body:**

  ```json
  {
    "username": "thukho_02",
    "password": "password123",
    "full_name": "Nguyễn Văn Kho",
    "role": "WAREHOUSE_KEEPER"
  }
  ```

- **Response 201 Created:** Đối tượng người dùng vừa tạo (mật khẩu đã được hash qua bcrypt).

---

### 3.2. Module Nhóm hàng hóa (`/categories`)

#### `GET /categories`

- **Query Params:**
  - `search` (string, optional): Tìm kiếm theo tên hoặc mã nhóm hàng.
  - `skip` (int, default: 0): Phân trang bỏ qua.
  - `limit` (int, default: 100): Giới hạn số lượng lấy ra.
- **Response 200 OK:** Danh sách mảng các đối tượng nhóm hàng:

  ```json
  [
    {
      "id": 1,
      "code": "DIEN-TU",
      "name": "Thiết bị điện tử",
      "description": "Linh kiện, chuột, bàn phím và phụ kiện điện tử"
    }
  ]
  ```

#### `POST /categories`

- **Quyền:** `ADMIN`, `WAREHOUSE_KEEPER`
- **Request Body:**

  ```json
  {
    "code": "GIA-DUNG",
    "name": "Đồ gia dụng",
    "description": "Các mặt hàng thiết yếu gia đình"
  }
  ```

- **Response 201 Created:** Thông tin nhóm hàng đã tạo.
- **Lỗi:** 400 Bad Request nếu trùng mã `code`.

#### `PUT /categories/{category_id}`

- **Quyền:** `ADMIN`, `WAREHOUSE_KEEPER`
- **Response 200 OK:** Thông tin nhóm hàng sau khi cập nhật.

#### `DELETE /categories/{category_id}`

- **Quyền:** `ADMIN`
- **Quy tắc bảo vệ dữ liệu:** Nếu nhóm hàng đang có sản phẩm liên kết (`products`), hệ thống trả về **HTTP 400 Bad Request** kèm thông báo: *"Không thể xóa nhóm hàng vì đang có X sản phẩm liên kết"*.

---

### 3.3. Module Hàng hóa & Cảnh báo tồn kho (`/products`)

#### `GET /products`

- **Query Params:**
  - `search` (string, optional): Tìm theo tên sản phẩm hoặc mã SKU.
  - `category_id` (int, optional): Lọc theo ID nhóm hàng.
  - `is_low_stock` (bool, optional):
    - `true`: Chỉ lấy các mặt hàng có `current_stock <= min_stock`.
    - `false`: Lấy các mặt hàng có `current_stock > min_stock`.
  - `status` (string, optional): `ACTIVE` hoặc `DISCONTINUED`.
  - `skip` (int, default: 0), `limit` (int, default: 50).
- **Response 200 OK:**

  ```json
  [
    {
      "id": 1,
      "code": "SKU-LOGI-G102",
      "name": "Chuột Gaming Logitech G102 Lightsync",
      "category_id": 1,
      "category_name": "Thiết bị điện tử",
      "unit": "Cái",
      "min_stock": 10,
      "current_stock": 4,
      "standard_price": 420000.0,
      "status": "ACTIVE",
      "created_at": "2026-09-22T08:00:00",
      "is_low_stock": true
    }
  ]
  ```

#### `POST /products`

- **Quyền:** `ADMIN`, `WAREHOUSE_KEEPER`
- **Request Body:**

  ```json
  {
    "code": "SKU-LOGI-G102",
    "name": "Chuột Gaming Logitech G102",
    "category_id": 1,
    "unit": "Cái",
    "min_stock": 10,
    "current_stock": 0,
    "standard_price": 420000.0,
    "status": "ACTIVE"
  }
  ```

- **Ràng buộc toàn vẹn & Kiểm tra:**
  1. Kiểm tra `category_id` có tồn tại trong bảng `categories` không $\rightarrow$ Nếu không có: HTTP 400.
  2. Kiểm tra mã `code` (SKU) có bị trùng lặp không $\rightarrow$ Nếu trùng: HTTP 400.
  3. Kiểm tra số lượng và giá trị không âm: `min_stock >= 0`, `current_stock >= 0`, `standard_price >= 0` $\rightarrow$ Nếu vi phạm: HTTP 422.
- **Response 201 Created:** Thông tin sản phẩm vừa tạo kèm thuộc tính tính toán `is_low_stock`.

#### `PUT /products/{product_id}`

- **Quyền:** `ADMIN`, `WAREHOUSE_KEEPER`
- **Mục đích:** Cập nhật thông tin hàng hóa (tên, nhóm hàng, đơn vị tính, định mức tồn tối thiểu, giá tiêu chuẩn, trạng thái).
- **Lưu ý bảo vệ kho:** Không cho phép sửa trực tiếp trường `current_stock` qua endpoint này; mọi biến động số lượng tồn kho bắt buộc phải thông qua Phiếu Nhập / Phiếu Xuất (Giai đoạn 3).

#### `DELETE /products/{product_id}`

- **Quyền:** `ADMIN`
- **Quy tắc bảo vệ lịch sử giao dịch:**
  - Nếu sản phẩm **đã có** lịch sử giao dịch (phiếu nhập, phiếu xuất, thẻ kho): Hệ thống tự động chuyển `status = "DISCONTINUED"` (Ngừng kinh doanh) để bảo toàn chứng từ kế toán.
  - Nếu sản phẩm **chưa có** phát sinh giao dịch: Cho phép xóa hoàn toàn khỏi cơ sở dữ liệu.

---

### 3.4. Module Nhà cung cấp (`/suppliers`)

#### `GET /suppliers`

- **Query Params:** `search`, `is_active`, `skip`, `limit`.
- **Response 200 OK:** Danh sách các nhà cung cấp.

#### `POST /suppliers`

- **Quyền:** `ADMIN`, `WAREHOUSE_KEEPER`
- **Request Body:**

  ```json
  {
    "code": "NCC-SAMSUNG",
    "name": "Công ty TNHH Điện tử Samsung Vina",
    "phone": "02838221234",
    "email": "info@samsung.vn",
    "address": "Khu công nghệ cao TP. Thủ Đức, TP.HCM",
    "is_active": true
  }
  ```

- **Response 201 Created:** Thông tin nhà cung cấp đã tạo.
- **Lỗi:** 400 Bad Request nếu trùng mã `code`.

#### `PUT /suppliers/{supplier_id}`

- **Quyền:** `ADMIN`, `WAREHOUSE_KEEPER`
- **Response 200 OK:** Thông tin nhà cung cấp sau cập nhật.

#### `DELETE /suppliers/{supplier_id}`

- **Quyền:** `ADMIN`
- **Quy tắc bảo toàn dữ liệu:**
  - Nếu nhà cung cấp đã có phiếu nhập liên kết: Tự động chuyển `is_active = false` (Ngừng hợp tác).
  - Nếu chưa có phiếu nhập: Xóa khỏi CSDL.
