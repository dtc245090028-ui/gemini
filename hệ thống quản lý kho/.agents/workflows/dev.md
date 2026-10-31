# Workflow: Dev Mode — Hệ Thống Quản Lý Kho Tích Hợp AI

## 1. Mục Tiêu
Hiện thực hóa các tính năng, API endpoints, logic dịch vụ kho và giao diện React SPA theo đúng Clean Architecture 3 tầng, chuẩn mã nguồn sạch và các ràng buộc toàn vẹn của hệ thống.

---

## 2. Khi Nào Kích Hoạt
- Khi kế hoạch kỹ thuật đã được duyệt (sau Architect Mode) hoặc nhận yêu cầu phát triển mã nguồn cụ thể.
- Khi người dùng yêu cầu thực hiện bước công việc (ví dụ: *"Làm Bước 06"*, *"Code tính năng xuất kho"*), tra cứu ngay tài liệu tại `docs/plans/TIEN-DO.md` và file tương ứng `docs/plans/Buoc-XX-*.md` kết hợp `Prompt.md` để nắm rõ tiêu chuẩn đầu vào/đầu ra.

---

## 3. Được Làm Gì / Không Được Làm Gì

- **ĐƯỢC:**
  - Viết code mới và chỉnh sửa code theo đúng phân tầng kiến trúc:
    - `backend/app/models/`: Định nghĩa ORM Models và ràng buộc CSDL.
    - `backend/app/schemas/`: Định nghĩa Pydantic Schemas validate dữ liệu vào/ra.
    - `backend/app/services/`: Triển khai Business Logic, Transaction ACID, AI Copilot & Fallback.
    - `backend/app/api/v1/endpoints/`: Viết FastAPI Routers, inject dependencies và kiểm tra quyền RBAC.
    - `frontend/src/`: Phát triển giao diện React 18 SPA (pages, components, context, api client).
  - Tích hợp kiểm tra chống tồn âm và ghi nhận thẻ kho đồng bộ.
  - Tích hợp Fallback Heuristic Engine dự phòng khi gọi Gemini API.
- **KHÔNG ĐƯỢC:**
  - Tuyệt đối KHÔNG viết business logic phức tạp bên trong các file endpoint tại `api/v1/endpoints/`.
  - Không thực hiện thao tác thay đổi tồn kho ngoài Database Transaction ACID.
  - Không sửa đổi schema CSDL khi chưa chạy script sao lưu.
  - Không hardcode API key (`GEMINI_API_KEY`), mật khẩu, token vào mã nguồn.
  - Không cho phép AI tự động ghi/sửa dữ liệu kho trong CSDL.

---

## 4. Quy Trình Làm Việc Từng Bước

1. **Kiểm tra đầu vào:** Đọc đặc tả nhiệm vụ trong `docs/plans/Buoc-XX-*.md`, `docs/codebase-map.md` và `Prompt.md`; xác định chính xác các file liên quan.
2. **Sao lưu CSDL (nếu đụng schema/dữ liệu):** Chạy lệnh sao lưu Online Backup trước khi can thiệp:
   ```powershell
   python backend/app/core/backup_db.py backup
   ```
3. **Cập nhật Schema & Model:**
   - Định nghĩa/cập nhật ORM Models tại `backend/app/models/` (chú ý `CheckConstraint` và Foreign Key).
   - Định nghĩa Pydantic Schemas tại `backend/app/schemas/` (validate type, boundary, enum).
4. **Triển khai Business Logic tại Services:**
   - Xây dựng nghiệp vụ trong `backend/app/services/inventory_service.py` hoặc dịch vụ tương ứng.
   - Luôn sử dụng transaction ACID cho các biến động tồn kho:
     ```python
     with db.begin():
         # 1. Kiểm tra tồn kho khả dụng
         # 2. Cập nhật current_stock
         # 3. Ghi log thẻ kho (StockLedger)
     ```
   - Xử lý Idempotency Key chống trùng lặp nếu là giao dịch tạo phiếu/điều chỉnh kho.
   - Nếu gọi Gemini API: Tích hợp timeout (<=10s), In-Day Cache (`ai_cache.py`), và Fallback tự động (`fallback_service.py`).
5. **Tạo / Cập nhật Endpoint:**
   - Viết API router tại `backend/app/api/v1/endpoints/`.
   - Inject dependencies `get_db`, `get_current_active_user`, và hàm kiểm tra vai trò RBAC (`admin`, `warehouse_keeper`, `accountant`).
   - Xử lý lỗi chuẩn mực bằng `fastapi.HTTPException` với status code thích hợp (400, 401, 403, 404, 409, 422) và thông điệp tiếng Việt rõ ràng.
6. **Tích hợp Giao Diện Frontend React:**
   - Cập nhật trang tại `frontend/src/pages/` hoặc component tại `frontend/src/components/`.
   - Giao tiếp qua `frontend/src/api/` hoặc Axios/Fetch client chuẩn hóa.
   - Tuân thủ quy chuẩn UX: Loading skeleton/spinner, Toast thông báo lỗi/thành công bằng tiếng Việt, ConfirmModal có bắt buộc nhập lý do (>= 5 ký tự) khi hủy/xóa phiếu.
7. **Chạy kiểm thử xác minh:**
   - Thực thi bộ test tự động để đảm bảo không gây hồi quy:
     ```powershell
     cd backend; pytest
     ```

---

## 5. Định Dạng Output Bắt Buộc

- **Nhiệm vụ / Chức năng thực hiện:** Tên hoặc mã bước theo `docs/plans/TIEN-DO.md`.
- **Danh sách file thay đổi:** Liệt kê đầy đủ đường dẫn các file đã thêm hoặc chỉnh sửa.
- **Chi tiết thay đổi:** Tóm tắt ngắn gọn các model, schema, service method, router endpoint hoặc React component đã thêm/sửa.
- **Kết quả kiểm thử:** Trích xuất kết quả chạy lệnh `pytest` (Số test pass, thời gian chạy).

---

## 6. Checklist Tự Kiểm Tra Trước Khi Hoàn Tất Mode

- [ ] Code có tuân thủ đúng quy ước: `snake_case` (Python), `PascalCase` (React/Model/Schema), `camelCase` (JS function)?
- [ ] Các thông báo lỗi `HTTPException` và thông báo trên giao diện đều bằng tiếng Việt có nghĩa?
- [ ] Đã phân quyền đúng vai trò RBAC (`admin`, `warehouse_keeper`, `accountant`) cho API mới?
- [ ] Nghiệp vụ xuất kho tuân thủ cỗ máy trạng thái 3 bước (`CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`)?
- [ ] Chốt chặn tồn âm kép và ghi thẻ kho (`stock_ledger`) đã được bảo đảm trong transaction?
- [ ] Đã có fallback dự phòng nếu endpoint sử dụng AI?
- [ ] Đã chạy `cd backend; pytest` và toàn bộ test suite đạt 100% màu xanh (PASS)?
- [ ] Tuyệt đối KHÔNG có secret, API key hay thông tin nhạy cảm bị rò rỉ vào code?
