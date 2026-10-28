# BƯỚC 07: MODULE NHẬP XUẤT KHO & THẺ KHO TRANSACTION ACID (CORE INVENTORY)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-07-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md`: SẢN PHẨM BÀN GIAO THẬT (Deliverable) giải trình giải pháp Transaction và chống tồn âm cho giảng viên chấm điểm KT2.
> - Mã nguồn được sinh trực tiếp vào thư mục `backend/app/` (models, schemas, services, endpoints).

---

## 1. Mục tiêu bước 7

- Xây dựng nghiệp vụ cốt lõi của kho bãi: Lập Phiếu nhập kho, Lập Phiếu xuất kho.
- Đảm bảo tính nhất quán dữ liệu 100% bằng Database Transactions (ACID):
  - Nhập hàng: Tăng tồn kho và tự động ghi Thẻ kho.
  - Xuất hàng: Kiểm tra tồn kho nghiêm ngặt, **chặn đứng nguy cơ tồn kho âm**, giảm tồn kho và tự động ghi Thẻ kho.
- Xây dựng Thẻ kho (`stock_ledger`) - sổ kiểm toán bất biến phục vụ truy vết lịch sử biến động từng giây.
- Báo cáo Nhập - Xuất - Tồn theo kỳ (tồn đầu kỳ + nhập - xuất = tồn cuối kỳ).

---

## 2. Nội dung công việc chi tiết

### 2.1. Models CSDL

- `app/models/import_note.py`: `ImportNote` và `ImportNoteDetail`.
- `app/models/export_note.py`: `ExportNote` và `ExportNoteDetail`.
- `app/models/stock_ledger.py`: `StockLedger` (Thẻ kho).

### 2.2. Nghiệp vụ Quản lý Kho bằng Transaction (`inventory_service.py`)

1. **Lập Phiếu Nhập**:

   ```python
   # Thực thi trong 1 transaction duy nhất (kèm Idempotency Key)
   with db.begin():
       # 1. Kiểm tra Idempotency Key chống tạo trùng
       # 2. Tạo phiếu nhập (ImportNote, status='COMPLETED')
       # 3. Tạo các dòng chi tiết (ImportNoteDetail)
       # 4. Cập nhật tăng current_stock của từng sản phẩm
       # 5. Ghi bản ghi vào StockLedger (type='IMPORT', qty_change=+X, balance_after=...)
   ```

2. **Lập Phiếu Xuất (Cỗ máy Trạng thái 3 Bước & Chống tồn kho âm)**:

   - **Bước 1: Tiếp nhận đơn xuất (`create_export_note`)**:
     - Kiểm tra nguyên tử: `product.current_stock >= item.quantity`. Nếu thiếu $\rightarrow$ ném HTTP 400 và Rollback 100%.
     - Tạo `ExportNote` ở trạng thái `CONFIRMED` và các dòng `ExportNoteDetail`.
     - *Lưu ý:* Chưa trừ tồn kho vật lý và chưa ghi Thẻ kho để tránh hiện tượng giam giữ hàng ảo.
     - Cho phép xóa vĩnh viễn phiếu (`DELETE /api/v1/export-notes/{id}`) nếu phiếu còn ở `CONFIRMED`.
   - **Bước 2: Bắt đầu giao hàng (`ship_export_note`)**:
     - Kiểm tra lại tồn kho tức thời tại thời điểm xuất kho vật lý.
     - Trừ tồn kho bằng biểu thức SQL nguyên tử: `UPDATE products SET current_stock = current_stock - :qty WHERE id = :id AND current_stock >= :qty RETURNING current_stock`.
     - Chuyển trạng thái sang `SHIPPING`.
     - Ghi nhận bản ghi Thẻ kho `StockLedger` (type='EXPORT', qty_change=-Y, balance_after lấy từ RETURNING SQL).
   - **Bước 3: Hoàn thành hoặc Hủy đơn**:
     - `complete_export_note`: Chuyển sang `COMPLETED` khi khách ký nhận (phiếu bị khóa).
     - `cancel_export_note`: Nếu phiếu đang `SHIPPING` mà bị hủy, hoàn lại 100% số lượng về kho và ghi Thẻ kho hoàn tác `ADJUSTMENT`.

### 2.3. Tra cứu Thẻ kho & Báo cáo Nhập - Xuất - Tồn

- `GET /api/v1/stock-ledger`: Tra cứu lịch sử thẻ kho theo mặt hàng, khoảng thời gian (sổ kiểm toán số lượng, không lưu giá tiền hay nhà cung cấp).
- `GET /api/v1/stock-ledger/adjust`: Endpoint lập phiếu điều chỉnh kiểm kê cân bằng kho.
- `GET /api/v1/stock-ledger/export-excel`: Xuất Sổ cái Thẻ kho ra file Excel (.xlsx).
- `GET /api/v1/reports/inventory-summary`: Báo cáo Nhập - Xuất - Tồn theo khoảng thời gian (`from_date`, `to_date`).
- `GET /api/v1/reports/inventory-summary/export-excel`: Xuất Báo cáo Nhập - Xuất - Tồn ra file Excel (.xlsx).
- `GET /api/v1/reports/low-stock`: Cảnh báo danh sách hàng hóa dưới định mức tồn an toàn.

---

## 3. Cấu trúc file/thư mục cần sinh

Khi thực hiện bước này, các file và thư mục sau phải được tạo ra:

```text
backend/
├── app/
│   ├── models/
│   │   ├── import_note.py             # Model Phiếu nhập & Chi tiết phiếu nhập
│   │   ├── export_note.py             # Model Phiếu xuất & Chi tiết phiếu xuất
│   │   └── stock_ledger.py            # Model Thẻ kho kiểm toán
│   ├── schemas/
│   │   ├── import_note.py             # Schemas ImportNote
│   │   ├── export_note.py             # Schemas ExportNote
│   │   ├── stock_ledger.py            # Schemas StockLedger
│   │   └── report.py                  # Schemas Báo cáo Nhập-Xuất-Tồn
│   ├── services/
│   │   └── inventory_service.py       # Logic Transaction Nhập, Xuất & Thẻ kho
│   └── api/
│       └── v1/
│           └── endpoints/
│               ├── import_notes.py    # Endpoints lập & tra cứu phiếu nhập
│               ├── export_notes.py    # Endpoints lập & tra cứu phiếu xuất
│               ├── stock_ledger.py    # Endpoints tra cứu thẻ kho
│               └── reports.py         # Endpoints báo cáo thống kê
docs/
└── SDLC/
    └── KT2/
        └── 02_Transaction_Design_and_Negative_Stock_Prevention.md  # Tài liệu giải trình thiết kế Transaction KT2
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Nếu xuất hàng quá số lượng tồn hiện có, API bắt buộc trả về mã lỗi HTTP 400 kèm thông báo chi tiết số lượng thiếu; số tồn kho không bị thay đổi.
- [x] Mọi giao dịch nhập/xuất đều tạo ra bản ghi tương ứng trong `stock_ledger` với `balance_after` hoàn toàn chính xác.
- [x] Báo cáo Nhập - Xuất - Tồn khớp công thức: `Tồn đầu + Nhập - Xuất = Tồn cuối`.

---

## 4b. Deliverable bổ sung — `docs/architecture.md` (trước KT2)

- [x] Hoàn thành `docs/architecture.md` với sơ đồ luồng nhập, xuất (chống tồn âm), AI và ranh giới 3 tầng `api/`, `services/`, `models/`.

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/gemini/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 07** theo đúng mẫu sau:

```markdown
| 2026-09-22 | Bước 07 | Module Nhập/Xuất kho & Thẻ kho (Transaction) | Hoàn thành | `backend/app/services/inventory_service.py`, `backend/app/api/v1/endpoints/*.py`, `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md`, `docs/architecture.md` | Hoàn thiện Transaction ACID Nhập/Xuất, Chống tồn âm, Guard-check Hủy phiếu, Thẻ kho, Báo cáo và Điều chỉnh kiểm kê |
```

---

## 6. CHANGELOG

### [2026-09-22] Hoàn thành Bước 07: Module Nhập/Xuất kho & Thẻ kho (Transaction ACID)

- **Nghiệp vụ cốt lõi (Core Inventory Service):**
  - Triển khai `backend/app/services/inventory_service.py`:
    - `create_import_note`: Transaction ACID nhập kho, tăng `current_stock`, ghi nhận Thẻ kho `StockLedger` (type `IMPORT`).
    - `create_export_note`: Kiểm tra tồn kho nguyên tử (Atomic Check). Nếu thiếu hàng $\rightarrow$ trả về HTTP 400 và Rollback 100%, số tồn giữ nguyên. Nếu đủ hàng $\rightarrow$ trừ tồn, ghi Thẻ kho (type `EXPORT`).
    - Sinh mã phiếu tự động: `PN-YYYYMMDD-XXXX` và `PX-YYYYMMDD-XXXX` kèm **Retry Pattern** (xử lý xung đột đồng thời).
    - `cancel_import_note`: **Guard-check chống tồn âm** (Phương án B) — từ chối hủy nếu hàng đã xuất bớt dẫn đến tồn kho hiện tại < số lượng cần hoàn trả.
    - `cancel_export_note`: Hủy phiếu xuất an toàn và hoàn trả số lượng về kho.
    - `adjust_stock`: **Lối thoát nghiệp vụ kiểm kê** (Phương án A) — endpoint điều chỉnh tồn kho theo số lượng thực tế khi hủy phiếu bị chặn hoặc kiểm kê định kỳ.
    - `get_inventory_summary_report`: Báo cáo Nhập - Xuất - Tồn tính toán chuẩn xác từ `StockLedger` theo công thức: `Tồn đầu kỳ + Nhập trong kỳ - Xuất trong kỳ = Tồn cuối kỳ`.
- **Pydantic Schemas:**
  - `backend/app/schemas/import_note.py`, `export_note.py`, `stock_ledger.py`, `report.py`.
- **API Endpoints:**
  - `backend/app/api/v1/endpoints/import_notes.py`: `/import-notes`, `/{id}`, `/{id}/cancel`.
  - `backend/app/api/v1/endpoints/export_notes.py`: `/export-notes`, `/{id}`, `/{id}/cancel`.
  - `backend/app/api/v1/endpoints/stock_ledger.py`: `/stock-ledger`, `/stock-ledger/adjust`.
  - `backend/app/api/v1/endpoints/reports.py`: `/reports/inventory-summary`, `/reports/low-stock`.
  - Đăng ký toàn bộ vào `backend/app/api/v1/api.py`.
- **Sản phẩm bàn giao (Deliverables KT2):**
  - Hoàn thành `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md`.
  - Hoàn thành `docs/architecture.md` (Kiến trúc phân tầng và sơ đồ luồng dữ liệu).
- **Kiểm thử tự động:**
  - Viết `backend/tests/test_stock_transactions.py` (12 bài test lớn bao quát trọn vẹn mọi luồng: ACID, idempotency key, hủy phiếu guard-check, điều chỉnh kiểm kê, hoàn kho shipping, xuất excel thẻ kho).
  - Kết quả: **12/12 test cases PASS 100%**.

---

## 7. Lịch sử đồng bộ (Reconciliation History)

- **Ngày thực hiện:** 2026-10-28
- **Căn cứ:** Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md) (Mục #7, #10, #11, #15, #17, #26, #32; Điểm Nghi ngờ 1 & 3).
- **Nội dung điều chỉnh:**
  1. *[Mục #10 - Nhóm A]:* Bỏ trạng thái `DRAFT`; chuẩn hóa trạng thái thực tế trong `import_notes` (`COMPLETED`, `CANCELLED`) và `export_notes` (`CONFIRMED`, `SHIPPING`, `COMPLETED`, `CANCELLED`) theo [`backend/app/models/export_note.py` L19](file:///e:/gemini/hệ thống quản lý kho/backend/app/models/export_note.py#L19).
  2. *[Mục #26, #32 - Nhóm C, D]:* Đồng bộ cỗ máy trạng thái xuất kho 3 bước: `POST /export-notes` chỉ tạo phiếu `CONFIRMED` (chưa trừ kho), khi gọi `POST /export-notes/{id}/ship` mới trừ kho và ghi Thẻ kho theo [`backend/app/services/inventory_service.py` L258-277 & L391-440](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L258-L277).
  3. *[Điểm Nghi ngờ 1]:* Ghi nhận endpoint `DELETE /api/v1/export-notes/{id}` cho phép xóa cứng phiếu xuất nếu còn ở trạng thái `CONFIRMED` theo [`backend/app/api/v1/endpoints/export_notes.py` L135-168](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/export_notes.py#L135-L168).
  4. *[Mục #15 - Nhóm B]:* Bổ sung cơ chế `idempotency_key` chống trùng lặp chứng từ theo [`backend/app/services/inventory_service.py` L196-204](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L196-L204).
  5. *[Mục #17 - Nhóm B & Mục #11 - Nhóm A]:* Bổ sung 2 endpoint xuất file Excel (`.xlsx`) cho Thẻ kho và Báo cáo Nhập-Xuất-Tồn theo [`backend/app/api/v1/endpoints/stock_ledger.py` L85](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/stock_ledger.py#L85) và [`backend/app/api/v1/endpoints/reports.py` L125](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/reports.py#L125). Ghi nhận hệ thống chỉ xuất file Excel, không xuất PDF.
  6. *[Mục #7 - Nhóm A & Điểm Nghi ngờ 3]:* Xác nhận Thẻ kho chỉ theo dõi số lượng thuần và số dư tức thời, không lọc theo NCC và không lưu đơn giá.
- **Lý do:** Đồng bộ tài liệu thiết kế nghiệp vụ kho cốt lõi khớp 100% với mã nguồn và dịch vụ thực tế.
