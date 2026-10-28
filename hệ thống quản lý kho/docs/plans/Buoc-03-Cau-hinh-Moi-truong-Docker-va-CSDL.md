# BƯỚC 03: CẤU HÌNH MÔI TRƯỜNG, DOCKER & CSDL (ENVIRONMENT SETUP)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-03-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - Mã nguồn & cấu hình được sinh trực tiếp vào thư mục gốc `backend/`, `frontend/`, và file gốc `docker-compose.yml`.

---

## 1. Mục tiêu bước 3

- Thiết lập môi trường phát triển nhất quán, độc lập và dễ chạy lại trên bất kỳ máy tính nào.
- Cấu hình file biến môi trường `.env` và mẫu `.env.example`.
- Thiết lập cấu hình kết nối CSDL linh hoạt: mặc định chạy `SQLite` cho demo nhanh, sẵn sàng đổi sang `PostgreSQL` qua chuỗi kết nối.
- Xây dựng cấu hình `docker-compose.yml` để đóng gói toàn bộ hệ thống (PostgreSQL + Backend + Frontend).

---

## 2. Nội dung công việc chi tiết

### 2.1. Quản lý Biến Môi Trường (.env)

- Các tham số cần quản lý:
  - `PROJECT_NAME`, `VERSION`, `API_V1_STR`.
  - `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
  - `DATABASE_URL`: `sqlite:///./warehouse.db` hoặc `postgresql://postgres:postgres@localhost:5432/warehouse_db`.
  - `GEMINI_API_KEY`, `AI_PROVIDER`, `AI_MODEL_NAME`.
  - `BACKEND_CORS_ORIGINS`.

### 2.2. Cấu hình Docker & Docker Compose

- `backend/Dockerfile`: Build ứng dụng FastAPI với Python 3.11 / 3.14 slim.
- `frontend/Dockerfile`: Multi-stage build ứng dụng React Vite với Node.js 18 và phục vụ qua Nginx Alpine.
- `docker-compose.yml`: Điều phối **2 containers** gọn nhẹ và độc lập:
  - `backend` (`warehouse_backend`): Chạy FastAPI tại cổng 8000, kết nối trực tiếp CSDL SQLite nhúng (`sqlite:///./warehouse.db`), mount volume `./backend:/app`, nạp cấu hình từ `./backend/.env`. (Hỗ trợ cấu hình chuyển sang PostgreSQL qua `DATABASE_URL` khi triển khai Enterprise).
  - `frontend` (`warehouse_frontend`): Chạy Nginx tại cổng 5173 (ánh xạ từ cổng 80 nội bộ), cấu hình `depends_on: backend`.

---

## 3. Cấu trúc file/thư mục cần sinh

Khi thực hiện bước này, các file và thư mục sau phải được tạo ra:

```text
he-thong-quan-ly-kho/
├── .env.example                       # Mẫu cấu hình môi trường gốc
├── docker-compose.yml                 # File điều phối 2 Docker containers (backend + frontend)
├── backend/
│   ├── .env                           # File cấu hình môi trường backend (không commit git)
│   ├── .env.example                   # Mẫu cấu hình môi trường backend
│   └── Dockerfile                     # Dockerfile đóng gói backend FastAPI
└── frontend/
    ├── Dockerfile                     # Dockerfile đóng gói frontend React + Nginx
    └── nginx.conf                     # Cấu hình Nginx reverse proxy cho frontend
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Ứng dụng chạy được cục bộ với `SQLite` mà không cần cài đặt thêm phần mềm máy chủ CSDL bên ngoài.
- [x] Chạy được lệnh `docker compose up --build` khởi động thành công cả 2 services (`warehouse_backend`, `warehouse_frontend`).
- [x] File `.env` chứa bí mật không bị commit lên kho mã nguồn Git.

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 03** theo đúng mẫu sau:

```markdown
| YYYY-MM-DD | Bước 03 | Cấu hình Môi trường, Docker & CSDL | Hoàn thành | `.env.example`, `docker-compose.yml`, `Dockerfile` | Đã hoàn thiện cấu hình .env, docker-compose.yml và Dockerfile |
```

---

## 6. Lịch sử đồng bộ (Reconciliation History)

- **Ngày thực hiện:** 2026-10-28
- **Căn cứ:** Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md) (Mục #5).
- **Nội dung điều chỉnh:**
  1. *[Mục #5 - Nhóm A]:* Điều chỉnh số lượng containers trong `docker-compose.yml` từ 3 containers (có PostgreSQL 16 Alpine) thành **2 containers** (`warehouse_backend` và `warehouse_frontend`) chạy CSDL SQLite nhúng trực tiếp theo đúng file thực tế [`docker-compose.yml` L1-26](file:///e:/gemini/hệ thống quản lý kho/docker-compose.yml#L1-L26).
  2. Ghi nhận PostgreSQL là phương án mở rộng hạ tầng qua chuỗi kết nối `DATABASE_URL` thay vì container cố định trong file compose hiện tại.
- **Lý do:** Đồng bộ tài liệu thiết kế môi trường khớp 100% với cấu hình Docker Compose thực tế đang vận hành của dự án.
