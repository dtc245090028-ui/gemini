# TÀI LIỆU SLIDE THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN (PRESENTATION SLIDES)

## Đề tài 07: Hệ thống Quản lý Kho Thông minh Tích hợp Trí tuệ Nhân tạo (WMS AI)
### Tệp trình chiếu thực tế: `Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx`

> **File trình chiếu chuẩn:** Bộ slide trình chiếu 16 trang định dạng PowerPoint đã được thiết kế sẵn sàng tại:
> 📊 [`Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx`](file:///E:/gemini/Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx) (kèm bản lưu tại `docs/SDLC/final/` và `docs/submissions/final/`).
> Dưới đây là nội dung chi tiết từng slide và ghi chú thuyết minh (Speaker Notes) tương ứng.

---

### SLIDE 1: TRANG BÌA BẢO VỆ ĐỒ ÁN
- **Cơ quan chủ quản:** BỘ GIÁO DỤC VÀ ĐÀO TẠO — TRƯỜNG ĐẠI HỌC CÔNG NGHỆ
- **Khoa / Bộ môn:** KHOA CÔNG NGHỆ THÔNG TIN • BỘ MÔN CÔNG NGHỆ PHẦN MỀM & TRÍ TUỆ NHÂN TẠO
- **Đề tài:** ĐỀ TÀI NGHIÊN CỨU & PHÁT TRIỂN 07: HỆ THỐNG QUẢN LÝ KHO THÔNG MINH TÍCH HỢP TRÍ TUỆ NHÂN TẠO (WMS AI)
- **Công nghệ chính:** FastAPI • SQLAlchemy 2.0 • SQLite ACID • React 18 • Tailwind CSS • Google Gemini 3.5 Flash Lite • Heuristic Math Engine
- **Thực hiện:** Nhóm nghiên cứu & phát triển sinh viên
- *Speaker Note:* "Kính chào Quý Thầy Cô và Hội đồng đánh giá. Hôm nay nhóm em xin phép được báo cáo kết quả nghiên cứu và hiện thực hóa Hệ thống Quản lý Kho Thông minh tích hợp AI."

---

### SLIDE 2: BỐI CẢNH & 3 BÀI TOÁN NHỨC NHỐI CỦA KHO BÃI TRUYỀN THỐNG
1. **Lỗi tồn kho âm (Negative Stock Disaster):** Các phần mềm cũ không khóa giao dịch hoặc kiểm tra lỏng lẻo, dẫn đến việc xuất nhiều hơn số lượng có, số liệu trên máy âm trong khi thực tế đã hết hàng.
2. **Hiện tượng giam giữ hàng ảo (Phantom Stock Hold):** Đơn vừa lập chưa xuất kho đã bị trừ số dư, làm kho bị tê liệt và từ chối các khách hàng khác một cách vô lý.
3. **Thao tác SKU rườm rà & Nhập liệu chậm:** Bắt buộc nhớ mã SKU 10-15 ký tự phức tạp, dễ nhầm lẫn sản phẩm tương đồng, gây ức chế và chậm trễ tiến độ kho vận.
- *Speaker Note:* "Hệ thống của chúng em được thiết kế từ gốc để giải quyết triệt để 3 vấn nạn này."

---

### SLIDE 3: KIẾN TRÚC PHÂN TẦNG 3-TIER CLEAN ARCHITECTURE
- **Presentation Layer:** React 18 Single Page Application, Tailwind CSS, Tokens Dark/Light, Lucide Icons, Axios Client với JWT Interceptor, 44 RESTful Endpoints (FastAPI) & RBAC Guard.
- **Business Service Layer:**
  - `InventoryService`: Quản lý toàn bộ giao dịch ACID Nhập, Xuất 3 bước, Thẻ kho, Kiểm kê.
  - `AIService`: Data Aggregation Pipeline, SQL Filtering (loại trừ giá vốn), AI In-Day Cache (`ai_cache.py`), Prompt Templates tập trung.
  - `FallbackService`: Heuristic Math Engine tính toán độc lập offline.
- **Persistence Layer:** SQLAlchemy 2.0 ORM, SQLite Engine kích hoạt `PRAGMA foreign_keys=ON;`, Google Gemini 3.5 API ngoài.
- *Speaker Note:* "Kiến trúc tách bạch rõ ràng giữa Presentation, Business Logic và Data Access giúp hệ thống bảo trì cực kỳ dễ dàng và kiểm thử độc lập mà không phụ thuộc hạ tầng."

---

### SLIDE 4: MA TRẬN PHÂN QUYỀN RBAC 3 CẤP ĐỘ (ROLE-BASED ACCESS CONTROL)
- **Nguyên tắc cốt lõi:** *Đúng người — Đúng việc*, bảo mật theo chiều sâu.
- **Admin (Quản trị viên):** Quản trị tài khoản người dùng (`/users`), xem toàn bộ kho bãi, cấu hình tham số, phê duyệt điều chỉnh kiểm kê lớn.
- **Thủ kho (Warehouse Keeper):** Nhập kho, xuất kho 3 bước, upload ảnh, cân đối kiểm kê thực tế, theo dõi cảnh báo hàng sắp hết và nhận đề xuất nhập hàng từ AI.
- **Kế toán (Accountant):** Chuyên trách giám sát, quyền xem toàn bộ Báo cáo Nhập-Xuất-Tồn, Sổ cái Thẻ kho, xuất file Excel, phân tích số liệu tài chính kho nhưng không thể tự ý sửa đổi số lượng vật lý.
- *Speaker Note:* "Tầng Backend bảo vệ bằng FastAPI Dependencies `require_roles`, tầng Frontend hiển thị công cụ Chuyển vai trò Demo 1-click."

---

### SLIDE 5: QUY TRÌNH NGHIỆP VỤ NHẬP KHO & GIAO DỊCH ACID
- **Quy trình 5 bước liền mạch:**
  1. Chọn Nhà cung cấp & Thêm đa dòng sản phẩm kèm số lượng và đơn giá mua thực tế (kèm `idempotency_key`).
  2. Hệ thống tự động sinh mã phiếu chuẩn `PN-YYYYMMDD-XXXX` (Retry Pattern chống đụng độ).
  3. Mở Database Transaction nguyên tử (ACID).
  4. Cập nhật đồng bộ: Tạo phiếu nhập $\rightarrow$ Tăng tồn kho `current_stock` $\rightarrow$ Ghi nhận biến động dương vào Sổ cái Thẻ kho.
  5. Commit an toàn. Nếu xảy ra bất kỳ lỗi ngoại lệ nào, Rollback tức thì để bảo đảm số dư không bị sai lệch.
- *Speaker Note:* "Tính toàn vẹn ACID đảm bảo không bao giờ có chuyện phiếu được tạo mà kho không tăng hàng, hoặc ngược lại."

---

### SLIDE 6: CỖ MÁY TRẠNG THÁI XUẤT KHO 3 BƯỚC (3-STAGE STATE MACHINE)
- **Đột phá loại bỏ giam giữ hàng ảo:**
  - `CONFIRMED` (Xác nhận đơn): Tiếp nhận lệnh xuất, kiểm tra hàng có sẵn nhưng **chưa trừ tồn kho thực tế**. Nếu có sai sót, thủ kho có thể bấm *Xóa phiếu* (`DELETE /export-notes/{id}`) dọn sạch dữ liệu không lưu rác.
  - `SHIPPING` (Đang giao hàng): Khi hàng rời cửa kho vật lý, thủ kho bấm *Bắt đầu giao*. Lúc này hệ thống mới **chính thức trừ tồn kho nguyên tử bằng câu lệnh SQL RETURNING** và ghi Thẻ kho. Nếu giao thất bại, bấm *Hủy đơn & Hoàn kho*, hệ thống tự động hoàn lại 100% số lượng.
  - `COMPLETED` (Hoàn thành): Khách ký nhận, phiếu bị khóa vĩnh viễn, chống sửa đổi.
- *Speaker Note:* "Quy trình này bám sát 100% thực tế vận hành kho hiện đại, giải quyết triệt để bài toán giữ hàng ảo."

---

### SLIDE 7: CƠ CHẾ CHỐNG TỒN KHO ÂM: CHỐT CHẶN KÉP (TWO-TIER DEFENSE)
- **Tầng 1 (Atomic SQL Update):** Trừ kho nguyên tử trực tiếp trong cơ sở dữ liệu `UPDATE ... WHERE current_stock >= :qty RETURNING current_stock`. Nếu không đủ hàng, lệnh trả về `None`, hệ thống ném HTTP 400 và Rollback.
- **Tầng 2 (Database Constraint):** Ràng buộc toàn vẹn cứng tại tầng cơ sở dữ liệu:
  $$\text{CHECK} (\text{current\_stock} \ge 0)$$
  Kể cả khi bị lỗi lập trình hoặc truy cập DB bất hợp pháp, cơ sở dữ liệu sẽ tự động từ chối giao dịch và bảo toàn dữ liệu.
- **Tầng Frontend (Defensive UI):** Cảnh báo đỏ tức thì ngay trên form khi nhập vượt số dư và khóa nút tạo phiếu.
- *Speaker Note:* "Chốt chặn kép đảm bảo về mặt toán học và vật lý: Tồn kho của hệ thống không bao giờ có thể mang giá trị âm."

---

### SLIDE 8: SỔ CÁI THẺ KHO BẤT BIẾN & TÍNH NĂNG KIỂM KÊ BÙ TRỪ
- **Sổ cái Thẻ kho (Stock Ledger - Audit Trail):**
  - Lưu vết kiểm toán từng giây: Thời gian, Loại GD (`IMPORT`, `EXPORT`, `ADJUSTMENT`), Mã chứng từ tham chiếu, Số lượng thay đổi và Số dư tồn sau giao dịch (`balance_after`).
  - **Bất biến (Immutable):** Tuyệt đối không cho phép sửa đổi hoặc xóa bỏ các bản ghi thẻ kho đã sinh ra.
  - Hỗ trợ nút bấm **Xuất Thẻ kho Excel (.xlsx)** phục vụ kiểm toán và lưu trữ.
- **Tính năng Kiểm kê Bù trừ:**
  - Hỗ trợ nhập số lượng thực tế đếm được trong kho vật lý.
  - Hệ thống tự động tính độ lệch và ghi nhận bản ghi `ADJUSTMENT` điều chỉnh số dư về đúng thực tế một cách minh bạch.
- *Speaker Note:* "Mọi biến động đều có thể truy vết kiểm toán, phục vụ công tác thanh tra tài chính kế toán chặt chẽ."

---

### SLIDE 9: PHÂN HỆ AI COPILOT TÍCH HỢP GOOGLE GEMINI 3.5
- **5 Năng lực Phân tích & Trợ giúp Thông minh:**
  1. *Báo cáo Tháng Điều hành:* Tổng hợp tình hình luân chuyển kho, hàng bán chạy và 3 đề xuất chiến lược (kèm xuất file Excel).
  2. *Gợi ý Bổ sung Hàng:* Tính toán vận tốc bán 30 ngày (Velocity) và đề xuất số lượng cần nhập chính xác kèm nút sinh nhanh đơn hàng.
  3. *Nhận diện Dị thường:* Phát hiện hàng xuất tăng vọt bất thường (`SURGE_EXPORT` > 200%) và hàng tồn đọng lâu ngày (`DEAD_STOCK` > 30 ngày).
  4. *Trợ lý SmartKho Copilot (`/ai/ask`):* Chat hỏi đáp thông tin kho thời gian thực.
  5. *Sinh Đơn hàng Xuất kho (`/ai/generate-order`):* Tự động soạn đơn từ yêu cầu tự nhiên.
- **Bảo vệ Bí mật Kinh doanh:** Loại bỏ 100% dữ liệu giá mua (`unit_price`) trước khi gửi dữ liệu sang LLM.
- **Tối ưu Chi phí:** Bộ đệm AI In-Day Cache (`ai_cache.py`) lưu kết quả trong ngày theo data fingerprint.
- *Speaker Note:* "AI không bao giờ tự ý thay đổi số liệu kho, chỉ đóng vai trò Trợ lý đề xuất thông minh trên dữ liệu thực tế."

---

### SLIDE 10: CƠ CHẾ DỰ PHÒNG HEURISTIC FALLBACK ENGINE
- **Sẵn sàng 24/7:** Khi mất kết nối Internet, hết quota API Gemini hoặc server bên ngoài gặp sự cố, hệ thống tự động kích hoạt Heuristic Engine chạy nội bộ trong $< 50$ms.
- **Đồng nhất cấu trúc:** Trả về cùng định dạng JSON với cờ `is_fallback: true`, giúp giao diện Web hiển thị nhãn cảnh báo mà không bị sập hay vỡ bố cục.
- *Speaker Note:* "Kho vận là huyết mạch doanh nghiệp, không thể ngừng hoạt động vì đứt cáp quang hay lỗi bên thứ ba."

---

### SLIDE 11: MÔ HÌNH CƠ SỞ DỮ LIỆU CHUẨN HÓA DẠNG 3 (3NF ERD)
- **9 Bảng thực thể chuẩn hóa:**
  1. `users`: Quản lý tài khoản và vai trò RBAC.
  2. `categories`: Nhóm hàng hóa.
  3. `products`: Hàng hóa, ngưỡng an toàn, ảnh sản phẩm (`image_url`) và tồn tức thời (`CHECK >= 0`).
  4. `suppliers`: Nhà cung cấp đối tác.
  5. `import_notes` & `import_note_details`: Phiếu nhập, chi tiết giá vốn, `idempotency_key`.
  6. `export_notes` & `export_note_details`: Phiếu xuất 3 trạng thái, `idempotency_key`.
  7. `stock_ledger`: Sổ cái thẻ kho kiểm toán.
- **Khóa ngoại & Chỉ mục (Indexes):** Kích hoạt SQLite Foreign Keys và đánh chỉ mục tối ưu truy vấn thời gian thực.
- *Speaker Note:* "Mô hình đạt chuẩn 3NF, không dư thừa dữ liệu và tối ưu hóa tối đa cho các truy vấn tổng hợp."

---

### SLIDE 12: ĐỘT PHÁ COMPONENT PRODUCTSELECT & TRẢI NGHIỆM CÔNG THÁI HỌC
- **Gõ tắt chữ cái đầu thông minh:** Thủ kho chỉ cần gõ `blv` $\rightarrow$ hệ thống tìm thấy ngay *Bàn Làm Việc*, không cần nhớ mã SKU.
- **Bộ lọc nhóm hàng trực quan:** Thu hẹp phạm vi tìm kiếm theo danh mục chỉ với 1 click.
- **Màu sắc công thái học & Dark mode:** Thiết lập giao diện Sáng / Tối linh hoạt qua Design Tokens, ConfirmModal bắt buộc lý do $\ge 5$ ký tự khi hủy/xóa phiếu.
- *Speaker Note:* "Giao diện được may đo riêng cho người vận hành kho thực tế, tối giản và thân thiện."

---

### SLIDE 13: TIÊU CHUẨN HIỆU NĂNG, ĐỘ TIN CẬY & AN TOÀN BẢO MẬT
- **Hiệu năng:** Thời gian phản hồi API trung bình $< 80$ms; Heuristic Fallback $< 50$ms.
- **Bảo mật:**
  - Mật khẩu băm chuẩn `bcrypt` tương thích hoàn hảo Python 3.14.
  - Xác thực phiên làm việc chuẩn JSON Web Token (JWT) mã hóa HS256, thời hạn 60 phút.
  - Cơ chế Rate Limiting chống brute-force đăng nhập và spam gọi AI (`SlidingWindowRateLimiter`).
  - Ngăn chặn triệt để lộ lọt giá vốn sang bên thứ ba.
- *Speaker Note:* "Đồ án đáp ứng các tiêu chuẩn bảo mật và hiệu năng phần mềm doanh nghiệp."

---

### SLIDE 14: KIẾN TRÚC TRIỂN KHAI & CONTAINER HÓA (DEPLOYMENT)
- **Đóng gói Docker:** Cung cấp đầy đủ `Dockerfile` (Backend FastAPI, Frontend React) và `docker-compose.yml` (2 containers: `warehouse_backend` & `warehouse_frontend`).
- **Triển khai 1-Click trên Windows:** Cung cấp sẵn file `run.bat` tự động khởi chạy cả 2 server cho giảng viên và hội đồng trải nghiệm trong vòng 5 giây.
- **Seed Data Quy mô lớn:** Kịch bản `seed_data.py` nạp sẵn **76 mặt hàng**, **7 danh mục**, **10 nhà cung cấp** và lịch sử **5 tháng (150 ngày)** nhập xuất liên tục.
- *Speaker Note:* "Người chấm thi chỉ cần nhấp đúp chuột là toàn bộ hệ thống đã sẵn sàng vận hành."

---

### SLIDE 15: TỔNG KẾT & ĐÁNH GIÁ ĐỀ TÀI 07
- **Hoàn thành 100% mục tiêu Đề tài 07:**
  - Toàn bộ **44 endpoints** RESTful APIs hoàn thiện trọn vẹn.
  - Quy trình nghiệp vụ kho chuẩn mực, cỗ máy xuất kho 3 bước, triệt tiêu lỗi tồn âm.
  - 5 Tính năng AI hỗ trợ thực chất (Gemini 3.5 Flash Lite) + Fallback Engine chạy offline.
  - Giao diện React hiện đại, hỗ trợ Dark mode, xuất Excel, chuyển đổi vai trò Demo tức thời.
  - **Bộ kiểm thử tự động 70/70 tests PASS 100%**, code coverage đạt 83%.
  - Hồ sơ SDLC 4 giai đoạn chuẩn mực, đầy đủ văn bản báo cáo Word và Slide PowerPoint.
- *Speaker Note:* "Đề tài đã hoàn thành xuất sắc tất cả các yêu cầu từ lý thuyết đến thực tiễn."

---

### SLIDE 16: LỜI CẢM ƠN & PHIÊN HỎI ĐÁP PHẢN BIỆN (Q&A)
- **Thông điệp kết thúc:** *"Nhóm nghiên cứu xin chân thành cảm ơn Quý Thầy Cô trong Hội đồng đã lắng nghe bài thuyết trình!"*
- **Kính mời Quý Thầy Cô đặt câu hỏi phản biện.**
- *Speaker Note:* "Nhóm em xin sẵn sàng lắng nghe các ý kiến đóng góp và trả lời câu hỏi của Hội đồng."

---

## LỊCH SỬ ĐỒNG BỘ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Slide 1, 9, 15:** Chuẩn hóa mô hình AI sang `gemini-3.5-flash-lite`, tổng số 44 endpoints.
  - **Slide 14:** Cập nhật quy mô dữ liệu mẫu trong `seed_data.py` lên **76 sản phẩm / 5 tháng (150 ngày)** và Docker Compose 2 services.
  - **Slide 15:** Cập nhật kết quả kiểm thử tự động lên **70/70 tests PASS 100%** (coverage 83%).
  - **Slide 3, 6, 8, 12:** Bổ sung mô tả cỗ máy xuất kho 3 bước, trừ kho nguyên tử, quyền xóa phiếu `CONFIRMED`, xuất file Excel và Dark mode.
