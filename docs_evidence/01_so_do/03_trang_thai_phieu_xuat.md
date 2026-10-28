# SƠ ĐỒ TRẠNG THÁI PHIẾU XUẤT KHO VÀ TÁC ĐỘNG TỒN KHO - THẺ KHO

**Mã sơ đồ:** `03_trang_thai_phieu_xuat`  
**Tập tin Mermaid:** [`03_trang_thai_phieu_xuat.mmd`](03_trang_thai_phieu_xuat.mmd)  
**Ảnh render:** [`03_trang_thai_phieu_xuat.png`](03_trang_thai_phieu_xuat.png)  
**Phương pháp thu thập:** [TỪ GIT/FILE] Trích xuất từ định nghĩa Model `ExportNote` và 4 hàm xử lý trạng thái trong `inventory_service.py`.

---

## 1. Nguồn trích xuất từ mã nguồn thực tế
1. **Định nghĩa 4 trạng thái trong Model:**
   - [`backend/app/models/export_note.py#L19`](file:///E:/gemini/hệ thống quản lý kho/backend/app/models/export_note.py#L19):
     `status = Column(String(20), nullable=False, default="CONFIRMED") # CONFIRMED, SHIPPING, COMPLETED, CANCELLED`
2. **Hành vi chuyển trạng thái & Tác động số liệu:**
   - **Tạo mới $\rightarrow$ `CONFIRMED`:**
     - Nguồn: [`inventory_service.py#L251-L260`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L251-L260).
     - *Tồn kho:* Giữ nguyên.
     - *Thẻ kho:* Chưa ghi bản ghi nào.
     - *Ý nghĩa:* Khắc phục triệt để lỗi "Giam hàng ảo" (Phantom Stock Hold) gặp ở các hệ thống WMS truyền thống.
   - **`CONFIRMED` $\rightarrow$ `SHIPPING`:**
     - Nguồn: [`inventory_service.py#L391-L480`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L391-L480).
     - *Tồn kho:* Trừ nguyên tử bằng SQL `UPDATE products SET current_stock = current_stock - :qty WHERE id = :prod_id AND current_stock >= :qty RETURNING current_stock`.
     - *Thẻ kho:* Ghi 1 bản ghi `StockLedger` (loại `EXPORT`, `quantity_change = -qty`, `balance_after = new_balance`).
   - **`SHIPPING` $\rightarrow$ `COMPLETED`:**
     - Nguồn: [`inventory_service.py#L484-L516`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L484-L516).
     - *Tồn kho & Thẻ kho:* Giữ nguyên. Phiếu bị khóa vĩnh viễn (Read-only), bảo đảm tính pháp lý của chứng từ kế toán.
   - **Hủy khi `CONFIRMED` (Xóa cứng):**
     - Nguồn: [`inventory_service.py#L528-L536`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L528-L536), [`export_notes.py#L216-L225`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/export_notes.py#L216-L225).
     - *Hành vi:* Xóa hoàn toàn bản ghi khỏi CSDL (`db.delete(export_note)`), không ảnh hưởng tồn kho hay thẻ kho.
   - **Hủy khi `SHIPPING` (Hoàn kho 100%):**
     - Nguồn: [`inventory_service.py#L540-L587`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L540-L587).
     - *Tồn kho:* Hoàn lại nguyên tử `current_stock = current_stock + qty`.
     - *Thẻ kho:* Ghi bản ghi `ADJUSTMENT` với mã tham chiếu `CANCEL-PX-YYYYMMDD-XXXX`, `quantity_change = +qty`.
     - *Trạng thái:* Chuyển sang `CANCELLED`, giữ nguyên phiếu để phục vụ đối soát kiểm toán.

---

## 2. Ghi chú so sánh
- [SUY LUẬN] Tài liệu cũ ở KT1 ghi nhận `DRAFT | COMPLETED | CANCELLED`. Trong mã nguồn thực tế (KT2 đến Final), cỗ máy trạng thái xuất kho đã được chuẩn hóa thành 4 trạng thái (`CONFIRMED`, `SHIPPING`, `COMPLETED`, `CANCELLED`). Sơ đồ này phản ánh chính xác 100% kiến trúc đang chạy trên hệ thống.
