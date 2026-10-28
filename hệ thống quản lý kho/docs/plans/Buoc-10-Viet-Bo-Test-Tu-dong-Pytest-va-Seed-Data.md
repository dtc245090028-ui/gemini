# BƯỚC 10: VIẾT BỘ TEST TỰ ĐỘNG PYTEST & SCRIPT SEED DATA (TESTING & DEMO DATA)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-10-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - `docs/SDLC/KT3/02_Test_Plan_and_Results.md`: SẢN PHẨM BÀN GIAO THẬT (Deliverable) báo cáo kết quả kiểm thử cho giảng viên chấm điểm KT3.
> - Mã nguồn kiểm thử được sinh trực tiếp vào `backend/tests/` và `backend/seed_data.py`.

---

## 1. Mục tiêu bước 10

- Xây dựng bộ kiểm thử tự động (Automated Test Suite) toàn diện bằng `pytest` bao phủ toàn bộ các tầng nghiệp vụ:
  1. Kiểm thử xác thực, phân quyền RBAC và cơ chế Rate Limiting (`test_auth.py`).
  2. Kiểm thử quản lý danh mục Hàng hóa, Nhóm hàng, Nhà cung cấp và upload ảnh (`test_master_data.py`).
  3. Kiểm thử giao dịch kho: Lập phiếu nhập, xuất kho luồng 3 bước, chặn tồn kho âm (HTTP 400), Idempotency Key, tính toàn vẹn Thẻ kho (`stock_ledger`), hủy/xóa phiếu (`test_stock_transactions.py`).
  4. Kiểm thử AI Pipeline, Prompt template, Fallback offline, Gemini Client, AI Cache và Endpoint AI rỗng (`test_ai_service.py`, `test_ai_empty_data.py`).
- Xây dựng script `seed_data.py` nạp sẵn bộ dữ liệu mẫu quy mô lớn: **76 sản phẩm**, **7 danh mục**, **10 nhà cung cấp**, lịch sử giao dịch liên tục **5 tháng (150 ngày)** nhằm phục vụ kiểm thử phân tích AI và demo thuyết trình.

---

## 2. Nội dung công việc chi tiết

### 2.1. Bộ Kiểm thử Tự động (`backend/tests/`)

1. `tests/conftest.py`:
   - Tạo database SQLite in-memory tách biệt (`sqlite:///:memory:`) với cờ Foreign Keys kích hoạt.
   - Fixture `db_session` tự động rollback sau mỗi ca test.
   - Fixture `client`: `TestClient(app)` gắn database ảo.
   - Fixture token xác thực JWT cho 3 vai trò: `auth_headers_admin`, `auth_headers_thukho`, `auth_headers_ketoan`.
2. `tests/test_auth.py` (12 tests):
   - Đăng nhập đúng/sai mật khẩu, tài khoản vô hiệu hóa.
   - Phân quyền RBAC theo endpoint cho Admin, Thủ kho, Kế toán.
   - Kiểm tra `SlidingWindowRateLimiter` chặn brute-force login sau 10 lần/phút.
3. `tests/test_master_data.py` (5 tests):
   - CRUD sản phẩm, nhóm hàng, nhà cung cấp.
   - Tải ảnh sản phẩm và xác thực định dạng file ảnh.
4. `tests/test_stock_transactions.py` (18 tests):
   - `test_import_stock_success()`: Nhập kho tăng tồn, ghi nhận thẻ kho.
   - `test_export_flow_3_stages()`: Luồng phiếu xuất `CONFIRMED` $\rightarrow$ `SHIPPING` (trừ kho) $\rightarrow$ `COMPLETED`.
   - `test_prevent_negative_stock()`: Chặn xuất vượt tồn, trả HTTP 400 và không làm biến động số lượng tồn.
   - `test_idempotency_key()`: Chống tạo trùng phiếu khi client retry.
   - `test_delete_export_note_only_confirmed()`: Chỉ cho phép xóa phiếu xuất khi chưa xuất kho.
   - `test_stock_ledger_continuity()`: Đảm bảo số dư Thẻ kho `balance_after` liên tục, không lệch số.
5. `tests/test_ai_service.py` (31 tests):
   - Pipeline tổng hợp dữ liệu kho (loại bỏ 100% giá nhập nhạy cảm).
   - Heuristic Fallback Engine hoạt động hoàn hảo khi mất mạng hoặc không có API Key.
   - Cơ chế AI In-Day Cache (`ai_cache.py`).
   - Mocking Gemini API calls với JSON response hợp lệ.
6. `tests/test_ai_empty_data.py` (4 tests):
   - Kiểm thử các endpoint AI khi kho hoàn toàn rỗng hoặc chưa có giao dịch nào, đảm bảo trả kết quả thống kê 0 mà không phát sinh lỗi HTTP 500.

### 2.2. Script Nạp Dữ liệu Mẫu (`backend/seed_data.py`)

- **Tài khoản mặc định**:
  - `admin` / `admin123` (Quản trị viên)
  - `thukho` / `thukho123` (Thủ kho)
  - `ketoan` / `ketoan123` (Kế toán)
- **Danh mục & Sản phẩm**:
  - 7 nhóm hàng: Thiết bị văn phòng, Linh kiện PC, Thiết bị mạng, Phụ kiện, Thiết bị hiển thị, Thiết bị âm thanh, Vật tư đóng gói.
  - 76 mặt hàng công nghệ đa dạng kèm mức tồn tối thiểu, đơn vị tính và mô tả chuẩn xác.
- **Nhà cung cấp & Lịch sử giao dịch**:
  - 10 nhà cung cấp uy tín trong nước và quốc tế.
  - Lịch sử nhập/xuất kho liên tục trong **5 tháng (150 ngày)** với hàng trăm phiếu nhập xuất.
  - Dữ liệu mô phỏng sát thực tế: hàng bán chạy sinh đột biến (`SURGE_EXPORT`), hàng ế không xuất trong 30 ngày (`DEAD_STOCK`), hàng dưới tồn an toàn (`LOW_STOCK`) để AI nhận diện chuẩn xác.

---

## 3. Cấu trúc file/thư mục triển khai thực tế

```text
backend/
├── seed_data.py                               # Script nạp 76 SP, 7 nhóm, 10 NCC, dữ liệu 5 tháng
└── tests/
    ├── __init__.py
    ├── conftest.py                            # Fixtures SQLite in-memory, TestClient, Auth tokens
    ├── test_auth.py                           # 12 ca test xác thực, RBAC và Rate limiting
    ├── test_master_data.py                    # 5 ca test CRUD danh mục và upload ảnh
    ├── test_stock_transactions.py             # 18 ca test giao dịch kho, ACID, thẻ kho, idempotency
    ├── test_ai_service.py                     # 31 ca test AI aggregation, heuristic fallback, AI cache
    └── test_ai_empty_data.py                  # 4 ca test bảo vệ các endpoint AI khi kho rỗng
docs/
└── SDLC/
    └── KT3/
        └── 02_Test_Plan_and_Results.md        # File báo cáo kết quả kiểm thử Pytest phục vụ chấm điểm KT3
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Chạy lệnh `pytest tests/ -v` đạt **100% Passed (70/70 tests PASS)**.
- [x] Test Coverage toàn dự án backend đạt $\ge 83\%$ (vượt yêu cầu chuẩn công nghiệp $\ge 80\%$).
- [x] Chạy lệnh `python seed_data.py` nạp thành công 76 sản phẩm và 5 tháng dữ liệu trong $< 5$ giây, dữ liệu liên tục và toàn vẹn Foreign Keys.
- [x] Báo cáo kết quả kiểm thử được đồng bộ tại `docs/SDLC/KT3/02_Test_Plan_and_Results.md`.

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/gemini/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 10** theo đúng mẫu sau:

```markdown
| YYYY-MM-DD | Bước 10 | Viết Bộ Test Tự động (Pytest) & Seed Data | Hoàn thành | `backend/tests/`, `backend/seed_data.py` | Đã hoàn thiện test suite Pytest 70 tests pass 100%, 83% coverage và script seed_data.py 76 SP / 5 tháng |
```

---

## 6. Lịch sử đồng bộ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Quy mô bộ Test Suite:** Điều chỉnh từ 30 test ban đầu lên tổng cộng **70 tests** (66 test từ PR #1 gồm `test_auth.py`: 12, `test_master_data.py`: 5, `test_stock_transactions.py`: 18, `test_ai_service.py`: 31; và bổ sung 4 test tại `test_ai_empty_data.py` kiểm thử kho rỗng). Tỷ lệ kiểm thử đạt 100% Pass với 83% code coverage.
  - **Quy mô Seed Data:** Nâng cấp từ kế hoạch 20+ SP / 60 ngày lên con số thực tế trong `seed_data.py` là **76 sản phẩm**, **7 nhóm hàng**, **10 nhà cung cấp** và dữ liệu lịch sử xuyên suốt **5 tháng (150 ngày)**.
