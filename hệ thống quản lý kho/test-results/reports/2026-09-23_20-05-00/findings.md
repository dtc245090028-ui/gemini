# GHI NHẬN SAI LỆCH & PHÁT HIỆN ĐẶC BIỆT (FINDINGS)

> **Mã phiên kiểm thử:** `2026-09-23_20-05-00`  
> **Dự án:** Hệ thống Quản lý Kho Thông minh tích hợp AI (Đề tài 07)  
> **Nguyên tắc:** Báo cáo phản ánh hiện trạng khách quan, không tự ý sửa code hoặc suy đoán ngoài dữ liệu kiểm chứng.

---

## 1. Sai Lệch Văn Bản Thông Báo Lỗi Nghiệp Vụ (Error Message Discrepancy)

- **Mô tả hiện trạng:**
  - Trong logic xử lý xuất kho (`backend/app/services/inventory_service.py`), khi người dùng cố gắng xuất số lượng lớn hơn tồn kho hiện tại, hàm ném ngoại lệ `HTTPException(status_code=400)` với nội dung tiếng Việt:
    ```text
    "Không đủ hàng tồn kho cho sản phẩm '{product.name}' (Mã SKU: {product.code}). Số lượng tồn hiện có: {product.current_stock}, Yêu cầu xuất: {detail_in.quantity}. Thiếu hụt: {detail_in.quantity - product.current_stock}. Giao dịch xuất kho đã bị hủy bỏ."
    ```
  - Trong file kiểm thử blackbox mở rộng (`test_agent_comprehensive_blackbox.py`), câu lệnh assertion kiểm tra xem chuỗi `"tồn kho không đủ"` có nằm trong `detail` hay không (`assert "tồn kho không đủ" in detail.lower()`).
  - Do thứ tự từ trong câu thông báo thực tế là `"không đủ hàng tồn kho"` chứ không phải `"tồn kho không đủ"`, test case đã bị báo fail (AssertionError) dù HTTP status trả về chính xác là 400.
- **Tác động:** Không ảnh hưởng đến an toàn dữ liệu hay tính đúng đắn của giao dịch ACID.

---

## 2. Kết Quả Kiểm Thử Giả Định An Ninh & Tấn Công (Security & Vulnerability Findings)

Thông qua bộ kiểm thử Blackbox & Security giả định, các phát hiện an ninh được ghi nhận như sau:

### 2.1. Thử nghiệm Tấn công SQL Injection vào bộ lọc tìm kiếm
- **Các chuỗi thử nghiệm:**
  - `' OR '1'='1`
  - `'; DROP TABLE users; --`
  - `1 UNION SELECT 1, 'admin', 'pass', 1, 1 --`
  - `' OR 1=1 --`
- **Hiện trạng ghi nhận:**
  - Các endpoint `/api/v1/products/`, `/api/v1/categories/`, `/api/v1/suppliers/` sử dụng SQLAlchemy ORM với `ilike(f"%{pattern}%")`.
  - SQLAlchemy tự động parameterize chuỗi truy vấn (truyền tham số qua SQL driver), không thực hiện nối chuỗi SQL thô (raw string interpolation).
  - Kết quả: Không có lỗi SQL Syntax (HTTP 500), không rò rỉ dữ liệu ngoài phạm vi tìm kiếm, trả về HTTP 200 an toàn với danh sách lọc chính xác.

### 2.2. Thử nghiệm Giả mạo JWT Token (JWT Tampering & Signature Forgery)
- **Kịch bản:**
  - Ký một JWT token mới chứa claim `role: "ADMIN"` nhưng sử dụng một `SECRET_KEY` giả mạo của kẻ tấn công.
  - Gửi token này vào endpoint được bảo vệ `/api/v1/auth/me`.
- **Hiện trạng ghi nhận:**
  - Module bảo mật `app/core/security.py` sử dụng thư viện `PyJWT` kiểm tra chữ ký với `settings.SECRET_KEY`.
  - Hệ thống phát hiện chữ ký không hợp lệ và từ chối ngay lập tức với mã lỗi **`HTTP 401 Unauthorized`**. Kẻ tấn công không thể leo thang đặc quyền thông qua việc giả mạo chữ ký JWT.

### 2.3. Thử nghiệm Phân quyền Trái phép (RBAC Violation)
- **Kịch bản:**
  - Dùng token của vai trò Kế toán (`ACCOUNTANT`) để gọi API tạo sản phẩm mới (`POST /api/v1/products/`) hoặc tạo phiếu nhập kho (`POST /api/v1/import-notes/`).
  - Dùng token của vai trò Thủ kho (`WAREHOUSE_KEEPER`) để gọi API tạo tài khoản người dùng mới (`POST /api/v1/auth/users`).
- **Hiện trạng ghi nhận:**
  - Dependency `require_roles` trong `app/api/deps.py` chặn đứng toàn bộ các request không đúng vai trò và trả về mã lỗi **`HTTP 403 Forbidden`**.

### 2.4. Thử nghiệm Guard-Check Chống Tồn Âm Khi Hủy Phiếu Nhập
- **Kịch bản:**
  - Tạo sản phẩm (tồn = 0) -> Nhập kho 50 cái (tồn = 50) -> Xuất bán 50 cái (tồn = 0) -> Cố gắng hủy phiếu nhập kho ban đầu (nếu hủy thành công sẽ làm tồn kho bị trừ ngược 50 cái thành -50).
- **Hiện trạng ghi nhận:**
  - Hàm `cancel_import_note` trong `inventory_service.py` kiểm tra số lượng khả dụng: `product.current_stock < detail.quantity` và chặn đứng giao dịch với mã lỗi **`HTTP 400 BAD REQUEST`**: `"Không thể hoàn trả phiếu nhập... tồn kho hiện tại không đủ"`.
  - Bất biến CSDL `current_stock >= 0` được bảo vệ toàn vẹn ở cả tầng logic Service và tầng CheckConstraint của CSDL.

---

## 3. Cảnh Báo Deprecation Từ Môi Trường Thực Thi (Runtime Warnings)

Trong quá trình chạy kiểm thử trên môi trường Python 3.14.6, ghi nhận các cảnh báo tĩnh:

1. **`datetime.datetime.utcnow()` Deprecation:**
   - Vị trí: `sqlalchemy/sql/schema.py:3627` và các model sử dụng `default=datetime.utcnow`.
   - Cảnh báo: Python 3.14 thông báo `datetime.datetime.utcnow()` đã bị deprecated và sẽ bị loại bỏ trong các phiên bản Python tương lai. Khuyến nghị chuẩn trong tương lai là sử dụng `datetime.now(datetime.timezone.utc)`.
2. **`starlette.testclient` Deprecation Warning:**
   - Cảnh báo: Sử dụng `httpx` với `starlette.testclient` hiển thị cảnh báo khuyên dùng `httpx2` trong các bản cập nhật sắp tới.
3. **`InsecureKeyLengthWarning` Khi Test Token Giả:**
   - Khi chạy test giả mạo token với khóa ngắn 24 bytes, thư viện PyJWT phát cảnh báo theo chuẩn RFC 7518 Section 3.2. Trong môi trường cấu hình chính của dự án (`settings.SECRET_KEY`), khóa mặc định dài 40 bytes đáp ứng chuẩn bảo mật.
