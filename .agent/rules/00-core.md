# Quy Tắc Cốt Lõi (Core Rules) — PharmaCare AI

Quy tắc nền tảng bắt buộc tuân thủ đối với mọi tác nhân AI làm việc trên dự án.

## 1. Ngôn Ngữ & Giao Tiếp
- **Ngôn ngữ phản hồi:** Bắt buộc 100% bằng tiếng Việt chuẩn mực, mạch lạc, chuyên nghiệp.
- **Thuật ngữ kỹ thuật:** Giữ nguyên các thuật ngữ chuẩn (FEFO, RBAC, FastAPI, SQLAlchemy, DTO, Session, Lock).
- **Minh bạch:** Giải thích rõ ràng nguyên nhân, vị trí file và lý do trước khi đưa ra giải pháp.

## 2. Bảo Mật & An Toàn Dữ Liệu
- **Bảo vệ Secret:** Repo là public. Tuyệt đối KHÔNG in ra màn hình hoặc commit secret, API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`), mật khẩu hoặc file `.env`.
- **Bảo vệ CSDL:** Tuyệt đối không xóa hay ghi đè `database.db` và thư mục `backups/`.
- **Sao lưu bắt buộc:** Chạy `python scripts/backup_data.py backup` TRƯỚC KHI can thiệp cấu trúc bảng hoặc schema trong `database.py`.
- **Quy tắc Migration:** Tuân thủ pattern hiện có, không can thiệp hay sửa đổi migration cũ trong `_archive/migrations/`.

## 3. Quản Lý File & Giới Hạn Phạm Vi
- **Không phá hủy:** Không tự ý xóa, di chuyển hoặc ghi đè file hiện có khi chưa hỏi và nhận xác nhận từ người dùng.
- **Phạm vi giao diện:** 
  - `static/` (Vanilla JS, HTML5, CSS3) là giao diện SPA chính thức được phục vụ qua `main.py`.
  - `frontend/` (React/Vite) là phụ/mở rộng, không chỉnh sửa trừ khi người dùng yêu cầu rõ ràng.
- **Quy tắc Thư mục gốc:** Giữ root sạch sẽ; các file tạm, bản nháp phải chuyển vào `_archive/`.

## 4. Quy Ước Đặt Tên & Cấu Trúc Mã Nguồn
- **File Python:** `snake_case.py` (ví dụ: `database.py`, `schemas.py`).
- **Class / Model / Schemas:** `PascalCase` (ví dụ: `Medicine`, `Batch`, `POSCheckoutRequest`).
- **Hàm & Biến:** `snake_case` (ví dụ: `calculate_box_deduction`, `get_db`).
- **Hằng số:** `UPPER_SNAKE_CASE` (ví dụ: `AI_PROVIDER`, `AI_TIMEOUT`).
- **Tài liệu Markdown:** `UPPER_SNAKE.md` hoặc `kebab-case.md`.
- **Commit Message:** Chuẩn Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

## 5. Tổ Chức Module Theo Kiến Trúc Dự Án
- **API Endpoints:** Đặt trong `routers/` (FastAPI router riêng biệt, inject `get_db` và `require_roles`).
- **Nghiệp vụ & AI:** Đặt trong `services/` (tách rời router, xử lý timeout, retry và fallback).
- **Model & Validation:** Models tại `database.py`, Pydantic Schemas tại `schemas.py`.
- **Kiểm thử tự động:** Toàn bộ đặt trong `tests/` với tiền tố `test_*.py`.
