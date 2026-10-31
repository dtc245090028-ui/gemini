# Workflow: Tester Mode — Hệ Thống Quản Lý Kho Tích Hợp AI

## 1. Mục Tiêu
Thiết kế và thực thi bộ kiểm thử tự động toàn diện, tìm kiếm các trường hợp biên (tồn âm, tranh chấp giao dịch, quyền truy cập, kịch bản lỗi AI) mà TUYỆT ĐỐI KHÔNG can thiệp sửa đổi mã nguồn nghiệp vụ của hệ thống kho.

---

## 2. Khi Nào Kích Hoạt
- Khi Dev mode hoàn thành mã nguồn hoặc cần bổ sung kiểm thử cho một module tính năng.
- Khi người dùng yêu cầu: *"Kiểm thử Bước-xx"*, *"Viết test cho phiếu xuất"*, *"Chạy regression test"*, *"Test chốt chặn tồn âm"*.
- Tự động tra cứu mục tiêu và tiêu chí chấp nhận tại `docs/plans/TIEN-DO.md`, file tương ứng trong `docs/plans/Buoc-XX-*.md` và `Prompt.md`.

---

## 3. Các Nguyên Tắc Kiểm Thử Bắt Buộc

### Ba Luật Chống Test Giả
1. **Không mock chính lớp/hàm đang test:** Mock chỉ dành cho ranh giới bên ngoài (Google Gemini API, đồng hồ thời gian hệ thống). Không mock Service logic khi đang kiểm thử Service.
2. **Mỗi bug fix phải có test tái hiện được bug:** Ca kiểm thử phải chạy ĐỎ (FAIL) trước khi sửa và XANH (PASS) sau khi sửa.
3. **Test AI phải assert nội dung thật:** Phải kiểm tra cấu trúc JSON, sự hiện diện của danh sách đề xuất, số lượng gợi ý hợp lý — không chỉ assert "không ném exception".

### Hai Luật Bao Phủ
1. Mỗi hàm public trong `backend/app/services/` có tối thiểu **1 test happy path + 1 test biên**.
2. Mọi thay đổi liên quan đến tồn kho **phải kèm test chặn tồn âm** (thử xuất quá số lượng hiện có và assert exception/lỗi).

---

## 4. Được Làm Gì / Không Được Làm Gì

- **ĐƯỢC:**
  - Viết file test mới hoặc bổ sung test case trong thư mục `backend/tests/` (tiền tố `test_*.py`).
  - Ghi báo cáo, biên bản kiểm thử vào thư mục `docs/SDLC/KT3/` hoặc `docs/testing/`.
  - Sử dụng `fastapi.testclient.TestClient`, SQLAlchemy fixtures (`client`, `db_session`, auth headers cho `admin`, `warehouse_keeper`, `accountant`).
  - Thực thi kiểm thử bằng lệnh chuẩn của dự án:
    ```powershell
    cd backend; pytest -v
    ```
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối KHÔNG sửa bất kỳ dòng mã nguồn nghiệp vụ nào trong `backend/app/` và `frontend/src/`.
  - Không sửa logic hệ thống để "ép" test case pass. Nếu test fail, nhiệm vụ là ghi nhận chi tiết lỗi và chuyển giao sang Debugger Mode.

---

## 5. Quy Trình Làm Việc Từng Bước

1. **Xác định kịch bản kiểm thử:** Đọc yêu cầu chức năng trong file kế hoạch `docs/plans/Buoc-XX-*.md`; lập danh mục ca kiểm thử.
2. **Xây dựng 3 nhóm ca kiểm thử:**
   - *Happy Path:* Luồng nghiệp vụ chuẩn (tạo phiếu nhập hợp lệ, duyệt xuất kho 3 bước thành công, thẻ kho tăng/giảm chính xác, AI sinh báo cáo hợp lệ).
   - *Negative Path:* Trường hợp dữ liệu sai hoặc vi phạm nghiệp vụ (xuất quá số lượng tồn, hủy phiếu đã xuất thành công, người dùng sai quyền RBAC bị chặn 403, sai format payload bị chặn 422).
   - *Boundary & Concurrency:* Trường hợp biên và tranh chấp (xuất hàng khi tồn kho vừa đúng bằng số lượng yêu cầu, hai luồng cùng trừ kho đồng thời, Gemini API trả về lỗi 429 hoặc timeout kích hoạt Fallback Heuristic).
3. **Hiện thực mã kiểm thử:** Viết hàm test bắt đầu bằng `test_` trong file tương ứng tại `backend/tests/`. Tận dụng `conftest.py` cho database session in-memory hoặc test isolation.
4. **Thực thi kiểm thử:**
   - Chạy riêng file test vừa viết: `pytest backend/tests/test_xxx.py -v`.
   - Chạy toàn bộ test suite để đảm bảo không có lỗi hồi quy: `cd backend; pytest`.
5. **Ghi nhận kết quả:** Trích xuất log kết quả test, tổng hợp số lượng ca test Pass/Fail và ghi biên bản kiểm thử nếu được yêu cầu.

---

## 6. Định Dạng Output Bắt Buộc

- **Chức năng / Module kiểm thử:** Tên chức năng và file test tương ứng.
- **Danh mục Test Cases:**
  | Tên Test Case | Phân loại (Happy/Negative/Edge) | Mục tiêu kiểm tra | Kết quả (PASS/FAIL) |
  | :--- | :--- | :--- | :--- |
- **Kết quả thực thi chi tiết:** Output log từ lệnh `pytest` (thời gian, tổng số test passed).
- **Phát hiện lỗi (nếu có):** Chi tiết hành vi sai khác, mã lỗi HTTP hoặc ngoại lệ gặp phải để cung cấp cho Debugger Mode.

---

## 7. Checklist Tự Kiểm Tra Trước Khi Hoàn Tất Mode

- [ ] Đã chạy đúng lệnh test của dự án: `cd backend; pytest`?
- [ ] Toàn bộ các ca test tuân thủ 3 Luật chống test giả và 2 Luật bao phủ?
- [ ] Đã bao phủ ca kiểm tra chốt chặn tồn âm và phân quyền RBAC 3 vai trò?
- [ ] Tuyệt đối KHÔNG có file mã nguồn nào trong `backend/app/` bị chỉnh sửa trong mode này?
