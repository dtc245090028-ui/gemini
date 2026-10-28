# MỤC LỤC & BỘ ẢNH GIAO DIỆN THỰC TẾ HỆ THỐNG SMARTKHO AI

**Dự án:** Hệ thống Quản lý Kho Thông minh tích hợp AI (Đề tài 07)  
**Thời điểm chụp thực tế:** `2026-10-27T23:29:33+07:00`  
**Công cụ tự động hóa:** Microsoft Edge (`msedge.exe`) qua Playwright 1.64.1 (Không sử dụng thao tác thủ công)  
**Quy chuẩn dữ liệu & An toàn:** 
- Toàn bộ là **GIAO DIỆN THỰC TẾ ĐANG CHẠY TRÊN DOCKER**, hoàn toàn **KHÔNG PHẢI wireframe thiết kế ban đầu**.
- Tuân thủ nghiêm ngặt nguyên tắc chỉ xem và chụp; **tuyệt đối không bấm Lưu, Tạo, Hủy hay Xóa bất kỳ dữ liệu nào**.
- Không chụp và không để lộ bất kỳ API Key, mật khẩu người dùng hay file cấu hình môi trường `.env`.

---

## BẢNG DANH MỤC 14 ẢNH CHỨNG MINH GIAO DIỆN THỰC TẾ

| STT | Tên file ảnh | Tên màn hình / Thao tác | Vai trò người dùng | Chức năng nghiệp vụ & Đặc điểm nhận diện giao diện |
| :-: | :--- | :--- | :---: | :--- |
| 1 | [`01_dang_nhap.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/01_dang_nhap.png) | Trang Đăng nhập hệ thống | Khách (Public) | Form đăng nhập chuẩn bảo mật, logo SmartKho AI, cùng 3 nút đăng nhập nhanh Demo (Admin, Thủ kho, Kế toán). |
| 2 | [`02_dashboard.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/02_dashboard.png) | Dashboard Tổng quan kho | `ADMIN` | Bảng điều khiển KPI: Tổng mặt hàng, giá trị tồn kho, cảnh báo dưới định mức, biểu đồ luân chuyển hàng hóa. |
| 3 | [`03_hang_hoa.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/03_hang_hoa.png) | Quản lý Hàng hóa & Tồn kho | `ADMIN` | Danh sách 76 sản phẩm thực tế từ DB, cột mã hàng, tên, danh mục, tồn hiện tại, tồn tối thiểu, nút Thêm/Sửa/Xóa. |
| 4 | [`04_nha_cung_cap.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/04_nha_cung_cap.png) | Quản lý Nhà cung cấp | `ADMIN` | Danh sách đối tác cung ứng, số điện thoại, địa chỉ, trạng thái hợp tác và nút chức năng thêm nhà cung cấp mới. |
| 5 | [`05_phieu_nhap_danh_sach.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/05_phieu_nhap_danh_sach.png) | Danh sách Phiếu nhập kho | `ADMIN` | Danh sách phiếu nhập hàng, ngày lập, nhà cung cấp, tổng tiền chứng từ và trạng thái `COMPLETED`. |
| 6 | [`06_phieu_nhap_form_tao.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/06_phieu_nhap_form_tao.png) | Form Lập phiếu nhập (Modal) | `ADMIN` | Modal nhập hàng: chọn nhà cung cấp, thêm nhiều mặt hàng kèm số lượng và đơn giá mua (chưa bấm lưu). |
| 7 | [`07_phieu_xuat_danh_sach.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/07_phieu_xuat_danh_sach.png) | Danh sách Phiếu xuất kho | `ADMIN` | Danh sách phiếu xuất kho hiển thị các trạng thái nghiệp vụ: `CONFIRMED`, `SHIPPING`, `COMPLETED`, `CANCELLED`. |
| 8 | [`08_phieu_xuat_form_tao.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/08_phieu_xuat_form_tao.png) | Form Lập phiếu xuất & Cảnh báo tồn | `ADMIN` | Form lập phiếu xuất: kiểm tra số lượng tồn kho theo thời gian thực và hiển thị cảnh báo đỏ khi nhập vượt tồn. |
| 9 | [`09_the_kho.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/09_the_kho.png) | Sổ cái Thẻ kho (Stock Ledger) | `ADMIN` | Bảng kiểm toán biến động (Audit Trail): thời gian, mã phiếu, lượng thay đổi (+/-), tồn sau giao dịch và nút Xuất Excel. |
| 10 | [`10_tro_ly_ai_bao_cao_thang.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/10_tro_ly_ai_bao_cao_thang.png) | Trợ lý AI — Tab 1: Báo cáo tháng | `ADMIN` | Giao diện AI sinh báo cáo tháng: bộ lọc kỳ, thẻ thống kê số liệu, nhận xét điều hành (Executive Summary) và khuyến nghị. |
| 11 | [`11_tro_ly_ai_goi_y_nhap.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/11_tro_ly_ai_goi_y_nhap.png) | Trợ lý AI — Tab 2: Gợi ý nhập hàng | `ADMIN` | Giao diện AI phân tích tốc độ tiêu thụ (daily velocity), số ngày hết hàng dự kiến, huy hiệu ưu tiên `HIGH/MEDIUM/LOW`. |
| 12 | [`12_tro_ly_ai_bat_thuong.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/12_tro_ly_ai_bat_thuong.png) | Trợ lý AI — Tab 3: Biến động bất thường | `ADMIN` | Giao diện AI phát hiện các trường hợp xuất tăng đột biến (`SURGE_EXPORT`) và hàng tồn kho lâu ngày không xuất (`DEAD_STOCK`). |
| 13 | [`13_swagger_api_docs.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/13_swagger_api_docs.png) | Tài liệu OpenAPI Swagger UI (`/docs`)| Public | Trang Swagger UI trực tiếp tại port 8000 liệt kê đầy đủ 44 API endpoints được phân loại theo từng nhóm chức năng. |
| 14 | [`14_ke_toan_an_nut_thao_tac.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/14_ke_toan_an_nut_thao_tac.png) | Phân quyền UI — Vai trò Kế toán | `ACCOUNTANT` | Minh chứng phân quyền: khi đăng nhập với vai trò Kế toán, toàn bộ các nút "Thêm mới hàng hóa", Sửa, Xóa đều bị ẩn hoàn toàn. |

---

## HƯỚNG DẪN XEM VÀ CHÈN VÀO BÁO CÁO ĐỒ ÁN
- Các file ảnh có thể chèn trực tiếp vào tài liệu Word/LaTeX/Markdown với kích thước khuyến nghị chiều rộng `100%` hoặc `14cm`.
- Đối với phần kiểm định phân quyền RBAC: Sử dụng cặp ảnh so sánh giữa [`03_hang_hoa.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/03_hang_hoa.png) (Admin có nút thao tác) và [`14_ke_toan_an_nut_thao_tac.png`](file:///e:/gemini/docs_evidence/05_hinh_giao_dien/14_ke_toan_an_nut_thao_tac.png) (Kế toán bị ẩn nút) làm minh chứng trực quan nhất.
