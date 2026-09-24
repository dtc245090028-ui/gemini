# HỒ SƠ TỔNG HỢP NỘP BÀI ĐÁNH GIÁ GIAI ĐOẠN 1 (KT1)

## Đề tài 07: Hệ thống quản lý kho có tích hợp AI

**Sinh viên thực hiện:** Đồ án môn học Triển khai phần mềm & Ứng dụng AI  
**Ngày bàn giao:** 2026-09-21  
**Trạng thái nghiệm thu:** ĐẠT 100% CÁC TIÊU CHÍ  

---

## 1. Mục tiêu & Tiêu chuẩn nghiệm thu mốc KT1

Theo yêu cầu chuẩn tại `docs/SDLC/KT1/README.md`, mốc KT1 yêu cầu hoàn thiện đầy đủ 4 hạng mục tài liệu đặc tả & thiết kế, kèm theo hiện thực hóa mô hình cơ sở dữ liệu trên mã nguồn thực tế:

- [x] Phân tích quy trình nghiệp vụ kho (Nhập, Xuất, Kiểm soát tồn, Báo cáo).
- [x] Xác định và phân tích 3 Actor: `Quản trị viên (Admin)`, `Thủ kho (Warehouse Keeper)`, `Kế toán (Accountant)`.
- [x] Thiết kế sơ đồ Use Case và ma trận phân quyền RBAC.
- [x] Thiết kế mô hình CSDL chuẩn hóa 3NF gồm 9 bảng dữ liệu, có sơ đồ Mermaid ERD và từ điển dữ liệu (Data Dictionary).
- [x] Thiết lập ràng buộc kiểm tra toàn vẹn chống tồn âm: `CHECK (current_stock >= 0)`.
- [x] Thiết kế kiến trúc module AI (Google Gemini + Heuristic Fallback Engine) và 3 bộ Prompt mẫu.
- [x] Phác thảo Wireframe các màn hình chính (Dashboard, Lập phiếu xuất chống tồn âm, Thẻ kho, Trợ lý AI).
- [x] Hiện thực hóa 9 SQLAlchemy Models trong mã nguồn backend (`backend/app/models/*.py`) và kiểm thử tự động thành công.

---

## 2. Danh mục tài liệu bàn giao trong gói nộp bài (`docs/submissions/KT1/`)

1. [`01_SRS_and_UseCases.md`](01_SRS_and_UseCases.md): Đặc tả yêu cầu phần mềm, phân tích 3 Actor, 8 luồng nghiệp vụ kho và sơ đồ Use Case.
2. [`02_Database_Design_ERD.md`](02_Database_Design_ERD.md): Thiết kế CSDL 9 bảng, sơ đồ Mermaid ERD, ràng buộc ACID và chống tồn kho âm.
3. [`03_AI_Architecture_and_Prompts.md`](03_AI_Architecture_and_Prompts.md): Thiết kế kiến trúc AI Gemini, kỹ thuật chống ảo giác (Grounding), an toàn dữ liệu và Heuristic Fallback khi offline.
4. [`04_Wireframes.md`](04_Wireframes.md): Bản vẽ phác thảo cấu trúc giao diện Dashboard, lập phiếu xuất cảnh báo realtime, thẻ kho và trợ lý AI.

---

## 3. Minh chứng Kiểm thử & Chạy thực tế trên Hệ thống

### 3.1. Cấu trúc 9 Bảng CSDL được sinh tự động

Kiểm tra cấu trúc cơ sở dữ liệu SQLite (`warehouse.db`) qua SQLAlchemy Inspector:

```python
['categories', 'export_note_details', 'export_notes', 'import_note_details', 'import_notes', 'products', 'stock_ledger', 'suppliers', 'users']
```

-> Kết quả: Đủ 9 bảng theo đúng thiết kế 100%.

### 3.2. Kết quả Chạy Bộ Kiểm thử Tự động (`pytest`)

```bash
backend> pytest
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-8.2.2, pluggy-1.6.0
rootdir: E:\gemini\hệ thống quản lý kho\backend

tests\test_foundation.py ...                                             [100%]

======================== 3 passed in 1.10s ========================
```

- `test_health_check`: Endpoint `/health` trả về mã 200 `healthy`.
- `test_database_all_nine_tables_created`: 9 bảng đã được sinh chuẩn xác.
- `test_prevent_negative_current_stock`: Ràng buộc `CHECK (current_stock >= 0)` ngăn chặn thành công trường hợp tồn kho âm và ném `IntegrityError` để rollback.
