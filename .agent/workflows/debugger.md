# Workflow: Debugger Mode

## 1. Mục Tiêu
Cô lập, tái hiện chính xác lỗi, tìm ra nguyên nhân gốc rễ (Root Cause) và khắc phục triệt để mà không làm phát sinh lỗi hồi quy (regression) trong PharmaCare AI.

## 2. Khi Nào Kích Hoạt
- Khi có test case bị FAIL trong `tests/`.
- Khi server FastAPI báo lỗi 500 Internal Server Error hoặc ngoại lệ không mong muốn trong log.
- Khi xuất hiện lỗi logic nghiệp vụ: sai lệch tồn kho lô FEFO, tính sai tổng tiền hóa đơn, race condition, hoặc LLM timeout không fallback.

## 3. Được Làm Gì / Không Được Làm Gì
- **ĐƯỢC:**
  - Viết test case cô lập lỗi vào `tests/` để tái hiện lỗi một cách tự động.
  - Sử dụng debug log (`logging.getLogger`), phân tích call stack và mã truy vấn SQLAlchemy.
  - Chỉnh sửa mã nguồn tại đúng vị trí gây ra lỗi sau khi đã xác định rõ nguyên nhân gốc.
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối KHÔNG sửa code theo cảm tính hoặc "đoán mò" khi chưa có kịch bản tái hiện lỗi.
  - Không dùng "băng gạc tạm thời" (quick-patch) như bọc `try...except pass` để giấu lỗi.
  - Không can thiệp sửa trực tiếp dữ liệu trong `database.db` để lấp liếm lỗi logic code.

## 4. Quy Trình Làm Việc Từng Bước
1. **Thu thập thông tin:** Đọc kỹ traceback, HTTP status code, request payload và phản hồi thực tế từ API.
2. **Tái hiện lỗi (Reproduce):** Viết một test case tối thiểu trong `tests/` mô phỏng đúng điều kiện phát sinh lỗi. Chạy test case này và xác nhận nó **FAIL**.
3. **Phân tích nguyên nhân gốc (RCA):** Lần theo luồng dữ liệu (Data Flow) từ Router -> Service -> Database để định vị chính xác dòng code gây lỗi.
4. **Sửa lỗi tận gốc:** Can thiệp chỉnh sửa logic cốt lõi tại đúng vị trí nguyên nhân, bảo toàn các ràng buộc nghiệp vụ (FEFO, RBAC, Data Types).
5. **Xác minh kép:**
   - Chạy lại test case tái hiện lỗi: Phải chuyển từ **FAIL -> PASS**.
   - Chạy toàn bộ test suite dự án bằng lệnh `pytest -v`: Đảm bảo 100% test cases đều **PASS**.

## 5. Định Dạng Output Bắt Buộc
- **Triệu chứng & Mã lỗi:** Mô tả lỗi, mã HTTP hoặc ngoại lệ (ví dụ: `HTTP 500`, `IntegrityError`).
- **Ca kiểm thử tái hiện:** Tên hàm test và file test đã viết để tái hiện lỗi.
- **Nguyên nhân gốc rễ (Root Cause):** Giải thích rõ ràng tại sao lỗi xảy ra ở mức độ code/dữ liệu.
- **Giải pháp khắc phục:** Chi tiết các dòng code được sửa đổi và lý do.
- **Kết quả xác minh:** Log `pytest -v` chứng minh lỗi đã hết và không gây hồi quy.

## 6. Checklist Tự Kiểm Tra Trước Khi Kết Thúc
- [ ] Đã có test case tái hiện lỗi và test đó đã PASS sau khi sửa?
- [ ] Không sử dụng `except: pass` hoặc bỏ qua kiểm tra an toàn?
- [ ] Lệnh `pytest -v` đã chạy và toàn bộ test suite đều đạt màu xanh?
- [ ] Không làm thay đổi cấu trúc bảng CSDL khi chưa chạy sao lưu?
