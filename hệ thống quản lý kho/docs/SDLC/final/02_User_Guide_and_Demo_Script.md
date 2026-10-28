# HƯỚNG DẪN SỬ DỤNG VÀ KỊCH BẢN DEMO 5 PHÚT (USER GUIDE & DEMO SCRIPT)

## Đề tài 07: Hệ thống Quản lý Kho Thông minh Tích hợp AI (WMS AI)
### Tài liệu Hướng dẫn Chấm thi & Nghiệm thu Cuối kỳ

---

## PHẦN 1: HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY 1-CLICK

### 1. Yêu cầu môi trường
- **Hệ điều hành:** Windows 10/11 (khuyến nghị) hoặc Linux / macOS.
- **Docker & Docker Compose:** Đã cài đặt Docker Desktop (khuyến nghị cho môi trường đồng nhất).
- **Hoặc chạy trực tiếp:** Python 3.10+ (đã kiểm định tương thích Python 3.14) & Node.js 18.x+.

### 2. Khởi chạy 1-Click bằng Docker Compose (Khuyến nghị chuẩn)
Tại thư mục gốc dự án, thực thi lệnh:
```bash
docker compose up -d --build
```
Hệ thống tự động dựng 2 containers:
1. **`warehouse_backend`**: Chạy tại `http://localhost:8000` (Swagger UI: `http://localhost:8000/docs`).
2. **`warehouse_frontend`**: Chạy tại `http://localhost:5173`.

### 3. Khởi chạy thủ công bằng dòng lệnh

#### Khởi chạy Backend (Terminal 1):
```bash
cd "E:\gemini\hệ thống quản lý kho\backend"
pip install -r requirements.txt
python seed_data.py   # Nạp dữ liệu mẫu 76 sản phẩm, 5 tháng giao dịch
uvicorn app.main:app --reload --port 8000
```

#### Khởi chạy Frontend (Terminal 2):
```bash
cd "E:\gemini\hệ thống quản lý kho\frontend"
npm install
npm run dev
```

### 4. Danh sách Tài khoản Đăng nhập Mẫu

| Vai trò người dùng | Tên đăng nhập (Username) | Mật khẩu (Password) | Quyền hạn chính |
| :--- | :---: | :---: | :--- |
| **Quản trị viên (Admin)** | `admin` | `admin123` | Toàn quyền quản trị tài khoản, cấu hình tham số, điều chỉnh kiểm kê |
| **Thủ kho (Warehouse)** | `thukho` | `thukho123` | Lập phiếu nhập/xuất, điều phối 3 trạng thái, upload ảnh, kiểm kê kho |
| **Kế toán (Accountant)** | `ketoan` | `ketoan123` | Đối soát chứng từ, xem Báo cáo NXT, tra cứu Thẻ kho, xuất file Excel |

> 💡 **Tính năng Tiện ích Hội đồng:** Trên thanh Header của giao diện Web đã tích hợp sẵn nút chuyển đổi Dark/Light mode và công cụ **"Chuyển vai trò Demo" (1-Click Role Switcher)** giúp đổi vai trò tức thời mà không cần gõ lại mật khẩu.

---

## PHẦN 2: HƯỚNG DẪN VẬN HÀNH CÁC PHÂN HỆ CHỨC NĂNG

### 1. Phân hệ Bảng điều khiển (Dashboard)
- Hiển thị 4 thẻ KPI động: Tổng số mặt hàng, Hàng dưới định mức tồn an toàn, Tổng giá trị tồn kho ước tính và Số lượng phiếu giao dịch trong tháng.
- Bảng danh sách cảnh báo "Hàng sắp hết" với badge màu đỏ trực quan giúp thủ kho nhận biết ngay mặt hàng cần nhập gấp.

### 2. Phân hệ Hàng hóa & Nhóm hàng (Products & Categories)
- **Thanh tìm kiếm thông minh:** Tìm kiếm linh hoạt theo Tên sản phẩm, Mã SKU hoặc gõ tắt chữ cái đầu (VD: gõ `blv` $\rightarrow$ gợi ý ngay *Bàn Làm Việc*).
- **Bộ lọc đa tiêu chí:** Lọc theo nhóm hàng, lọc nhanh danh sách sản phẩm cảnh báo thiếu hụt (`is_low_stock`).
- **Upload ảnh sản phẩm:** Hỗ trợ tải ảnh đại diện sản phẩm trực tiếp từ máy tính (`POST /api/v1/products/{id}/image`).
- **Thêm/Sửa/Xóa:** Phân quyền theo RBAC. Khi xóa sản phẩm đã phát sinh giao dịch, hệ thống tự động chuyển trạng thái mềm `DISCONTINUED` nhằm bảo toàn dữ liệu lịch sử thẻ kho.

### 3. Phân hệ Nhà cung cấp (Suppliers)
- Quản lý danh bạ đối tác cung ứng hàng hóa: Tên công ty, Người liên hệ, Số điện thoại, Email, Địa chỉ.
- Tự động kiểm tra ràng buộc toàn vẹn khi ngưng hợp tác (`is_active = false`).

### 4. Phân hệ Phiếu Nhập kho (Import Notes)
- Lập phiếu nhập đa dòng hàng hóa: Chọn nhà cung cấp $\rightarrow$ Thêm các dòng sản phẩm $\rightarrow$ Nhập số lượng và đơn giá thực tế (hỗ trợ `idempotency_key` chống trùng lặp).
- Tự động tính thành tiền từng dòng và tổng tiền phiếu nhập.
- Khi lưu phiếu: Hệ thống mở giao dịch ACID, sinh mã phiếu chuẩn `PN-YYYYMMDD-XXXX`, cập nhật tăng số dư `current_stock` và ghi bản ghi `IMPORT` vào Thẻ kho.
- Hỗ trợ hủy phiếu nhập kèm Guard-check chống tồn kho âm.

### 5. Phân hệ Phiếu Xuất kho & Cỗ máy Trạng thái 3 Bước (Export Notes)
- **Defensive UI Chống Xuất Âm:** Khi thủ kho nhập số lượng xuất vượt quá tồn kho thực tế, giao diện lập tức cảnh báo đỏ và vô hiệu hóa nút bấm "Tạo phiếu".
- **Cỗ máy trạng thái 3 bước:**
  1. `CONFIRMED` (Chờ xuất): Kiểm tra hàng khả dụng nhưng **chưa trừ tồn kho**. Hỗ trợ nút "Xóa phiếu" (`DELETE /api/v1/export-notes/{id}`) dọn sạch dữ liệu an toàn nếu lập nhầm.
  2. `SHIPPING` (Bắt đầu giao): Bấm khi hàng rời cửa kho vật lý. Hệ thống thực hiện câu lệnh Atomic SQL `RETURNING current_stock` trừ kho nguyên tử và ghi bản ghi `EXPORT` vào Thẻ kho. Nếu giao hàng thất bại, có thể bấm "Hủy đơn", hệ thống tự động hoàn lại 100% số lượng về kho.
  3. `COMPLETED` (Hoàn thành): Khách đã ký biên bản giao nhận. Phiếu bị khóa vĩnh viễn, bảo mật tuyệt đối.
- **ConfirmModal:** Mọi thao tác hủy phiếu hoặc xóa phiếu đều bắt buộc nhập lý do $\ge 5$ ký tự để chống bấm nhầm.

### 6. Phân hệ Sổ cái Thẻ kho & Điều chỉnh Kiểm kê (Stock Ledger & Adjustment)
- Thẻ kho ghi nhận mọi biến động theo thời gian thực (Giờ/Phút/Giây), gồm: Loại GD (`IMPORT`, `EXPORT`, `ADJUSTMENT`), Mã chứng từ, Số lượng biến động và Tồn sau biến động (`balance_after`). Không hiển thị đơn giá/thành tiền để tách biệt với kế toán giá vốn.
- Tính năng **Xuất Thẻ kho Excel (.xlsx):** Tải về toàn bộ lịch sử biến động thẻ kho của từng mặt hàng phục vụ lưu trữ kế toán.
- Tính năng **Điều chỉnh Kiểm kê:** Cho phép nhập số lượng thực tế đếm được trong kho, hệ thống tự động tính độ lệch và ghi bản ghi `ADJUSTMENT` cân bằng tồn kho.

### 7. Phân hệ Trợ lý AI & Báo cáo Thông minh (AI Assistant)
- **Tab 1 - Báo cáo Nhập-Xuất-Tồn & Xuất Excel:** Bảng tổng hợp số lượng và giá trị kho kèm nút bấm **"Xuất Báo cáo Excel"** và phân tích tổng quan từ Gemini 3.5 Flash Lite.
- **Tab 2 - Gợi ý Nhập hàng:** Tính toán vận tốc bán trong 30 ngày, dự báo số ngày còn hàng và đề xuất số lượng nhập tối ưu kèm nút sinh nhanh đơn hàng (`/ai/generate-order`).
- **Tab 3 - Nhận diện Dị thường:** Quét toàn bộ kho bãi, phát hiện hàng xuất tăng vọt bất thường (`SURGE_EXPORT` > 200%) và hàng tồn kho lâu ngày không phát sinh xuất (`DEAD_STOCK` > 30 ngày).
- **Tab 4 - Hỏi đáp SmartKho Copilot:** Trò chuyện tự do với AI về tình hình kho hàng qua `/ai/ask`.
- **Heuristic Fallback Engine & AI Cache:** Tự động trả kết quả từ bộ đệm cache trong ngày hoặc chuyển mạch sang thuật toán quy tắc khi offline.

---

## PHẦN 3: KỊCH BẢN DEMO 5 PHÚT CHUẨN CHẤM THI HỘI ĐỒNG

| Thời gian | Phân hệ / Thao tác thực hiện | Lời thoại thuyết trình gợi ý | Điểm nhấn kỹ thuật cần chỉ rõ |
| :---: | :--- | :--- | :--- |
| **Phút 1:00** | **Giới thiệu Tổng quan & RBAC**<br>- Mở trang chủ Dashboard.<br>- Dùng thanh "Chuyển vai trò Demo". | *"Kính thưa Hội đồng, Đề tài 07 giải quyết bài toán quản trị kho cho doanh nghiệp với 3 vai trò: Quản trị viên, Thủ kho và Kế toán. Giao diện tích hợp công cụ chuyển vai trò 1-click giúp minh chứng sự phân quyền chặt chẽ giữa các bên."* | - Kiến trúc Clean Architecture 3 tầng.<br>- RBAC Guard tại Backend Dependencies.<br>- Dashboard KPIs & Cảnh báo tồn trực quan. |
| **Phút 2:00** | **Thử thách Chống Tồn Âm**<br>- Chọn vai trò **Thủ kho**.<br>- Vào *Phiếu xuất kho* $\rightarrow$ Chọn sản phẩm đang có tồn 10 cái.<br>- Cố ý nhập số lượng xuất là **50 cái**. | *"Một lỗi kinh điển của kho bãi là xuất âm. Hệ thống của chúng em áp dụng cơ chế Chốt Chặn Kép: Tầng Frontend chặn ngay trên form với cảnh báo đỏ. Kể cả nếu gọi API trực tiếp, Backend và CheckConstraint trong Database sẽ lập tức ném lỗi 400 và Rollback giao dịch."* | - **Defensive UI** khóa nút submit.<br>- **Atomic Transaction** kiểm tra tồn.<br>- Ràng buộc `CHECK (current_stock >= 0)`. |
| **Phút 3:00** | **Quy trình Xuất 3 Bước & Thẻ kho**<br>- Nhập số lượng hợp lệ (5 cái) $\rightarrow$ Tạo phiếu (`CONFIRMED`).<br>- Bấm "Bắt đầu giao" $\rightarrow$ `SHIPPING`.<br>- Mở tab *Sổ cái thẻ kho* $\rightarrow$ Thử xuất Excel. | *"Điểm đột phá của chúng em là cỗ máy trạng thái 3 bước. Ở bước Xác nhận, hàng không bị giam ảo và có thể xóa phiếu. Khi chuyển sang Đang giao, câu lệnh SQL nguyên tử mới chính thức trừ kho. Sổ cái thẻ kho lập tức ghi nhận biến động với số tồn sau giao dịch và hỗ trợ xuất file Excel chuẩn."* | - Cỗ máy trạng thái xuất kho 3 bước.<br>- Trừ kho nguyên tử SQL RETURNING.<br>- Xóa phiếu chưa xuất & Xuất Thẻ kho Excel. |
| **Phút 4:00** | **Trợ lý AI Copilot & Báo cáo NXT**<br>- Mở trang *Trợ lý AI & Báo cáo*.<br>- Tab 1: Xem Báo cáo NXT & Thử xuất Excel.<br>- Tab 2: Xem AI Gợi ý nhập hàng.<br>- Tab 3: Cảnh báo bất thường. | *"Phân hệ AI Copilot sử dụng Google Gemini 3.5 Flash Lite đã được tối ưu: Trước khi gửi dữ liệu, hệ thống tự động loại bỏ 100% giá vốn nhạy cảm để bảo mật và sử dụng bộ đệm AI Cache trong ngày. AI dựa trên vận tốc bán 30 ngày để gợi ý số lượng nhập và phát hiện chính xác hàng tồn chết."* | - **SQL Aggregation Pipeline** loại giá vốn.<br>- **Gemini 3.5 Flash Lite** + Fallback chain.<br>- **AI In-Day Cache** (`ai_cache.py`).<br>- Gộp Báo cáo NXT & Xuất Excel trực quan. |
| **Phút 5:00** | **Cơ chế Fallback & Kết quả Test**<br>- Giới thiệu cơ chế Heuristic khi offline.<br>- Trình chiếu kết quả Pytest **70/70 tests passed**, độ bao phủ 83%. | *"Đặc biệt, hệ thống sở hữu Heuristic Fallback Engine hoạt động dưới 50ms khi mất mạng, đảm bảo kho vận hành 24/7. Toàn bộ mã nguồn đã vượt qua bộ kiểm thử tự động 70 ca test với tỷ lệ thành công 100% và độ bao phủ code đạt 83%."* | - **Heuristic Fallback Engine** offline-safe.<br>- **70/70 Pytest test cases PASS 100%**.<br>- Coverage 83% & Seed data 76 SP / 5 tháng. |

---

## PHẦN 4: LỊCH SỬ ĐỒNG BỘ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Cập nhật quy mô Seed Data:** Điều chỉnh số liệu nạp mẫu từ 60 ngày lên **76 sản phẩm**, **7 nhóm hàng**, **10 nhà cung cấp** và lịch sử giao dịch liên tục **5 tháng (150 ngày)**.
  - **Đồng bộ tính năng Xuất Excel:** Bổ sung hướng dẫn sử dụng tính năng xuất file Excel cho Thẻ kho (`StockLedger.jsx`) và Báo cáo Nhập-Xuất-Tồn (`AIAssistant.jsx`).
  - **Đồng bộ quy trình xuất kho 3 bước:** Làm rõ quyền xóa phiếu xuất khi ở trạng thái `CONFIRMED` (`DELETE /api/v1/export-notes/{id}`) và hộp thoại ConfirmModal yêu cầu lý do $\ge 5$ ký tự.
  - **Cập nhật mô hình AI & Bộ test:** Nâng cấp mô hình chính thức sang `gemini-3.5-flash-lite`, bổ sung AI Cache, và cập nhật kết quả kiểm thử tự động lên **70/70 tests PASS 100%** với độ bao phủ code đạt 83%.
