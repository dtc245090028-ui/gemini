# BẰNG CHỨNG C2: CÔNG THỨC ĐẾM VÀ PHÂN TÍCH SỐ HOÀN LEDGER

## 1. Công Thức Trong Script `run_full_20rounds.py`

Trong file `/tmp/run_full_20rounds.py` (Test 1: Race cancel export):
```python
cur.execute("SELECT count(*) FROM stock_ledger WHERE product_id = ?", (pid,))
ledger_cnt = cur.fetchone()[0]
...
# Ky vong: ton ban dau 10, xuat 4 (con 6), sau khi huy hoan lai 4 -> ton phai la 10.
# Ledger: 1 IMPORT (ban dau) + 1 EXPORT (ship) + 1 ADJUSTMENT (cancel) = 3 dong.
is_err = (stock_after != 10) or (succ_200 != 1) or (ledger_cnt != 3)
```

## 2. Phân Tích Logic và Dump Các Dòng Ledger

Một chu trình kiểm thử Test 1 trên 1 sản phẩm gồm 3 bước:
1. **Bước 1 (Khởi tạo)**: Tạo sản phẩm với tồn kho ban đầu = 10 -> Hệ thống sinh tự động 1 phiếu nhập ban đầu và ghi nhận 1 bản ghi thẻ kho loại `IMPORT` (+10, số dư lũy kế = 10).
2. **Bước 2 (Xuất kho)**: Tạo phiếu xuất 4 sản phẩm và gọi `/ship` -> Ghi nhận 1 bản ghi thẻ kho loại `EXPORT` (-4, số dư lũy kế = 6).
3. **Bước 3 (Hủy phiếu đồng thời)**: 20 request hủy được bắn đồng thời:
   - **Kỳ vọng (Hệ thống đúng)**: Chỉ có DUY NHẤT 1 request thành công (HTTP 200), 19 request còn lại bị từ chối 400 (`ALREADY_CANCELLED`). Request thành công này sinh DUY NHẤT 1 bản ghi thẻ kho loại `ADJUSTMENT` hoàn trả (+4, số dư lũy kế = 10).
   - **Tổng số dòng ledger chuẩn**: $1 + 1 + 1 = 3$ dòng. Số dòng hoàn trả là $3 - 2 = 1$ dòng.
   - **Lỗi Race Condition (Code cũ dd84fcd)**: Khi không có `WriteGateContext`, nhiều request hủy cùng vượt qua bước kiểm tra trạng thái và cùng commit hoàn kho:
     - Nếu $k$ request cùng thành công (ví dụ Vòng 4 có $20\times 200$), hệ thống sẽ chèn $k$ bản ghi `ADJUSTMENT` (+4).
     - Tổng số dòng thẻ kho là: $\text{ledger\_cnt} = 2 + k = 2 + 20 = 22$ (hoặc 21 bản ghi).
     - Tồn kho bị hoàn lặp lên tới $6 + 4 \times 20 = 86$ (thay vì 10).
     - Như vậy, "Số hoàn ledger" trong báo cáo vòng trước nếu nói tổng số ledger là $\text{ledger\_cnt}$, còn nếu nói số lần hoàn là $k = \text{ledger\_cnt} - 2$.
