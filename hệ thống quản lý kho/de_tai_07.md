# Hệ thống quản lý kho có tích hợp AI

## 1. Mô tả bài toán

Doanh nghiệp nhỏ cần quản lý hàng hóa, nhà cung cấp, nhập kho, xuất kho, tồn kho và cảnh báo hàng sắp hết. Quản lý bằng bảng tính dễ sai lệch số lượng, khó truy vết giao dịch và chậm phát hiện bất thường. Đề tài yêu cầu xây dựng hệ thống quản lý kho có tích hợp AI sinh báo cáo nhập xuất tồn, tóm tắt biến động kho và gợi ý nhập hàng.

1. Mục tiêu

- Xây dựng hệ thống quản lý hàng hóa, nhà cung cấp, phiếu nhập, phiếu xuất và tồn kho.
- Tích hợp AI để sinh báo cáo nhập xuất tồn, phát hiện biến động đáng chú ý và gợi ý nhập hàng.
- Sử dụng AI trong SDLC để thiết kế nghiệp vụ kho, sinh mã, kiểm thử và tài liệu.
- Đảm bảo số liệu kho nhất quán và có thể truy vết.

1. Yêu cầu chức năng

3.1. Chức năng quản lý

1. Đăng nhập và phân quyền quản trị viên, thủ kho, kế toán.
2. Quản lý hàng hóa, nhóm hàng, đơn vị tính, tồn tối thiểu.
3. Quản lý nhà cung cấp.
4. Lập phiếu nhập kho và cập nhật tồn kho.
5. Lập phiếu xuất kho và kiểm tra số lượng còn.
6. Tra cứu lịch sử nhập xuất theo hàng hóa, thời gian, nhà cung cấp.
7. Cảnh báo hàng dưới tồn tối thiểu.
8. Thống kê nhập xuất tồn và xuất báo cáo.

3.2. Chức năng AI

1. AI sinh báo cáo nhập xuất tồn theo tháng từ dữ liệu kho.
2. AI gợi ý nhập hàng dựa trên tồn kho, mức tồn tối thiểu và tốc độ xuất.
3. AI tóm tắt biến động bất thường, ví dụ xuất tăng đột biến hoặc hàng tồn lâu.

4. Yêu cầu kỹ thuật

- Backend: FastAPI/Flask/Django.
- Frontend: React/Vue/HTML template.
- CSDL: SQLite/MySQL/PostgreSQL.
- AI Engine: OpenAI/Gemini/Claude/Hugging Face/Ollama.
- Có giao dịch CSDL để đảm bảo cập nhật tồn kho đúng.
- Có prompt template cho báo cáo kho và gợi ý nhập hàng.
- Có test cho nhập, xuất, tồn kho âm và báo cáo AI.

1. Dữ liệu đầu vào, đầu ra và dữ liệu hệ thống

- Dữ liệu chính: hàng hóa, nhóm hàng, nhà cung cấp, phiếu nhập, phiếu xuất, tồn kho.
- Đầu vào quản lý: thông tin hàng hóa, số lượng nhập/xuất, ngày chứng từ.
- Đầu vào AI: bảng tồn kho, lịch sử xuất, tồn tối thiểu, hàng tồn lâu.
- Đầu ra quản lý: thẻ kho, báo cáo nhập xuất tồn, cảnh báo.
- Đầu ra AI: nhận xét kho, khuyến nghị nhập hàng, tóm tắt bất thường.

Ví dụ dữ liệu mẫu: `Mã HH001, Bàn phím cơ, tồn 5, tồn tối thiểu 10, xuất 25 sản phẩm trong 30 ngày`.

Prompt mẫu:

System: Bạn là trợ lý quản lý kho. Chỉ phân tích dựa trên số liệu được cung cấp. Không tự tạo số liệu mới.
User: Dữ liệu nhập xuất tồn tháng này: {{inventory_report}}. Hãy sinh báo cáo ngắn gồm tình trạng tồn kho, hàng cần nhập thêm và điểm bất thường.

Không gửi thông tin giá mua nhạy cảm nếu báo cáo AI không cần phân tích chi phí.
6. Hướng dẫn sử dụng AI trong từng giai đoạn SDLC

 Giai đoạn 1: Phân tích yêu cầu và thiết kế hệ thống (Bài KT1)

- Dùng AI phân tích quy trình nhập kho, xuất kho, kiểm kê và báo cáo tồn.
- Dùng AI thiết kế ERD và ràng buộc tránh tồn kho âm.
- Dùng AI xác định actor: thủ kho, kế toán, quản trị viên.
- Dùng AI đề xuất chức năng AI sinh báo cáo và gợi ý nhập hàng.
- Dùng AI sinh wireframe màn hình phiếu nhập/xuất và dashboard tồn kho.

 Giai đoạn 2: Xây dựng chức năng quản lý (Bài KT2)

- Dùng AI sinh model/API cho hàng hóa, nhà cung cấp, phiếu nhập, phiếu xuất.
- Dùng AI sinh logic cập nhật tồn kho bằng transaction.
- Dùng AI debug lỗi tồn kho âm hoặc tính sai tồn cuối kỳ.
- Lưu minh chứng dùng AI khi sinh truy vấn và xử lý nghiệp vụ.

 Giai đoạn 3: Tích hợp AI, tối ưu prompt và kiểm thử (Bài KT3)

- Dùng AI thiết kế prompt báo cáo không bịa số liệu.
- Dùng AI sinh code tổng hợp dữ liệu trước khi gửi model.
- Dùng AI tạo test case cho dữ liệu rỗng, tồn kho âm, xuất tăng bất thường.
- So sánh các prompt để báo cáo ngắn, đúng số liệu, dễ hiểu.

 Giai đoạn 4: Hoàn thiện, triển khai và báo cáo (Bài thi cuối kỳ)

- Dùng AI viết README, hướng dẫn nhập dữ liệu mẫu và demo kho.
- Dùng AI review tính nhất quán dữ liệu và xử lý lỗi.
- Dùng AI tạo báo cáo kỹ thuật và slide.
- Dùng AI hỗ trợ đóng gói/triển khai ứng dụng.

## 5. Mức độ khó

Trung bình: Nghiệp vụ kho yêu cầu tính nhất quán dữ liệu và báo cáo số liệu. Chức năng AI chủ yếu là sinh báo cáo và gợi ý dựa trên dữ liệu tổng hợp.

---

## 6. Phụ lục: Ghi chú triển khai thực tế của Hệ thống (Implementation Notes)

Để đáp ứng và tối ưu hóa 100% các yêu cầu trên trong thực tiễn công nghệ, nhóm phát triển đã hiện thực hóa các nội dung như sau:

1. **Tra cứu lịch sử theo Nhà cung cấp (Yêu cầu 3.1.6):**
   - Phiếu nhập kho (`import_notes`) có trường `supplier_id` và hỗ trợ lọc trực tiếp theo Nhà cung cấp trên cả API (`GET /api/v1/import-notes?supplier_id=...`) và giao diện `ImportNotes.jsx`.
   - Đối với phiếu xuất kho (`export_notes`), nghiệp vụ xuất hàng gắn liền với người nhận/khách hàng (`recipient_name`), vì kho xuất ra không liên kết trực tiếp với nhà cung cấp.
2. **Thống kê Nhập - Xuất - Tồn và Xuất báo cáo (Yêu cầu 3.1.8):**
   - Phân hệ Thống kê Nhập - Xuất - Tồn được bố trí tích hợp tại **Tab 1 của trang Trợ lý AI (`pages/AIAssistant.jsx`)**, kết hợp bảng số liệu kế toán và phân tích của AI trên cùng một màn hình điều hành.
   - Hỗ trợ xuất file Excel chuẩn định dạng cho cả Báo cáo Nhập-Xuất-Tồn (`/reports/inventory-summary-excel`) và Thẻ kho (`/reports/stock-ledger-excel/{product_id}`).
3. **Mô hình AI & Fallback (Yêu cầu 3.2 & 4):**
   - Hệ thống triển khai mô hình **Google Gemini 3.5 Flash Lite** (`gemini-3.5-flash-lite`) với cơ chế chuỗi Fallback Model (`3.1-flash-lite` $\rightarrow$ `3.6-flash`), bộ đệm AI In-Day Cache (`ai_cache.py`), kết hợp **Heuristic Fallback Engine** phản hồi $< 50$ms khi offline.
4. **Bộ kiểm thử & Dữ liệu mẫu (Yêu cầu 4):**
   - Bộ kiểm thử tự động đạt **70/70 ca test PASS 100%** (bao gồm cả kiểm thử dữ liệu rỗng cho AI, tồn âm, ACID, và phân quyền RBAC), code coverage đạt 83%.
   - Dữ liệu mẫu `seed_data.py` gồm **76 sản phẩm**, **7 danh mục**, **10 nhà cung cấp** và lịch sử giao dịch liên tục **5 tháng (150 ngày)**.
