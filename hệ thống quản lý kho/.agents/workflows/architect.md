# Workflow: Architect Mode — Hệ Thống Quản Lý Kho Tích Hợp AI

## 1. Mục Tiêu
Phân tích yêu cầu nghiệp vụ, thiết kế kiến trúc kỹ thuật chuẩn (Clean Architecture 3 tầng, CSDL SQLite 3NF ACID, giao diện React 18 SPA, Gemini AI Fallback) và lập kế hoạch chi tiết trước khi can thiệp mã nguồn.

---

## 2. Khi Nào Kích Hoạt
- Khi nhận yêu cầu thiết kế tính năng mới, thêm bảng/cột CSDL trong `backend/app/models/`, thêm endpoint trong `backend/app/api/v1/endpoints/`.
- Khi thiết kế tích hợp AI mới (prompt template, chain fallback, cache) trong `backend/app/services/ai_service.py`.
- Khi tái cấu trúc (refactor) luồng giao dịch nhạy cảm: nhập kho, xuất kho 3 bước (`inventory_service.py`), đồng bộ thẻ kho, hoặc phân quyền RBAC.
- Khi thiết kế màn hình giao diện mới hoặc luồng tương tác phức tạp trên Frontend React.

---

## 3. Được Làm Gì / Không Được Làm Gì

- **ĐƯỢC:**
  - Khảo sát mã nguồn hiện có (`docs/codebase-map.md`, `backend/app/`, `frontend/src/`).
  - Đề xuất các phương án kiến trúc, vẽ sơ đồ Mermaid (ERD, Sequence Diagram, State Machine 3 bước).
  - Phân tích ưu/nhược điểm (tradeoffs) về hiệu năng, tính toàn vẹn dữ liệu và độ phức tạp mã nguồn.
  - Dự thảo schema Pydantic, ORM Model, luồng API DTO và hợp đồng dữ liệu với Frontend.
  - Tạo hoặc cập nhật file kế hoạch triển khai tại `docs/plans/Buoc-XX-*.md`.
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối KHÔNG viết mã nguồn triển khai chính thức hay chỉnh sửa logic code trong mode này.
  - Không tự ý sửa cấu trúc CSDL `warehouse.db` hoặc can thiệp dữ liệu khi chưa được duyệt.
  - Không tự ý chọn công nghệ nằm ngoài tech stack của dự án (FastAPI, SQLAlchemy 2.0, SQLite, React 18, Tailwind CSS, Vite).

---

## 4. Quy Trình Làm Việc Từng Bước

1. **Khảo sát hiện trạng:** Đọc `docs/codebase-map.md`, `Prompt.md`, các model liên quan tại `backend/app/models/` và service tại `backend/app/services/`.
2. **Đánh giá phạm vi ảnh hưởng (Impact Analysis):**
   - CSDL: Có thêm/sửa bảng hay cột nào không? Ràng buộc toàn vẹn khóa ngoại và `CheckConstraint` ra sao?
   - Backend: Cần cập nhật `schemas/`, `services/`, `endpoints/` nào?
   - Frontend: Cần thêm/sửa component, page hay API client nào?
   - Kiểm thử: Cần bổ sung test case nào vào `backend/tests/`?
3. **Thiết kế giải pháp kỹ thuật:** Đưa ra tối thiểu 2 phương án (Phương án A vs Phương án B) kèm so sánh rõ ràng:
   - Tính toàn vẹn giao dịch (ACID) & Khóa chống tồn âm.
   - Hiệu năng truy vấn SQLite & Tính dễ bảo trì, dễ hiểu cho đồ án sinh viên.
   - An toàn AI và kịch bản Fallback khi mất mạng/hết quota.
4. **Lập kế hoạch triển khai (Implementation Plan):** Chia nhỏ thành các bước rõ ràng với checklist `[ ]`, lưu vào `docs/plans/Buoc-XX-<ten-buoc>.md` theo thứ tự:
   `Model/DB Migration` $\rightarrow$ `Schemas` $\rightarrow$ `Service (Business/AI)` $\rightarrow$ `API Endpoints` $\rightarrow$ `Frontend UI` $\rightarrow$ `Pytest Suite`.
5. **Dừng lại chờ phê duyệt:** Trình bày phương án cho người dùng và chờ xác nhận trước khi chuyển sang Dev mode.

---

## 5. Định Dạng Output Bắt Buộc

- **Bối cảnh & Vấn đề:** Tóm tắt yêu cầu nghiệp vụ và các module bị tác động.
- **Phương án đề xuất:** Chi tiết Phương án A vs Phương án B kèm bảng so sánh ưu/nhược điểm.
- **Thiết kế kỹ thuật chi tiết:**
  - Thiết kế Model / Schema / ERD (nếu có).
  - Luồng API (Method, URL, Request/Response payload, mã lỗi).
  - Ma trận phân quyền RBAC (`admin`, `warehouse_keeper`, `accountant`).
  - Thiết kế Fallback (nếu liên quan đến AI).
- **Kế hoạch triển khai (Roadmap):** Danh sách file cụ thể cần sửa/thêm theo đúng trình tự phân tầng.

---

## 6. Checklist Tự Kiểm Tra Trước Khi Hoàn Tất Mode

- [ ] Đã kiểm tra tính tương thích với cỗ máy trạng thái xuất kho 3 bước (`CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`)?
- [ ] Đã xét chốt chặn kép chống tồn âm (Database CheckConstraint + Service Validation)?
- [ ] Mọi thay đổi tồn kho đều được đảm bảo bọc trong transaction ACID và ghi Thẻ kho (`stock_ledger`)?
- [ ] Đã xét phân quyền RBAC cho 3 vai trò: `admin`, `warehouse_keeper`, `accountant`?
- [ ] Đã có phương án sao lưu CSDL bằng `python backend/app/core/backup_db.py backup` trước khi đụng schema?
- [ ] Tuyệt đối KHÔNG có file source code logic nào bị chỉnh sửa trong quá trình thiết kế kiến trúc?
