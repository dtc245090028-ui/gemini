# SƠ ĐỒ LUỒNG NHẬP KHO VÀ XUẤT KHO TOÀN DIỆN

**Mã sơ đồ:** `02_luong_nhap_xuat_kho`  
**Tập tin Mermaid:** [`02_luong_nhap_xuat_kho.mmd`](02_luong_nhap_xuat_kho.mmd)  
**Ảnh render:** [`02_luong_nhap_xuat_kho.png`](02_luong_nhap_xuat_kho.png)  
**Phương pháp thu thập:** [TỪ GIT/FILE] Trích xuất từ mã nguồn xử lý giao dịch tại `inventory_service.py` và các router endpoints.

---

## 1. Nguồn trích xuất từ mã nguồn thực tế
1. **Luồng Nhập kho (`create_import_note`):**
   - [`backend/app/services/inventory_service.py#L47-L182`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L47-L182).
   - Kiểm tra trùng lặp khóa `idempotency_key` (dòng 63-67).
   - Kiểm tra nhà cung cấp và trạng thái sản phẩm `DISCONTINUED` (dòng 70-91).
   - Vòng lặp Retry tối đa 7 lần với Exponential Backoff & Random Jitter (dòng 98-182).
   - Câu lệnh cập nhật nguyên tử `UPDATE products SET current_stock = current_stock + :qty RETURNING current_stock` (dòng 138-146).
   - Ghi Thẻ kho `StockLedger` loại `IMPORT` (dòng 151-162).
2. **Luồng Hủy phiếu nhập kho (`cancel_import_note`):**
   - [`backend/app/services/inventory_service.py#L298-L389`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L298-L389).
   - **Cơ chế Guard-check chống tồn âm:** Duyệt toàn bộ chi tiết, nếu `product.current_stock < detail.quantity` thì từ chối hủy (HTTP 400 Bad Request) và hướng dẫn sử dụng tính năng "Điều chỉnh kiểm kê tồn kho" (dòng 320-335).
   - Nếu đủ tồn kho để trừ: Trừ tồn kho nguyên tử, ghi Thẻ kho `ADJUSTMENT` với mã tham chiếu `CANCEL-PN-...`, đổi trạng thái sang `CANCELLED` (dòng 345-385).
3. **Luồng Xuất kho (`create_export_note`, `ship_export_note`, `complete_export_note`, `cancel_export_note`):**
   - [`backend/app/services/inventory_service.py#L184-L290`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L184-L290) (`create_export_note`):
     - Kiểm tra `product.current_stock < item.quantity` $\rightarrow$ ném HTTP 400 Bad Request ngay từ đầu, rollback 100%.
     - Tạo phiếu `CONFIRMED`, chưa trừ tồn kho nhằm tránh giam hàng ảo.
   - [`backend/app/services/inventory_service.py#L391-L480`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L391-L480) (`ship_export_note`):
     - Guard-check lần 2 tại thời điểm giao hàng thực tế.
     - Câu lệnh SQL nguyên tử: `UPDATE products SET current_stock = current_stock - :qty WHERE id = :prod_id AND current_stock >= :qty RETURNING current_stock` (dòng 444-453).
     - Ghi Thẻ kho loại `EXPORT` (dòng 467-478).
   - [`backend/app/services/inventory_service.py#L484-L516`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L484-L516) (`complete_export_note`): Khóa phiếu ở trạng thái `COMPLETED`.
   - [`backend/app/services/inventory_service.py#L518-L593`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L518-L593) (`cancel_export_note`):
     - Hủy khi `CONFIRMED`: Xóa cứng khỏi CSDL (Hard delete) để không rác bảng (`was_deleted = True`).
     - Hủy khi `SHIPPING`: Đổi trạng thái sang `CANCELLED`, hoàn trả 100% tồn kho và ghi Thẻ kho `ADJUSTMENT` mã `CANCEL-PX-...`.

---

## 2. Ghi chú sự khác biệt so với tài liệu thiết kế ban đầu
- [SUY LUẬN] Tài liệu cũ ở KT1 chỉ vẽ sơ đồ luồng thành công (Happy Path). Sơ đồ này phản ánh đúng thực tế mã nguồn sau khi trải qua các bài kiểm thử tải và PR #1:
  1. Đã tích hợp nhánh kiểm tra `X-Idempotency-Key` ở đầu vào cả 2 luồng.
  2. Bổ sung Guard-check tại hàm hủy phiếu nhập.
  3. Cỗ máy xuất kho 3 bước rõ ràng giữa `CONFIRMED` (chưa trừ kho) và `SHIPPING` (mới trừ kho).
