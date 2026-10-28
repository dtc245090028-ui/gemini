# BƯỚC 05: XÁC THỰC, ĐĂNG NHẬP & PHÂN QUYỀN RBAC (AUTHENTICATION & AUTHORIZATION)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-05-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - Mã nguồn được sinh trực tiếp vào thư mục `backend/app/` (models, schemas, routers, dependencies).

---

## 1. Mục tiêu bước 5

- Xây dựng hệ thống xác thực người dùng an toàn bằng JWT (JSON Web Tokens) và mã hóa mật khẩu một chiều với `bcrypt`.
- Triển khai phân quyền theo vai trò (Role-Based Access Control - RBAC) chặt chẽ tại tầng Backend cho 3 nhóm người dùng:
  - `ADMIN` (Quản trị viên)
  - `WAREHOUSE_KEEPER` (Thủ kho)
  - `ACCOUNTANT` (Kế toán)

---

## 2. Nội dung công việc chi tiết

### 2.1. Model & Schemas Người dùng

- Model `User` (`app/models/user.py`):
  - `id`: Integer, Primary Key.
  - `username`: String, Unique, Indexed.
  - `password_hash`: String.
  - `full_name`: String.
  - `role`: Enum/String (`ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT`).
  - `is_active`: Boolean, default True.
  - `created_at`: DateTime.
- Schemas (`app/schemas/user.py`):
  - `UserLogin`, `UserCreate`, `UserResponse`, `TokenResponse`.

### 2.2. Cơ chế Bảo mật & JWT & Rate Limiting

- `app/core/security.py`:
  - `verify_password(plain_password, hashed_password) -> bool`
  - `get_password_hash(password) -> str`
  - `create_access_token(data: dict, expires_delta: timedelta) -> str`
  - `decode_access_token(token: str) -> dict`
- `app/api/deps.py`:
  - Bộ kiểm soát tần suất In-Memory (`SlidingWindowRateLimiter`):
    - `rate_limit_login`: Giới hạn tối đa 10 lượt đăng nhập / phút trên mỗi địa chỉ IP (hỗ trợ đọc IP thực qua header `X-Forwarded-For` phía sau Proxy).
    - `check_ai_rate_limit`: Giới hạn tối đa 10 yêu cầu gọi AI / phút trên mỗi tài khoản người dùng.

### 2.3. Endpoints Xác thực & Phân quyền

- Router `app/api/v1/endpoints/auth.py`:
  - `POST /api/v1/auth/login`: Nhận username/password qua JSON $\rightarrow$ Cấp JWT Token.
  - `POST /api/v1/auth/login-form`: Hỗ trợ OAuth2PasswordRequestForm cho nút Authorize trên Swagger UI.
  - `GET /api/v1/auth/me`: Trả về thông tin người dùng đang đăng nhập.
  - `POST /api/v1/auth/users`: Tạo tài khoản người dùng mới (Chỉ dành riêng cho `ADMIN`). (Các tính năng sửa, khóa tài khoản, đổi mật khẩu không triển khai trên UI để giữ hệ thống tinh gọn, thuộc lộ trình nâng cấp sau).
- Dependencies (`app/api/deps.py`):
  - `get_current_user`: Trích xuất token từ header `Authorization: Bearer <token>`, giải mã và tìm user trong DB.
  - `require_roles(["ADMIN", "WAREHOUSE_KEEPER"])`: Kiểm tra `current_user.role`, trả về HTTP 403 Forbidden nếu không đủ quyền. (Kế toán `ACCOUNTANT` chỉ có quyền xem dữ liệu, bị cấm mọi quyền tạo/sửa/xóa).

---

## 3. Cấu trúc file/thư mục cần sinh

Khi thực hiện bước này, các file và thư mục sau phải được tạo ra:

```text
backend/
├── app/
│   ├── core/
│   │   └── security.py                # Hash bcrypt & sinh/giải mã JWT token
│   ├── models/
│   │   └── user.py                    # SQLAlchemy Model User
│   ├── schemas/
│   │   └── user.py                    # Pydantic Schemas User & Token
│   ├── api/
│   │   ├── deps.py                    # Dependencies: get_current_user, require_roles
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           └── auth.py            # Routers /login, /me, /users
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Mật khẩu không bao giờ lưu dưới dạng plain text; 100% mật khẩu được băm qua `bcrypt`.
- [x] API trả về lỗi HTTP 401 khi token sai hoặc hết hạn; trả về HTTP 403 khi gọi API vượt quyền.
- [x] Test thành công chức năng đăng nhập và lấy thông tin tài khoản qua Swagger UI và bộ test tự động.

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/gemini/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 05** theo đúng mẫu sau:

```markdown
| 2026-09-22 | Bước 05 | Xác thực, Đăng nhập & Phân quyền RBAC | Hoàn thành | `backend/app/api/v1/endpoints/auth.py`, `core/security.py`, `core/seed.py` | Đã hoàn thiện xác thực JWT, hash bcrypt, RBAC 3 vai trò, idempotent seed và bật SQLite FK |
```

---

## 6. CHANGELOG

### [2026-09-22] Hoàn thành Bước 05 & 3 Điểm Kỹ Thuật Tối Ưu

- **Bảo mật & Mã hóa:**
  - Triển khai `backend/app/core/security.py` sử dụng trực tiếp thư viện `bcrypt` (thay thế `passlib` nhằm loại bỏ cảnh báo tương thích trên Python 3.14) và thư viện `pyjwt` tiêu chuẩn.
  - Chuẩn hóa JWT config tối thiểu: `ACCESS_TOKEN_EXPIRE_MINUTES = 60` (được nạp từ `.env`), thuật toán `HS256`, không lạm dụng refresh token phức tạp.
- **Schemas & API Xác thực:**
  - Xây dựng `backend/app/schemas/user.py`: `UserLogin`, `UserCreate`, `UserResponse`, `TokenResponse`, `UserRole`.
  - Xây dựng `backend/app/api/deps.py`: `get_current_user` (Bearer token) và dependency factory `require_roles` (RBAC).
  - Xây dựng `backend/app/api/v1/endpoints/auth.py`: `POST /login` (JSON cho Frontend), `POST /login-form` (OAuth2PasswordRequestForm cho Swagger UI Authorize), `GET /me`, `POST /users` (dành riêng cho ADMIN).
  - Đăng ký auth router vào `backend/app/api/v1/api.py`.
- **Cải tiến kỹ thuật bổ sung theo đề xuất:**
  - **SQLite Foreign Keys:** Thêm event listener `@event.listens_for(engine, "connect")` thực thi `PRAGMA foreign_keys=ON;` trong `backend/app/core/database.py`.
  - **Exception Handler:** Tinh chỉnh `backend/app/main.py` bắt riêng `IntegrityError` trả về HTTP 400 kèm thông báo rõ ràng thay vì lỗi 500 chung.
  - **Idempotent Seed:** Tạo `backend/app/core/seed.py` tự động khởi tạo 3 tài khoản mẫu (`admin/admin123`, `thukho/thukho123`, `ketoan/ketoan123`) trong `lifespan` với kiểm tra `filter_by(username=...)` an toàn khi khởi động lại server nhiều lần.
- **Kiểm thử tự động:**
  - Bổ sung `backend/tests/test_auth.py` kiểm thử toàn diện 12 trường hợp: Seed an toàn, đăng nhập đúng/sai, lấy thông tin tài khoản, Swagger login, phân quyền RBAC, ràng buộc Foreign Key và Rate Limiter chống brute-force IP.
  - Kết quả: **12/12 test cases PASS 100%**.

---

## 7. Lịch sử đồng bộ (Reconciliation History)

- **Ngày thực hiện:** 2026-10-28
- **Căn cứ:** Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md) (Mục #2, #3, #16, #34).
- **Nội dung điều chỉnh:**
  1. *[Mục #2, #3 - Nhóm A]:* Bỏ mô tả tính năng đổi mật khẩu và quản lý user sửa/khóa/reset mật khẩu trên UI; ghi rõ hiện tại chỉ có API `POST /auth/users` cho Admin theo [`backend/app/api/v1/endpoints/auth.py` L96-124](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/auth.py#L96-L124).
  2. *[Mục #16 - Nhóm B]:* Bổ sung cơ chế Rate Limiting trượt `SlidingWindowRateLimiter` (10 req/phút/IP và 10 req/phút/user) theo [`backend/app/api/deps.py` L18-89](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/deps.py#L18-L89).
  3. *[Mục #34 - Nhóm D]:* Thống nhất vai trò Kế toán: chỉ có quyền Read-only đối soát chứng từ, không can thiệp thay đổi số lượng kho theo [`backend/app/api/deps.py` L135-148](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/deps.py#L135-L148).
  4. Cập nhật số ca test thực tế trong `test_auth.py` là 12 tests (thêm test rate limit IP).
- **Lý do:** Đồng bộ tài liệu xác thực và phân quyền RBAC khớp chính xác với mã nguồn thực tế.
