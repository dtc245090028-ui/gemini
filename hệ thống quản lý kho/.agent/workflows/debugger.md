# Workflow: Debugger Mode — Hệ Thống Quản Lý Kho Tích Hợp AI

## 1. Mục Tiêu
Cô lập, tái hiện chính xác lỗi, tìm ra nguyên nhân gốc rễ (Root Cause Analysis - RCA) và khắc phục triệt để mà không làm phát sinh lỗi hồi quy (regression) trong hệ thống quản lý kho.

---

## 2. Khi Nào Kích Hoạt
- Khi có test case bị FAIL trong `backend/tests/`.
- Khi server FastAPI báo lỗi `500 Internal Server Error`, ngoại lệ CSDL (`IntegrityError`, `CheckConstraint failed`, `database is locked`).
- Khi xuất hiện lỗi logic nghiệp vụ kho: sai lệch tồn kho, tồn kho bị âm, lệch số dư thẻ kho (`stock_ledger`), nhảy cóc trạng thái xuất kho 3 bước.
- Khi AI service timeout (>10s) hoặc gặp lỗi 429 mà không tự động kích hoạt Heuristic Fallback làm sập ứng dụng.
- Khi Frontend React gặp lỗi kết nối API, vỡ giao diện hoặc xử lý sai state.

---

## 3. Được Làm Gì / Không Được Làm Gì

- **ĐƯỢC:**
  - Viết test case cô lập lỗi vào `backend/tests/` để tái hiện lỗi một cách tự động.
  - Sử dụng debug logging (`logging.getLogger`), phân tích call stack, câu lệnh truy vấn SQLAlchemy và log giao dịch.
  - Chỉnh sửa mã nguồn tại đúng vị trí gây ra lỗi sau khi đã chứng minh được nguyên nhân gốc rễ.
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối KHÔNG sửa code theo cảm tính hoặc "đoán mò" khi chưa có kịch bản tái hiện lỗi.
  - Không dùng "băng gạc tạm thời" (quick-patch) như bọc `try...except Exception: pass` để giấu lỗi.
  - Không can thiệp sửa trực tiếp dữ liệu trong file CSDL `warehouse.db` để lấp liếm lỗi logic code.
  - Không sửa đổi schema CSDL khi chưa chạy script sao lưu.

---

## 4. Quy Trình Làm Việc Từng Bước

1. **Thu thập thông tin:** Đọc kỹ traceback, HTTP status code, request payload, phản hồi thực tế từ API và dữ liệu liên quan trong bảng.
2. **Tái hiện lỗi (Reproduce):**
   - Viết một test case tối thiểu trong `backend/tests/` mô phỏng đúng điều kiện phát sinh lỗi.
   - Chạy test case này và xác nhận nó **FAIL** (chứng minh lỗi có thật và tái hiện được).
3. **Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA):**
   - Lần theo luồng dữ liệu (Data Flow): `Frontend Client` $\rightarrow$ `API Router` $\rightarrow$ `Service Business Logic` $\rightarrow$ `Database Transaction & Constraints`.
   - Định vị chính xác dòng code gây lỗi và cơ chế phát sinh (ví dụ: race condition, thiếu begin transaction, sai điều kiện lọc).
4. **Sửa lỗi tận gốc:**
   - Can thiệp chỉnh sửa logic cốt lõi tại đúng vị trí nguyên nhân.
   - Bảo toàn các ràng buộc nghiệp vụ: cỗ máy trạng thái xuất kho 3 bước, chốt chặn tồn âm kép, transaction ACID đồng bộ thẻ kho, và phân quyền RBAC.
5. **Xác minh kép (Dual Verification):**
   - Chạy lại test case tái hiện lỗi: Phải chuyển từ **FAIL $\rightarrow$ PASS**.
   - Chạy toàn bộ test suite dự án bằng lệnh:
     ```powershell
     cd backend; pytest
     ```
     Đảm bảo 100% test cases đều đạt trạng thái màu xanh (PASS).

---

## 5. Định Dạng Output Bắt Buộc

- **Triệu chứng & Mã lỗi:** Mô tả lỗi, mã HTTP hoặc ngoại lệ (ví dụ: `HTTP 500`, `IntegrityError: CHECK constraint failed: chk_positive_stock`).
- **Ca kiểm thử tái hiện:** Tên hàm test và file test đã viết trong `backend/tests/` để tái hiện lỗi.
- **Nguyên nhân gốc rễ (RCA):** Giải thích rõ ràng tại sao lỗi xảy ra ở mức độ code/dữ liệu/giao dịch.
- **Giải pháp khắc phục:** Chi tiết các dòng code được sửa đổi và lý do kỹ thuật.
- **Kết quả xác minh kép:** Output log từ lệnh `pytest` chứng minh lỗi đã được vá và không gây hồi quy.

---

## 6. Checklist Tự Kiểm Tra Trước Khi Hoàn Tất Mode

- [ ] Đã có test case tái hiện lỗi và test đó đã PASS sau khi sửa?
- [ ] Không sử dụng `except: pass` hoặc bỏ qua kiểm tra an toàn?
- [ ] Không làm phát sinh lỗi tồn kho âm hoặc phá vỡ tính toàn vẹn của Thẻ kho?
- [ ] Lệnh `cd backend; pytest` đã chạy và toàn bộ test suite đều đạt màu xanh (PASS 100%)?
- [ ] Không làm thay đổi cấu trúc bảng CSDL khi chưa chạy sao lưu?
