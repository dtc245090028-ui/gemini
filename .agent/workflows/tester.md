# Workflow: Tester Mode

## 1. Mục Tiêu
Thiết kế và thực thi bộ kiểm thử tự động toàn diện, tìm kiếm các trường hợp biên (edge cases) và lỗi tiềm ẩn mà TUYỆT ĐỐI KHÔNG sửa logic mã nguồn của PharmaCare AI.

## 2. Khi Nào Kích Hoạt
- Khi Dev mode hoàn thành mã nguồn hoặc cần bổ sung kiểm thử cho một module.
- Khi người dùng yêu cầu: *"kiểm thử S-xx"* hoặc kiểm thử chức năng, tự động tra cứu mục tiêu và yêu cầu tại `docs/plans/implementation_plan.md` (kết hợp `docs/specs/yeu_cau.md` mục 3.1 & 3.2) để xác định tiêu chí chấp nhận (Acceptance Criteria).

## 3. Được Làm Gì / Không Được Làm Gì
- **ĐƯỢC:**
  - Viết file test mới hoặc bổ sung test case trong thư mục `tests/` (tiền tố `test_*.py`).
  - Ghi báo cáo, biên bản kiểm thử và nhật ký test vào thư mục `docs/testing/` (tự tạo thư mục nếu chưa có).
  - Sử dụng `fastapi.testclient.TestClient`, fixtures (`client`, `cashier_headers`, `db_session`), và `pytest.mark.asyncio`.
  - Thực thi kiểm thử bằng lệnh chuẩn của dự án: `pytest -v` hoặc `pytest`.
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối KHÔNG sửa bất kỳ dòng mã nguồn nào trong `routers/`, `services/`, `database.py`, `schemas.py`, `static/`.
  - Không sửa logic hệ thống để "ép" test case pass. Nếu test fail, nhiệm vụ là báo cáo lỗi.

## 4. Quy Trình Làm Việc Từng Bước
1. **Xác định kịch bản kiểm thử:** Tra cứu chức năng trong `docs/plans/implementation_plan.md`; lập danh mục test cases.
2. **Xây dựng 3 nhóm ca kiểm thử:**
   - *Happy Path:* Trường hợp nghiệp vụ chuẩn (bán đúng lô FEFO còn hạn, login hợp lệ).
   - *Negative Path:* Trường hợp dữ liệu sai (bán lô hết hạn, sai mật khẩu, thiếu trường bắt buộc).
   - *Boundary & Concurrency:* Trường hợp biên (mua thuốc số lượng lẻ, kho vừa đủ 0, tranh chấp đồng thời nhiều cashier).
3. **Hiện thực mã kiểm thử:** Viết hàm test bắt đầu bằng `test_` trong `tests/` tuân thủ style của `test_pos_fefo.py`.
4. **Thực thi kiểm thử:** Chạy lệnh `pytest -v tests/<ten_file_test>.py` hoặc toàn bộ bằng `pytest -v`.
5. **Ghi nhận kết quả:** Xuất biên bản chi tiết kết quả test vào `docs/testing/`.

## 5. Định Dạng Output Bắt Buộc
- **Chức năng / Nhiệm vụ kiểm thử:** Tên hoặc mã chức năng theo `docs/plans/implementation_plan.md`.
- **Danh sách Test Cases:** Bảng gồm: Tên Test | Loại (Happy/Negative/Edge) | Kỳ vọng.
- **Kết quả thực thi:** Output log từ lệnh `pytest -v` (Số test PASS/FAIL, thời gian thực thi).
- **Phát hiện & Cảnh báo (nếu có):** Chi tiết các ca test thất bại hoặc hành vi bất thường của hệ thống.

## 6. Checklist Tự Kiểm Tra Trước Khi Kết Thúc
- [ ] Đã chạy đúng lệnh test của dự án: `pytest -v`?
- [ ] Tuyệt đối không chỉnh sửa bất kỳ file logic nào ngoài `tests/` và `docs/testing/`?
- [ ] Đã bao phủ các ca kiểm tra phân quyền RBAC và nguyên tắc chặn thuốc hết hạn FEFO?
- [ ] Báo cáo đã được lưu vào thư mục `docs/testing/`?
