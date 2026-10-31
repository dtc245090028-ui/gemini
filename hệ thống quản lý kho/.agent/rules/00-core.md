# Quy Tắc Cốt Lõi (Core Rules) — Hệ Thống Quản Lý Kho Tích Hợp AI

Quy tắc nền tảng bắt buộc tuân thủ đối với mọi tác nhân AI làm việc trên dự án Hệ Thống Quản Lý Kho (Đề tài 07).

---

## 1. Ngôn Ngữ & Giao Tiếp

- **Ngôn ngữ phản hồi:** Bắt buộc 100% bằng tiếng Việt chuẩn mực, mạch lạc, giải thích rõ ràng và có tính sư phạm (đồ án môn học cần sinh viên hiểu và giải thích được trước hội đồng chấm thi).
- **Ngôn ngữ trong mã nguồn & tài liệu:**
  - **Tài liệu, comment, thông báo lỗi cho người dùng:** Tiếng Việt có dấu, rõ nghĩa.
  - **Định danh code (tên biến, hàm, class, bảng, cột, file):** Tiếng Anh không dấu chuẩn mực (ví dụ: `product`, `supplier`, `import_note`, `export_note`, `stock_ledger`).
- **Minh bạch:** Giải thích rõ lý do, vị trí file và các đánh đổi (tradeoffs) trước khi đề xuất hoặc triển khai giải pháp.

---

## 2. Bảo Mật & An Toàn Dữ Liệu

- **Bảo vệ Secret & Môi trường:** Repo là public. Tuyệt đối KHÔNG hardcode, in ra log/màn hình hoặc commit secret, API keys (`GEMINI_API_KEY`, `SECRET_KEY`), mật khẩu hoặc file `.env`. Sử dụng `.env.example` làm mẫu cấu hình.
- **Bảo vệ CSDL SQLite:** Tuyệt đối không xóa hay ghi đè file CSDL `warehouse.db` và thư mục `backend/backups/`.
- **Sao lưu bắt buộc (Online Backup):** Chạy lệnh sao lưu chuẩn trước khi thay đổi cấu trúc bảng hoặc schema models:
  ```powershell
  python backend/app/core/backup_db.py backup
  ```
- **Toàn vẹn khóa ngoại:** Luôn kích hoạt ràng buộc khóa ngoại SQLite: `PRAGMA foreign_keys = ON;`.

---

## 3. Quản Lý File & Giới Hạn Phạm Vi

- **Thư mục làm việc chuẩn:** Mọi thao tác thực thi trong dự án diễn ra tại thư mục gốc `hệ thống quản lý kho`.
- **Phân định rõ ranh giới các thành phần:**
  - `backend/app/`: Chứa mã nguồn Backend (FastAPI, SQLAlchemy 2.0).
  - `frontend/src/`: Chứa mã nguồn Frontend chính thức (React 18, Tailwind CSS, Vite).
  - `docs/`: Chứa toàn bộ tài liệu dự án, lộ trình kế hoạch (`docs/plans/`), bản đồ mã nguồn (`docs/codebase-map.md`), tài liệu nộp bài SDLC (`docs/SDLC/`), và nhật ký phiên (`docs/sessions/`).
- **Không phá hủy:** Không tự ý xóa, di chuyển hoặc ghi đè file hiện có khi chưa khảo sát kỹ và nhận xác nhận từ người dùng.
- **Giữ thư mục gốc sạch sẽ:** Không xả file tạm, file rác ra root.

---

## 4. Quy Ước Đặt Tên & Cấu Trúc Mã Nguồn

- **Backend (Python):**
  - File & Module: `snake_case.py` (ví dụ: `inventory_service.py`, `stock_ledger.py`).
  - Class / Model / Schemas: `PascalCase` (ví dụ: `Product`, `ExportNote`, `StockLedgerResponse`).
  - Hàm & Biến: `snake_case` (ví dụ: `calculate_stock_balance`, `get_db`).
  - Hằng số: `UPPER_SNAKE_CASE` (ví dụ: `GEMINI_TIMEOUT_SECONDS`, `DEFAULT_MIN_STOCK`).
- **Frontend (JavaScript / React):**
  - Component & Page: `PascalCase.jsx` (ví dụ: `ExportNotes.jsx`, `ConfirmModal.jsx`).
  - Hook / Utility / Service: `camelCase.js` (ví dụ: `useAuth.js`, `apiClient.js`).
- **Commit Message:** Chuẩn `<loại>: <mô tả>` bằng tiếng Việt không dấu hoặc tiếng Anh (ví dụ: `feat: them chot chan chong ton am export note`, `fix: sua loi timeout fallback gemini`).

---

## 5. Kiến Trúc Phân Tầng Clean Architecture

- **API Endpoints (`backend/app/api/v1/endpoints/`):** Chỉ làm nhiệm vụ HTTP: parse request, kiểm tra quyền RBAC, gọi service, trả response DTO. **Tuyệt đối không viết logic nghiệp vụ phức tạp trong endpoint.**
- **Business Services (`backend/app/services/`):** Chứa toàn bộ nghiệp vụ lõi (tính toán tồn kho, điều phối transaction, fallback AI). Độc lập với HTTP request, có thể test riêng biệt.
- **Data Models (`backend/app/models/`) & Schemas (`backend/app/schemas/`):** Tách biệt giữa ORM entity và Pydantic DTO validate dữ liệu vào/ra.
- **Frontend State & API:** Sử dụng React Context (`AuthContext.jsx`) và module tập trung `frontend/src/api/` để giao tiếp với backend.

---

## 6. Quy Tắc Nghiệp Vụ Kho Cốt Lõi

1. **Phân quyền RBAC (Role-Based Access Control):**
   - 3 vai trò: `admin` (Quản trị viên toàn quyền), `warehouse_keeper` (Thủ kho - quản lý nhập xuất tồn), `accountant` (Kế toán - xem báo cáo, hóa đơn, thẻ kho).
   - Mọi API nhạy cảm đều phải inject dependency kiểm tra role tương ứng.
2. **Giao dịch ACID & Thẻ kho (`stock_ledger`):**
   - Mọi thao tác làm thay đổi số lượng tồn kho (`current_stock`) bắt buộc phải bọc trong một Database Transaction ACID duy nhất.
   - Mỗi biến động nhập, xuất, cân bằng kho bắt buộc phải tự động ghi một bản ghi vào bảng `stock_ledger` để phục vụ đối soát và kiểm toán.
3. **Chốt chặn kép chống tồn âm (Negative Stock Prevention):**
   - Cấp CSDL: Ràng buộc `CheckConstraint("current_stock >= 0", name="chk_positive_stock")` trên bảng `products`.
   - Cấp Ứng dụng: Service kiểm tra số lượng tồn khả dụng và khóa dòng/transaction trước khi trừ kho.
4. **Cỗ máy trạng thái xuất kho 3 bước:**
   - Trạng thái phiếu xuất: `CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`.
   - Chỉ thực hiện trừ tồn kho khi trạng thái chuyển sang `SHIPPING` hoặc `COMPLETED`.
   - Phiếu ở trạng thái `CONFIRMED` chưa trừ kho và được phép hủy hoặc xóa.
5. **Idempotency Key:** Sử dụng cơ chế Idempotency Key trên các API tạo giao dịch kho để chống trùng lặp dữ liệu do gửi lại request.
6. **An Toàn AI & Fallback Engine:**
   - Không đưa giá mua/giá vốn vào prompt AI nếu yêu cầu không phục vụ phân tích chi phí.
   - AI chỉ đọc dữ liệu và sinh nhận xét/gợi ý, **tuyệt đối không cho AI quyền tự ý ghi/sửa trực tiếp số liệu kho trong CSDL**.
   - Nếu Gemini API timeout (>10s), mất mạng hoặc gặp lỗi HTTP 429 Quota, `FallbackService` (Rule-Based Heuristic) phải tự động sinh kết quả thay thế ngay lập tức, không làm gián đoạn người dùng.
