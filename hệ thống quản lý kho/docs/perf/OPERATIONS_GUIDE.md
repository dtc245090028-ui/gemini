# HƯỚNG DẪN VẬN HÀNH CƠ SỞ DỮ LIỆU & HỆ THỐNG SMARTKHO

Tài liệu này hướng dẫn cách kiểm tra toàn vẹn, đo tải, sao lưu online, phục hồi cơ sở dữ liệu SQLite sau khi chuyển sang Docker Named Volume `warehouse_data` (ext4), cùng các ràng buộc cấu hình và đánh đổi kỹ thuật trọng yếu trong môi trường vận hành thực tế.

---

## 1. RÀNG BUỘC KIẾN TRÚC BẮT BUỘC (ARCHITECTURAL CONSTRAINTS)

> [!CAUTION]
> **RÀNG BUỘC SỐ LƯỢNG WORKER CỦA UVICORN:**
> **Hệ thống chỉ chạy đúng khi uvicorn dùng 1 worker; nếu tăng worker sẽ hỏng in-process write gate và in-process SSE pub/sub.**
>
> **Lý do kỹ thuật:**
> 1. **Write Gate FIFO (`app.core.write_gate`):** Được thiết kế in-process sử dụng `collections.deque` và `threading.Event` để tuần tự hóa an toàn các thao tác ghi vào SQLite (tránh lỗi `database is locked`). Nếu cấu hình nhiều worker (nhiều tiến trình OS khác nhau), mỗi worker sẽ sở hữu một hàng đợi riêng biệt, dẫn đến việc nhiều tiến trình cùng ghi đồng thời vào file CSDL SQLite và làm vỡ cổng tuần tự hóa.
> 2. **SSE Pub/Sub Broadcaster (`app.core.broadcaster`):** Bộ phân phối sự kiện realtime hoạt động in-memory trong không gian bộ nhớ của tiến trình FastAPI. Khi chạy đa worker, sự kiện phát ra từ worker xử lý ghi sẽ không thể chuyển giao sang các client SSE đang giữ kết nối ở worker khác (trừ khi tích hợp thêm Redis Pub/Sub bên ngoài).
>
> Khi cần mở rộng quy mô đa tiến trình/đa node (horizontal scaling), kiến trúc bắt buộc phải:
> - Chuyển sang hệ quản trị CSDL đa luồng máy chủ (PostgreSQL).
> - Sử dụng Redis Pub/Sub cho kênh truyền SSE.
> - Bỏ cơ chế in-process Write Gate.

---

## 2. ĐÁNH ĐỔI ĐỘ BỀN CỦA PRAGMA `synchronous = NORMAL` (DURABILITY TRADE-OFF)

Cấu hình PRAGMA kết nối mặc định trong SQLAlchemy Connection Pool (`app/core/database.py`):
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;       -- (Giá trị số: 1)
PRAGMA busy_timeout = 5000;        -- (5.000 ms)
PRAGMA wal_autocheckpoint = 1000;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -64000;        -- (64 MB)
```

### Phân tích đánh đổi độ bền dữ liệu:
* **Khả năng chịu lỗi phần mềm & Crash container:**
  * Với `journal_mode = WAL` và `synchronous = NORMAL`, mỗi giao dịch `commit()` đều được ghi thành công vào file WAL (`warehouse.db-wal`). Nếu ứng dụng FastAPI bị crash, Python process bị kill đột ngột (`SIGKILL`), hoặc Docker container bị tắt bất ngờ, **100% dữ liệu đã commit vẫn an toàn tuyệt đối**, không bị mất mát hay hỏng hóc.
* **Đánh đổi khi mất điện đột ngột máy chủ vật lý (Host Power Loss / OS Crash):**
  * Ở chế độ `NORMAL`, hệ điều hành không bắt buộc gọi lệnh flush phần cứng (`fsync()`) ở mỗi commit nhỏ (chỉ fsync định kỳ khi checkpoint WAL). Do đó, nếu máy chủ vật lý bị mất điện đột ngột hoặc hệ điều hành máy chủ bị crash:
    * **Có thể mất dữ liệu của vài giao dịch gần nhất** (những giao dịch còn nằm trong OS page cache chưa kịp flush xuống đĩa).
    * **TUYỆT ĐỐI KHÔNG HỎNG CẤU TRÚC CSDL:** File SQLite không bao giờ bị corrupt cấu trúc nhờ cơ chế kiểm tra toàn vẹn checksum theo từng frame của WAL. Khi khởi động lại, SQLite chỉ rollback các frame chưa hoàn tất.
* **Lựa chọn cấu hình theo yêu cầu nghiệp vụ:**
  * Nếu hệ thống ưu tiên thông lượng ghi cao (~50 - 100 req/s) và chạy trên hạ tầng có UPS / Cloud VM: Giữ nguyên `synchronous = NORMAL` (Commit latency siêu nhanh ~0.6ms).
  * Nếu bắt buộc độ bền tuyệt đối chống cúp điện vật lý (chuẩn ACID nghiêm ngặt mức tài chính): Đổi sang `PRAGMA synchronous = FULL;`. Đánh đổi: độ trễ mỗi lần commit sẽ tăng lên 2-5ms do phải chờ ổ cứng fsync vật lý ở mọi giao dịch.

---

## 3. Vị trí CSDL và Biến Môi Trường

* **CSDL trong Named Volume:** `/var/lib/warehouse/warehouse.db` (Filesystem: `ext4` native trên Linux container, loại bỏ hoàn toàn độ trễ ảo hóa mạng 9p).
* **Biến môi trường:** `DATABASE_URL=sqlite:////var/lib/warehouse/warehouse.db`
* **Docker Compose:** Đã ánh xạ volume `warehouse_data:/var/lib/warehouse`.
* **Biến an toàn production:** `BENCH_ENDPOINTS=0` và `WRITE_METRICS=0` mặc định tắt.

---

## 4. Kiểm tra 5 Bất biến Toàn vẹn Dữ liệu (`check_invariants`)

Script có cơ chế tự động phát hiện môi trường:
* **Từ Windows Host:**
  ```powershell
  python backend/tests/performance/check_invariants.py
  ```
  *(Script tự động ủy quyền thực thi vào container `warehouse_backend` để tránh xung đột khóa WAL).*
* **Trực tiếp trong container:**
  ```bash
  docker exec warehouse_backend python /app/tests/performance/check_invariants.py
  ```

---

## 5. Chạy Kịch bản Đo Tải & Dọn dẹp Demo

* **Chạy kịch bản đo tải (Stress 100 RPS):**
  ```powershell
  python backend/tests/performance/demo_run.py --profile stress100
  ```
* **Dọn dẹp sạch dữ liệu demo sau khi quan sát:**
  ```powershell
  python backend/tests/performance/demo_cleanup.py --yes
  ```
  *(Tự động kiểm tra snapshot 6 bảng trọng yếu, đảm bảo đối chiếu lệch đúng 0 dòng).*

---

## 6. Sao lưu CSDL Online An toàn (Không khóa hệ thống)

> [!IMPORTANT]
> **TUYỆT ĐỐI KHÔNG** dùng lệnh copy file trực tiếp (`cp warehouse.db ...`) khi CSDL đang mở ở chế độ WAL, vì sẽ bỏ sót dữ liệu trong `-wal` hoặc gây hỏng file (file corruption).
> Hãy sử dụng công cụ Online Backup API được xây dựng sẵn:

* **Tạo bản sao lưu Online:**
  ```bash
  docker exec warehouse_backend python -m app.core.backup_db backup --file /var/lib/warehouse/backups/warehouse_manual_backup.db
  ```
* **Sao chép file sao lưu ra máy host Windows:**
  ```powershell
  docker cp warehouse_backend:/var/lib/warehouse/backups/warehouse_manual_backup.db ./backend/backups/warehouse_manual_backup.db
  ```
* **Kiểm tra trạng thái & tính toàn vẹn CSDL:**
  ```bash
  docker exec warehouse_backend python -m app.core.backup_db status
  ```

---

## 7. Phục hồi CSDL từ bản sao lưu

* **Phục hồi CSDL từ file backup đã lưu:**
  ```bash
  docker exec warehouse_backend python -m app.core.backup_db restore --file /var/lib/warehouse/backups/warehouse_manual_backup.db
  ```
* **Chạy kiểm tra bất biến ngay sau phục hồi:**
  ```powershell
  python backend/tests/performance/check_invariants.py
  ```

---

## 8. Hướng dẫn Người dùng Kiểm tra Thủ công Giao diện & SSE Realtime (CHƯA THỬ, chờ người dùng)

Do môi trường tự động hóa CLI không thể click chuột trực tiếp trên trình duyệt web, người dùng có thể thực hiện kiểm chứng trực quan bằng các bước sau:

1. **Chuẩn bị 2 tab trình duyệt:**
   - Mở Tab 1: `http://localhost:5173` -> Đăng nhập tài khoản `admin` / `admin123` -> Mở trang **Bảng điều khiển (Dashboard)** hoặc **Hàng hóa & Tồn kho (Products)**.
   - Mở Tab 2: `http://localhost:5173` -> Đăng nhập `admin` / `admin123` -> Mở trang **Nhà cung cấp (Suppliers)** hoặc **Xuất kho (Export Notes)**.
2. **Thực hiện thao tác thay đổi dữ liệu trên Tab 2:**
   - Bấm nút **"Thêm nhà cung cấp"**, điền thông tin và lưu lại.
3. **Quan sát Tab 1 (TUYỆT ĐỐI KHÔNG BẤM F5):**
   - Sự kiện SSE sẽ được đẩy xuống kênh stream `/api/v1/events/stream` trong vòng ~200ms.
   - Tab 1 tự động cập nhật danh sách nhà cung cấp mới vào dropdown form hàng hóa và cập nhật số liệu mà không cần tải lại trang.
4. **Kiểm tra hiển thị số tổng (Total Count):**
   - Mở trang **Thẻ kho (StockLedger)**: quan sát dòng chân trang hiển thị `Hiển thị 1 - 50 trên tổng số N dòng thẻ kho` (N phản ánh chính xác toàn bộ bản ghi của CSDL thay vì chỉ hiển thị 50).
5. **Kiểm tra khi ẩn/hiện tab (`visibilitychange`):**
   - Chuyển Tab 1 sang chế độ background (chuyển sang xem tab khác) trong 1 phút, thực hiện ghi dữ liệu ở Tab 2, sau đó quay lại Tab 1. Tab 1 sẽ tự động kích hoạt kiểm tra stale qua ETag và refresh dữ liệu mới nhất.
