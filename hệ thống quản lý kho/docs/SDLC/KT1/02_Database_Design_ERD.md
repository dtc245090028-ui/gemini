# THIẾT KẾ CƠ SỞ DỮ LIỆU & SƠ ĐỒ ERD CHUẨN (DATABASE DESIGN)

## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

**Mốc đánh giá:** KT1 — Phân tích yêu cầu & Thiết kế hệ thống  
**Học phần:** Triển khai phần mềm & Ứng dụng AI  
**Ngày hoàn thành:** 2026-09-21  

---

## 1. Giới thiệu & Triết lý thiết kế CSDL

Hệ thống quản lý kho yêu cầu tính toàn vẹn và nhất quán dữ liệu ở mức độ tuyệt đối. Mô hình CSDL được thiết kế theo chuẩn hóa dạng chuẩn 3 (3NF), đảm bảo các nguyên tắc kỹ thuật sau:

1. **Toàn vẹn thực thể & quan hệ:** Toàn bộ bảng đều có Khóa chính (`id` tự tăng) và các ràng buộc Khóa ngoại (`FOREIGN KEY`) chỉ rõ hành vi toàn vẹn tham chiếu. Bật thực thi khóa ngoại trên SQLite (`PRAGMA foreign_keys=ON;`).
2. **Triệt tiêu nguy cơ tồn kho âm:** Cài đặt ràng buộc kiểm tra cấp độ CSDL:
   ```sql
   CHECK (current_stock >= 0)
   ```
   Ràng buộc này đóng vai trò chốt chặn cuối cùng (Last line of defense), ngăn chặn bất kỳ lỗi race condition nào làm số lượng tồn kho bị âm.
3. **Audit Trail bất biến qua Thẻ kho (`stock_ledger`):** Mọi giao dịch làm tăng/giảm tồn kho đều bắt buộc sinh một bản ghi kiểm toán ghi nhận số dư tức thời sau giao dịch (`balance_after`), chỉ theo dõi số lượng vật lý và không lưu đơn giá/thành tiền.
4. **Cơ chế Idempotency Key:** Hai bảng chứng từ `import_notes` và `export_notes` đều trang bị trường `idempotency_key` (Unique Index) để chống tạo trùng phiếu khi client retry hoặc rớt mạng.
5. **Cỗ máy trạng thái xuất kho 3 bước:** Bảng `export_notes` quản lý các trạng thái: `CONFIRMED` (Chờ xuất), `SHIPPING` (Đang giao / trừ kho), `COMPLETED` (Hoàn thành), và `CANCELLED` (Đã hủy).

---

## 2. Sơ đồ Quan hệ Thực thể Chuẩn (Mermaid ERD)

```mermaid
erDiagram
    users ||--o{ import_notes : "tạo"
    users ||--o{ export_notes : "tạo"
    users ||--o{ stock_ledger : "thực hiện"

    categories ||--o{ products : "chứa"
    suppliers ||--o{ import_notes : "cung cấp"

    import_notes ||--|{ import_note_details : "có"
    products ||--o{ import_note_details : "được nhập"

    export_notes ||--|{ export_note_details : "có"
    products ||--o{ export_note_details : "được xuất"

    products ||--o{ stock_ledger : "ghi nhận biến động"

    users {
        int id PK "Khóa chính tự tăng"
        string username UK "Tên đăng nhập duy nhất"
        string password_hash "Mật khẩu mã hóa bcrypt"
        string full_name "Họ và tên hiển thị"
        string role "ADMIN | WAREHOUSE_KEEPER | ACCOUNTANT"
        boolean is_active "Trạng thái hoạt động"
        datetime created_at "Thời điểm tạo"
    }

    categories {
        int id PK "Khóa chính tự tăng"
        string code UK "Mã nhóm hàng hóa duy nhất"
        string name "Tên nhóm hàng"
        string description "Mô tả chi tiết"
    }

    products {
        int id PK "Khóa chính tự tăng"
        string code UK "Mã SKU sản phẩm duy nhất"
        string name "Tên mặt hàng"
        int category_id FK "Thuộc nhóm hàng"
        string unit "Đơn vị tính: Cái, Hộp, Thùng..."
        int min_stock "Ngưỡng cảnh báo tồn tối thiểu"
        int current_stock "Số lượng tồn kho tức thời (>=0)"
        float standard_price "Giá niêm yết / tham khảo"
        string image_url "Đường dẫn ảnh sản phẩm"
        string status "ACTIVE | DISCONTINUED"
        datetime created_at "Thời điểm tạo"
    }

    suppliers {
        int id PK "Khóa chính tự tăng"
        string code UK "Mã nhà cung cấp duy nhất"
        string name "Tên nhà cung cấp"
        string phone "Số điện thoại liên hệ"
        string email "Email liên hệ"
        string address "Địa chỉ trụ sở"
        boolean is_active "Trạng thái hợp tác"
    }

    import_notes {
        int id PK "Khóa chính tự tăng"
        string code UK "Mã chứng từ: PN-YYYYMMDD-XXX"
        string idempotency_key UK "Khóa chống trùng lặp"
        int supplier_id FK "Nhà cung cấp hàng"
        int created_by FK "Người lập phiếu (User ID)"
        datetime note_date "Ngày giờ nhập kho"
        float total_amount "Tổng tiền phiếu nhập"
        string note "Ghi chú phiếu nhập"
        string status "COMPLETED | CANCELLED"
    }

    import_note_details {
        int id PK "Khóa chính tự tăng"
        int import_note_id FK "Mã phiếu nhập"
        int product_id FK "Mã mặt hàng"
        int quantity "Số lượng nhập (>0)"
        float unit_price "Đơn giá nhập (>=0)"
        float subtotal "Thành tiền dòng chi tiết"
    }

    export_notes {
        int id PK "Khóa chính tự tăng"
        string code UK "Mã chứng từ: PX-YYYYMMDD-XXX"
        string idempotency_key UK "Khóa chống trùng lặp"
        string recipient_name "Tên người nhận / Khách hàng"
        int created_by FK "Người lập phiếu (User ID)"
        datetime note_date "Ngày giờ xuất kho"
        float total_amount "Tổng tiền phiếu xuất"
        string note "Ghi chú xuất kho"
        string status "CONFIRMED | SHIPPING | COMPLETED | CANCELLED"
    }

    export_note_details {
        int id PK "Khóa chính tự tăng"
        int export_note_id FK "Mã phiếu xuất"
        int product_id FK "Mã mặt hàng"
        int quantity "Số lượng xuất (>0)"
        float unit_price "Đơn giá xuất (>=0)"
        float subtotal "Thành tiền dòng chi tiết"
    }

    stock_ledger {
        int id PK "Khóa chính tự tăng"
        int product_id FK "Mã mặt hàng biến động"
        string transaction_type "IMPORT | EXPORT | ADJUSTMENT"
        string reference_code "Mã phiếu liên quan (PN/PX)"
        int quantity_change "Số lượng thay đổi (+/-)"
        int balance_after "Số dư tồn tức thời sau giao dịch"
        int created_by FK "Người thực hiện (User ID)"
        datetime transaction_date "Thời điểm giao dịch chính xác"
        string note "Ghi chú biến động"
    }
```

---

## 3. Từ điển Dữ liệu Chi tiết (Data Dictionary)

### 3.1. Bảng `users` (Tài khoản người dùng)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất của tài khoản |
| `username` | VARCHAR(50) | NOT NULL, UNIQUE, INDEX | Tên đăng nhập hệ thống |
| `password_hash` | VARCHAR(255) | NOT NULL | Chuỗi băm mật khẩu bảo mật (bcrypt) |
| `full_name` | VARCHAR(100) | NOT NULL | Họ và tên đầy đủ của nhân viên |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'WAREHOUSE_KEEPER' | Vai trò: `ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT` |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Trạng thái: `true` (hoạt động), `false` (bị khóa) |
| `created_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Thời điểm khởi tạo tài khoản |

### 3.2. Bảng `categories` (Nhóm hàng hóa)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất nhóm hàng |
| `code` | VARCHAR(20) | NOT NULL, UNIQUE, INDEX | Mã viết tắt nhóm hàng |
| `name` | VARCHAR(100) | NOT NULL | Tên hiển thị đầy đủ của nhóm hàng |
| `description` | TEXT | NULLABLE | Mô tả chi tiết danh mục |

### 3.3. Bảng `products` (Hàng hóa)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất sản phẩm |
| `code` | VARCHAR(50) | NOT NULL, UNIQUE, INDEX | Mã SKU sản phẩm (ví dụ: `LAPTOP-DELL-5520`) |
| `name` | VARCHAR(200) | NOT NULL | Tên thương mại của sản phẩm |
| `category_id` | INTEGER | NOT NULL, FOREIGN KEY (`categories.id`) | Nhóm hàng tương ứng |
| `unit` | VARCHAR(20) | NOT NULL, DEFAULT 'Cái' | Đơn vị tính: Cái, Hộp, Thùng, Bộ, Kg... |
| `min_stock` | INTEGER | NOT NULL, DEFAULT 10 | Ngưỡng tồn an toàn để kích hoạt cảnh báo |
| `current_stock` | INTEGER | NOT NULL, DEFAULT 0, **`CHECK (current_stock >= 0)`** | **Số lượng tồn kho tức thời (tuyệt đối không âm)** |
| `standard_price` | DECIMAL(12,2) | NOT NULL, DEFAULT 0.0 | Giá niêm yết/tham khảo |
| `image_url` | VARCHAR(255) | NULLABLE | Đường dẫn ảnh sản phẩm tải lên |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'ACTIVE' | Trạng thái: `ACTIVE` hoặc `DISCONTINUED` |
| `created_at` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Ngày tạo mặt hàng |

### 3.4. Bảng `suppliers` (Nhà cung cấp)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất nhà cung cấp |
| `code` | VARCHAR(30) | NOT NULL, UNIQUE, INDEX | Mã nhà cung cấp |
| `name` | VARCHAR(150) | NOT NULL | Tên doanh nghiệp/đối tác |
| `phone` | VARCHAR(20) | NULLABLE | Số điện thoại liên lạc |
| `email` | VARCHAR(100) | NULLABLE | Thư điện tử |
| `address` | VARCHAR(255) | NULLABLE | Địa chỉ văn phòng / kho nhà cung cấp |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Trạng thái hợp tác |

### 3.5. Bảng `import_notes` (Phiếu nhập kho)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất phiếu nhập |
| `code` | VARCHAR(50) | NOT NULL, UNIQUE, INDEX | Số chứng từ: `PN-YYYYMMDD-XXX` |
| `idempotency_key` | VARCHAR(100) | NULLABLE, UNIQUE, INDEX | Khóa chống tạo trùng lặp giao dịch |
| `supplier_id` | INTEGER | NOT NULL, FOREIGN KEY (`suppliers.id`) | Đơn vị cung ứng hàng hóa |
| `created_by` | INTEGER | NOT NULL, FOREIGN KEY (`users.id`) | Nhân viên/Thủ kho lập phiếu |
| `note_date` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Thời điểm lập phiếu nhập |
| `total_amount` | DECIMAL(15,2) | NOT NULL, DEFAULT 0.0 | Tổng giá trị phiếu nhập (VNĐ) |
| `note` | TEXT | NULLABLE | Ghi chú thêm về lô hàng |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'COMPLETED' | `COMPLETED`, `CANCELLED` |

### 3.6. Bảng `import_note_details` (Chi tiết phiếu nhập kho)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất dòng chi tiết |
| `import_note_id` | INTEGER | NOT NULL, FOREIGN KEY (`import_notes.id`) ON DELETE CASCADE | Thuộc phiếu nhập nào |
| `product_id` | INTEGER | NOT NULL, FOREIGN KEY (`products.id`) | Mặt hàng được nhập |
| `quantity` | INTEGER | NOT NULL, `CHECK (quantity > 0)` | Số lượng nhập vào (phải > 0) |
| `unit_price` | DECIMAL(12,2) | NOT NULL, `CHECK (unit_price >= 0)` | Đơn giá nhập thực tế của lô hàng |
| `subtotal` | DECIMAL(15,2) | NOT NULL | Thành tiền (`quantity * unit_price`) |

### 3.7. Bảng `export_notes` (Phiếu xuất kho)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất phiếu xuất |
| `code` | VARCHAR(50) | NOT NULL, UNIQUE, INDEX | Số chứng từ: `PX-YYYYMMDD-XXX` |
| `idempotency_key` | VARCHAR(100) | NULLABLE, UNIQUE, INDEX | Khóa chống tạo trùng lặp giao dịch |
| `recipient_name` | VARCHAR(100) | NOT NULL | Tên người nhận hàng / Khách hàng |
| `created_by` | INTEGER | NOT NULL, FOREIGN KEY (`users.id`) | Nhân viên/Thủ kho lập phiếu xuất |
| `note_date` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Thời điểm lập phiếu xuất |
| `total_amount` | DECIMAL(15,2) | NOT NULL, DEFAULT 0.0 | Tổng giá trị hàng xuất (VNĐ) |
| `note` | TEXT | NULLABLE | Ghi chú / lý do xuất kho |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'CONFIRMED' | `CONFIRMED`, `SHIPPING`, `COMPLETED`, `CANCELLED` |

### 3.8. Bảng `export_note_details` (Chi tiết phiếu xuất kho)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất dòng chi tiết |
| `export_note_id` | INTEGER | NOT NULL, FOREIGN KEY (`export_notes.id`) ON DELETE CASCADE | Thuộc phiếu xuất nào |
| `product_id` | INTEGER | NOT NULL, FOREIGN KEY (`products.id`) | Mặt hàng xuất kho |
| `quantity` | INTEGER | NOT NULL, `CHECK (quantity > 0)` | Số lượng xuất kho (phải > 0) |
| `unit_price` | DECIMAL(12,2) | NOT NULL, `CHECK (unit_price >= 0)` | Đơn giá xuất |
| `subtotal` | DECIMAL(15,2) | NOT NULL | Thành tiền (`quantity * unit_price`) |

### 3.9. Bảng `stock_ledger` (Thẻ kho / Sổ kiểm toán tồn kho)

| Tên trường | Kiểu dữ liệu | Ràng buộc | Mô tả ý nghĩa |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Định danh duy nhất bản ghi thẻ kho |
| `product_id` | INTEGER | NOT NULL, FOREIGN KEY (`products.id`), INDEX | Mặt hàng có biến động số lượng |
| `transaction_type` | VARCHAR(20) | NOT NULL | Loại giao dịch: `IMPORT`, `EXPORT`, `ADJUSTMENT` |
| `reference_code` | VARCHAR(50) | NOT NULL, INDEX | Mã chứng từ gốc (`PN-XXXX` hoặc `PX-XXXX`) |
| `quantity_change` | INTEGER | NOT NULL | Số lượng biến động: dương (`+`) khi nhập, âm (`-`) khi xuất |
| `balance_after` | INTEGER | NOT NULL, `CHECK (balance_after >= 0)` | Số lượng tồn kho sau giao dịch |
| `created_by` | INTEGER | NOT NULL, FOREIGN KEY (`users.id`) | Tài khoản thực hiện giao dịch |
| `transaction_date` | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP, INDEX | Thời điểm phát sinh giao dịch |
| `note` | VARCHAR(255) | NULLABLE | Diễn giải chi tiết biến động |

---

## 4. Cơ chế Đảm bảo Toàn vẹn Dữ liệu & Giao dịch ACID

### 4.1. Quy trình Transaction khi Nhập kho

```python
# Toàn bộ khối lệnh chạy trong một Database Transaction
db.begin()
try:
    # 1. Kiểm tra Idempotency Key (nếu có)
    # 2. Tạo phiếu nhập (import_notes)
    # 3. Với mỗi sản phẩm:
    #    - Lưu chi tiết (import_note_details)
    #    - Cập nhật tăng: product.current_stock += item.quantity
    #    - Thêm bản ghi thẻ kho: stock_ledger(product_id, qty_change=+quantity, balance_after=product.current_stock)
    db.commit()
except Exception:
    db.rollback()
    raise
```

### 4.2. Quy trình Cỗ máy Trạng thái Xuất kho & Chống Tồn Kho Âm (Atomic SQL)

```python
# Khi chuyển trạng thái từ CONFIRMED sang SHIPPING:
db.begin()
try:
    for item in export_note.details:
        # Thực thi câu lệnh SQL trừ kho nguyên tử cấp độ Database Engine
        stmt = text("""
            UPDATE products
            SET current_stock = current_stock - :qty
            WHERE id = :prod_id AND current_stock >= :qty
            RETURNING current_stock
        """)
        result = db.execute(stmt, {"qty": item.quantity, "prod_id": item.product_id}).scalar()
        
        if result is None:
            # Không đủ tồn kho: Rollback tức thời
            raise HTTPException(
                status_code=400,
                detail=f"Sản phẩm ID {item.product_id} không đủ tồn kho để xuất {item.quantity}!"
            )
            
        # Ghi nhận Thẻ kho với số dư sau trừ
        record_stock_ledger(
            product_id=item.product_id,
            qty_change=-item.quantity,
            balance_after=result,
            ref_code=export_note.code
        )
        
    export_note.status = "SHIPPING"
    db.commit()
except Exception:
    db.rollback()
    raise
```

---

## 5. Kết luận

Thiết kế CSDL trên đảm bảo tính chuẩn hóa 3NF, đáp ứng trọn vẹn nghiệp vụ quản lý kho của Đề tài 07, triệt tiêu khả năng phát sinh tồn kho âm bằng câu lệnh SQL nguyên tử, hỗ trợ đầy đủ Idempotency Key và upload ảnh sản phẩm.

---

## 6. Lịch sử đồng bộ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Bổ sung trường `image_url`:** Thêm vào bảng `products` để lưu trữ đường dẫn ảnh đại diện sản phẩm (`/uploads/...`).
  - **Bổ sung trường `idempotency_key`:** Thêm vào hai bảng `import_notes` và `export_notes` (Unique Index) để chống tạo trùng giao dịch khi rớt mạng.
  - **Điều chỉnh trạng thái chứng từ:** Bỏ trạng thái `DRAFT`. Đồng bộ trạng thái thực tế: `import_notes` (`COMPLETED`, `CANCELLED`); `export_notes` (`CONFIRMED`, `SHIPPING`, `COMPLETED`, `CANCELLED`).
  - **Đồng bộ Thẻ kho:** Xác nhận bảng `stock_ledger` chỉ lưu trữ số lượng và số dư tồn sau giao dịch, không có cột giá tiền.
  - **Cập nhật mã nguồn trừ kho:** Thay thế cơ chế trừ kho thông thường bằng câu lệnh Atomic SQL `RETURNING current_stock` của luồng `SHIPPING`.
