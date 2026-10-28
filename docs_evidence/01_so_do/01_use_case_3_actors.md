# SƠ ĐỒ USE CASE THEO 3 ACTOR (RBAC)

**Mã sơ đồ:** `01_use_case_3_actors`  
**Tập tin Mermaid:** [`01_use_case_3_actors.mmd`](01_use_case_3_actors.mmd)  
**Ảnh render:** [`01_use_case_3_actors.png`](01_use_case_3_actors.png)  
**Phương pháp thu thập:** [TỪ GIT/FILE] Trích xuất trực tiếp từ mã nguồn thực tế kiểm tra quyền hạn và endpoints.

---

## 1. Nguồn trích xuất từ mã nguồn thực tế
1. **Kiểm tra phân quyền (Security Dependencies):**
   - [`backend/app/api/deps.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/deps.py#L40-L71): Hàm `require_roles(allowed_roles)` kiểm tra token JWT và so sánh vai trò người dùng trong CSDL (`User.role`).
2. **3 Actor và phạm vi chức năng:**
   - **`ADMIN` (Quản trị viên):**
     - Tạo người dùng mới: [`backend/app/api/v1/endpoints/auth.py#L95-L105`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/auth.py#L95-L105) (`require_roles(["ADMIN"])`).
     - Xóa nhóm hàng: [`backend/app/api/v1/endpoints/categories.py#L132-L140`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/categories.py#L132-L140).
     - Xóa / Ngừng kinh doanh hàng hóa: [`backend/app/api/v1/endpoints/products.py#L278-L287`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/products.py#L278-L287).
     - Xóa / Ngừng hợp tác NCC: [`backend/app/api/v1/endpoints/suppliers.py#L149-L157`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/suppliers.py#L149-L157).
   - **`WAREHOUSE_KEEPER` (Thủ kho):**
     - Thao tác nghiệp vụ danh mục: Tạo / Sửa nhóm hàng, sản phẩm, nhà cung cấp.
     - Nghiệp vụ Nhập/Xuất kho: Lập phiếu nhập (`POST /import-notes/`), hủy phiếu nhập (`POST /import-notes/{id}/cancel`), lập phiếu xuất (`POST /export-notes/`), chuyển bước giao hàng (`ship`), hoàn tất (`complete`), hủy hoàn kho (`cancel`).
     - Điều chỉnh kiểm kê: [`backend/app/api/v1/endpoints/stock_ledger.py#L266-L282`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/stock_ledger.py#L266-L282).
     - Tự động sinh đơn hàng AI: [`backend/app/api/v1/endpoints/ai.py#L124-L143`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/ai.py#L124-L143).
   - **`ACCOUNTANT` (Kế toán kho - Read-only):**
     - Tra cứu thông tin danh mục, sản phẩm, nhà cung cấp, cảnh báo tồn kho (`GET /products/`, `GET /reports/low-stock`).
     - Tra cứu Sổ cái Thẻ kho và xuất Excel: [`backend/app/api/v1/endpoints/stock_ledger.py#L27-L105`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/stock_ledger.py#L27-L105).
     - Xem Báo cáo Nhập-Xuất-Tồn tổng hợp: [`backend/app/api/v1/endpoints/reports.py#L22-L55`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/reports.py#L22-L55).
     - Xem Báo cáo AI Copilot tháng, Gợi ý nhập, Biến động dị thường và Hỏi đáp trợ lý (`endpoints/ai.py`).
     - *Lưu ý:* Kế toán bị chặn hoàn toàn khỏi mọi endpoint POST, PUT, DELETE dữ liệu (trả về HTTP 403 Forbidden).

---

## 2. Ghi chú sự khác biệt so với tài liệu thiết kế ban đầu
- [SUY LUẬN] Trong tài liệu SRS cũ (`01_SRS_and_UseCases.md`), phân hệ AI chỉ đề cập 3 chức năng: Báo cáo tháng, Gợi ý nhập hàng và Dị thường. Mã nguồn thực tế có thêm 2 chức năng:
  1. `POST /api/v1/ai/generate-order`: Tự động sinh đơn hàng xuất kho theo kịch bản khách hàng (dành cho Admin và Thủ kho).
  2. `POST /api/v1/ai/ask`: Hỏi đáp tương tác với trợ lý kho có chế độ phân tích ngữ cảnh `#SmartKho` (mở cho cả 3 vai trò).
- Sơ đồ này cập nhật đầy đủ và chuẩn xác theo mã nguồn đang chạy.
