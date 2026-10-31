# Workflow: Architect Mode

## 1. Mục Tiêu
Phân tích yêu cầu, thiết kế giải pháp kiến trúc, đánh giá rủi ro và lập kế hoạch kỹ thuật chi tiết trước khi triển khai mã nguồn vào PharmaCare AI.

## 2. Khi Nào Kích Hoạt
- Khi nhận yêu cầu thêm tính năng lớn, thiết kế bảng mới trong `database.py`, thêm router mới vào `routers/`, hoặc tích hợp AI provider mới vào `services/ai_service.py`.
- Khi cần tái cấu trúc (refactor) luồng nghiệp vụ nhạy cảm như bán hàng FEFO (`routers/pos.py`) hoặc phân quyền RBAC (`routers/auth.py`).

## 3. Được Làm Gì / Không Được Làm Gì
- **ĐƯỢC:**
  - Khảo sát mã nguồn hiện có (`database.py`, `schemas.py`, `routers/`, `services/`, `main.py`).
  - Đề xuất các phương án kiến trúc, vẽ mô hình quan hệ bảng, phân tích ưu nhược điểm.
  - Dự thảo schema Pydantic, ORM Model và luồng xử lý dữ liệu.
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối KHÔNG viết mã nguồn triển khai chính thức hay chỉnh sửa logic code.
  - Không tự ý sửa schema CSDL hoặc can thiệp `database.db`.
  - Không chọn công nghệ nằm ngoài tech stack hiện có (FastAPI, SQLAlchemy, SQLite, Pydantic, Vanilla SPA).

## 4. Quy Trình Làm Việc Từng Bước
1. **Khảo sát hiện trạng:** Đọc các model liên quan trong `database.py` và schema trong `schemas.py`.
2. **Đánh giá ảnh hưởng:** Xác định các endpoint bị tác động trong `routers/` và ảnh hưởng đến kiểm thử trong `tests/`.
3. **Thiết kế giải pháp:** Đưa ra tối thiểu 2 phương án (nêu rõ trade-offs về hiệu năng, độ phức tạp và bảo mật).
4. **Lập kế hoạch triển khai:** Chia nhỏ thành các task rõ ràng theo từng file cụ thể, dự kiến test case tương ứng.
5. **Chờ xác nhận:** Xuất tài liệu thiết kế và dừng lại chờ người dùng phê duyệt phương án.

## 5. Định Dạng Output Bắt Buộc
- **Bối cảnh & Vấn đề:** Tóm tắt yêu cầu và file bị ảnh hưởng.
- **Phương án đề xuất:** Chi tiết Phương án A vs Phương án B kèm bảng so sánh ưu/nhược điểm.
- **Thiết kế kỹ thuật:** Định nghĩa model/schema (nếu có), luồng API endpoint và vai trò RBAC truy cập.
- **Kế hoạch triển khai (Roadmap):** Danh sách file cần sửa/thêm theo đúng thứ tự (`database.py` -> `schemas.py` -> `services/` -> `routers/` -> `tests/`).

## 6. Checklist Tự Kiểm Tra Trước Khi Kết Thúc
- [ ] Đã kiểm tra tính tương thích với nguyên tắc xuất kho FEFO và chuẩn GPP chưa?
- [ ] Đã xét đến phân quyền RBAC (`manager`, `pharmacist`, `cashier`) chưa?
- [ ] Không có file source code nào bị chỉnh sửa trong quá trình thiết kế?
- [ ] Kế hoạch đã bao gồm phương án sao lưu CSDL bằng `python scripts/backup_data.py backup` chưa?
