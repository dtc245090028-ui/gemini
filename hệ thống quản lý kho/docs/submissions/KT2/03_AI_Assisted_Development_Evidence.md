# MINH CHỨNG SỬ DỤNG AI TRONG QUÁ TRÌNH PHÁT TRIỂN SDLC (BÀI KT2)

## Đề tài 07: Hệ thống Quản lý Kho Thông minh tích hợp AI

---

## 1. MỤC TIÊU & BỐI CẢNH MINH CHỨNG

Tài liệu này ghi nhận bằng chứng thực tế về việc sinh viên áp dụng Trí tuệ Nhân tạo (AI Assistant) như một **"Lập trình viên cặp đôi (Pair Programmer)"** trong suốt Giai đoạn 2 và Giai đoạn 3 (Mốc đánh giá KT2).

Mục tiêu không phải là để AI viết thay toàn bộ mà là **sử dụng AI có định hướng, kiểm soát chất lượng chặt chẽ, phát hiện lỗ hổng logic nghiệp vụ sớm và tối ưu hóa giải pháp kỹ thuật**.

---

## 2. CÁC TÌNH HUỐNG KỸ THUẬT TIÊU BIỂU CÓ SỰ THAM GIA CỦA AI

### Tình huống 1: Phát hiện lỗ hổng tồn âm khi Hủy phiếu nhập cũ (Critical Edge Case)

- **Vấn đề đặt ra:** Ban đầu kế hoạch cho phép hủy phiếu nhập kho bằng cách trừ ngược lại số lượng đã nhập.
- **AI & Con người phối hợp phân tích:**
  - AI cùng sinh viên phát hiện ra kịch bản rủi ro: Nếu phiếu nhập 100 sản phẩm đã nhập từ 5 ngày trước, nhưng 80 sản phẩm đã bị xuất bán cho khách qua các phiếu xuất sau đó (tồn kho hiện chỉ còn 20). Nếu cho phép hủy phiếu nhập, kho sẽ bị trừ 100 cái $\rightarrow$ tồn thành $20 - 100 = -80$ (âm kho nghiêm trọng, vi phạm nguyên tắc bất biến).
- **Giải pháp sinh ra:**
  - Thiết kế cơ chế **Guard-check (Phương án B)**: Kiểm tra số tồn hiện tại trước khi cho phép hủy phiếu nhập.
  - Bổ sung **Lối thoát nghiệp vụ kiểm kê (Phương án A)**: Endpoint `/api/v1/stock-ledger/adjust` theo chuẩn kế toán ERP (SAP, MISA) để điều chỉnh số dư thực tế thay vì hủy hồi tố mờ ám.

---

### Tình huống 2: Giải quyết xung đột Race Condition khi sinh mã phiếu tự động

- **Vấn đề đặt ra:** Khi 2 thủ kho cùng lúc tạo phiếu ở cùng một mili-giây, cả 2 có thể cùng sinh ra mã `PN-20260922-0001`, dẫn đến xung đột khóa Unique trên CSDL.
- **AI & Con người phối hợp phân tích:**
  - Thay vì dùng cơ chế Lock bảng gây nghẽn hiệu năng (Pessimistic Locking), AI đề xuất mô hình **Optimistic Concurrency Control kết hợp Retry Pattern**:
    - Để CSDL làm trọng tài cuối cùng chặn mã trùng.
    - Tầng Dịch vụ `InventoryService` bắt ngoại lệ `IntegrityError` và tự động sinh lại mã kế tiếp với số lần thử lại tối đa (3 lần).
- **Kết quả:** Xử lý triệt để đụng độ đồng thời một cách trong suốt với người dùng.

---

### Tình huống 3: Chuẩn hóa công thức Báo cáo Nhập - Xuất - Tồn theo thời gian thực

- **Vấn đề đặt ra:** Bảng `products` chỉ lưu số tồn tức thời ở thời điểm hiện tại, không thể biết chính xác tồn kho của ngày hôm qua hay tuần trước.
- **AI & Con người phối hợp phân tích:**
  - Sử dụng bảng Thẻ kho `StockLedger` (Audit Trail) làm nguồn chân lý duy nhất.
  - Xây dựng thuật toán tính toán:
    $$\text{Tồn đầu kỳ} = \text{balance\_after của giao dịch gần nhất trước ngày bắt đầu}$$
    $$\text{Tồn cuối kỳ} = \text{Tồn đầu kỳ} + \text{Nhập trong kỳ} - \text{Xuất trong kỳ}$$
- **Kết quả:** Báo cáo luôn đảm bảo tính cân đối kế toán 100%, sẵn sàng giải trình trước hội đồng chấm thi.

---

## 3. BẢNG SO SÁNH TRƯỚC VÀ SAU KHI ỨNG DỤNG AI

| Hạng mục | Quy trình truyền thống (Không AI) | Quy trình có AI hỗ trợ (Pair Programming) |
| --- | --- | --- |
| **Phát hiện lỗi logic** | Thường chỉ phát hiện khi chạy thử nghiệm hoặc bị chấm điểm trừ khi demo. | Phát hiện và chặn đứng ngay từ khâu thiết kế (như lỗi hủy phiếu gây âm kho). |
| **Thiết kế Transaction ACID** | Dễ bỏ sót bước ghi Thẻ kho hoặc quên rollback khi xuất thiếu hàng. | Cấu trúc code chặt chẽ, bao bọc toàn bộ chu trình trong 1 transaction an toàn. |
| **Độ phủ kiểm thử (Test Coverage)** | Viết ít test, chỉ test trường hợp chạy đúng (Happy path). | Xây dựng bộ test tự động toàn diện 24 bài test bao quát cả Happy path và Edge cases. |
| **Tài liệu kỹ thuật** | Viết sơ sài sau khi code xong. | Tài liệu hóa đồng thời từng bước (`01_API_Specifications.md`, `02_Transaction_Design...`, `architecture.md`). |

---

## 4. KẾT LUẬN & CAM KẾT HỌC THUẬT

Việc ứng dụng AI trong đồ án đã giúp nâng cao chất lượng kỹ thuật, tính ổn định và tính chuyên nghiệp của hệ thống tương đương tiêu chuẩn các phần mềm quản lý doanh nghiệp thực tế. Sinh viên hoàn toàn làm chủ kiến trúc, hiểu rõ từng dòng mã nguồn và tự tin thuyết trình bảo vệ trước hội đồng phản biện.
