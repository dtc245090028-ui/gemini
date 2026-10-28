# BƯỚC 09: XÂY DỰNG FRONTEND WEB REACT & TAILWIND (FRONTEND APPLICATION)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-09-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - Mã nguồn được sinh trực tiếp vào thư mục `frontend/src/` (components, pages, context, api client).

---

## 1. Mục tiêu bước 9

- Xây dựng giao diện Web Dashboard hoàn chỉnh, hiện đại bằng React 18 + Vite + Tailwind CSS + Lucide Icons.
- Thiết kế hệ thống Design Tokens nhất quán (`tokens.css`) hỗ trợ chuyển đổi giao diện Sáng / Tối (Dark / Light Theme).
- Kết nối toàn bộ RESTful APIs từ Backend: Đăng nhập, Hàng hóa (kèm upload ảnh), Nhà cung cấp, Phiếu nhập, Phiếu xuất (luồng 3 bước), Thẻ kho, Báo cáo NXT (kèm xuất Excel) và Trợ lý AI SmartKho Copilot.
- Quản lý trải nghiệm người dùng nâng cao: Hộp thoại xác nhận thao tác nguy hiểm yêu cầu nhập lý do (`ConfirmContext`), hệ thống thông báo Toast (`ToastContext`), cơ chế lưu nháp form (`draftStorage.js`).
- Tích hợp bộ chuyển đổi vai trò (Role Switcher) nhanh trên thanh tiêu đề để thuận tiện demo cho giảng viên xem quyền hạn của Admin, Thủ kho, Kế toán.

---

## 2. Nội dung công việc chi tiết

### 2.1. Khung Giao diện & Điều hướng (Layout & Navigation)

- `Layout.jsx`:
  - `Sidebar`: Menu điều hướng (Tổng quan, Hàng hóa, Nhà cung cấp, Nhập kho, Xuất kho, Thẻ kho, Trợ lý AI & Báo cáo). Báo cáo Nhập-Xuất-Tồn được gộp trực tiếp vào tab phân hệ Trợ lý AI.
  - `Header`: Thông tin tài khoản đăng nhập, nút chuyển nhanh vai trò (Role Switcher: Admin, Thủ kho, Kế toán), nút chuyển đổi Dark / Light Theme, nút Đăng xuất.
- `AuthContext.jsx`: Quản lý JWT Token, phân quyền người dùng, lưu phiên đăng nhập tại `localStorage`.
- `ConfirmContext.jsx`: Hộp thoại xác nhận hành động hủy/xóa phiếu xuất bắt buộc nhập lý do ($\ge 5$ ký tự) để chống bấm nhầm.
- `ToastContext.jsx`: Hệ thống thông báo toast đa trạng thái (success, error, warning, info) tự động tắt sau 3 giây.

### 2.2. Các Trang Chức năng Chính (Pages)

1. **Trang Dashboard (`pages/Dashboard.jsx`)**:
   - Thẻ thống kê KPI: Tổng mặt hàng, Hàng sắp hết, Giá trị tồn kho, Phiếu trong tháng.
   - Bảng cảnh báo hàng dưới mức tồn tối thiểu (`is_low_stock` kèm badge màu).
2. **Trang Hàng hóa (`pages/Products.jsx`)**:
   - Danh sách hàng hóa: Tìm kiếm thời gian thực, lọc danh mục, hiển thị hình ảnh thu nhỏ (`image_url`).
   - Modal Thêm / Sửa mặt hàng: Tự động tạo phiếu nhập ban đầu nếu có tồn kho khai báo ban đầu.
   - Modal Upload ảnh sản phẩm (`POST /api/v1/products/{id}/image`).
   - Nút liên kết nhanh xem Thẻ kho của mặt hàng.
3. **Trang Lập Phiếu Nhập (`pages/ImportNotes.jsx`)**:
   - Chọn nhà cung cấp, ngày nhập, bảng chọn sản phẩm (`ProductSelect.jsx`) kèm số lượng và đơn giá nhập.
   - Tự động tính tổng tiền; Lưu trữ bản nháp cục bộ qua `draftStorage.js`.
4. **Trang Lập & Quản lý Phiếu Xuất (`pages/ExportNotes.jsx`)**:
   - Hỗ trợ luồng 3 trạng thái: `CONFIRMED` (Chờ xuất kho) $\longrightarrow$ `SHIPPING` (Đang giao / trừ kho) $\longrightarrow$ `COMPLETED` (Hoàn thành) hoặc `CANCELLED` (Đã hủy / hoàn kho).
   - Form tạo phiếu xuất kiểm tra tồn kho tức thời (Defensive UI chặn xuất vượt số lượng tồn).
   - Cho phép xóa phiếu xuất ở trạng thái `CONFIRMED` (`DELETE /api/v1/export-notes/{id}`) trước khi xuất kho.
5. **Trang Thẻ Kho (`pages/StockLedger.jsx`)**:
   - Tra cứu lịch sử nhập xuất theo từng mặt hàng và khoảng thời gian.
   - Bảng thẻ kho hiển thị số lượng nhập, xuất và số dư tồn sau giao dịch (không hiển thị đơn giá/thành tiền).
   - Nút **"Xuất Thẻ kho Excel"** (`GET /api/v1/reports/stock-ledger-excel/{product_id}`).
6. **Trang Trợ lý AI & Báo cáo (`pages/AIAssistant.jsx`)**:
   - **Tab 1 - Báo cáo Nhập - Xuất - Tồn**: Thống kê số lượng, giá trị tồn, xuất file Excel (`GET /api/v1/reports/inventory-summary-excel`).
   - **Tab 2 - Gợi ý Nhập hàng**: AI phân tích tốc độ tiêu thụ 30 ngày và đưa ra đề xuất số lượng cần nhập, tích hợp nút sinh nhanh đơn hàng (`/ai/generate-order`).
   - **Tab 3 - Phát hiện Bất thường**: Cảnh báo hàng tồn kho lâu ngày không xuất hoặc xuất tăng đột biến $>200\%$.
   - **Tab 4 - Hỏi đáp SmartKho Copilot**: Trò chuyện tự do với AI về trạng thái kho hàng qua `/ai/ask`.

---

## 3. Cấu trúc file/thư mục triển khai thực tế

```text
frontend/
├── src/
│   ├── api/
│   │   └── client.js                  # Axios client cấu hình baseURL, JWT auth & 401 interceptor
│   ├── components/
│   │   ├── Badge.jsx                  # Component nhãn trạng thái/cảnh báo
│   │   ├── ErrorBoundary.jsx          # Bắt lỗi crash UI toàn cục
│   │   ├── Layout.jsx                 # Sidebar + Header + Theme Toggle + Role Switcher
│   │   ├── Loader.jsx / Loader.css    # Hiệu ứng loading spinner
│   │   ├── Modal.jsx                  # Hộp thoại modal tái sử dụng
│   │   └── ProductSelect.jsx          # Dropdown tìm kiếm và chọn sản phẩm
│   ├── context/
│   │   ├── AuthContext.jsx            # Quản lý đăng nhập & phân quyền RBAC
│   │   ├── ConfirmContext.jsx         # Modal xác nhận thao tác kèm bắt buộc lý do (>= 5 ký tự)
│   │   └── ToastContext.jsx           # Quản lý thông báo toast notification
│   ├── hooks/
│   │   └── useDelayedLoading.js       # Hook chống nhấp nháy spinner khi gọi API nhanh
│   ├── pages/
│   │   ├── AIAssistant.jsx            # Báo cáo Nhập-Xuất-Tồn (kèm Excel) & Trợ lý AI 4 tabs
│   │   ├── Dashboard.jsx              # Tổng quan KPI & cảnh báo tồn thấp
│   │   ├── ExportNotes.jsx            # Lập & quản lý phiếu xuất luồng 3 bước
│   │   ├── ImportNotes.jsx            # Lập phiếu nhập kho & tính tiền
│   │   ├── Login.jsx                  # Đăng nhập hệ thống
│   │   ├── Products.jsx               # Quản lý sản phẩm & upload ảnh
│   │   ├── StockLedger.jsx            # Tra cứu thẻ kho & xuất file Excel
│   │   └── Suppliers.jsx              # Quản lý danh mục nhà cung cấp
│   ├── utils/
│   │   ├── draftStorage.js            # Lưu và khôi phục nháp phiếu vào localStorage
│   │   └── stockEvents.js             # Quản lý custom event cập nhật tồn kho real-time
│   ├── App.jsx                        # React Router v6 định tuyến các trang
│   ├── index.css                      # Tailwind base styling
│   ├── main.jsx                       # Entry point React 18
│   └── tokens.css                     # Design tokens cho Dark / Light mode
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Giao diện phản hồi tức thời (Single Page Application), không bị load lại trang khi thao tác.
- [x] Form xuất kho chặn người dùng bấm gửi nếu nhập số lượng xuất lớn hơn tồn kho hiện có (Defensive UI kết hợp Backend ACID).
- [x] Nút "Yêu cầu AI phân tích" hiển thị trạng thái loading đẹp mắt trong lúc chờ phản hồi (Gemini 3.5 / Heuristic Fallback).
- [x] Hỗ trợ Dark Theme và Light Theme hoàn chỉnh, lưu cấu hình vào `localStorage`.
- [x] Thao tác hủy phiếu hoặc xóa phiếu xuất chưa giao bắt buộc xác nhận và điền lý do $\ge 5$ ký tự.
- [x] Nút xuất Excel hoạt động tốt, tải về file `.xlsx` chuẩn định dạng.
- [x] Bộ chuyển đổi vai trò Demo tức thì (ADMIN, WAREHOUSE_KEEPER, ACCOUNTANT) hỗ trợ thuyết trình 1-click.
- [x] Build thành công không có lỗi cú pháp hoặc thiếu modules (`npm run build` PASS).

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/gemini/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 09** theo đúng mẫu sau:

```markdown
| YYYY-MM-DD | Bước 09 | Xây dựng Frontend Web (React + Tailwind) | Hoàn thành | `frontend/src/App.jsx`, `pages/Dashboard.jsx`, `pages/...` | Đã hoàn thiện giao diện React + Tailwind CSS cho toàn bộ 7 phân hệ, Dark mode, ConfirmModal |
```

---

## 6. Lịch sử đồng bộ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Gộp trang Báo cáo:** Xác nhận không có trang riêng `Reports.jsx`; toàn bộ chức năng Báo cáo Nhập-Xuất-Tồn và xuất Excel đã được tích hợp gọn gàng tại Tab 1 của `pages/AIAssistant.jsx`.
  - **Đường dẫn Client:** Cập nhật vị trí chính xác của Axios client tại `src/api/client.js`.
  - **Bổ sung tính năng Dark / Light Theme:** Bổ sung mô tả hệ thống Design Tokens (`tokens.css`) và nút toggle theme trên thanh tiêu đề `Layout.jsx`.
  - **Bổ sung Dialogs & Notifications:** Bổ sung `ConfirmContext.jsx` (bắt buộc lý do $\ge 5$ ký tự khi hủy/xóa phiếu) và `ToastContext.jsx`.
  - **Bổ sung Upload ảnh:** Thêm chức năng tải ảnh sản phẩm (`POST /api/v1/products/{id}/image`) trên trang `Products.jsx`.
  - **Đồng bộ luồng 3 trạng thái phiếu xuất:** Cập nhật giao diện `ExportNotes.jsx` hỗ trợ đầy đủ các bước `CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED` và nút xóa phiếu chưa xuất kho.
  - **Bổ sung tính năng Xuất Excel:** Bổ sung nút xuất file Excel tại Thẻ kho (`StockLedger.jsx`) và Báo cáo NXT (`AIAssistant.jsx`).
