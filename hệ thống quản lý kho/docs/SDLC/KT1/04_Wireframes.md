# PHÁC THẢO BỐ CỤC GIAO DIỆN NGƯỜI DÙNG (WIREFRAMES)

## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

**Mốc đánh giá:** KT1 — Phân tích yêu cầu & Thiết kế hệ thống  
**Học phần:** Triển khai phần mềm & Ứng dụng AI  
**Ngày hoàn thành:** 2026-09-21  

---

## 1. Triết lý Thiết kế Giao diện

Giao diện của hệ thống được thiết kế theo phong cách hiện đại, tối giản, trực quan trên nền tảng **React 18 + Tailwind CSS**:

- **Trải nghiệm người dùng nhất quán:** Bố cục chia hai phần rõ rệt: Thanh điều hướng (Sidebar bên trái) và Vùng nội dung chính (Main Content bên phải).
- **Hỗ trợ Giao diện Sáng / Tối (Dark / Light Theme):** Thiết lập qua Design Tokens (`tokens.css`) với nút chuyển đổi nhanh trên Header.
- **Phản hồi nghiệp vụ tức thời:** Khi lập phiếu xuất kho, hệ thống tự động kiểm tra số lượng tồn kho thời gian thực; đổi màu đỏ cảnh báo ngay tại ô nhập liệu nếu số lượng vượt quá số dư trong kho.
- **Chặn thao tác nguy hiểm bằng ConfirmModal:** Các thao tác hủy phiếu hoặc xóa phiếu xuất chưa giao bắt buộc xác nhận và điền lý do $\ge 5$ ký tự.
- **Thân thiện cho buổi thuyết trình (Demo Friendly):** Tích hợp nút **Chuyển vai trò nhanh (Role Switcher)** trên thanh tiêu đề (Header) để sinh viên dễ dàng chuyển đổi qua lại giữa `Admin`, `Thủ kho` và `Kế toán` để chứng minh cơ chế phân quyền RBAC trước hội đồng chấm thi.

---

## 2. Bố cục Tổng thể Hệ thống (Master Layout)

```text
+-------------------------------------------------------------------------------------------------------+
|  [LOGO] SMART WAREHOUSE AI                 [🌙/☀️ Theme]  [Vai trò: THỦ KHO v]  [Tên User] [Đăng xuất] |
+-------------------+-----------------------------------------------------------------------------------+
| [=] Tổng quan     |  BREADCRUMB: Trang chủ > Tổng quan                                                |
| [P] Hàng hóa      |                                                                                   |
| [S] Nhà cung cấp  |  [NỘI DUNG CHỨC NĂNG CỦA TỪNG MÀN HÌNH TẠI ĐÂY]                                   |
| [I] Phiếu Nhập    |                                                                                   |
| [E] Phiếu Xuất    |                                                                                   |
| [L] Thẻ kho       |                                                                                   |
| [A] Trợ lý AI &   |  *(Phân hệ Báo cáo Nhập-Xuất-Tồn được tích hợp tại Tab 1 trang Trợ lý AI)*        |
|     Báo cáo       |                                                                                   |
+-------------------+-----------------------------------------------------------------------------------+
| Phiên bản v1.0.0  | Hệ thống quản lý kho Đề tài 07 - Tích hợp AI Gemini 3.5 Flash Lite                |
+-------------------+-----------------------------------------------------------------------------------+
```

---

## 3. Chi tiết Wireframe các Màn hình Chính

### 3.1. Màn hình Dashboard & Cảnh báo Tồn kho (`pages/Dashboard.jsx`)

Cung cấp các thẻ chỉ số KPI quan trọng và danh sách các mặt hàng đang chạm ngưỡng nguy hiểm cần nhập thêm.

```text
+---------------------------------------------------------------------------------------------+
| TỔNG QUAN TỒN KHO                                                   [Cập nhật: 21/09/2026]  |
+---------------------------------------------------------------------------------------------+
|  [THẺ KPI 1]               [THẺ KPI 2]               [THẺ KPI 3]               [THẺ KPI 4]  |
|  Tổng số mặt hàng          Hàng sắp hết              Phiếu nhập trong tháng    Phiếu xuất   |
|       76 SP                     12 SP                     24 Phiếu               58 Phiếu   |
|  (7 Nhóm hàng)             (CẦN NHẬP GẤP)           (Tổng: 185.000.000 đ)     (12.450 SP)   |
+---------------------------------------------------------------------------------------------+
|  DANH SÁCH HÀNG DƯỚI NGƯỠNG TỒN TỐI THIỂU (LOW STOCK ALERTS)                                |
|  +---------+--------------------------+----------+-----------+------------+---------------+ |
|  | Mã SKU  | Tên sản phẩm             | Tồn kho  | Ngưỡng an | Trạng thái | Thao tác      | |
|  +---------+--------------------------+----------+-----------+------------+---------------+ |
|  | SP-002  | Bàn phím cơ DareU        |    7 Cái |    10 Cái | [SẮP HẾT]  | [+ Lập P.Nhập]| |
|  | SP-004  | Dây cáp mạng CAT6 305m   |   5 Cuộn |   10 Cuộn | [SẮP HẾT]  | [+ Lập P.Nhập]| |
|  | SP-015  | Chuột không dây Logitech |    2 Cái |    15 Cái | [NGUY HIỂM]| [+ Lập P.Nhập]| |
|  +---------+--------------------------+----------+-----------+------------+---------------+ |
+---------------------------------------------------------------------------------------------+
```

---

### 3.2. Màn hình Lập & Điều phối Phiếu Xuất kho 3 Bước (`pages/ExportNotes.jsx`)

Quản lý vòng đời phiếu xuất qua 3 trạng thái: `CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED` kết hợp trừ kho nguyên tử.

```text
+---------------------------------------------------------------------------------------------+
| QUẢN LÝ PHIẾU XUẤT KHO                                             [+ TẠO PHIẾU XUẤT MỚI]   |
+---------------------------------------------------------------------------------------------+
| DANH SÁCH PHIẾU XUẤT:                                                                       |
| +----------------+----------------------+------------+------------+-------------+---------+ |
| | Mã phiếu       | Khách hàng / Người nhận| Ngày xuất  | Trạng thái | Tổng tiền   | Thao tác| |
| +----------------+----------------------+------------+------------+-------------+---------+ |
| | PX-20260921-01 | Cty TNHH Công nghệ ABC | 21/09/2026 | [CHỜ XUẤT] | 4.500.000 đ | [Giao]  | |
| |                |                      |            | (CONFIRMED)|             | [Xóa]   | |
| | PX-20260920-03 | Showroom Tin học XYZ | 20/09/2026 | [ĐANG GIAO]| 8.200.000 đ | [Chốt]  | |
| |                |                      |            | (SHIPPING) |             | [Hủy]   | |
| | PX-20260919-02 | Đại lý Phụ kiện Hoàng| 19/09/2026 |[HOÀN THÀNH]| 1.250.000 đ | [Xem]   | |
| +----------------+----------------------+------------+------------+-------------+---------+ |
| * Lưu ý: Nút [Xóa] chỉ hiển thị khi phiếu ở trạng thái CONFIRMED (chưa trừ tồn kho vật lý). |
| * Hộp thoại ConfirmModal yêu cầu nhập lý do (>= 5 ký tự) khi Hủy hoặc Xóa phiếu.            |
+---------------------------------------------------------------------------------------------+
```

---

### 3.3. Màn hình Thẻ kho / Tra cứu Biến động Tồn (`pages/StockLedger.jsx`)

Truy vết toàn bộ lịch sử biến động số lượng của từng mặt hàng phục vụ kiểm toán (chỉ hiển thị số lượng vật lý, không có cột giá tiền).

```text
+---------------------------------------------------------------------------------------------+
| TRA CỨU THẺ KHO (STOCK LEDGER AUDIT TRAIL)                   [📥 Xuất Thẻ kho Excel (.xlsx)]|
| Chọn mặt hàng: [ SP-001 - Chuột không dây Logitech v ]     Từ ngày: [01/09] Đến ngày: [21/09]|
+---------------------------------------------------------------------------------------------+
| +---------------------+-----------+-------------+-------------+------------+--------------+ |
| | Ngày giờ            | Loại GD   | Số chứng từ | Biến động   | Số dư sau  | Người tạo    | |
| +---------------------+-----------+-------------+-------------+------------+--------------+ |
| | 21/09/2026 14:30:15 | NHẬP KHO  | PN-202609-03| + 50 Cái    | 75 Cái     | thukho       | |
| | 21/09/2026 10:15:02 | XUẤT KHO  | PX-202609-08| - 20 Cái    | 25 Cái     | thukho       | |
| | 18/09/2026 09:00:11 | XUẤT KHO  | PX-202609-05| - 15 Cái    | 45 Cái     | thukho       | |
| | 15/09/2026 16:20:45 | NHẬP KHO  | PN-202609-01| + 60 Cái    | 60 Cái     | admin        | |
| +---------------------+-----------+-------------+-------------+------------+--------------+ |
| Ghi chú: Thẻ kho chỉ theo dõi số lượng tồn kho vật lý và số dư sau giao dịch.               |
+---------------------------------------------------------------------------------------------+
```

---

### 3.4. Màn hình Trợ lý AI & Báo cáo Thông minh (`pages/AIAssistant.jsx`)

Màn hình hợp nhất gồm 4 Tabs: Báo cáo NXT & Xuất Excel, Gợi ý nhập hàng, Cảnh báo bất thường và SmartKho Copilot.

```text
+---------------------------------------------------------------------------------------------+
| TRỢ LÝ KHO & BÁO CÁO (AI COPILOT)                          [Trạng thái AI: ONLINE (Gemini)] |
+---------------------------------------------------------------------------------------------+
|  [TAB 1: BÁO CÁO NXT & EXCEL] [TAB 2: GỢI Ý NHẬP] [TAB 3: BẤT THƯỜNG] [TAB 4: COPILOT CHAT] |
+---------------------------------------------------------------------------------------------+
|  KỲ BÁO CÁO: Tháng [ 09 v ] Năm [ 2026 v ]              [📥 Xuất Báo cáo NXT Excel (.xlsx)] |
|                                                                                             |
|  📊 1. Bảng Tổng hợp Nhập - Xuất - Tồn theo kỳ:                                             |
|  +--------+------------------------+----------+----------+----------+-----------+---------+ |
|  | Mã SKU | Tên mặt hàng           | Tồn đầu  | Nhập kỳ  | Xuất kỳ  | Tồn cuối  | Giá trị | |
|  +--------+------------------------+----------+----------+----------+-----------+---------+ |
|  | SP-001 | Chuột Logitech M331    | 20 Cái   | 100 Cái  | 95 Cái   | 25 Cái    | 7.5 tr  | |
|  | SP-002 | Bàn phím cơ DareU      | 15 Cái   | 50 Cái   | 58 Cái   | 7 Cái     | 3.1 tr  | |
|  +--------+------------------------+----------+----------+----------+-----------+---------+ |
|                                                                                             |
|  🤖 2. Nhận xét Phân tích Thông minh từ Gemini 3.5 Flash Lite:                              |
|  - Tốc độ luân chuyển nhóm Phụ kiện đạt mức rất cao (tỷ lệ xuất/nhập 92%).                   |
|  - Đề xuất bổ sung gấp 50 SP-001 và 30 SP-002 để tránh nguy cơ gián đoạn bán lẻ.           |
+---------------------------------------------------------------------------------------------+
```

---

## 4. Kết luận

Bộ Wireframe trên đảm bảo tính trực quan, phản ánh chính xác cấu trúc thực tế của giao diện web React, hỗ trợ Dark theme, phân quyền 3 vai trò và tích hợp toàn diện phân hệ Trợ lý AI.

---

## 5. Lịch sử đồng bộ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Gộp menu Báo cáo kho:** Loại bỏ mục menu riêng `[R] Báo cáo kho`, tích hợp toàn bộ tính năng Báo cáo NXT và nút xuất Excel vào Tab 1 của trang Trợ lý AI (`AIAssistant.jsx`).
  - **Bổ sung Dark / Light Theme:** Thêm nút toggle theme trên thanh Header.
  - **Bổ sung nút Xuất Excel:** Thêm nút xuất file Excel tại Thẻ kho (`StockLedger.jsx`) và Báo cáo NXT (`AIAssistant.jsx`).
  - **Đồng bộ luồng xuất kho 3 bước:** Bổ sung giao diện quản lý trạng thái `CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED` và nút xóa phiếu chưa xuất kho.
  - **Bổ sung ConfirmModal:** Mô tả hộp thoại xác nhận bắt buộc nhập lý do $\ge 5$ ký tự khi hủy/xóa phiếu.
