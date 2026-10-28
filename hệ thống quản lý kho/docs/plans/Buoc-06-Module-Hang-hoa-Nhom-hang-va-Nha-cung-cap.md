# BƯỚC 06: MODULE HÀNG HÓA, NHÓM HÀNG & NHÀ CUNG CẤP (MASTER DATA)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-06-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - Mã nguồn được sinh trực tiếp vào thư mục `backend/app/` (models, schemas, endpoints).

---

## 1. Mục tiêu bước 6

- Xây dựng các chức năng CRUD cho dữ liệu nền tảng của kho: Nhóm hàng (Categories), Hàng hóa (Products), Nhà cung cấp (Suppliers).
- Tích hợp logic tìm kiếm, lọc theo danh mục và tự động tính cờ cảnh báo hàng dưới mức tồn tối thiểu (`is_low_stock`).
- Đảm bảo tính toàn vẹn dữ liệu: mã SKU duy nhất, đơn vị tính chuẩn, số lượng $\ge 0$.

---

## 2. Nội dung công việc chi tiết

### 2.1. Models CSDL

- `app/models/category.py`: `id`, `code`, `name`, `description`.
- `app/models/product.py`:
  - `id`, `code` (SKU duy nhất), `name`, `category_id` (FK), `unit`, `min_stock`, `current_stock`, `standard_price`, `image_url`, `status`, `created_at`.
  - Ràng buộc: `CHECK (current_stock >= 0)`.
- `app/models/supplier.py`: `id`, `code`, `name`, `phone`, `email`, `address`, `is_active`.

### 2.2. Schemas Xác thực (Pydantic v2)

- `app/schemas/category.py`: `CategoryCreate`, `CategoryUpdate`, `CategoryResponse`.
- `app/schemas/product.py`: `ProductCreate` (hỗ trợ các trường tùy chọn nhập ban đầu: `initial_quantity`, `initial_price`, `supplier_id`), `ProductUpdate`, `ProductResponse` (bổ sung thuộc tính tính toán `@computed_field is_low_stock: bool` và `image_url`).
- `app/schemas/supplier.py`: `SupplierCreate`, `SupplierUpdate`, `SupplierResponse`.

### 2.3. Endpoints RESTful API

- `app/api/v1/endpoints/categories.py`: CRUD nhóm hàng hóa (`GET`, `POST`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`).
- `app/api/v1/endpoints/products.py`:
  - `GET /api/v1/products`: Hỗ trợ phân trang (`skip`, `limit`), tìm kiếm theo từ khóa tên/SKU, lọc theo `category_id`, lọc `is_low_stock=true`.
  - `POST /api/v1/products`: Thêm mới mặt hàng (chỉ Admin/Thủ kho). Nếu có `initial_quantity > 0`, tự động khởi tạo luôn phiếu nhập kho ban đầu và ghi Thẻ kho trong một Transaction nguyên tử.
  - `GET /api/v1/products/{id}`: Xem chi tiết hàng hóa.
  - `PUT /api/v1/products/{id}`: Cập nhật thông tin hàng hóa.
  - `DELETE /api/v1/products/{id}`: Xóa cứng nếu chưa có giao dịch, hoặc chuyển trạng thái mềm sang `DISCONTINUED` nếu đã có chứng từ liên quan.
  - `POST /api/v1/products/{id}/image`: Tải lên tệp ảnh đại diện sản phẩm (Multipart form data).
- `app/api/v1/endpoints/suppliers.py`: CRUD nhà cung cấp (`GET`, `POST`, `GET /{id}`, `PUT /{id}`, `DELETE /{id}`).

---

## 3. Cấu trúc file/thư mục cần sinh

Khi thực hiện bước này, các file và thư mục sau phải được tạo ra:

```text
backend/
├── app/
│   ├── models/
│   │   ├── category.py                # Model Nhóm hàng
│   │   ├── product.py                 # Model Hàng hóa
│   │   └── supplier.py                # Model Nhà cung cấp
│   ├── schemas/
│   │   ├── category.py                # Schemas Category
│   │   ├── product.py                 # Schemas Product
│   │   └── supplier.py                # Schemas Supplier
│   └── api/
│       └── v1/
│           └── endpoints/
│               ├── categories.py      # Routers danh mục
│               ├── products.py        # Routers hàng hóa & cảnh báo tồn
│               └── suppliers.py       # Routers nhà cung cấp
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Không thể tạo sản phẩm với mã SKU trùng lặp (trả về lỗi 400 rõ ràng).
- [x] Bộ lọc `is_low_stock=true` trả về chính xác danh sách các mặt hàng có `current_stock <= min_stock`.
- [x] Pydantic chặn đứng mọi yêu cầu nhập số lượng hoặc giá trị âm.

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/gemini/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 06** theo đúng mẫu sau:

```markdown
| 2026-09-22 | Bước 06 | Module Hàng hóa, Nhóm hàng & Nhà cung cấp | Hoàn thành | `backend/app/schemas/*.py`, `backend/app/api/v1/endpoints/*.py`, `docs/SDLC/KT2/01_API_Specifications.md` | Đã hoàn thiện CRUD Nhóm hàng, Hàng hóa, Nhà cung cấp, cảnh báo tồn kho và tài liệu API Spec KT2 |
```

---

## 6. CHANGELOG

### [2026-09-22] Hoàn thành Bước 06: Module Hàng hóa, Nhóm hàng & Nhà cung cấp

- **Pydantic Schemas:**
  - `backend/app/schemas/category.py`: `CategoryCreate`, `CategoryUpdate`, `CategoryResponse`.
  - `backend/app/schemas/product.py`: `ProductCreate`, `ProductUpdate`, `ProductResponse` với computed field `@computed_field is_low_stock` tự động tính `current_stock <= min_stock`.
  - `backend/app/schemas/supplier.py`: `SupplierCreate`, `SupplierUpdate`, `SupplierResponse`.
  - Xuất toàn bộ schema tại `backend/app/schemas/__init__.py`.
- **API Endpoints & RBAC:**
  - `backend/app/api/v1/endpoints/categories.py`: CRUD nhóm hàng, tìm kiếm, phân trang, chặn xóa nhóm hàng khi có sản phẩm liên kết (HTTP 400).
  - `backend/app/api/v1/endpoints/products.py`: CRUD hàng hóa, lọc theo nhóm hàng, từ khóa SKU/tên, lọc cảnh báo tồn `is_low_stock`, bảo toàn lịch sử bằng soft delete (`DISCONTINUED`).
  - `backend/app/api/v1/endpoints/suppliers.py`: CRUD nhà cung cấp, kiểm tra trùng mã, chuyển `is_active=False` nếu đã có phiếu nhập liên kết.
  - Đăng ký toàn bộ routers vào `backend/app/api/v1/api.py`.
- **Tài liệu bàn giao KT2:**
  - Hoàn thành `docs/SDLC/KT2/01_API_Specifications.md` đặc tả chi tiết toàn bộ RESTful APIs và ma trận phân quyền RBAC.
- **Kiểm thử tự động:**
  - Viết `backend/tests/test_master_data.py` (5 test functions lớn bao quát vòng đời Category, Product, Supplier, Initial Import và RBAC).
  - Tổng số test cases toàn dự án: **19/19 PASS 100%**.

---

## 7. Lịch sử đồng bộ (Reconciliation History)

- **Ngày thực hiện:** 2026-10-28
- **Căn cứ:** Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md) (Mục #14, #21, #23).
- **Nội dung điều chỉnh:**
  1. *[Mục #14 - Nhóm B]:* Bổ sung cột `image_url` vào model `Product` và bổ sung endpoint `POST /products/{id}/image` theo [`backend/app/models/product.py` L20](file:///e:/gemini/hệ thống quản lý kho/backend/app/models/product.py#L20) và [`backend/app/api/v1/endpoints/products.py` L231-275](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/products.py#L231-L275).
  2. *[Mục #21 - Nhóm B]:* Bổ sung tính năng tạo phiếu nhập đầu kỳ tích hợp trong `POST /products` (`initial_quantity`, `initial_price`, `supplier_id`) theo [`backend/app/api/v1/endpoints/products.py` L108-160](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/products.py#L108-L160).
  3. Cập nhật số ca kiểm thử trong `test_master_data.py` là 5 tests (thêm test kiểm thử nhập ban đầu `test_product_creation_with_initial_import_note`).
- **Lý do:** Hoàn thiện đặc tả Master Data khớp 100% với mã nguồn triển khai.
