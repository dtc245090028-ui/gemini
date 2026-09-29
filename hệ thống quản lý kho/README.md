# Hệ thống quản lý kho — Đề tài 07

> **File này là nhật ký vận hành phiên làm việc** — dành cho bạn (người dùng) đọc trước mỗi phiên.
> Ở Giai đoạn 7, file này sẽ được thay thế bằng hướng dẫn cài đặt thật sự.

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
| [de_tai_07.md](de_tai_07.md) | Đề bài gốc GV — KHÔNG SỬA | Khi cần đối chiếu yêu cầu gốc |

---

## 📊 TRẠNG THÁI DỰ ÁN (CẬP NHẬT CHÍNH THỨC)

```text
Giai đoạn hiện tại : ✅ 7 — Đóng gói + Tài liệu cuối (HOÀN THÀNH 100%)
Bước đang làm      : Hoàn thành toàn bộ (11/11 Bước)
Mốc SDLC gần nhất  : Cuối kỳ (Final)
Kết quả kiểm thử   : 60/60 tests PASS (100%)
Ngày cập nhật dòng này: 2026-09-25
```

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG ĐỂ CHẤM THI & TRẢI NGHIỆM

### Cách 1: Khởi chạy 1-Click trên Windows (Khuyến nghị)
Nhấp đúp chuột vào file:
$$\implies \mathbf{run.bat}$$
Hệ thống sẽ tự động khởi động đồng thời cả Backend (port 8000) và Frontend (port 5173).

### Cách 2: Khởi chạy thủ công qua dòng lệnh
1. **Khởi động Backend API (Terminal 1):**
   ```bash
   cd "E:\gemini\hệ thống quản lý kho\backend"
   uvicorn app.main:app --reload --port 8000
   ```
2. **Khởi động Frontend Web App (Terminal 2):**
   ```bash
   cd "E:\gemini\hệ thống quản lý kho\frontend"
   npm run dev
   ```

Sau đó mở trình duyệt tại: **`http://localhost:5173`**

### Tài khoản mẫu đăng nhập
- **Quản trị viên (Admin):** `admin` / `admin123`
- **Thủ kho (Warehouse):** `thukho` / `thukho123`
- **Kế toán (Accountant):** `ketoan` / `ketoan123`

*(Trên giao diện Web đã tích hợp sẵn thanh công cụ "Chuyển vai trò Demo" để chuyển đổi 1-click giữa 3 vai trò phục vụ thuyết trình).*

---

## 📁 DANH MỤC HỒ SƠ BÀN GIAO SDLC & BÁO CÁO TỔNG KẾT

- **Hồ sơ SDLC 4 Giai đoạn:** Xem tại [`docs/SDLC/`](docs/SDLC/) (gồm `KT1/`, `KT2/`, `KT3/`, `final/`).
- **Báo cáo Kỹ thuật đặc tả kiến trúc:** [`Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`](docs/SDLC/final/Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx) (10 chương hoàn chỉnh).
- **Bộ Slide thuyết trình bảo vệ đồ án:** [`Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx`](docs/SDLC/final/Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx) (16 slide đồ họa).
- **Bản sao lưu hồ sơ nộp bài:** Xem tại [`docs/submissions/final/`](docs/submissions/final/).

