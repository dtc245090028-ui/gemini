# BƯỚC 04: CẤU TRÚC BACKEND, CẤU HÌNH & DATABASE SESSION (BACKEND FOUNDATION)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-04-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - Mã nguồn được sinh trực tiếp vào thư mục `backend/app/`.

---

## 1. Mục tiêu bước 4

- Thiết lập nền tảng FastAPI theo mô hình kiến trúc phân tầng (Layered Architecture): `Routers -> Services -> Models -> Schemas`.
- Cấu hình quản lý phiên kết nối CSDL (SQLAlchemy Engine, SessionLocal, Dependency `get_db`).
- Thiết lập hệ thống Middleware (CORS) và bộ xử lý lỗi tập trung (Global Exception Handlers).
- Tự động khởi tạo cấu trúc bảng CSDL khi ứng dụng khởi chạy.

---

## 2. Nội dung công việc chi tiết

### 2.1. Cấu hình SQLAlchemy & Phiên làm việc CSDL

- `app/core/database.py`:
  - Tạo `engine` với cấu hình phù hợp (`check_same_thread=False` cho SQLite, connection pool cho PostgreSQL).
  - Khai báo `Base = declarative_base()`.
  - Hàm `get_db()` yield session và đảm bảo `db.close()` sau mỗi request.

### 2.2. Khởi tạo FastAPI App & Middleware

- `app/main.py`:
  - Khởi tạo `app = FastAPI(title=..., version=..., docs_url="/docs", lifespan=lifespan)`.
  - Cấu hình `CORSMiddleware` cho phép kết nối an toàn từ frontend React (`http://localhost:5173`).
  - Đăng ký Router chính `/api/v1` (gom 9 sub-routers nghiệp vụ).
  - Mount thư mục tĩnh `app.mount("/static", StaticFiles(directory=...), name="static")` phục vụ ảnh sản phẩm.
  - Tự động kiểm tra và migrate cột `idempotency_key` cho 2 bảng `import_notes` và `export_notes` trong lifespan.

### 2.3. Bộ xử lý lỗi tập trung (Global Exception Handler)

- Chuẩn hóa định dạng lỗi trả về tiếng Việt thống nhất toàn hệ thống:
  - `StarletteHTTPException`: Bắt lỗi HTTP nghiệp vụ, trả về mã trạng thái tương ứng kèm `"error_code": "HTTP_xxx"`.
  - `RequestValidationError`: Bắt lỗi Pydantic validation (422 Unprocessable Entity).
  - `IntegrityError`: Bắt vi phạm ràng buộc toàn vẹn CSDL (trùng khóa Unique, vi phạm CheckConstraint `current_stock >= 0`), trả về HTTP 400 Bad Request rõ ràng thay vì sập lỗi 500.
  - `SQLAlchemyError`: Nhận diện đụng độ ghi đồng thời (`database is locked` / `busy`), trả về mã lỗi `DATABASE_BUSY` (500) kèm lời nhắn thử lại sau giây lát.

  ```json
  {
    "success": false,
    "detail": "Thông báo lỗi tiếng Việt dễ hiểu",
    "error_code": "INTEGRITY_ERROR"
  }
  ```

---

## 3. Cấu trúc file/thư mục cần sinh

Khi thực hiện bước này, các file và thư mục sau phải được tạo ra:

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                        # Điểm khởi chạy FastAPI, middleware, handlers & static mount
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic Settings đọc biến môi trường
│   │   ├── database.py                # Engine, SessionLocal, get_db(), SQLite PRAGMA listener
│   │   └── seed.py                    # Idempotent seed tài khoản mặc định
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                    # Dependencies: auth, RBAC require_roles, sliding window rate limiter
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── api.py                 # Gom 9 sub-routers vào API router v1
│   └── models/
│       └── __init__.py                # Import Base và các models để khởi tạo bảng
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Khởi động backend thành công bằng lệnh: `uvicorn app.main:app --reload`.
- [x] Truy cập được trang Swagger UI tại `http://localhost:8000/docs` và thấy endpoint `/health` trả về `{"status": "healthy"}`.
- [x] Session database mở và đóng tự động, không bị rò rỉ kết nối (connection leak).
- [x] Bật cưỡng chế khóa ngoại SQLite qua `PRAGMA foreign_keys = ON;`.

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 04** theo đúng mẫu sau:

```markdown
| YYYY-MM-DD | Bước 04 | Cấu trúc Backend & Database Session | Hoàn thành | `backend/app/main.py`, `core/database.py`, `core/config.py` | Đã hoàn thiện cấu trúc FastAPI phân tầng, database session và global error handlers |
```

---

## 6. Lịch sử đồng bộ (Reconciliation History)

- **Ngày thực hiện:** 2026-10-28
- **Căn cứ:** Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md) (Mục #14, #15, #16).
- **Nội dung điều chỉnh:**
  1. *[Mục #14 - Nhóm B]:* Bổ sung tài liệu về cấu hình mount thư mục tĩnh `/static` cho ảnh sản phẩm trong `app/main.py` ([`backend/app/main.py` L136-139](file:///e:/gemini/hệ thống quản lý kho/backend/app/main.py#L136-L139)).
  2. *[Mục #15 - Nhóm B]:* Bổ sung cơ chế auto-migrate an toàn cột `idempotency_key` trong lifespan startup ([`backend/app/main.py` L31-37](file:///e:/gemini/hệ thống quản lý kho/backend/app/main.py#L31-L37)).
  3. *[Mục #16 - Nhóm B]:* Ghi nhận exception handler chuyên biệt cho `IntegrityError` (trả về 400 rõ ràng) và `SQLAlchemyError` với mã `DATABASE_BUSY` khi SQLite bị khóa đồng thời ([`backend/app/main.py` L96-130](file:///e:/gemini/hệ thống quản lý kho/backend/app/main.py#L96-L130)).
- **Lý do:** Hoàn thiện đặc tả kiến trúc nền tảng Backend khớp chính xác với mã nguồn thực tế triển khai.
