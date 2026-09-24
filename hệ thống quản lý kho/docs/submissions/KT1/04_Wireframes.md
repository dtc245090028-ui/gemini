# PHÁC THẢO BỐ CỤC GIAO DIỆN NGƯỜI DÙNG (WIREFRAMES)

## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

**Mốc đánh giá:** KT1 — Phân tích yêu cầu & Thiết kế hệ thống  
**Học phần:** Triển khai phần mềm & Ứng dụng AI  
**Ngày hoàn thành:** 2026-09-21  

---

## 1. Triết lý Thiết kế Giao diện

Giao diện của hệ thống được thiết kế theo phong cách hiện đại, tối giản, trực quan trên nền tảng **React 18 + Tailwind CSS**:

- **Trải nghiệm người dùng nhất quán:** Bố cục chia hai phần rõ rệt: Thanh điều hướng (Sidebar bên trái) và Vùng nội dung chính (Main Content bên phải).
- **Phản hồi nghiệp vụ tức thời:** Khi lập phiếu xuất kho, hệ thống tự động kiểm tra số lượng tồn kho thời gian thực; đổi màu đỏ cảnh báo ngay tại ô nhập liệu nếu số lượng vượt quá số dư trong kho.
- **Thân thiện cho buổi thuyết trình (Demo Friendly):** Tích hợp nút **Chuyển vai trò nhanh (Role Switcher)** trên thanh tiêu đề (Header) để sinh viên dễ dàng chuyển đổi qua lại giữa `Admin`, `Thủ kho` và `Kế toán` để chứng minh cơ chế phân quyền RBAC trước hội đồng chấm thi.

---

## 2. Bố cục Tổng thể Hệ thống (Master Layout)

```text
+---------------------------------------------------------------------------------------------+
|  [LOGO] SMART WAREHOUSE AI                       [Vai trò: THỦ KHO v]  [Đăng xuất]         |
+-------------------+-------------------------------------------------------------------------+
| [=] Tổng quan     |  BREADCRUMB: Trang chủ > Tổng quan                                      |
| [P] Hàng hóa      |                                                                         |
| [S] Nhà cung cấp  |  [NỘI DUNG CHỨC NĂNG CỦA TỪNG MÀN HÌNH TẠI ĐÂY]                         |
| [I] Phiếu Nhập    |                                                                         |
| [E] Phiếu Xuất    |                                                                         |
| [L] Thẻ kho       |                                                                         |
| [R] Báo cáo kho   |                                                                         |
| [A] Trợ lý AI     |                                                                         |
+-------------------+-------------------------------------------------------------------------+
| Phiên bản v1.0.0  | Hệ thống quản lý kho Đề tài 07 - Tích hợp AI Gemini                     |
+-------------------+-------------------------------------------------------------------------+
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
|       148 SP                    12 SP                     24 Phiếu               58 Phiếu   |
|  (+3 SP mới tuần này)      (CẦN NHẬP GẤP)           (Tổng: 185.000.000 đ)     (12.450 SP)   |
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

### 3.2. Màn hình Lập Phiếu Xuất kho & Chống Tồn Âm (`pages/ExportNotes.jsx`)

Kiểm tra số lượng tồn theo thời gian thực và ngăn chặn hoàn toàn lỗi xuất âm.

```text
+---------------------------------------------------------------------------------------------+
| LẬP PHIẾU XUẤT KHO                                                  [Hủy] [LƯU PHIẾU XUẤT]  |
+---------------------------------------------------------------------------------------------+
| Người nhận hàng: [ Công ty Cổ phần Công nghệ ABC                      ]                     |
| Ngày xuất:       [ 21/09/2026       ]     Số phiếu: [ PX-20260921-001 (Tự động) ]          |
| Ghi chú:         [ Xuất hàng dự án văn phòng                                       ]        |
+---------------------------------------------------------------------------------------------+
| DANH SÁCH MẶT HÀNG XUẤT:                                                                    |
| +----+----------------------+----------+-------------+---------------+--------------------+ |
| | STT| Chọn sản phẩm        | Tồn hiện | Số lượng    | Đơn giá xuất  | Thành tiền         | |
| +----+----------------------+----------+-------------+---------------+--------------------+ |
| | 1  | Bàn phím cơ DareU    |  7 Cái   | [ 5    ]    | 450.000 đ     | 2.250.000 đ        | |
| | 2  | Chuột không dây Logi |  2 Cái   | [ 10   ] ⚠️ | 250.000 đ     | (Cảnh báo tồn âm!) | |
| +----+----------------------+----------+-------------+---------------+--------------------+ |
| ⚠️ CẢNH BÁO: Mặt hàng 'Chuột không dây Logi' chỉ còn tồn 2 Cái, không thể xuất 10 Cái!      |
|                                                                                             |
| [+ Thêm dòng sản phẩm]                                            TỔNG CỘNG: 2.250.000 đ    |
+---------------------------------------------------------------------------------------------+
| * Lưu ý: Nút [LƯU PHIẾU XUẤT] bị vô hiệu hóa khi có cảnh báo tồn kho âm!                    |
+---------------------------------------------------------------------------------------------+
```

---

### 3.3. Màn hình Thẻ kho / Tra cứu Biến động Tồn (`pages/StockLedger.jsx`)

Truy vết toàn bộ lịch sử biến động số lượng của từng mặt hàng phục vụ kiểm toán.

```text
+---------------------------------------------------------------------------------------------+
| TRA CỨU THẺ KHO (STOCK LEDGER AUDIT TRAIL)                                                  |
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
+---------------------------------------------------------------------------------------------+
```

---

### 3.4. Màn hình Trợ lý AI Thông minh (`pages/AIAssistant.jsx`)

Màn hình 1-Click gọi trợ lý Gemini để sinh báo cáo, gợi ý đặt hàng và cảnh báo bất thường.

```text
+---------------------------------------------------------------------------------------------+
| TRỢ LÝ KHO THÔNG MINH (AI ASSISTANT)                       [Trạng thái AI: ONLINE (Gemini)] |
+---------------------------------------------------------------------------------------------+
|  Chọn kỳ phân tích: Tháng [ 09 v ] Năm [ 2026 v ]                                           |
|                                                                                             |
|  [🤖 1. BÁO CÁO THÁNG]         [💡 2. GỢI Ý NHẬP HÀNG]        [⚠️ 3. PHÁT HIỆN BẤT THƯỜNG]   |
+---------------------------------------------------------------------------------------------+
|  KẾT QUẢ PHÂN TÍCH TỪ AI:                                                                   |
|                                                                                             |
|  📊 1. Đánh giá tốc độ luân chuyển:                                                         |
|  - Trong tháng 09/2026, kho vận hành ổn định với tổng 58 giao dịch xuất kho (tổng 12.450 SP)|
|  - Tỷ lệ quay vòng hàng hóa nhóm 'Phụ kiện' đạt mức cao nhất (85% số lượng nhập đã xuất).   |
|                                                                                             |
|  💡 2. Đề xuất kế hoạch nhập hàng:                                                          |
|  - Cần nhập bổ sung 50 cái 'Chuột không dây Logitech' (Tồn hiện tại: 2, Vận tốc: 3 SP/ngày).|
|  - Cần nhập 30 cái 'Bàn phím cơ DareU' để duy trì mức an toàn tối thiểu trong 15 ngày tới.  |
|                                                                                             |
|  ⚠️ 3. Cảnh báo biến động bất thường:                                                       |
|  - Mặt hàng 'Dây cáp mạng CAT6' không phát sinh bất kỳ giao dịch xuất nào trong 32 ngày qua.|
|    Khuyến nghị kiểm tra hạn bảo quản và áp dụng chính sách chiết khấu để xả hàng.           |
+---------------------------------------------------------------------------------------------+
```

---

## 4. Kết luận

Bộ Wireframe trên đảm bảo tính trực quan, công năng đầy đủ và bám sát toàn bộ yêu cầu nghiệp vụ của Đề tài 07. Đây là căn cứ chuẩn xác để xây dựng giao diện Frontend tại Giai đoạn 6.
