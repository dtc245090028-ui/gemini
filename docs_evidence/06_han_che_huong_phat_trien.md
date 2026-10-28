# BÁO CÁO HẠN CHẾ HỆ THỐNG VÀ HƯỚNG PHÁT TRIỂN

**Đề tài 07:** Hệ thống Quản lý Kho Thông minh tích hợp AI  
**Người thực hiện đánh giá:** AI Assistant (Phân tích mã nguồn và kiểm chứng thực nghiệm)  
**Thời điểm lập báo cáo:** 2026-10-27T23:30:30+07:00  
**Nguyên tắc đánh giá:** Mọi hạn chế đều đi kèm bằng chứng cụ thể trong mã nguồn (`file:dòng`), cấu trúc CSDL hoặc kết quả đo đạc thực tế; tuyệt đối không nhận định cảm tính.

---

## 1. DANH SÁCH CÁC HẠN CHẾ KỸ THUẬT VÀ NGHIỆP VỤ THỰC TẾ

### Hạn chế 1: Phiếu xuất `CONFIRMED` chưa có cơ chế giữ chỗ tồn kho (Allocated / Reserved Stock)
- **Mô tả hiện tượng:** Khi người dùng lập phiếu xuất kho mới, hệ thống gán trạng thái `CONFIRMED`. Tại trạng thái này, hệ thống chỉ kiểm tra `current_stock >= requested_quantity` tại thời điểm tạo, nhưng **hoàn toàn chưa trừ tồn kho thực tế và chưa có cơ chế tạm giữ chỗ (Hold/Reserve)**.
- **Bằng chứng trong mã nguồn:**
  * File [`backend/app/services/inventory_service.py` L448-L470](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L448-L470):
    ```python
    # Trạng thái ban đầu là CONFIRMED - Chưa trừ tồn kho vật lý
    export_note = ExportNote(..., status="CONFIRMED")
    # current_stock của Product và StockLedger hoàn toàn không bị tác động ở bước này
    ```
  * Tồn kho chỉ thực sự bị trừ khi chuyển trạng thái sang `SHIPPING` tại dòng 505:
    ```python
    product.current_stock -= detail.quantity
    ```
  * Model `Product` tại [`backend/app/models/product.py`](file:///e:/gemini/hệ thống quản lý kho/backend/app/models/product.py) chỉ có duy nhất cột `current_stock`, không có cột `reserved_stock` hoặc `available_stock`.
- **Mức độ ảnh hưởng:** **Trung bình – Nghiệp vụ.** Nếu 2 thủ kho cùng lập 2 phiếu xuất cho cùng một mặt hàng có tồn kho là 10 (mỗi phiếu yêu cầu xuất 10), cả 2 phiếu đều tạo thành công ở trạng thái `CONFIRMED`. Tuy nhiên, khi thủ kho thứ nhất chuyển sang `SHIPPING` (hàng xuất đi, tồn còn 0), thủ kho thứ hai bấm `SHIPPING` sẽ bị hệ thống chặn lại với lỗi `400 Bad Request: Tồn kho không đủ để xuất`. Điều này có thể gây bất ngờ cho nhân viên đóng gói.
- **Hướng khắc phục:** Bổ sung trường `allocated_stock` vào bảng `products`. Khi phiếu ở trạng thái `CONFIRMED`, tăng `allocated_stock`; công thức kiểm tra tồn khả dụng sẽ là:
  $$\text{Tồn khả dụng} = \text{current\_stock} - \text{allocated\_stock}$$
  Khi chuyển sang `SHIPPING`, giảm đồng thời cả `current_stock` và `allocated_stock`.

---

### Hạn chế 2: Giới hạn ghi đơn luồng của CSDL SQLite (Single-Writer Concurrency Bottleneck)
- **Mô tả hiện tượng:** Dự án sử dụng SQLite làm CSDL mặc định. Mặc dù SQLite hỗ trợ nhiều luồng đọc đồng thời, nhưng tại một thời điểm chỉ cho phép duy nhất một giao dịch ghi (Write Lock toàn bộ file database).
- **Bằng chứng trong mã nguồn:**
  * File [`backend/app/services/inventory_service.py` L38-L58](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L38-L58): Nhóm phát triển đã phải viết một decorator bọc ngoài `@retry_on_db_lock(max_retries=3, base_delay=0.1)` để bắt ngoại lệ `sqlite3.OperationalError: database is locked` và thử lại bằng cơ chế exponential backoff kèm jitter.
  * Trong file cấu hình [`backend/app/core/config.py` L19](file:///e:/gemini/hệ thống quản lý kho/backend/app/core/config.py#L19): `DATABASE_URL = "sqlite:///./warehouse.db"`.
- **Mức độ ảnh hưởng:** **Thấp đối với đồ án môn học, Cao đối với môi trường doanh nghiệp lớn.** Khi số lượng giao dịch nhập/xuất tăng vọt (hàng trăm nhân viên thao tác đồng thời), độ trễ ghi sẽ tăng cao và có nguy cơ lỗi timeout `database is locked`.
- **Hướng khắc phục:** Chuyển đổi chuỗi kết nối sang Hệ quản trị CSDL Client-Server mạnh mẽ hơn như **PostgreSQL** (đã được để sẵn ghi chú tại `.env.example`: `postgresql://postgres:postgres@localhost:5432/warehouse_db`) kết hợp cơ chế khóa bi quan cấp độ dòng (`SELECT ... FOR UPDATE`).

---

### Hạn chế 3: Phản hồi của Fallback Engine phụ thuộc vào luật cố định (Rule-Based Heuristic)
- **Mô tả hiện tượng:** Khi mất kết nối Internet, thiếu API Key hoặc khi Google Gemini chạm ngưỡng hạn mức Quota Free Tier (HTTP 429), hệ thống kích hoạt `FallbackService`. Mặc dù cơ chế này đảm bảo phản hồi tức thì (< 50ms) và đúng schema JSON, nhưng nội dung nhận xét dựa trên các mẫu câu ghép chuỗi số học cố định, thiếu tính linh hoạt và chiều sâu phân tích ngữ cảnh tự nhiên của một mô hình ngôn ngữ lớn (LLM).
- **Bằng chứng trong mã nguồn:**
  * File [`backend/app/services/fallback_service.py` L26-L55](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/fallback_service.py#L26-L55): Các câu văn nhận xét được sinh bằng các khối điều kiện `if/else` cố định:
    ```python
    flow_comment = (
        f"Lượng nhập ròng đạt {net_flow} sản phẩm..." if net_flow > 0
        else f"Lượng xuất vượt lượng nhập {abs(net_flow)} sản phẩm..." if net_flow < 0
        else "Lượng nhập và xuất cân bằng hoàn toàn trong kỳ."
    )
    ```
- **Mức độ ảnh hưởng:** **Thấp.** Đây là giải pháp kiến trúc an toàn ("Graceful Degradation") được đánh giá cao trong đồ án vì giúp hệ thống không bao giờ bị crash khi đi chấm thi hoặc mất mạng. Tuy nhiên, người dùng cuối sẽ nhận được nội dung nhận xét lặp lại nếu dữ liệu không có nhiều đột biến.
- **Hướng khắc phục:** Tích hợp mô hình AI nhỏ chạy cục bộ tại máy chủ nội bộ (ví dụ: Ollama chạy model `Qwen2.5-Coder` hoặc `Gemma 2 2B`) làm tầng trung gian giữa Gemini Cloud và Heuristic Fallback.

---

### Hạn chế 4: Giới hạn phạm vi một kho duy nhất (Single-Warehouse Scope)
- **Mô tả hiện tượng:** Toàn bộ kiến trúc dữ liệu hiện tại chỉ quản lý một kho bãi tập trung. Hệ thống chưa hỗ trợ mô hình chuỗi kho bãi (Multi-warehouse / Multi-branch) và chưa quản lý chi tiết vị trí kệ/ô (Bin/Location layout).
- **Bằng chứng trong mã nguồn:**
  * Toàn bộ 9 bảng trong CSDL (`products`, `categories`, `suppliers`, `import_notes`, `export_notes`, `stock_ledger`, `users`) không có bảng `warehouses` và không có trường `warehouse_id`.
  * Không có endpoint điều chuyển hàng giữa các kho (`stock_transfer`).
- **Mức độ ảnh hưởng:** **Trung bình.** Phù hợp hoàn hảo với quy mô doanh nghiệp vừa và nhỏ (SME) theo đúng đề bài, nhưng chưa đáp ứng được các doanh nghiệp logistics hoặc chuỗi bán lẻ đa chi nhánh.
- **Hướng khắc phục:** Bổ sung thực thể `Warehouse` và `WarehouseLocation` (Kệ/Dãy/Tầng); chuyển đổi các phiếu nhập/xuất để gắn với từng kho cụ thể.

---

### Hạn chế 5: Những yêu cầu trong đề tài chưa được phủ trọn vẹn trên Giao diện Frontend
- **Mô tả hiện tượng:** Qua kết quả kiểm chứng tại Phần D, phát hiện 2 điểm giao diện chưa được hoàn thiện tương xứng với Backend:
  1. **Tra cứu theo Nhà cung cấp:** Endpoint `GET /api/v1/import-notes/` có hỗ trợ `supplier_id`, nhưng màn hình `ImportNotes.jsx` chưa có thanh công cụ lọc theo Nhà cung cấp; màn hình Thẻ kho không liên kết với thông tin Nhà cung cấp.
  2. **Báo cáo Nhập-Xuất-Tồn chuyên biệt & Xuất PDF:** Backend có logic tính NXT theo chuẩn kế toán (`GET /api/v1/reports/inventory-summary`) và xuất Excel (`/export-excel`), nhưng trên giao diện React **chưa xây dựng màn hình hiển thị bảng báo cáo NXT chuyên biệt** và hệ thống **hoàn toàn chưa có tính năng xuất file PDF**.
- **Bằng chứng trong mã nguồn:**
  * File [`frontend/src/pages/ImportNotes.jsx`](file:///e:/gemini/hệ thống quản lý kho/frontend/src/pages/ImportNotes.jsx): Bảng danh sách phiếu nhập chỉ hiển thị tên nhà cung cấp, thiếu dropdown filter `supplier_id`.
  * File [`frontend/src/api/client.js` L266-L271](file:///e:/gemini/hệ thống quản lý kho/frontend/src/api/client.js#L266-L271): Khai báo `inventorySummary` và `exportInventorySummaryExcel` nhưng không có file `.jsx` nào trong `frontend/src/pages/` gọi đến các hàm này.
- **Mức độ ảnh hưởng:** **Trung bình.** Người dùng vẫn có thể xem tổng quan qua Dashboard, Thẻ kho và Trợ lý AI, nhưng thiếu một bảng đối soát kế toán chuyên nghiệp trên giao diện web.
- **Hướng khắc phục:**
  1. Thêm bộ lọc `Select Nhà cung cấp` vào thanh công cụ tìm kiếm của trang Phiếu nhập.
  2. Xây dựng thêm một trang mới `InventorySummaryReport.jsx` trên Frontend kết nối với endpoint `/api/v1/reports/inventory-summary` và gắn nút tải file Excel trực tiếp.
  3. Tích hợp thư viện sinh PDF như `@react-pdf/renderer` ở Frontend hoặc `ReportLab` ở Backend.

---

### Hạn chế 6: Độ bao phủ kiểm thử (Coverage) còn thiếu ở một số nhánh phụ và file Cache
- **Mô tả hiện tượng:** Độ bao phủ code tổng thể đạt 83%, nhưng một số nhánh ngoại lệ hiếm gặp chưa được kiểm thử tự động phủ hết.
- **Bằng chứng trong mã nguồn:**
  * Báo cáo kiểm định `test-results/reports/2026-10-02_10-00-00/test-summary.md`: File `app/services/ai_cache.py` đạt độ bao phủ 83%, còn thiếu kiểm thử cho các dòng 34, 38-40, 48-49, 65-67 (các đoạn xử lý ngoại lệ file cache JSON bị hỏng, lỗi IO disk hoặc không có quyền ghi file).
- **Mức độ ảnh hưởng:** **Thấp.** Không ảnh hưởng đến luồng nghiệp vụ chính.
- **Hướng khắc phục:** Viết thêm các bài unit test giả lập lỗi hệ thống file (`mock OSError`, `mock JSONDecodeError`) khi đọc/ghi file `ai_cache.json`.

---

## 2. LỘ TRÌNH PHÁT TRIỂN NÂNG CẤP (ROADMAP)

```mermaid
flowchart LR
    A["Giai đoạn Hiện tại (v1.0)<br/>FastAPI + SQLite + React<br/>Single Warehouse + Gemini Flash-Lite"] --> B["Giai đoạn Nâng cấp Ngắn hạn (v1.1)<br/>Thêm UI Báo cáo NXT<br/>Lọc NCC trên Frontend<br/>Bổ sung Allocated Stock"]
    B --> C["Giai đoạn Nâng cấp Trung hạn (v2.0)<br/>Chuyển sang PostgreSQL<br/>Tích hợp Local LLM (Ollama)<br/>Xuất báo cáo PDF tự động"]
    C --> D["Giai đoạn Hoàn thiện Doanh nghiệp (v3.0)<br/>Quản lý Đa kho (Multi-warehouse)<br/>Sơ đồ vị trí kệ hàng (Bin Location)<br/>Quét mã vạch Barcode/QR bằng Camera"]
```

1. **Ngắn hạn (1-2 tuần):**
   - Bổ sung màn hình giao diện "Báo cáo Nhập - Xuất - Tồn" trên React Frontend và tích hợp nút gọi `exportInventorySummaryExcel`.
   - Bổ sung dropdown lọc Nhà cung cấp trong trang Phiếu nhập kho.
   - Thêm cột `allocated_stock` để giải quyết triệt để bài toán giữ chỗ tồn kho khi phiếu ở trạng thái `CONFIRMED`.
2. **Trung hạn (1-2 tháng):**
   - Chuyển CSDL sang PostgreSQL để tối ưu hóa năng lực xử lý đa luồng đồng thời.
   - Bổ sung tính năng xuất báo cáo định dạng PDF có đóng dấu điện tử và biểu đồ trực quan.
   - Cung cấp tùy chọn cấu hình Local LLM qua Ollama để doanh nghiệp tự chủ 100% dữ liệu offline.
3. **Dài hạn (3-6 tháng):**
   - Mở rộng kiến trúc Đa kho (Multi-warehouse) và quản lý chuyển kho nội bộ.
   - Xây dựng ứng dụng di động (Mobile App) hỗ trợ thủ kho quét mã QR/Barcode trên kiện hàng bằng camera điện thoại.
