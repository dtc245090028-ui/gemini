Thứ tự: PREP, E, D, A, B, C, CLEANUP
Trạng thái: PREP [x] E [ ] D [ ] A [ ] B [ ] C [ ] CLEANUP [ ]

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

---

## Cần bạn quyết
- Không có vướng mắc. Chuẩn bị bước sang hạng mục kế tiếp: **E. Điều tra các điểm còn mở**.
