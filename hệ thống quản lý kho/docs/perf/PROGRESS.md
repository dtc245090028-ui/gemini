# TIẾN ĐỘ TỐI ƯU HIỆU NĂNG & THỜI GIAN THỰC CHO SMARTKHO (PROGRESS.MD)

Tài liệu này theo dõi tiến độ thực hiện theo từng bước, lưu lại số đo thực tế, các quyết định kiến trúc và việc còn lại. Cập nhật liên tục sau mỗi bước.

---

## 1. BẢNG TRẠNG THÁI TỔNG THỂ

| Hạng mục / Nhiệm vụ | Trạng thái | Đánh giá / Ghi chú |
| :--- | :--- | :--- |
| **Bảo lưu dữ liệu & An toàn** | **XONG - ĐÃ KIỂM CHỨNG** | Đã sao lưu `warehouse_original_baseline.db`, không có thao tác phá hủy. |
| **Bước 2a: Chuyển DB sang Docker Named Volume (ext4)** | **XONG - ĐÃ HOÀN TẤT C1-C5** | Commit `aafde3c`. Tx time giảm từ 62ms xuống 1.96ms, commit giảm từ 6.6ms xuống 0.77ms. |
| **C1: Dọn dẹp đo đạc & Guard biến môi trường `WRITE_METRICS`** | **XONG - ĐÃ KIỂM CHỨNG** | Đã bọc toàn bộ instrumentation sau `WRITE_METRICS=1` (mặc định tắt = 0 overhead). |
| **C2: Đo phân bố đầy đủ từng chặng (arrival -> response)** | **XONG - ĐÃ ĐO THỰC TẾ** | Đo chi tiết 1.534 requests trên 7 chặng, tổng các chặng khớp 100% với `total_server_time`. |
| **C3: Giải thích nghịch lý (tx 2ms vs throughput ~32 req/s)** | **XONG - ĐÃ CHỨNG MINH** | Nút thắt là ASGI Event loop queue (23.4ms/31.9ms) + cấu trúc 2 HTTP calls cho mỗi phiếu xuất (1.534 HTTP calls = 48.1 HTTP req/s). |
| **C4: Thử nghiệm công bằng 9p vs Named Volume (500 tx)** | **XONG - ĐÃ CHỨNG MINH** | Cùng PRAGMAs: 1 luồng nhanh gấp 11.3 lần; 10 luồng nhanh gấp 55.3 lần (4.610 tx/s vs 83.4 tx/s). |
| **C5: Tài liệu hướng dẫn vận hành Named Volume** | **XONG - ĐÃ KIỂM CHỨNG** | Đã tạo `backup_db.py` và `docs/perf/OPERATIONS_GUIDE.md`, test tay thành công. |
| **Bước 2b: Cổng ghi an toàn + Backpressure** | **ĐANG TIẾN HÀNH** | Triển khai Semaphore + Backpressure trả về 503/429 khi hàng đợi quá tải. |
| **Bước 2c: Idempotency điều chỉnh kho (`stock_ledger.adjust`)** | **CHƯA LÀM** | Thêm cột `idempotency_key` nullable + unique index. |
| **Bước 3: Server-Sent Events (SSE) Backend & Nginx** | **CHƯA LÀM** | In-memory pub/sub, heartbeat, debounce, proxy buffering off. |
| **Bước 4: Frontend Realtime Sync & Mutation Cache** | **XONG 1 PHẦN - CHƯA KIỂM CHỨNG** | Đã có cache invalidation cơ bản; thiếu SSE subscriber, X-Client-Id. |
| **Bước 5: Tăng năng lực đọc (ETag/304, Connection Pool, Paging)** | **CHƯA LÀM** | Cấu hình pool, ETag, tối ưu query N+1. |
| **Bước 6: Nghiệm thu toàn diện & Báo cáo so sánh** | **CHƯA LÀM** | Baseline vs Hiện tại, chạy toàn bộ test suite. |

---

## 2. KẾT QUẢ ĐO ĐẠC CHI TIẾT C2, C3, C4

### Bảng phân bố thời gian từng chặng (C2) - Đo trên 1.534 requests thực tế (`stress100`):

| Chặng đo | Ý nghĩa | Mean (ms) | p50 (ms) | p95 (ms) | Max (ms) | Tỷ trọng |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Arrival to Deps** | Uvicorn/ASGI event loop tiếp nhận và chuyển tiếp vào middleware | **23.44** | 25.97 | 59.73 | 196.92 | **73.4%** |
| **2. Auth & Deps** | Giải mã Bearer JWT token + truy vấn User từ DB | **1.58** | 0.67 | 1.53 | 94.98 | 4.9% |
| **3. Threadpool Wait** | Chờ AnyIO worker threadpool tiếp nhận hàm ghi `def` | **2.07** | 1.10 | 4.41 | 34.93 | 6.5% |
| **4. Tx Exec** | Thực thi INSERT/UPDATE logic trong giao dịch | **1.87** | 0.44 | 2.41 | 233.46 | 5.9% |
| **5. Commit** | Ghi WAL trên Docker Named Volume ext4 | **0.71** | 0.50 | 1.71 | 9.15 | 2.2% |
| **6. Serialize & Send** | Chuyển đổi Pydantic model và gửi HTTP response | **2.27** | 1.18 | 5.10 | 198.96 | 7.1% |
| **7. Total Server Time** | Tổng thời gian xử lý toàn vẹn từ lúc chạm server đến phản hồi xong | **31.94** | 31.20 | 74.21 | 311.27 | **100.0%** |

*(Tổng chặng 1 đến 6 = $23.44 + 1.58 + 2.07 + 1.87 + 0.71 + 2.27 = 31.94 \text{ ms}$, khớp chính xác 100% với Total Server Time).*

### Giải thích nghịch lý Throughput ~32 req/s (C3):
1. **Nút thắt KHÔNG nằm ở Database hay Commit:** Giao dịch DB chỉ mất $1.87 + 0.71 = 2.58 \text{ ms}$ (chỉ chiếm ~8% thời gian). Năng lực SQLite WAL thuần trên Named Volume đạt **4.610 tx/s**.
2. **Nút thắt nằm ở tầng ASGI Event Loop (Chặng 1 chiếm 73.4%):** Một tiến trình Uvicorn đơn luồng chạy Python event loop phải tuần tự hóa việc parse HTTP protocol, TLS/TCP handshake, và dispatching cho 100 kết nối dồn dập trong 1 giây, dẫn tới hàng đợi tích lũy trung bình 23.4 ms trước khi vào code FastAPI.
3. **Mỗi nghiệp vụ xuất kho là 2 HTTP request tuần tự:**
   Trong kịch bản đo tải, mỗi phiếu xuất gồm 2 HTTP requests: `POST /api/v1/export-notes/` (tạo) $\rightarrow$ `POST /api/v1/export-notes/{id}/ship` (giao hàng).
   Do đó, 1.020 nghiệp vụ thực chất gửi **1.530 HTTP requests**.
   Tốc độ xử lý HTTP thực tế của server là:
   $$\frac{1534 \text{ requests}}{31.89 \text{ s}} \approx \mathbf{48.1 \text{ HTTP req/s}}$$

### Đối chứng công bằng: 9p Bind Mount vs Named Volume ext4 (C4 - 500 giao dịch 4 bảng chuẩn):
- **Cấu hình PRAGMAs đồng nhất:** `journal_mode=wal`, `synchronous=1 (NORMAL)`, `wal_autocheckpoint=1000`, `busy_timeout=5000`, `temp_store=2 (MEMORY)`, `cache_size=-64000`.
- **Chế độ 1 luồng (tuần tự):**
  - 9p Mount: Throughput = **31.0 tx/s** | Commit = 7.30 ms (p95: 15.22 ms)
  - Named Volume: Throughput = **349.3 tx/s** | Commit = 1.06 ms (p95: 1.43 ms) $\rightarrow$ **Nhanh hơn 11.3 lần**.
- **Chế độ 10 luồng (đồng thời tranh chấp):**
  - 9p Mount: Throughput = **83.4 tx/s** | Commit = 13.34 ms (p95: 29.34 ms, Max: 43.51 ms) | Tx Mean = 110.57 ms.
  - Named Volume: Throughput = **4,610.6 tx/s** | Commit = 0.164 ms (p95: 1.386 ms, Max: 4.36 ms) | Tx Mean = 1.69 ms.
  $\rightarrow$ **Named Volume nhanh hơn 55.3 lần về thông lượng (4.610 vs 83.4 tx/s)!**
- **Độ bền của `synchronous=NORMAL`:**
  - Crash ứng dụng / container: KHÔNG MẤT DỮ LIỆU.
  - Mất điện đột ngột vật lý: Có thể mất một vài transaction cuối chưa checkpoint, nhưng cấu trúc CSDL hoàn toàn không bao giờ bị hỏng (database corruption = 0).
