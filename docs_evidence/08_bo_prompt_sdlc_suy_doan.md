# BỘ PROMPT THỰC THI & PHẢN BIỆN QUA 4 GIAI ĐOẠN SDLC
## (DỰNG LẠI TỪ KẾ HOẠCH `docs/plans/` VÀ HỒ SƠ BÀN GIAO `docs/SDLC/`)

**Dự án:** Hệ thống Quản lý Kho Thông minh tích hợp AI (WMS AI) — Đề tài 07  
**Phân loại nhãn gốc:** `[SUY ĐOÁN TỪ PLANS & SDLC]`  
**Căn cứ phục dựng:** 
- 11 tài liệu đặc tả nhiệm vụ tự thân (Self-contained Execution Specs) tại [`docs/plans/Buoc-01-...md`](file:///e:/gemini/hệ thống quản lý kho/docs/plans/) đến [`Buoc-11-...md`](file:///e:/gemini/hệ thống quản lý kho/docs/plans/).
- Hồ sơ sản phẩm bàn giao 4 mốc đánh giá tại [`docs/SDLC/`](file:///e:/gemini/hệ thống quản lý kho/docs/SDLC/) (`KT1/`, `KT2/`, `KT3/`, `final/`).
- Bằng chứng đồng hành Pair-programming tại [`docs/SDLC/KT2/03_AI_Assisted_Development_Evidence.md`](file:///e:/gemini/hệ thống quản lý kho/docs/SDLC/KT2/03_AI_Assisted_Development_Evidence.md).
- Báo cáo Prompt Engineering tại [`docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md`](file:///e:/gemini/hệ thống quản lý kho/docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md).
- Đặc tả vai trò hệ thống tại [`Prompt.md`](file:///e:/gemini/hệ thống quản lý kho/Prompt.md) và kịch bản Agent tại [`docs/prompts/MASTER.md`](file:///e:/gemini/docs/prompts/MASTER.md).
- **Ghi chú cập nhật đồng bộ:** Tái dựng từ mã nguồn tại thời điểm đồng bộ toàn diện theo Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md).

---

## MỤC LỤC TỔNG QUAN

- [0. Khung Prompt Hệ thống Chuẩn (System Context Prompt)](#0-khung-prompt-hệ-thống-chuẩn-system-context-prompt)
- [1. Giai đoạn 1: Phân tích Yêu cầu & Thiết kế Kiến trúc (Mốc KT1)](#1-giai-đoạn-1-phân-tích-yêu-cầu--thiết-kế-kiến-trúc-mốc-kt1)
- [2. Giai đoạn 2: Xây dựng Chức năng Quản lý Kho (Mốc KT2)](#2-giai-đoạn-2-xây-dựng-chức-năng-quản-lý-kho-mốc-kt2)
- [3. Giai đoạn 3: Tích hợp AI, Tối ưu Prompt & Kiểm thử (Mốc KT3)](#3-giai-đoạn-3-tích-hợp-ai-tối-ưu-prompt--kiểm-thử-mốc-kt3)
- [4. Giai đoạn 4: Hoàn thiện, Triển khai, Đo tải & PR #1 (Final)](#4-giai-đoạn-4-hoàn-thiện-triển-khai-đo-tải--pr-1-final)
- [5. Các Prompt Bổ sung theo Tiến trình Nâng cấp & Đồng bộ Thực tế](#5-các-prompt-bổ-sung-theo-tiến-trình-nâng-cấp--đồng-bộ-thực-tế)
  - [5.1. Nhóm Prompt Điều chỉnh Phạm vi](#51-nhóm-prompt-bổ-sung-sau--điều-chỉnh-phạm-vi)
  - [5.2. Nhóm Prompt Nâng cấp & Mở rộng](#52-nhóm-prompt-bổ-sung-sau--nâng-cấpmở-rộng)
  - [5.3. Nhóm Prompt Đồng bộ Số liệu Tài liệu](#53-nhóm-prompt-bổ-sung-sau--đồng-bộ-tài-liệu)
- [6. Bảng Tổng kết Ánh xạ Giữa các Bước Plans và Toàn bộ Prompt](#6-bảng-tổng-kết-ánh-xạ-giữa-các-bước-plans-và-bộ-prompt)

---

## 0. KHUNG PROMPT HỆ THỐNG CHUẨN (SYSTEM CONTEXT PROMPT)
Toàn bộ quá trình phát triển được định vị dưới vai trò kỹ sư cố vấn kỹ thuật dẫn dắt sinh viên làm đồ án:

```text
[SYSTEM PROMPT CHUNG CHO CẢ DỰ ÁN]
Bạn là một Kỹ sư phần mềm Full-stack Senior, đóng vai trò dẫn dắt một sinh viên CNTT năm cuối 
(đang học song song môn Triển khai phần mềm & Ứng dụng AI) xây dựng đồ án "Hệ thống quản lý kho tích hợp AI" (Đề tài 07).

Ràng buộc làm việc bắt buộc:
1. Sinh viên phải tự bảo vệ đồ án trước Hội đồng chấm thi: Mọi đoạn code sinh ra phải sạch, cấu trúc phân tầng rõ ràng, có chú thích tiếng Việt, không dùng thư viện dạng "hộp đen".
2. Tính toàn vẹn số liệu là ưu tiên số 1: Luôn dùng Database Transaction, chặn 100% nguy cơ tồn kho âm, có Thẻ kho (Stock Ledger) truy vết từng giây.
3. Không tự ý thêm tính năng ngoài phạm vi (Feature creep). Bám sát 4 mốc SDLC: KT1 -> KT2 -> KT3 -> Cuối kỳ.
4. Mọi tính năng AI phải tuân thủ: Loại bỏ thông tin giá mua nhạy cảm khỏi ngữ cảnh và luôn có cơ chế Fallback Heuristic chạy offline khi mất mạng/hết quota.
```

---

## 1. GIAI ĐOẠN 1: PHÂN TÍCH YÊU CẦU & THIẾT KẾ KIẾN TRÚC (MỐC KT1)

### 1.1. Phân tích 8 Luồng Nghiệp vụ & Ma trận Phân quyền 3 Actor
* **Căn cứ phục dựng:** `docs/plans/Buoc-01-Dac-ta-yeu-cau-va-Phan-tich-nghiep-vu.md` và `docs/SDLC/KT1/01_SRS_and_UseCases.md`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Đề tài của mình là Đề tài 07: "Hệ thống quản lý kho có tích hợp AI" cho doanh nghiệp vừa và nhỏ.
Yêu cầu bạn phân tích bài toán và viết tài liệu SRS giai đoạn KT1 gồm:
1. Phân tích chi tiết 3 Actor: Quản trị viên (Admin), Thủ kho (Warehouse Keeper), Kế toán (Accountant). Phân định rõ ai được làm gì, ai bị cấm thao tác kho vật lý.
2. Vẽ ma trận phân quyền RBAC và sơ đồ Use Case bằng cú pháp Mermaid.
3. Đặc tả chi tiết 8 luồng nghiệp vụ kho cốt lõi (Nhập, Xuất, Tồn, Cảnh báo, Thẻ kho, Báo cáo và 3 bài toán AI).
Đầu ra lưu tại: docs/SDLC/KT1/01_SRS_and_UseCases.md
```

```text
[PROMPT PHẢN BIỆN / TINH CHỈNH CỦA CON NGƯỜI] [SUY ĐOÁN TỪ PLANS & SDLC]
Kế toán có được bấm duyệt phiếu xuất kho không? Trong nghiệp vụ doanh nghiệp thực tế, kế toán chỉ theo dõi chứng từ đối chiếu công nợ chứ không được can thiệp vào số lượng hàng vật lý trong kho. Hãy chỉnh lại ma trận phân quyền: Kế toán chỉ có quyền Read-only đối với phiếu xuất/nhập và thẻ kho, tuyệt đối không được có nút tạo hoặc duyệt phiếu.
```

---

### 1.2. Thiết kế Mô hình CSDL Chuẩn 3NF (9 Bảng) & Sơ đồ ERD
* **Căn cứ phục dựng:** `docs/plans/Buoc-02-Thiet-ke-CSDL-va-So-do-ERD.md` và `docs/SDLC/KT1/02_Database_Design_ERD.md`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Hãy thiết kế cơ sở dữ liệu quan hệ chuẩn 3NF cho hệ thống quản lý kho Đề tài 07 sử dụng SQLite và SQLAlchemy.
Yêu cầu:
1. Thiết kế đầy đủ 9 bảng cốt lõi: users, categories, products, suppliers, import_notes, import_note_details, export_notes, export_note_details, stock_ledger.
2. Viết sơ đồ thực thể mối quan hệ Mermaid ERD.
3. Tách riêng bảng chi tiết phiếu nhập/xuất để lưu đơn giá thực tế tại thời điểm giao dịch, không lưu giá nhập tĩnh trên bảng sản phẩm.
4. Thiết kế bảng Thẻ kho (stock_ledger) làm sổ cái kiểm toán bất biến (Audit Trail) lưu trữ: product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date.
Đầu ra lưu tại: docs/SDLC/KT1/02_Database_Design_ERD.md
```

```text
[PROMPT PHẢN BIỆN / TINH CHỈNH CỦA CON NGƯỜI] [SUY ĐOÁN TỪ PLANS & SDLC]
Đề bài yêu cầu rất gắt gao về việc chống tồn kho âm. Nếu chỉ kiểm tra bằng code Python `if stock < qty` thì khi chạy đồng thời hoặc có lỗi phát sinh vẫn có thể lọt giao dịch âm. Hãy bổ sung ngay ràng buộc toàn vẹn ở tầng CSDL (Check Constraint) `CHECK (current_stock >= 0)` trực tiếp trên bảng `products` của SQLAlchemy model để CSDL làm người gác cổng cuối cùng.
```

---

### 1.3. Thiết kế Kiến trúc AI Copilot & Cơ chế Bảo mật Dữ liệu (Zero Price Leak)
* **Căn cứ phục dựng:** `docs/plans/Buoc-08-Module-AI-Tro-ly-...md` và `docs/SDLC/KT1/03_AI_Architecture_and_Prompts.md`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Theo mục 5 của de_tai_07.md, hệ thống phải tích hợp AI giải quyết 3 bài toán: (1) Báo cáo nhập xuất tồn tháng, (2) Gợi ý nhập hàng, (3) Phát hiện biến động bất thường.
Hãy thiết kế kiến trúc tích hợp AI 4 tầng:
- Tầng CSDL kho
- Tầng tiền xử lý dữ liệu (Pre-processing Pipeline)
- Tầng mô hình AI (Google Gemini API + Heuristic Fallback Engine)
- Tầng hiển thị Frontend.
Đặc biệt, làm rõ giải pháp bảo vệ dữ liệu kinh doanh nhạy cảm và nguyên tắc chống ảo giác (Anti-hallucination).
Đầu ra lưu tại: docs/SDLC/KT1/03_AI_Architecture_and_Prompts.md
```

```text
[PROMPT PHẢN BIỆN / TINH CHỈNH CỦA CON NGƯỜI] [SUY ĐOÁN TỪ PLANS & SDLC]
Trong đề bài có lưu ý: "Không gửi thông tin giá mua nhạy cảm nếu báo cáo AI không cần phân tích chi phí". Giá nhập hàng là bí mật sống còn của doanh nghiệp. Bạn hãy thiết kế pipeline SQL Aggregation sao cho chỉ trích xuất số lượng hàng hóa và vận tốc xuất; lọc bỏ 100% các cột `unit_price`, `cost_price` trước khi ráp vào Prompt gửi cho Google Gemini.
```

---

## 2. GIAI ĐOẠN 2: XÂY DỰNG CHỨC NĂNG QUẢN LÝ KHO (MỐC KT2)

### 2.1. Phát hiện Lỗ hổng Hủy phiếu nhập gây Tồn kho âm & Thiết kế Lối thoát Kiểm kê
* **Căn cứ phục dựng:** `docs/plans/Buoc-07-...md` và `docs/SDLC/KT2/03_AI_Assisted_Development_Evidence.md` (Tình huống 1).

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Tôi chuẩn bị viết API hủy phiếu nhập kho `POST /api/v1/import-notes/{id}/cancel`. Logic dự kiến: Tìm phiếu nhập, chuyển trạng thái sang CANCELLED, lấy số lượng trong chi tiết và trừ ngược lại `current_stock` của sản phẩm. Bạn hãy review logic này xem có rủi ro gì không?
```

```text
[AI PHẢN HỒI PHÁT HIỆN LỖ HỔNG (PAIR-PROGRAMMING)] [SUY ĐOÁN TỪ PLANS & SDLC]
CẢNH BÁO LỖ HỔNG NGHIÊM TRỌNG: Logic này sẽ gây TỒN KHO ÂM!
Giả sử: Ngày 01/10 nhập 100 chiếc Ram Kingston (tồn kho tăng lên 100). Đến ngày 05/10 đã xuất bán 80 chiếc cho khách (tồn kho hiện tại chỉ còn 20).
Nếu hôm nay thủ kho bấm "Hủy phiếu nhập" ngày 01/10, hệ thống trừ 100 chiếc:
Tồn kho mới = 20 - 100 = -80 (Âm kho nghiêm trọng, vi phạm ràng buộc CHECK CSDL và thực tế vật lý)!
```

```text
[PROMPT PHẢN BIỆN / TINH CHỈNH CỦA CON NGƯỜI] [SUY ĐOÁN TỪ PLANS & SDLC]
Cảm ơn phát hiện rất hay. Để giải quyết triệt để, chúng ta sẽ áp dụng giải pháp kép:
1. Chốt chặn Guard-check: Khi hủy phiếu nhập, phải kiểm tra `current_stock >= detail.quantity`. Nếu vi phạm thì từ chối ngay với mã lỗi 400 và thông báo rõ mặt hàng nào không đủ tồn để hoàn trừ.
2. Lối thoát nghiệp vụ kiểm kê chuẩn ERP: Trong thực tế, nếu hàng bị hư hỏng hoặc sai lệch sau nhiều ngày, thủ kho không được hủy hồi tố chứng từ cũ mà phải lập phiếu kiểm kê điều chỉnh. Hãy viết thêm endpoint `POST /api/v1/stock-ledger/adjust` để cân bằng tồn kho thực tế và ghi nhận chênh lệch vào Thẻ kho.
```

---

### 2.2. Xử lý Xung đột Race Condition khi Sinh mã Chứng từ Tự động
* **Căn cứ phục dựng:** `docs/plans/Buoc-07-...md` và `docs/SDLC/KT2/03_AI_Assisted_Development_Evidence.md` (Tình huống 2).

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Khi 2 thủ kho cùng lúc tạo phiếu nhập hoặc phiếu xuất ở cùng 1 giây, cả 2 sẽ cùng đọc ra số thứ tự tiếp theo và sinh trùng mã chứng từ dạng `PN-YYYYMMDD-0001`. Vì cột `code` có ràng buộc UNIQUE nên request thứ hai sẽ bị văng lỗi 500 Internal Server Error làm người dùng khó chịu.
Làm thế nào để xử lý triệt để đụng độ này trong SQLite mà không dùng khóa bàn gây treo ứng dụng?
```

```text
[PROMPT PHẢN BIỆN / TINH CHỈNH CỦA CON NGƯỜI] [SUY ĐOÁN TỪ PLANS & SDLC]
SQLite không hỗ trợ khóa hàng chi tiết như PostgreSQL. Hãy cài đặt mô hình Optimistic Concurrency kết hợp Retry Pattern:
1. Cho phép CSDL làm trọng tài cuối cùng kích hoạt ngoại lệ `IntegrityError`.
2. Tầng `InventoryService` bọc trong vòng lặp thử lại tối đa 3 lần. Nếu bắt được lỗi trùng mã, tự động đọc lại sequence mới nhất và sinh lại mã tiếp theo.
3. Toàn bộ quá trình phải diễn ra trong suốt, người dùng không nhận thấy lỗi.
```

---

### 2.3. Cài đặt Transaction ACID Bảo đảm Toàn vẹn Nhập/Xuất kho
* **Căn cứ phục dựng:** `docs/plans/Buoc-07-...md` và `docs/SDLC/KT2/02_Transaction_Design_and_Negative_Stock_Prevention.md`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Hãy viết hàm `create_export_note` và `create_import_note` trong `inventory_service.py` bảo đảm tính nguyên tử (Atomicity) theo chuẩn ACID.
Quy trình lập phiếu xuất:
1. Kiểm tra từng mặt hàng xem tồn hiện tại có đủ không (`current_stock >= requested_qty`).
2. Nếu thiếu bất kỳ mặt hàng nào: Dừng ngay, ném ngoại lệ rõ ràng, không lưu phiếu.
3. Nếu đủ: Tạo bản ghi `ExportNote`, tạo danh sách `ExportNoteDetail`, trừ `current_stock`, và ghi dòng biến động vào `StockLedger` (với số lượng âm và số dư sau giao dịch).
Tất cả phải nằm trong 1 Transaction duy nhất của SQLAlchemy session.
```

---

## 3. GIAI ĐOẠN 3: TÍCH HỢP AI, TỐI ƯU PROMPT & KIỂM THỬ (MỐC KT3)

### 3.1. Tối ưu Prompt v3 Chống Ảo giác & Ép chuẩn Structured JSON
* **Căn cứ phục dựng:** `docs/plans/Buoc-08-...md` và `docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Khi mình thử prompt v1 ("Hãy viết báo cáo kho tháng này...") và prompt v2 ("Kẻ bảng markdown tổng hợp..."), AI thường trả về lời chào hỏi lan man ("Chào ban giám đốc..."), tự bịa thêm các mặt hàng không có thật và Frontend React không thể nào bóc tách số liệu để vẽ biểu đồ được.
Bạn hãy thiết kế phiên bản Prompt v3 cho 3 bài toán: Báo cáo tháng, Gợi ý nhập hàng và Phát hiện biến động bất thường sao cho:
1. Ép chặt System Prompt kỷ luật tiếp đất (Grounding): Chỉ phân tích số liệu được cung cấp, cấm tự tạo số liệu mới.
2. Ép đầu ra trả về 100% JSON thuần khớp với Pydantic Schema.
3. Tách riêng các file template độc lập trong thư mục `backend/app/ai/prompts/`.
```

```text
[PROMPT PHẢN BIỆN / TINH CHỈNH CỦA CON NGƯỜI] [SUY ĐOÁN TỪ PLANS & SDLC]
Đôi khi Gemini vẫn bọc kết quả JSON trong khối markdown ```json ... ``` hoặc thêm lời dẫn ở đầu câu làm hàm `json.loads()` bị sập. Hãy xử lý 2 lớp:
1. Trong prompt template ghi rõ: "Trả về kết quả ĐÚNG ĐỊNH DẠNG JSON sau (không thêm markdown ngoài khối json)".
2. Trong hàm `_call_gemini_with_models` cấu hình tham số `response_mime_type="application/json"` của Google Gemini SDK để API trả về chuỗi JSON chuẩn mực ngay từ tầng mạng.
```

---

### 3.2. Thiết kế Động cơ Heuristic Fallback Engine Hoạt động Offline
* **Căn cứ phục dựng:** `docs/plans/Buoc-08-...md` và `docs/SDLC/KT3/03_AI_Integration_Architecture.md`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Khi đi bảo vệ đồ án, phòng thi có thể bị mất mạng Internet hoặc tài khoản Google Gemini Free Tier bị vượt hạn mức 15 request/phút (lỗi HTTP 429 Resource Exhausted).
Hãy xây dựng class `FallbackService` trong `backend/app/services/fallback_service.py` để:
1. Hoạt động độc lập 100% không cần mạng và không cần API Key.
2. Tự động tính toán các công thức toán học thống kê:
   - Gợi ý nhập: `suggested_qty = max((min_stock * 2) - current_stock, min_stock)`. Phân loại ưu tiên HIGH khi tồn = 0 hoặc dưới 50% min_stock.
   - Bất thường: Nhận diện `SURGE_EXPORT` khi xuất tuần này tăng >200% và `DEAD_STOCK` khi tồn kho >0 nhưng không phát sinh xuất >30 ngày.
3. Trả về đúng cấu trúc Schema JSON như khi gọi Gemini thật để giao diện React hiển thị mượt mà không hề bị lỗi.
```

---

### 3.3. Xây dựng Bộ Kiểm thử Tự động Pytest
* **Căn cứ phục dựng:** `docs/plans/Buoc-10-Viet-Bo-Test-Tu-dong-Pytest-va-Seed-Data.md` và `docs/SDLC/KT3/02_Test_Plan_and_Results.md`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Hãy viết bộ kiểm thử tự động toàn diện bằng `pytest` trong `backend/tests/` bao phủ toàn bộ hệ thống để nộp bài KT3:
1. `test_stock_transactions.py`: Kiểm tra giao dịch ACID nhập/xuất, chặn tồn âm, tự động ghi Thẻ kho, tính toán báo cáo NXT và test guard-check hủy phiếu.
2. `test_ai_service.py`: Kiểm tra bảo mật không rò rỉ giá mua (`unit_price`), kiểm tra Heuristic Fallback khi offline, mock Gemini API trả về JSON thành công, phân quyền RBAC và kiểm tra cache trong ngày.
3. `seed_data.py`: Tạo script nạp dữ liệu mẫu thể hiện rõ các kịch bản demo: bán chạy sắp hết hàng, xuất đột biến, tồn chết.
Mục tiêu: Đạt 100% Test Passed và sẵn sàng cho giảng viên chạy lệnh kiểm thử.
```

---

## 4. GIAI ĐOẠN 4: HOÀN THIỆN, TRIỂN KHAI, ĐO TẢI & PR #1 (FINAL)

### 4.1. Khắc phục Thất thoát Tồn kho (Lost Update) Dưới Tải Đồng Thời (Item A)
* **Căn cứ phục dựng:** `docs/prompts/MASTER.md` (Mục A), Commit `dc89507`, và `docs/SDLC/final/01_Final_Technical_Report.md`.

```text
[USER PROMPT - AGENT NHIỆM VỤ TỰ HÀNH ITEM A] [SUY ĐOÁN TỪ PLANS & SDLC]
Báo cáo đo tải đồng thời Locust ghi nhận hiện tượng nghiêm trọng: Tồn kho thực tế của sản phẩm cao hơn giá trị kỳ vọng (lệch tới 1.944 đơn vị), thẻ kho stock_ledger bị lặp balance_after và vi phạm tính lũy kế liên tục.
Nguyên nhân: Trong `inventory_service.py`, lệnh đọc `product.current_stock` và lệnh ghi `product.current_stock -= qty` diễn ra tách rời trong bộ nhớ Python, tạo ra khe hở Lost Update giữa các luồng.
Nhiệm vụ của bạn:
1. Chuyển đổi toàn bộ thao tác cập nhật tồn kho sang biểu thức số học nguyên tử trực tiếp ở tầng SQL:
   `UPDATE products SET current_stock = current_stock - :qty WHERE id = :id AND current_stock >= :qty RETURNING current_stock`
2. Lấy giá trị tồn sau giao dịch (`balance_after`) trực tiếp từ mệnh đề `RETURNING` của SQL để ghi vào Thẻ kho, loại bỏ hoàn toàn việc tính toán ở RAM.
3. Đo lại với 30 luồng song song để chứng minh thất thoát tồn kho giảm về 0 đơn vị.
```

---

### 4.2. Triệt tiêu Lỗi HTTP 409 khi Bị Khóa CSDL SQLite (Item B & C)
* **Căn cứ phục dựng:** `docs/prompts/MASTER.md` (Mục B & C), Commit `70aaf91` và `e3be4a5`.

```text
[USER PROMPT - AGENT NHIỆM VỤ TỰ HÀNH ITEM B & C] [SUY ĐOÁN TỪ PLANS & SDLC]
Dưới tải cao 50 luồng, hệ thống phát sinh 418 lỗi HTTP 409 (chiếm 15%) do đụng độ ghi file SQLite và lỗi `database is locked`.
Nhiệm vụ của bạn:
1. Tối ưu cấu hình SQLite PRAGMA trong `database.py`: Bật `PRAGMA synchronous = NORMAL`, tăng `cache_size = -64000`, thiết lập `temp_store = MEMORY`.
2. Nâng cấp decorator retry trong `inventory_service.py`: Tăng `max_retries` từ 3 lên 7 lần, áp dụng thuật toán ngẫu nhiên hóa thời gian chờ (Exponential Backoff with Jitter):
   `delay = 0.025 * (2 ** attempt) + random.uniform(0.015, 0.045)`
3. Chạy kiểm thử đo tải 50 luồng để xác minh tỷ lệ lỗi 409 giảm xuống 0.0%.
```

---

### 4.3. Nâng cấp Trải nghiệm Người dùng: Thay thế Confirm bằng `ConfirmModal` & `Toast`
* **Căn cứ phục dựng:** Commit `067dc7b` và PR #1 `9d7218e`.

```text
[USER PROMPT - SINH VIÊN GIAO VIỆC] [SUY ĐOÁN TỪ PLANS & SDLC]
Hiện tại giao diện Frontend đang dùng lệnh mặc định của trình duyệt `window.confirm()` và `alert()`. Trông rất thô sơ, làm gián đoạn luồng người dùng và không cho phép nhập lý do khi hủy phiếu xuất/nhập.
Bạn hãy tái cấu trúc toàn diện:
1. Xây dựng `ToastContext` và component thông báo nổi (Toast Notification) tự động biến mất sau 3 giây với các trạng thái Success / Error / Warning.
2. Xây dựng `ConfirmModal` chuyên nghiệp theo phong cách UI Wood/Warm của dự án, có ô nhập văn bản bắt buộc: "Nhập lý do hủy phiếu (tối thiểu 5 ký tự)" trước khi kích hoạt API hủy.
3. Thay thế toàn bộ các lệnh `window.confirm` trên các trang `ImportNotes.jsx` và `ExportNotes.jsx`.
```

---

## 5. CÁC PROMPT BỔ SUNG THEO TIẾN TRÌNH NÂNG CẤP & ĐỒNG BỘ THỰC TẾ

> **Ghi chú phương pháp luận:** Các khối prompt dưới đây được **Tái dựng từ mã nguồn tại thời điểm đồng bộ (2026-10-28)**, nhằm phản ánh chính xác các quyết định kiến trúc, điều chỉnh phạm vi và tính năng mở rộng phát sinh sau đợt rà soát mã nguồn thực tế tại [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md).

### 5.1. Nhóm Prompt `[BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]`

#### Prompt 5.1.1: Tinh chỉnh Phạm vi Quản trị Hệ thống & Đổi mật khẩu
- **Nhãn:** `[BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/core/config.py` L23-24](file:///e:/gemini/hệ thống quản lý kho/backend/app/core/config.py#L23-L24); [`backend/app/api/v1/endpoints/auth.py` L15-124](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/auth.py#L15-L124).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-01-...md`, `Buoc-05-...md`, `docs/SDLC/KT1/01_SRS_and_UseCases.md`, `Prompt.md`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #1, #2, #3.

```text
[USER PROMPT - ĐIỀU CHỈNH PHẠM VI QUẢN TRỊ] [BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]
Sau khi rà soát yêu cầu bảo mật, chúng ta không nên làm giao diện UI để cấu hình API Key AI hoặc đổi mật khẩu trong phạm vi MVP vì dễ gây rủi ro lộ lọt và phân tán nguồn lực.
Yêu cầu điều chỉnh:
1. Toàn bộ cấu hình hệ thống (Database URL, Secret Key, Gemini API Key, Model Name) sẽ đọc tĩnh từ biến môi trường (.env / Pydantic Settings). Không tạo bảng CSDL cấu hình và không làm trang Settings.
2. Về quản trị người dùng: Admin chỉ cần một endpoint API `POST /api/v1/auth/users` để tạo tài khoản mới. Tạm hoãn tính năng đổi mật khẩu cá nhân (/change-password) và UI quản lý danh sách user sang Phase 2.
3. Kế toán là vai trò Read-Only, xem được toàn bộ danh mục, phiếu nhập/xuất, thẻ kho và báo cáo, nhưng bị chặn 100% các nút thêm/sửa/xóa và không được can thiệp tồn kho vật lý.
Hãy cập nhật lại tài liệu SRS KT1 và các bước kế hoạch cho khớp đúng hiện trạng này.
```

#### Prompt 5.1.2: Hợp nhất Giao diện Báo cáo Nhập-Xuất-Tồn vào Phân hệ Trợ lý AI
- **Nhãn:** `[BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]`
- **Căn cứ mã nguồn thực tế:** [`frontend/src/components/Layout.jsx` L60-68](file:///e:/gemini/hệ thống quản lý kho/frontend/src/components/Layout.jsx#L60-L68); [`frontend/src/pages/AIAssistant.jsx` L174-245](file:///e:/gemini/hệ thống quản lý kho/frontend/src/pages/AIAssistant.jsx#L174-L245).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-01-...md`, `Buoc-09-...md`, `docs/SDLC/KT1/04_Wireframes.md`, `Prompt.md`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #4, #11, Mục nghi ngờ 2.

```text
[USER PROMPT - GỘP GIAO DIỆN BÁO CÁO KHO] [BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]
Thay vì tách một trang riêng `Reports.jsx` và một nút menu `Báo cáo kho` trên Sidebar, hãy hợp nhất Báo cáo Nhập - Xuất - Tồn vào Tab 1 của trang Trợ lý AI (`AIAssistant.jsx`).
Lý do:
1. Giúp lãnh đạo và kế toán vừa xem bảng số liệu luân chuyển kỳ kế toán, vừa đọc được nhận xét phân tích thông minh của Gemini trên cùng một màn hình điều hành.
2. Rút gọn Sidebar xuống 7 tabs trực quan, tránh phân mảnh điều hướng.
3. Bổ sung nút bấm xuất file Excel (.xlsx) chuẩn cho Báo cáo NXT ngay tại đầu bảng để đối soát nhanh.
Hãy cập nhật Wireframes và đặc tả giao diện theo thiết kế hợp nhất này.
```

#### Prompt 5.1.3: Thay thế Scheduler Quét Tồn Định kỳ Bằng `@computed_field` Thời gian thực
- **Nhãn:** `[BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/schemas/product.py` L44](file:///e:/gemini/hệ thống quản lý kho/backend/app/schemas/product.py#L44); [`backend/requirements.txt` L1-13](file:///e:/gemini/hệ thống quản lý kho/backend/requirements.txt#L1-L13).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-08-...md`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #6.

```text
[USER PROMPT - BỎ SCHEDULER NỀN] [BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]
Kế hoạch ban đầu có ý định dùng APScheduler hoặc Background Task chạy định kỳ quét hàng dưới mức tồn tối thiểu. Tuy nhiên, việc chạy cron job nền gây phức tạp hạ tầng và khó kiểm soát trạng thái trên server SQLite nhúng.
Hãy tối ưu lại:
- Bỏ hoàn toàn APScheduler.
- Sử dụng `@computed_field` trong Pydantic schema của sản phẩm: `is_low_stock = current_stock <= min_stock`.
- Bất cứ khi nào API `GET /products` hay Dashboard được gọi, hệ thống tự động tính toán tức thời theo thời gian thực (Zero Lag, Zero CPU overhead).
Cập nhật lại kế hoạch Bước 08 và loại bỏ từ khóa scheduler trong tiêu đề.
```

---

### 5.2. Nhóm Prompt `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`

#### Prompt 5.2.1: Cài đặt Rate Limiting Chống Tấn công Brute-force & Spam AI
- **Nhãn:** `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/api/deps.py` L18-89](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/deps.py#L18-L89).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-04-...md`, `Buoc-05-...md`, `docs/SDLC/KT2/01_API_Specifications.md`, `docs/architecture.md`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #16.

```text
[USER PROMPT - BỔ SUNG RATE LIMITING] [BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]
Hệ thống cần bổ sung cơ chế kiểm soát tần suất truy cập (Rate Limiting) để bảo vệ 2 điểm nhạy cảm:
1. Endpoint đăng nhập `/api/v1/auth/login`: Chặn tấn công dò quét mật khẩu (Brute-force) với ngưỡng 10 requests / phút / IP.
2. Các endpoint Trợ lý AI `/api/v1/ai/*`: Chặn spam làm cạn kiệt token hạn mức Google Gemini với ngưỡng 10 requests / phút / User ID.
Hãy xây dựng class `SlidingWindowRateLimiter` thuần Python trong `deps.py` (không phụ thuộc Redis) và tích hợp vào các router tương ứng.
```

#### Prompt 5.2.2: Thiết kế Cỗ máy Trạng thái Xuất kho 3 Bước & Quyền Xóa Phiếu Chưa Giao
- **Nhãn:** `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/models/export_note.py` L19](file:///e:/gemini/hệ thống quản lý kho/backend/app/models/export_note.py#L19); [`backend/app/services/inventory_service.py` L258-277](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py#L258-L277); [`backend/app/api/v1/endpoints/export_notes.py` L135-168](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/export_notes.py#L135-L168).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-01-...md`, `Buoc-07-...md`, `docs/SDLC/KT1/01_SRS...`, `KT2/02_Transaction...`, `final/01_Final_Report...`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #10, #26, Mục nghi ngờ 1.

```text
[USER PROMPT - CỖ MÁY XUẤT KHO 3 BƯỚC] [BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]
Để xóa bỏ hiện tượng "giam giữ hàng ảo" trong kho khi phiếu xuất vừa lập nhưng xe chưa tới nhận, hãy thiết kế cỗ máy trạng thái 3 bước cho `ExportNote`:
1. `CONFIRMED` (Xác nhận đơn): Phiếu vừa tạo, xác nhận đủ tồn nhưng CHƯA trừ tồn kho thực tế.
   - Đặc biệt: Cho phép thủ kho Xóa hoàn toàn phiếu (`DELETE /api/v1/export-notes/{id}`) để dọn rác nếu nhập nhầm, vì kho chưa bị trừ.
2. `SHIPPING` (Bắt đầu giao): Khi hàng bốc lên xe rời cửa kho, thủ kho bấm "Giao hàng". Lúc này hệ thống mới thực thi câu lệnh SQL nguyên tử `RETURNING current_stock` để trừ tồn và ghi Thẻ kho. Nếu giao thất bại, cho phép hủy phiếu và hoàn trả kho 100%.
3. `COMPLETED` (Hoàn thành): Khách đã ký biên bản nhận hàng. Khóa phiếu vĩnh viễn.
Hãy cập nhật nghiệp vụ này vào toàn bộ hồ sơ kỹ thuật.
```

#### Prompt 5.2.3: Bổ sung Cơ chế Khóa Chống Trùng lặp (Idempotency Key)
- **Nhãn:** `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/models/import_note.py` L20](file:///e:/gemini/hệ thống quản lý kho/backend/app/models/import_note.py#L20); [`backend/app/models/export_note.py` L20](file:///e:/gemini/hệ thống quản lý kho/backend/app/models/export_note.py#L20); [`backend/app/main.py` L31-37](file:///e:/gemini/hệ thống quản lý kho/backend/app/main.py#L31-L37).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-02-...md`, `Buoc-07-...md`, `docs/SDLC/KT1/02_ERD...`, `KT2/02_Transaction...`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #15.

```text
[USER PROMPT - BỔ SUNG IDEMPOTENCY KEY] [BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]
Khi đường truyền mạng chập chờn, người dùng thường có xu hướng bấm nút "Tạo phiếu" nhiều lần liên tục hoặc client tự động retry. Điều này dẫn đến nguy cơ nhân đôi số lượng nhập/xuất kho.
Hãy bổ sung giải pháp Idempotency Key:
1. Thêm cột `idempotency_key VARCHAR(100)` có đánh Unique Index trên cả 2 bảng `import_notes` và `export_notes`.
2. Tự động kiểm tra trong `InventoryService`: Nếu key đã tồn tại, trả về ngay phiếu đã tạo trước đó mà không thực hiện trừ/cộng kho lần 2.
3. Thêm migration tự động tạo index trong hàm `lifespan` tại `main.py`.
```

#### Prompt 5.2.4: Bổ sung Upload Ảnh Sản phẩm & Tự động Tạo Phiếu Nhập Ban đầu
- **Nhãn:** `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/models/product.py` L20](file:///e:/gemini/hệ thống quản lý kho/backend/app/models/product.py#L20); [`backend/app/api/v1/endpoints/products.py` L108-160, L231-275](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/products.py#L108-L160).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-02-...md`, `Buoc-06-...md`, `docs/SDLC/KT1/02_ERD...`, `KT2/01_API_Specifications.md`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #14, #21.

```text
[USER PROMPT - UPLOAD ẢNH & NHẬP ĐẦU KỲ] [BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]
Để tăng trải nghiệm trực quan cho thủ kho:
1. Thêm trường `image_url` vào bảng `products` và viết endpoint `POST /api/v1/products/{id}/image` hỗ trợ upload ảnh (.jpg, .png, .webp), lưu trữ tại thư mục `uploads/` và mount static tại `/static`.
2. Khi thủ kho thêm sản phẩm mới mà có khai báo số lượng tồn kho ban đầu (`initial_quantity > 0`), hệ thống tự động sinh một Phiếu nhập kho đầu kỳ tương ứng để đảm bảo nguyên tắc kế toán: Tồn kho không tự nhiên sinh ra mà phải có chứng từ đối ứng!
```

#### Prompt 5.2.5: Bổ sung Tính năng Xuất Báo cáo và Thẻ kho ra file Excel (.xlsx)
- **Nhãn:** `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/api/v1/endpoints/reports.py` L125-170](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/reports.py#L125-L170); [`backend/app/api/v1/endpoints/stock_ledger.py` L85-130](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/stock_ledger.py#L85-L130).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-07-...md`, `Buoc-09-...md`, `docs/SDLC/KT2/01_API_Specifications.md`, `final/02_User_Guide...`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #17.

```text
[USER PROMPT - XUẤT EXCEL THẺ KHO & BÁO CÁO] [BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]
Theo chuẩn mực lưu trữ kế toán, người dùng cần xuất dữ liệu ra file bảng tính để lưu trữ hoặc đối soát:
1. Viết endpoint `GET /api/v1/reports/stock-ledger-excel/{product_id}` xuất toàn bộ dòng thời gian biến động thẻ kho của sản phẩm ra file `.xlsx` chuẩn (dùng thư viện `openpyxl`).
2. Viết endpoint `GET /api/v1/reports/inventory-summary-excel` xuất bảng tổng hợp Nhập - Xuất - Tồn theo tháng/năm ra file `.xlsx`.
3. Tích hợp 2 nút bấm xuất file trực tiếp trên giao diện `StockLedger.jsx` và `AIAssistant.jsx`.
```

#### Prompt 5.2.6: Mở rộng Trợ lý SmartKho Copilot (`/ai/ask`) & Bộ đệm AI In-Day Cache
- **Nhãn:** `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/api/v1/endpoints/ai.py` L167-290](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/ai.py#L167-L290); [`backend/app/services/ai_cache.py` L1-150](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/ai_cache.py#L1-L150).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-08-...md`, `docs/SDLC/KT1/03_AI...`, `KT3/03_AI_Integration...`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #12, #13, #18.

```text
[USER PROMPT - MỞ RỘNG NĂNG LỰC AI] [BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]
Hãy nâng cấp phân hệ Trợ lý AI thành SmartKho Copilot toàn diện:
1. Thêm endpoint `POST /api/v1/ai/ask` cho phép người dùng trò chuyện, hỏi đáp tự do bằng ngôn ngữ tự nhiên về tình hình tồn kho.
2. Thêm endpoint `POST /api/v1/ai/generate-order` hỗ trợ bóc tách yêu cầu xuất kho từ tin nhắn văn bản và tự động điền form đơn hàng.
3. Xây dựng module `ai_cache.py`: Lưu trữ kết quả phân tích AI trong ngày theo Data Fingerprint (chữ ký số lượng dữ liệu). Nếu dữ liệu kho không đổi, trả kết quả tức thời từ cache (< 5ms), tiết kiệm tối đa hạn ngạch API.
```

#### Prompt 5.2.7: Bổ sung Theme Dark/Light (`tokens.css`) và Hệ thống Dialog An toàn
- **Nhãn:** `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]`
- **Căn cứ mã nguồn thực tế:** [`frontend/src/tokens.css` L1-180](file:///e:/gemini/hệ thống quản lý kho/frontend/src/tokens.css#L1-L180); [`frontend/src/context/ConfirmContext.jsx` L1-120](file:///e:/gemini/hệ thống quản lý kho/frontend/src/context/ConfirmContext.jsx#L1-L120); [`frontend/src/context/ToastContext.jsx` L1-90](file:///e:/gemini/hệ thống quản lý kho/frontend/src/context/ToastContext.jsx#L1-L90).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-09-...md`, `docs/SDLC/KT1/04_Wireframes.md`, `final/01_Final_Report...`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #19, #20.

```text
[USER PROMPT - DARK MODE & DIALOG AN TOÀN] [BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]
Nâng cấp giao diện người dùng đạt chuẩn phần mềm doanh nghiệp:
1. Thiết kế bộ Design Tokens tại `tokens.css` hỗ trợ chuyển đổi mượt mà giữa chế độ Sáng và Tối (Dark / Light Theme), lưu trạng thái vào `localStorage`.
2. Tích hợp `ToastContext` hiển thị thông báo góc màn hình (success, error, warning) tự tắt sau 3 giây.
3. Tích hợp `ConfirmContext`: Bắt buộc người dùng nhập lý do hủy/xóa phiếu tối thiểu 5 ký tự để tránh click nhầm làm ảnh hưởng chứng từ kho.
```

---

### 5.3. Nhóm Prompt `[BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]`

#### Prompt 5.3.1: Đồng bộ Mô hình AI Chính thức `gemini-3.5-flash-lite` và Chuỗi Fallback Chain
- **Nhãn:** `[BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]`
- **Căn cứ mã nguồn thực tế:** [`backend/app/core/config.py` L24](file:///e:/gemini/hệ thống quản lý kho/backend/app/core/config.py#L24); [`backend/app/services/ai_service.py` L352-359](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/ai_service.py#L352-L359).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-08-...md`, `docs/SDLC/KT1/03_AI...`, `KT3/01_Prompts...`, `KT3/03_AI_Arch...`, `final/...`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #22.

```text
[USER PROMPT - ĐỒNG BỘ MODEL AI GEMINI 3.5] [BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]
Mã nguồn thực tế trong `config.py` đang cấu hình mô hình AI chính thức là `gemini-3.5-flash-lite`, kết hợp chuỗi fallback:
`gemini-3.5-flash-lite` -> `gemini-3.1-flash-lite` -> `gemini-3.6-flash`.
Tuy nhiên một số tài liệu cũ vẫn ghi `gemini-1.5-flash`.
Hãy rà soát và đồng bộ toàn bộ tài liệu các giai đoạn sang tên model chính thức `gemini-3.5-flash-lite`.
```

#### Prompt 5.3.2: Chuẩn hóa Quy mô Toàn hệ thống thành 44 Endpoints
- **Nhãn:** `[BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]`
- **Căn cứ mã nguồn thực tế:** Runtime OpenAPI Schema từ [`backend/app/main.py`](file:///e:/gemini/hệ thống quản lý kho/backend/app/main.py).
- **Hồ sơ tài liệu đã sửa:** Toàn bộ các file tài liệu KT2, Final, Prompt.md, codebase-map.md, TIEN-DO.md.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #23.

```text
[USER PROMPT - CHUẨN HÓA 44 ENDPOINTS] [BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]
Theo kiểm tra tự động qua OpenAPI Schema của FastAPI, toàn hệ thống có chính xác 44 endpoints (42 API endpoints v1 + 2 endpoints root/health). Các tài liệu cũ ghi rải rác 30 hoặc 42 endpoints.
Hãy cập nhật đồng bộ con số 44 endpoints vào toàn bộ tài liệu API Spec KT2, Final Technical Report, Slide bảo vệ đồ án và MASTER-ROADMAP.
```

#### Prompt 5.3.3: Đồng bộ Quy mô Dữ liệu Mẫu `seed_data.py` (76 Sản phẩm / 5 Tháng / 150 Ngày)
- **Nhãn:** `[BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]`
- **Căn cứ mã nguồn thực tế:** [`backend/seed_data.py` L52-222](file:///e:/gemini/hệ thống quản lý kho/backend/seed_data.py#L52-L222).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-10-...md`, `docs/SDLC/KT3/02_Test_Plan...`, `final/...`, `Prompt.md`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #25, #31.

```text
[USER PROMPT - ĐỒNG BỘ SEED DATA ENTERPRISE] [BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]
Script `backend/seed_data.py` thực tế nạp tới 76 mặt hàng, 7 nhóm hàng, 10 nhà cung cấp và lịch sử giao dịch liên tục 5 tháng (150 ngày). Trong khi các file kế hoạch cũ chỉ ghi 20-22 mặt hàng / 60 ngày.
Hãy đồng bộ số liệu quy mô lớn này vào tất cả các tài liệu kiểm thử, kịch bản demo và báo cáo kỹ thuật.
```

#### Prompt 5.3.4: Đồng bộ Bộ Kiểm thử Tự động 70 Ca Test PASS 100% (Coverage 83%)
- **Nhãn:** `[BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]`
- **Căn cứ mã nguồn thực tế:** [`backend/tests/` (70 ca test thực tế)](file:///e:/gemini/hệ thống quản lý kho/backend/tests/).
- **Hồ sơ tài liệu đã sửa:** `docs/plans/Buoc-10-...md`, `docs/SDLC/KT3/02_Test_Plan...`, `final/...`, `Prompt.md`.
- **Mã sai lệch tương ứng trong Báo cáo 09:** Sai lệch #24, #29, #30.

```text
[USER PROMPT - ĐỒNG BỘ TEST SUITE 70 TESTS] [BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]
Bộ test thực tế đã đạt 70 tests pass 100% (gồm 12 auth, 5 master data, 18 stock transactions, 31 ai service, và 4 empty data tests) với độ bao phủ code 83%.
Hãy chuẩn hóa bảng tiến trình kiểm thử: KT3 đạt 30 tests -> Final đạt 60 tests -> PR #1 mở rộng 66 tests -> Bổ sung test kho rỗng đạt 70 tests. Cập nhật vào toàn bộ hồ sơ nghiệm thu.
```

---

## 6. BẢNG TỔNG KẾT ÁNH XẠ GIỮA CÁC BƯỚC PLANS VÀ BỘ PROMPT

| Giai đoạn SDLC | Bước thực thi (`docs/plans/`) | Hồ sơ bàn giao (`docs/SDLC/`) | Mã Prompt tương ứng | Phân loại nhãn | Vấn đề kỹ thuật cốt lõi giải quyết |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **KT1** | Bước 01, 02 | `KT1/01_SRS...`, `02_ERD...` | `P-KT1-01`, `P-KT1-02` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | 3 Actor, RBAC matrix, 9 bảng 3NF, ràng buộc CSDL chống tồn âm. |
| **KT1** | Bước 03, 04 | `KT1/03_AI...`, `04_Wireframes...`| `P-KT1-03` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | Lọc sạch giá mua trước khi gửi LLM, kiến trúc Heuristic Fallback. |
| **KT2** | Bước 05, 06 | `KT2/01_API...` | `P-KT2-01` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | CRUD danh mục/sản phẩm/NCC, JWT Auth, Seed idempotent. |
| **KT2** | Bước 07 | `KT2/02_Transaction...`, `03_Evidence...`| `P-KT2-02`, `P-KT2-03` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | Guard-check chống âm kho khi hủy phiếu, Retry sinh mã phiếu, Thẻ kho. |
| **KT3** | Bước 08 | `KT3/01_Prompts...`, `03_AI_Arch...` | `P-KT3-01`, `P-KT3-02` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | Prompt v3 ép JSON Schema Pydantic, Heuristic Fallback engine < 50ms. |
| **KT3** | Bước 10 | `KT3/02_Test_Results...` | `P-KT3-03` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | Bộ Pytest tự động 30 tests, Seed data kịch bản nghiệp vụ. |
| **Final**| Bước 09, 11 | `final/01_Final_Report...`, `02_User_Guide...`| `P-KT4-01`, `P-KT4-03` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | React 18 SPA 7 phân hệ, ConfirmModal có lý do, Toast thông báo, Docker. |
| **Final**| PR #1 | `docs/prompts/MASTER.md` | `P-KT4-02` | `[SUY ĐOÁN TỪ PLANS & SDLC]` | Biểu thức SQL nguyên tử xóa Lost Update, Jitter Backoff xóa lỗi 409. |
| **Audit**| Bước 01, 05, 08, 09 | Toàn bộ các mốc SDLC | `P-MOD-01` đến `P-MOD-03` | `[BỔ SUNG SAU – ĐIỀU CHỈNH PHẠM VI]` | Bỏ UI cấu hình, bỏ đổi mật khẩu, gộp Báo cáo NXT vào AIAssistant, bỏ scheduler. |
| **Audit**| Bước 02, 04, 06-09 | Toàn bộ các mốc SDLC | `P-EXT-01` đến `P-EXT-07` | `[BỔ SUNG SAU – NÂNG CẤP/MỞ RỘNG]` | Rate Limiter, Xuất kho 3 bước, Idempotency Key, Upload ảnh, Xuất Excel, Copilot Chat, Dark mode. |
| **Audit**| Bước 04, 08, 10, 11 | Toàn bộ các mốc SDLC | `P-SYNC-01` đến `P-SYNC-04` | `[BỔ SUNG SAU – ĐỒNG BỘ TÀI LIỆU]` | Chuẩn hóa Gemini 3.5, 44 endpoints, 70 tests pass 100%, Seed data 76 SP / 5 tháng. |
