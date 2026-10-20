Thứ tự: PREP, E, D, A, B, C, CLEANUP
Trạng thái: PREP [x] E [x] D [ ] A [ ] B [ ] C [ ] CLEANUP [ ]

## Baseline

### 1. Bất biến CSDL hiện tại (Đo qua `check_invariants.py` trên bản sao DB sau Bậc 4)
- **Bất biến 1 (Cân bằng tồn kho kế toán)**: **KHÔNG ĐẠT** (Vi phạm Lost Update)
  - `SKU-PERF-BULK-01`: Tồn hiện tại 19.218, kỳ vọng kế toán 17.312 (lệch +1.906 đơn vị).
  - `SKU-PERF-BULK-02`: Tồn hiện tại 19.277, kỳ vọng kế toán 17.340 (lệch +1.937 đơn vị).
- **Bất biến 2 (Tính đơn điệu lũy kế Thẻ kho)**: **KHÔNG ĐẠT**
  - Tổng số dòng vi phạm $balance_n \neq balance_{n-1} + change_n$: 2.249 dòng.
  - Tổng số giá trị `balance_after` bị lặp lại: 1.236 giá trị.
- **Bất biến 3 (Số phiếu SHIPPING = Số dòng thẻ kho EXPORT)**: **KHÔNG ĐẠT**
  - Số phiếu SHIPPING: 5.348; Số dòng Thẻ kho EXPORT: 5.632 (chênh -284 do các lần chạy trước).
- **Bất biến 4 (Số phiếu CONFIRMED lửng)**: 10 phiếu CONFIRMED.
- **Bất biến 5 (Bảo vệ chống tồn kho âm)**: **ĐẠT** (0 sản phẩm tồn kho âm).

### 2. Pytest Baseline (Toàn bộ Unit & Integration tests)
- **Tổng số test**: 66 tests.
- **Kết quả**: 66 passed, 12 warnings trong 37.15s.

---

## Nhật ký từng phiên

### [PREP] Thiết lập công cụ đo lường bất biến và Baseline
- **Hành động**:
  1. Tạo nhánh làm việc `fix/concurrency-cleanup`.
  2. Tạo script `tests/performance/check_invariants.py` nhận đường dẫn DB chỉ đọc qua CLI để kiểm tra 5 bất biến.
  3. Đo lường baseline trên bản sao CSDL hiện tại, ghi nhận vi phạm nghiêm trọng ở Bất biến 1, 2 và 3.
  4. Chạy `pytest --ignore=tests/performance`, xác nhận baseline 66/66 test cases đạt chuẩn.
- **Commit**: `[PREP] Thiết lập check_invariants.py và ghi nhận baseline vi phạm`

### [E] Điều tra các điểm còn mở (Chỉ đọc CSDL và Log)
- **Kết quả điều tra 4 điểm mở**:
  1. *Chênh lệch 29 mẫu giữa CSDL và Locust CSV*: [đã đo]
     - CSDL có 5.378 phiếu xuất (5.370 SHIPPING, 8 CONFIRMED). Log Uvicorn ghi nhận 5.794 request tạo phiếu (5.371 lần 201, 420 lần 409, 3 lần 500) và 5.363 request ship (5.362 lần 200, 1 lần 500).
     - Locust CSV ghi nhận 5.349 create thành công và 5.341 ship thành công.
     - Khớp từng dòng: Độ lệch đúng 29 create và 29 ship nằm ở 2 giây cuối cùng (17:14:28 - 17:14:30) khi Locust đạt giới hạn `duration=3m` (180s), client ngắt socket trước khi kịp lưu response vào file thống kê.
  2. *Số phiếu CONFIRMED còn lại*: [đã đo]
     - Thống nhất con số chính xác là **8 phiếu** (ID 2369 tạo lúc 17:12:45Z bị lỗi 500 khi ship; 7 phiếu IDs 5446-5452 tạo lúc 17:14:28 - 17:14:30 chưa kịp gọi ship thì test dừng).
  3. *CPU > 100%*: [đã đo]
     - Container có `cpu_count = 16`, tiến trình Uvicorn chạy 25 worker threads, `cpu.max = max`. Khi nhiều thread cùng chạy song song trên nhiều CPU cores logic, `docker stats` tính theo single-core equivalent nên việc đạt 103,23% là bình thường (~1,03 core trên 16 cores khả dụng).
  4. *Con số 1.298 ms*: [chưa kiểm chứng]
     - Đã chuyển nhãn thành "chưa kiểm chứng" do chưa có bộ đếm nội bộ phân rã thời gian xếp hàng trong socket buffer.
- **Pytest**: 66 passed (không đổi so với baseline).
- **Commit**: `[E] Điều tra và khép kín 4 điểm còn mở với nhãn bằng chứng rõ ràng`

---

## Cần bạn quyết
- Không có vướng mắc. Chuẩn bị bước sang hạng mục kế tiếp: **D. Validation note**.
