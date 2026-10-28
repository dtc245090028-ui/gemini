# Hệ thống quản lý kho — Đề tài 07

> **File này là hướng dẫn khởi chạy & danh mục hồ sơ đồ án** — phục vụ chấm thi, nghiệm thu và vận hành.

---

## ⚡ MỞ PHIÊN — làm theo thứ tự này

### Bước 1 — Nhắc AI đọc ngữ cảnh (copy paste vào chat)

```text
Đọc các file sau trước khi làm bất cứ gì:
1. CLAUDE.md — quy tắc làm việc, kiến trúc, trigger cập nhật tài liệu
2. docs/codebase-map.md — file nào đang có, vai trò gì
3. docs/plans/TIEN-DO.md — đang ở bước nào, còn gì chưa xong
4. docs/MASTER-ROADMAP.md — bức tranh toàn cảnh 8 giai đoạn
```

> Nếu đang ở giữa 1 bước cụ thể, bổ sung thêm:
> `5. docs/plans/Buoc-NN-<tên>.md — kế hoạch chi tiết bước đang làm`

---

### Bước 2 — Bạn tự kiểm tra (không cần AI)

- [ ] `docs/plans/TIEN-DO.md` — Bước hiện tại đang ở trạng thái gì?
- [ ] `docs/MASTER-ROADMAP.md` — Giai đoạn nào đang ⬜ / 🔄 / ✅?
- [ ] Phiên trước có việc còn dở không? (xem cột "Ghi chú" trong TIEN-DO.md)
- [ ] Backend/Frontend có đang chạy không? (nếu đang code)

---

### Bước 3 — Thảo luận với AI TRƯỚC KHI bắt đầu bước mới

Trước khi bảo AI viết code cho bước tiếp theo, hỏi AI những thứ này:

```text
Trước khi bắt đầu [Bước XX], hãy trả lời:
1. Bước này phụ thuộc vào gì? Đã đủ chưa?
2. File nào sẽ được tạo mới / sửa đổi?
3. Có rủi ro gì cần lưu ý không?
4. Tiêu chí hoàn thành (Definition of Done) là gì?
```

> Nếu AI không nêu được tiêu chí hoàn thành rõ ràng → **chưa bắt đầu code**.

---

## 🔚 ĐÓNG PHIÊN — không được bỏ qua nếu có thay đổi code

- [ ] Chạy `cd backend && pytest` — ghi kết quả vào cột "Ghi chú" của TIEN-DO.md
- [ ] Tick `[x]` vào checkbox của các nhiệm vụ đã hoàn thành trong `Buoc-NN.md`
- [ ] Cập nhật `docs/plans/TIEN-DO.md` — đổi trạng thái bước (nếu xong hẳn)
- [ ] Cập nhật `docs/MASTER-ROADMAP.md` — đổi ô trạng thái + thêm dòng lịch sử
- [ ] Cập nhật `docs/codebase-map.md` — nếu có file mới / xóa / đổi vai trò
- [ ] Nếu kế hoạch thay đổi so với Buoc-NN.md → thêm `📝 Cập nhật thực tế [ngày]` vào Buoc-NN.md

---

## 🗺️ LINK NHANH

| Tài liệu | Mục đích | Khi nào dùng |
| --- | --- | --- |
| [CLAUDE.md](CLAUDE.md) | Quy tắc toàn dự án | Nhắc AI đọc đầu phiên |
| [docs/MASTER-ROADMAP.md](docs/MASTER-ROADMAP.md) | Bức tranh 8 giai đoạn | Xem tổng thể, điều hướng |
| [docs/plans/TIEN-DO.md](docs/plans/TIEN-DO.md) | Trạng thái thực tế | Biết đang ở đâu |
| [docs/codebase-map.md](docs/codebase-map.md) | File nào đang có | Khi AI hỏi "file X ở đâu" |
| [Prompt.md](Prompt.md) | Đặc tả hợp nhất | Khi cần tra nghiệp vụ/kỹ thuật |
| [de_tai_07.md](de_tai_07.md) | Đề bài gốc GV kèm Phụ lục | Khi cần đối chiếu yêu cầu gốc |

---

## 📊 TRẠNG THÁI DỰ ÁN (CẬP NHẬT CHÍNH THỨC)

```text
Giai đoạn hiện tại : ✅ 7 — Đóng gói + Tài liệu cuối (HOÀN THÀNH 100%)
Bước đang làm      : Hoàn thành toàn bộ (11/11 Bước)
Mốc SDLC gần nhất  : Cuối kỳ (Final)
Tổng số Endpoints  : 44 endpoints (42 API v1 + 2 root/health)
Kết quả kiểm thử   : 70/70 tests PASS (100%), Coverage 83%
Dữ liệu mẫu        : 76 sản phẩm, 7 danh mục, 10 NCC, dữ liệu 5 tháng (150 ngày)
Ngày cập nhật dòng này: 2026-10-28
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY HỆ THỐNG

### Cách 1: Khởi chạy bằng Docker Compose (Khuyến nghị chuẩn)
```bash
docker compose up -d --build
```
Hệ thống tự động dựng 2 services độc lập:
- Backend FastAPI: `http://localhost:8000` (Swagger UI: `http://localhost:8000/docs`).
- Frontend React: `http://localhost:5173`.

---

### Cách 2: Khởi chạy 1-Click tự động trên Windows
Nhấp đúp chuột vào file `run.bat` ở thư mục gốc, hoặc mở Command Prompt gõ:
```cmd
run.bat
```
- **Kịch bản tự động của `run.bat`:**
  1. Kiểm tra môi trường Python (>= 3.10) và Node.js (>= 18).
  2. Tự động khởi tạo môi trường ảo Python venv (`backend\.venv`) nếu chưa có.
  3. Kích hoạt venv và cài đặt dependencies (`pip install -r requirements.txt`).
  4. Kiểm tra CSDL (`backend\warehouse.db`): nếu chưa có, nạp dữ liệu mẫu 5 tháng chuẩn (`seed_data.py`); nếu đã có, bảo toàn CSDL.
  5. Cài đặt thư viện Frontend (`npm install`) nếu chưa có `node_modules`.
  6. Khởi động Backend (port 8000) và Frontend (port 5173) trong 2 cửa sổ độc lập.
  7. Mở trình duyệt web tại `http://localhost:5173`.

---

### Cách 3: Khởi chạy thủ công từng phần qua dòng lệnh
1. **Thiết lập và chạy Backend API (Terminal 1):**
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate.bat
   pip install -r requirements.txt
   python seed_data.py
   uvicorn app.main:app --reload --port 8000
   ```
2. **Thiết lập và chạy Frontend Web App (Terminal 2):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Mở trình duyệt tại: **`http://localhost:5173`**

---

### 🔑 Cấu hình Trí tuệ nhân tạo (AI Assistant)
- Hệ thống sử dụng mô hình **Google Gemini 3.5 Flash Lite** (`gemini-3.5-flash-lite`).
- Cấu hình file `.env` trong thư mục `backend/` với nội dung:
  ```env
  GEMINI_API_KEY=your_gemini_api_key_here
  ```
- *Lưu ý:* Nếu không cấu hình API Key hoặc mất mạng, hệ thống **tự động kích hoạt cơ chế Heuristic Fallback Engine** và bộ đệm AI In-Day Cache (`ai_cache.py`), đảm bảo 100% tính năng phân tích, gợi ý nhập hàng và phát hiện bất thường vẫn vận hành mượt mà, không gián đoạn.

---

### 👥 Tài khoản mẫu đăng nhập theo 3 vai trò
Hệ thống đã nạp sẵn 3 tài khoản chuẩn theo phân quyền đề bài:
- **Quản trị viên (Admin):** Tài khoản: `admin` | Mật khẩu: `admin123` *(toàn quyền hệ thống, quản lý người dùng, danh mục)*
- **Thủ kho (Warehouse Keeper):** Tài khoản: `thukho` | Mật khẩu: `thukho123` *(quản lý nhập/xuất kho 3 bước, xóa phiếu CONFIRMED, thẻ kho, upload ảnh, trợ lý AI, xuất Excel)*
- **Kế toán kho (Accountant):** Tài khoản: `ketoan` | Mật khẩu: `ketoan123` *(đối soát chứng từ, xem báo cáo nhập xuất tồn tại AIAssistant, tra cứu thẻ kho, xuất file Excel)*

*(Trên thanh điều hướng giao diện Web có sẵn nút chuyển vai trò Demo 1-click và nút bật/tắt Dark/Light Theme).*

---

## 📁 DANH MỤC HỒ SƠ BÀN GIAO SDLC & BÁO CÁO TỔNG KẾT

- **Hồ sơ SDLC 4 Giai đoạn:** Xem tại [`docs/SDLC/`](docs/SDLC/) (gồm `KT1/`, `KT2/`, `KT3/`, `final/`).
- **Báo cáo Kỹ thuật đặc tả kiến trúc:** [`Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`](docs/SDLC/final/Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx) (10 chương hoàn chỉnh).
- **Bộ Slide thuyết trình bảo vệ đồ án:** [`Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx`](docs/SDLC/final/Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx) (16 slide đồ họa).
- **Bản sao lưu hồ sơ nộp bài:** Xem tại [`docs/submissions/final/`](docs/submissions/final/).

---

## 📝 LỊCH SỬ ĐỒNG BỘ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - Cập nhật số liệu kiểm thử: **70/70 tests PASS 100%**, coverage 83%.
  - Cập nhật số liệu seed data: **76 sản phẩm**, 7 nhóm hàng, 10 nhà cung cấp, **5 tháng (150 ngày)**.
  - Chuẩn hóa 44 endpoints và mô hình `gemini-3.5-flash-lite`.
  - Bổ sung hướng dẫn Docker Compose 2 containers.
