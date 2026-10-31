# Bộ Quy Chuẩn Tác Nhân AI (.agents) — Hệ Thống Quản Lý Kho Tích Hợp AI (Đề Tài 07)

Bộ quy tắc và quy trình chuẩn hóa dành cho các tác nhân AI khi làm việc trên dự án **Hệ thống Quản lý Kho có Tích hợp AI (Đề tài 07)** — đồ án môn học với kiến trúc chuẩn, Clean Architecture 3 tầng, CSDL SQLite ACID, giao diện React 18 SPA và trợ lý AI Google Gemini kèm Heuristic Fallback Engine.

---

## 1. Cấu Trúc Thư Mục `.agents/`

```text
.agents/
├── hooks/                      # Scripts hook vòng đời phiên làm việc
│   ├── session-start.ps1       # Khởi tạo log phiên tự động tại docs/sessions/
│   ├── session-stop.ps1        # Xác nhận đóng phiên & checklist kiểm thử
│   └── settings.json           # Cấu hình kích hoạt hook
├── rules/
│   └── 00-core.md              # Bộ quy tắc cốt lõi: ngôn ngữ, kiến trúc, an toàn CSDL, RBAC, AI
├── workflows/
│   ├── architect.md            # Thiết kế giải pháp, mô hình hóa CSDL, lập kế hoạch kỹ thuật
│   ├── dev.md                  # Triển khai mã nguồn Backend (FastAPI) & Frontend (React/Vite)
│   ├── tester.md               # Thiết kế & thực thi kiểm thử tự động (Pytest), KHÔNG sửa code
│   ├── debugger.md             # Tái hiện lỗi -> Phân tích nguyên nhân gốc (RCA) -> Sửa triệt để
│   └── audit.md                # Chế độ CHỈ ĐỌC: kiểm toán an ninh, ACID, chống tồn âm & báo cáo
└── README.md                   # Bản đồ hướng dẫn và cách kích hoạt từng chế độ làm việc
```

---

## 2. Cách Sử Dụng Từng Mode Làm Việc

| Mode | Mục đích | Cách kích hoạt / Từ khóa | Thư mục tác động |
| :--- | :--- | :--- | :--- |
| **Core** | Quy tắc nền tảng áp dụng mọi lúc | Mặc định luôn luôn kích hoạt | Toàn bộ dự án |
| **Architect** | Thiết kế giải pháp, vẽ sơ đồ ERD, luồng API, chọn phương án | *"Thiết kế...", "Lập kế hoạch...", "Thêm module mới", "Kiến trúc..."* | Chỉ xuất đề xuất & kế hoạch vào `docs/plans/` |
| **Dev** | Triển khai mã nguồn API Backend và giao diện Frontend React | *"Làm Bước-xx", "Code tính năng...", "Tạo API...", "Làm giao diện..."* | `backend/app/`, `frontend/src/` |
| **Tester** | Viết test case tự động, tìm edge case tồn kho, đo kiểm | *"Kiểm thử Bước-xx", "Viết test...", "Test xuất kho", "Test AI"* | `backend/tests/`, `docs/SDLC/` |
| **Debugger** | Tái hiện lỗi và vá lỗi tận gốc, không gây lỗi hồi quy | *"Sửa bug...", "Fix lỗi...", "API 500...", "Test fail", "Lỗi CSDL"* | `backend/tests/`, mã nguồn phát sinh lỗi |
| **Audit** | Kiểm toán an ninh, giao dịch ACID, chống tồn âm, an toàn AI | *"Audit code", "Rà soát bảo mật", "Kiểm tra ACID", "Soát lỗi tồn âm"* | **CHỈ ĐỌC**, chỉ ghi báo cáo vào `docs/SDLC/` hoặc `docs/Audit/` |

---

## 3. Các Nguyên Tắc Bất Di Bất Dịch Của Hệ Thống Kho

1. **Bảo mật Secret & Môi trường:** Repo là public. Tuyệt đối KHÔNG hardcode hoặc commit `GEMINI_API_KEY`, `SECRET_KEY`, chuỗi kết nối DB hoặc file `.env`.
2. **Bảo vệ CSDL & Sao lưu Online:** Tuyệt đối không xóa hay ghi đè `warehouse.db`. Chạy sao lưu qua công cụ chuẩn trước khi sửa schema:
   ```powershell
   python backend/app/core/backup_db.py backup
   ```
3. **Chốt chặn kép chống tồn âm (Negative Stock Prevention):**
   - Ràng buộc CSDL: `CheckConstraint("current_stock >= 0", name="chk_positive_stock")`.
   - Ràng buộc nghiệp vụ: Kiểm tra số lượng khả dụng và giao dịch ACID có khóa trong `backend/app/services/inventory_service.py`.
4. **Cỗ máy trạng thái xuất kho 3 bước:**
   - Luồng xuất kho: `CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`.
   - Chỉ trừ tồn kho thực tế khi phiếu chuyển trạng thái sang `SHIPPING` hoặc `COMPLETED`. Cho phép hủy/xóa phiếu khi đang ở `CONFIRMED`.
   - Mọi biến động kho phải ghi nhận Thẻ kho (`stock_ledger`) đồng bộ trong cùng một transaction.
5. **An toàn AI & Fallback Heuristic Engine:**
   - Không gửi giá mua/giá nhập vào prompt AI khi không phân tích chi phí.
   - AI KHÔNG tự ý thay đổi số liệu kho (chỉ đọc và gợi ý).
   - Khi Gemini API gặp sự cố (mất mạng, timeout > 10s, lỗi 429), `FallbackService` (Rule-Based Heuristic) phải tự động xử lý liền mạch, không làm sập giao diện.
6. **Kiểm thử tự động thực chất (3 luật chống test giả):**
   - Không mock chính lớp đang test (chỉ mock external boundary: Gemini API, thời gian hệ thống).
   - Mỗi bug fix phải có test tái hiện được bug (FAIL trước khi sửa $\rightarrow$ PASS sau khi sửa).
   - Test AI phải assert cấu trúc và nội dung dữ liệu thật.
   - Chạy test chuẩn:
     ```powershell
     cd backend; pytest
     ```
7. **Nguồn sự thật về tiến độ & tài liệu:**
   - Đầu phiên: Đọc `docs/codebase-map.md` và `docs/plans/TIEN-DO.md`.
   - Kết thúc phiên: Cập nhật `docs/plans/TIEN-DO.md`, `docs/codebase-map.md` và hoàn tất log trong `docs/sessions/`.
