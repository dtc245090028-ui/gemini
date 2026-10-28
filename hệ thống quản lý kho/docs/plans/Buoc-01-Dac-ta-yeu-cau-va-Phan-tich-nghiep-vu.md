# BƯỚC 01: ĐẶC TẢ YÊU CẦU & PHÂN TÍCH NGHIỆP VỤ (REQUIREMENTS ANALYSIS)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-01-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - `docs/SDLC/KT1/01_SRS_and_UseCases.md`: SẢN PHẨM BÀN GIAO THẬT (Deliverable) dùng để nộp bài và chấm điểm giai đoạn KT1.

---

## 1. Mục tiêu bước 1

- Thiết lập ranh giới chức năng rõ ràng cho đồ án "Hệ thống quản lý kho có tích hợp AI" (Đề tài 07).
- Phân tích chi tiết 3 Actor: Quản trị viên (Admin), Thủ kho (Warehouse Keeper), Kế toán (Accountant).
- Xây dựng sơ đồ Use Case tổng quan và đặc tả các luồng nghiệp vụ kho chính.
- Xác định phạm vi và bài toán đầu vào/đầu ra cho 3 chức năng AI.

---

## 2. Nội dung công việc chi tiết

### 2.1. Phân tích 3 Actor & Ma trận quyền hạn

1. **Quản trị viên (Admin)**:
   - Khởi tạo tài khoản người dùng mới và phân vai trò (`ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT`) qua API `POST /auth/users`. (Quản lý sửa/khóa/đổi mật khẩu thuộc lộ trình nâng cấp ERP sau).
   - Quản trị tham số hệ thống và API Key AI (Gemini) an toàn qua biến môi trường tĩnh `.env` / Pydantic Settings (không mở form UI cấu hình để bảo mật tuyệt đối API Key).
   - Xem toàn bộ báo cáo tổng hợp hệ thống.
2. **Thủ kho (Warehouse Keeper)**:
   - Tạo phiếu nhập kho từ nhà cung cấp (ACID Transaction cập nhật tăng tồn kho và ghi Thẻ kho).
   - Lập và điều phối phiếu xuất kho theo cỗ máy trạng thái 3 bước (`CONFIRMED` -> `SHIPPING` -> `COMPLETED`), kiểm tra chống tồn âm nghiêm ngặt (chỉ trừ tồn kho và ghi Thẻ kho khi chuyển sang `SHIPPING`). Cho phép xóa phiếu xuất khi còn ở `CONFIRMED`.
   - Theo dõi tồn kho thực tế, nhận cảnh báo hàng chạm/dưới mức tồn tối thiểu (`is_low_stock`).
   - Tra cứu Thẻ kho chi tiết theo từng mặt hàng (chỉ theo dõi số lượng biến động và số dư tức thời sau giao dịch, không kèm đơn giá/thành tiền).
   - Xem gợi ý nhập hàng và tóm tắt biến động từ AI.
3. **Kế toán (Accountant)**:
   - Tra cứu lịch sử nhập xuất theo chứng từ, thời gian, nhà cung cấp (thông qua danh sách phiếu nhập kho).
   - Tra cứu Thẻ kho theo mặt hàng và thời gian (chỉ đọc số lượng, không có lọc theo nhà cung cấp trên Thẻ kho).
   - Xem báo cáo tổng hợp Nhập - Xuất - Tồn theo kỳ (tháng, quý) tích hợp tại phân hệ Trợ lý AI & Báo cáo (`AIAssistant.jsx`).
   - Ranh giới quyền hạn: Chỉ có quyền đọc (Read-only); tuyệt đối không được phép tạo/duyệt phiếu hoặc can thiệp làm thay đổi trực tiếp số lượng tồn kho vật lý.

### 2.2. Đặc tả các luồng nghiệp vụ cốt lõi

- **Luồng Nhập kho**: Lập phiếu $\rightarrow$ Nhập danh sách mặt hàng, số lượng, đơn giá $\rightarrow$ Xác nhận $\rightarrow$ Transaction cập nhật tăng tồn kho $\rightarrow$ Ghi Thẻ kho (`IMPORT`).
- **Luồng Xuất kho (Cỗ máy trạng thái 3 bước)**:
  - Bước 1: Lập phiếu $\rightarrow$ Chọn mặt hàng, số lượng xuất $\rightarrow$ Kiểm tra `current_stock >= requested_qty` $\rightarrow$ Nếu thiếu: báo lỗi HTTP 400 và dừng $\rightarrow$ Nếu đủ: Lưu phiếu ở trạng thái `CONFIRMED` (chưa trừ tồn kho, cho phép xóa phiếu nếu cần).
  - Bước 2: Khi hàng rời cửa kho, chuyển sang trạng thái `SHIPPING` $\rightarrow$ Chính thức trừ tồn kho và ghi Thẻ kho (`EXPORT`). Nếu giao hàng thất bại, có thể hủy hoàn trả lại tồn kho.
  - Bước 3: Giao nhận thành công, chuyển sang trạng thái `COMPLETED` (khóa vĩnh viễn chứng từ).
- **Luồng Cảnh báo tồn**: Tự động đánh dấu mặt hàng khi `current_stock <= min_stock` qua trường tính toán `@computed_field is_low_stock`.
- **Báo cáo Nhập - Xuất - Tồn**: Được tích hợp trực tiếp vào màn hình Trợ lý AI & Báo cáo (`AIAssistant.jsx`), gộp chung so với thiết kế tách rời ban đầu để tiện theo dõi đối chiếu một nơi.

### 2.3. Xác định 3 chức năng AI

1. AI sinh báo cáo Nhập - Xuất - Tồn theo tháng từ dữ liệu tổng hợp.
2. AI gợi ý nhập hàng dựa trên tồn kho, tồn tối thiểu và tốc độ xuất.
3. AI tóm tắt biến động bất thường (xuất tăng đột biến $>200\%$ hoặc hàng tồn lâu $>30$ ngày).
*(Mở rộng sau: Phân hệ Hỏi đáp tự do / Trợ lý kho SmartKho và AI sinh đơn hàng).*

---

## 3. Cấu trúc file/thư mục cần sinh

Khi thực hiện bước này, sản phẩm bàn giao thực tế phải được tạo ra chính xác tại:

```text
he-thong-quan-ly-kho/
└── docs/
    └── SDLC/
        └── KT1/
            └── 01_SRS_and_UseCases.md        # File đặc tả yêu cầu, phân tích 3 actor và sơ đồ Use Case
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [ ] Tài liệu đặc tả được viết bằng tiếng Việt rõ ràng, mạch lạc, chuẩn thuật ngữ chuyên ngành.
- [ ] Có sơ đồ Use Case (dạng PlantUML/Mermaid hoặc hình vẽ).
- [ ] Bám sát 100% yêu cầu trong file gốc `de_tai_07.md`.
- [ ] Được lưu trữ chính xác tại `docs/SDLC/KT1/01_SRS_and_UseCases.md`.

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 01** theo đúng mẫu sau:

```markdown
| YYYY-MM-DD | Bước 01 | Đặc tả Yêu cầu & Phân tích Nghiệp vụ | Hoàn thành | `docs/SDLC/KT1/01_SRS_and_UseCases.md` | Đã hoàn thiện tài liệu SRS và sơ đồ Use Case |
```

---

## 6. Lịch sử đồng bộ (Reconciliation History)

- **Ngày thực hiện:** 2026-10-28
- **Căn cứ:** Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md) (Mục #1, #2, #3, #4, #7, #26, #32, #34).
- **Nội dung điều chỉnh:**
  1. *[Mục #1, #3 - Nhóm A]:* Điều chỉnh phạm vi quyền Admin: bỏ mô tả cấu hình hệ thống/API key trên giao diện web và quản lý user toàn diện; ghi nhận cấu hình thực tế qua file `.env` và API `POST /auth/users` (`backend/app/core/config.py` L23-24, `backend/app/api/v1/endpoints/auth.py` L96).
  2. *[Mục #4 - Nhóm A]:* Ghi nhận Báo cáo Nhập-Xuất-Tồn được tích hợp trực tiếp vào màn hình Trợ lý AI (`frontend/src/pages/AIAssistant.jsx` L174) thay vì tách trang `Reports.jsx` độc lập.
  3. *[Mục #7 - Nhóm A]:* Làm rõ tra cứu lịch sử theo Nhà cung cấp chỉ áp dụng cho danh sách Phiếu nhập kho, Thẻ kho là sổ cái số lượng vật lý theo Mã hàng (`backend/app/models/stock_ledger.py` L9-28).
  4. *[Mục #26, #32 - Nhóm C, D]:* Đồng bộ luồng xuất kho từ 1 bước sang cỗ máy trạng thái 3 bước (`CONFIRMED` -> `SHIPPING` -> `COMPLETED`), hàng chỉ trừ tồn khi sang `SHIPPING` (`backend/app/services/inventory_service.py` L258-277, L391-440).
  5. *[Mục #34 - Nhóm D]:* Thống nhất vai trò Kế toán: chỉ có quyền Read-only đối soát chứng từ và báo cáo, không được can thiệp vào số lượng kho vật lý (`backend/app/api/deps.py` L135-148).
- **Lý do:** Điều chỉnh tài liệu kế hoạch cho khớp 100% với mã nguồn và hành vi thực tế của web.
