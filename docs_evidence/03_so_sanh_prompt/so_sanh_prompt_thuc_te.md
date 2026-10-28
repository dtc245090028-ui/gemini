# BÁO CÁO THỰC NGHIỆM ĐỐI SÁNH 3 PHIÊN BẢN PROMPT (BÀI BÁO CÁO KT3)

**Đề tài 07:** Hệ thống Quản lý Kho Thông minh tích hợp AI  
**Người thực hiện kiểm định:** AI Assistant (Tra soát & Chạy thực tế tự động)  
**Thời điểm thực nghiệm:** 2026-10-27T23:10:02+07:00 đến 2026-10-27T23:13:40+07:00  
**Mô hình AI thực tế sử dụng:** `gemini-3.5-flash-lite` (Cấu hình qua file `backend/.env`)  
**Bộ dữ liệu kiểm thử:** Cố định 01 bộ số liệu tổng hợp thực tế Tháng 10/2026 từ CSDL SQLite `warehouse.db`.

---

## 1. NGUỒN GỐC & TRẠNG THÁI CỦA CÁC PHIÊN BẢN PROMPT

### 1.1. Phiên bản v3 (Production Grounded Structured JSON)
- **Phân loại nhãn:** `[TỪ GIT/FILE]`
- **Vị trí file trong repo:** [`backend/app/ai/prompts/inventory_report_prompt.txt`](file:///e:/gemini/hệ thống quản lý kho/backend/app/ai/prompts/inventory_report_prompt.txt)
- **Mã commit khởi tạo:** `cf136bf7f4e673622c6a3bef73e0454b7d2e9d3f` (Commit message: `final1.1`, tác giả: `dtc245090028-ui`, ngày: `23/09/2026 19:59:13 +0700`).
- **Lịch sử Git:** Tra soát toàn bộ lịch sử git (`git log --all -- backend/app/ai/prompts/inventory_report_prompt.txt`) xác nhận: File này được tạo mới tại commit `cf136bf` và được giữ nguyên tại baseline checkpoint `147f53b`. **Không tồn tại phiên bản cũ hơn của file này trong kho lưu trữ Git**.
- **Cơ chế nạp & ghép dữ liệu:** Nạp vào qua hàm `AIService._read_prompt_template("inventory_report_prompt.txt")` và ghép dữ liệu người dùng tại [`backend/app/services/ai_service.py` L468-L481](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/ai_service.py#L468-L481).

### 1.2. Phiên bản v1 (Naive Unstructured Prompt)
- **Phân loại nhãn:** `[DỰNG LẠI TỪ MÔ TẢ, KHÔNG PHẢI BẢN GỐC]`
- **Nguồn mô tả:** Báo cáo thiết kế KT3 tại [`docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md` L32-L39](file:///e:/gemini/hệ thống quản lý kho/docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md#L32-L39).
- **Trạng thái Git:** Đã tìm kiếm sâu trong lịch sử git bằng lệnh `git log -S "Hãy viết báo cáo nhập xuất tồn"` và xác nhận **không có file hay commit nào lưu trữ bản prompt v1 này**.
- **Nội dung dựng lại:** Lưu tại file [`docs_evidence/03_so_sanh_prompt/prompt_v1_reconstructed.txt`](file:///e:/gemini/docs_evidence/03_so_sanh_prompt/prompt_v1_reconstructed.txt).

### 1.3. Phiên bản v2 (Markdown Table Constrained Prompt)
- **Phân loại nhãn:** `[DỰNG LẠI TỪ MÔ TẢ, KHÔNG PHẢI BẢN GỐC]`
- **Nguồn mô tả:** Báo cáo thiết kế KT3 tại [`docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md` L40-L46](file:///e:/gemini/hệ thống quản lý kho/docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md#L40-L46).
- **Trạng thái Git:** Không tìm thấy trong kho lưu trữ Git.
- **Nội dung dựng lại:** Lưu tại file [`docs_evidence/03_so_sanh_prompt/prompt_v2_reconstructed.txt`](file:///e:/gemini/docs_evidence/03_so_sanh_prompt/prompt_v2_reconstructed.txt).

---

## 2. BỘ DỮ LIỆU ĐẦU VÀO CỐ ĐỊNH & XÁC THỰC BẢO MẬT (ZERO PRICE LEAK)

- **Phân loại nhãn:** `[CHẠY THỰC TẾ]`
- **File lưu trữ:** [`docs_evidence/03_so_sanh_prompt/fixed_input_metrics.json`](file:///e:/gemini/docs_evidence/03_so_sanh_prompt/fixed_input_metrics.json)
- **Phương thức trích xuất:** Đọc từ SQLite `warehouse.db` thông qua pipeline tổng hợp số liệu `AIService.get_monthly_aggregated_data(db, month=10, year=2026)` ở chế độ chỉ đọc.
- **Chi tiết bộ số liệu:**
  ```json
  {
    "period": "10/2026 (2026-10-01 đến 2026-10-31)",
    "total_products": 76,
    "active_products": 25,
    "total_imports_qty": 96,
    "total_exports_qty": 165,
    "low_stock_count": 4,
    "top_exported_products": [
      {"product_code": "SP002", "product_name": "Chuột không dây Logitech G304", "quantity": 39},
      {"product_code": "SP036", "product_name": "Dell Inspiron 15 3520 i5", "quantity": 23},
      {"product_code": "SP016", "product_name": "Cáp mạng bấm sẵn Cat6 UTP 10 mét", "quantity": 20},
      {"product_code": "SP050", "product_name": "Logitech M185", "quantity": 18},
      {"product_code": "SP023", "product_name": "iPhone 16 128GB", "quantity": 16}
    ]
  }
  ```
- **Xác thực bảo mật giá mua (`unit_price`):**
  - Trong bộ dữ liệu đầu vào: **HOÀN TOÀN KHÔNG CÓ** trường `unit_price`, `cost_price`, `price` hay bất kỳ đơn giá tiền tệ nào.
  - Cơ chế đảm bảo: Tầng SQL Aggregation Pipeline tại `app/services/ai_service.py` chỉ `SELECT func.sum(quantity)` và thông tin mô tả `Product.code`, `Product.name`, loại bỏ triệt để các cột giá của bảng `import_note_details` và `export_note_details`.

---

## 3. PHƯƠNG PHÁP ĐO LƯỜNG & ĐỊNH NGHĨA CHỈ SỐ

Thử nghiệm chạy liên tiếp 5 lần cho mỗi phiên bản (tổng cộng 15 lượt gọi trực tiếp tới Google Gemini API):
1. **Khoảng nghỉ (Throttle delay):** Giữa mỗi lần gọi nghỉ 3.0 giây để bảo vệ hạn mức Quota Free Tier và tránh lỗi HTTP 429.
2. **Độ trễ (Latency ms):** Đo bằng đồng hồ bấm giờ `time.time()` từ khi gửi request HTTP đến khi nhận trọn vẹn response text.
3. **Parse JSON thành công (JSON Parse Success):** Đạt (`True`) nếu văn bản trả về parse được bằng `json.loads()` và chứa trường bắt buộc `executive_summary`. Ngược lại là Không (`False`).
4. **Cách phát hiện & đếm ảo giác (Hallucination Detection):**
   - **Ảo giác mã hàng (SKU Hallucination):** Quét toàn bộ regex `SP\d{3}` trong output; nếu xuất hiện mã hàng không nằm trong danh sách Top 5 được cung cấp (`SP002`, `SP036`, `SP016`, `SP050`, `SP023`), tính là 1 lỗi ảo giác.
   - **Ảo giác đơn giá/tiền tệ (Price Hallucination):** Quét regex tìm các từ khóa tiền tệ `VNĐ`, `USD`, `đồng`, `triệu`, `nghìn`, `giá vốn`; nếu AI tự bịa ra giá trị tiền tệ trong khi đầu vào không có, tính lỗi.
   - **Ảo giác mặt hàng lạ (Bizarre Items):** Quét các mặt hàng phi công nghệ như áo sơ mi, bút bi, sách vở (được ghi nhận trong báo cáo thiết kế cũ).

---

## 4. KẾT QUẢ THỰC NGHIỆM ĐO ĐƯỢC (5 LẦN CHẠY MỖI PHIÊN BẢN)

- **Phân loại nhãn:** `[CHẠY THỰC TẾ]`
- **Dữ liệu thô từng lượt:** Lưu đầy đủ tại thư mục [`docs_evidence/03_so_sanh_prompt/raw_outputs/`](file:///e:/gemini/docs_evidence/03_so_sanh_prompt/raw_outputs/) gồm 15 file: `v1_run1.txt` đến `v3_run5.txt`.

### 4.1. Bảng chi tiết kết quả chạy thực tế

| Phiên bản | Lượt chạy | Độ trễ (ms) | Parse JSON | Số lỗi ảo giác phát hiện | Độ dài output (ký tự) | Tóm tắt hình thức phản hồi |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **v1 (Naive)** | Run 1 | 6,668.8 | ❌ Không | 0 | 1,816 | Văn xuôi dài dòng, chia mục I, II, III, mở đầu chào hỏi |
| **v1 (Naive)** | Run 2 | 12,702.0 | ❌ Không | 0 | 1,926 | Văn bản hành chính có tiêu ngữ, lời mở đầu giải thích |
| **v1 (Naive)** | Run 3 | 5,882.2 | ❌ Không | 0 | 1,485 | Văn bản tự do dạng bài luận phân tích |
| **v1 (Naive)** | Run 4 | 13,012.6 | ❌ Không | 0 | 2,066 | Báo cáo chi tiết, tự thêm phần nhận định xu hướng thị trường |
| **v1 (Naive)** | Run 5 | 22,958.7 | ❌ Không | 0* | 2,292 | Văn bản hành chính đầy đủ Quốc hiệu - Tiêu ngữ, bảng ký tên |
| **v2 (Markdown)**| Run 1 | 4,037.3 | ❌ Không | 0 | 1,920 | Bảng Markdown + 3 khuyến nghị gạch đầu dòng, lời chào thủ kho |
| **v2 (Markdown)**| Run 2 | 2,872.9 | ❌ Không | 0 | 1,785 | Bảng Markdown tổng hợp + phân tích ngắn |
| **v2 (Markdown)**| Run 3 | 3,874.1 | ❌ Không | 0 | 2,191 | Kẻ bảng Markdown chi tiết 5 cột + khuyến nghị |
| **v2 (Markdown)**| Run 4 | 4,736.1 | ❌ Không | 0* | 1,889 | Kẻ bảng Markdown + 3 gạch đầu dòng |
| **v2 (Markdown)**| Run 5 | 10,180.9 | ❌ Không | 0 | 1,952 | Bảng Markdown + 3 khuyến nghị |
| **v3 (JSON Prod)**| Run 1 | 26,049.6 |  **Có (100%)** | 0 | 764 | JSON sạch, chuẩn Schema `{executive_summary, recommendations}` |
| **v3 (JSON Prod)**| Run 2 | 11,473.2 |  **Có (100%)** | 0 | 1,018 | JSON sạch, tính nhẩm đúng 51 mặt hàng không giao dịch |
| **v3 (JSON Prod)**| Run 3 | 11,652.4 |  **Có (100%)** | 0 | 887 | JSON sạch, đúng Schema |
| **v3 (JSON Prod)**| Run 4 | 18,437.3 |  **Có (100%)** | 0 | 974 | JSON sạch, không kèm markdown thừa ngoài khối json |
| **v3 (JSON Prod)**| Run 5 | 18,111.0 |  **Có (100%)** | 0 | 911 | JSON sạch, khớp 100% Pydantic Model |

*\*Ghi chú:* Bộ lọc regex ban đầu bắt từ "sách" trong cụm "danh sách mặt hàng" và "chính sách nhập hàng" của v1 Run 5 và v2 Run 4. Sau khi đối chiếu thủ công văn bản thô, xác nhận không phải ảo giác "sách vở", do đó số lỗi ảo giác thực tế là 0.

### 4.2. Bảng tổng hợp các chỉ số trung bình

| Chỉ số đánh giá | Phiên bản v1 (Naive) | Phiên bản v2 (Markdown Table) | Phiên bản v3 (Production JSON) |
| :--- | :---: | :---: | :---: |
| **Tỷ lệ Parse JSON thành công** | **0.0%** (0/5) | **0.0%** (0/5) | **100.0%** (5/5) |
| **Độ trễ trung bình (Latency)** | 12,244.9 ms (~12.2s) | 5,140.3 ms (~5.1s) | 17,144.7 ms (~17.1s) |
| **Tỷ lệ ảo giác số liệu / SKU** | 0.0% (Không bịa SKU/giá) | 0.0% (Không bịa SKU/giá) | **0.0%** (Tuyệt đối bám sát số liệu) |
| **Hiện tượng mở đầu thừa (Conversational overhead)** | Rất cao ("Dưới đây là mẫu...", tiêu ngữ, chữ ký) | Cao ("Chào ban giám đốc, tôi là thủ kho...") | **0.0%** (Chỉ trả về JSON thuần túy) |
| **Độ dài trung bình phản hồi** | 1,917 ký tự (dư thừa) | 1,947 ký tự (dư thừa) | **911 ký tự** (cô đọng, đúng trọng tâm) |
| **Bảo mật giá nhập (Zero Price Leak)** | **Đạt** (SQL lọc từ đầu) | **Đạt** (SQL lọc từ đầu) | **Đạt** (SQL lọc từ đầu) |

---

## 5. SO SÁNH VỚI CON SỐ TRONG TÀI LIỆU CŨ (`docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md`)

- **Phân loại nhãn:** `[SUY LUẬN]` (So sánh giữa báo cáo thiết kế cũ và thực nghiệm đo đạc thực tế)

| Tiêu chí | Số liệu trong tài liệu cũ KT3 (`gemini-1.5-flash`, 20 tests) | Kết quả đo thực tế (`gemini-3.5-flash-lite`, 5 runs/phiên bản) | Phân tích & Giải thích sự khác biệt |
| :--- | :---: | :---: | :--- |
| **Tỷ lệ Parse JSON Frontend** | - v1: 40.0%<br>- v2: 75.0%<br>- v3: 100.0% | - v1: **0.0%**<br>- v2: **0.0%**<br>- v3: **100.0%** | Tài liệu cũ KT3 dùng hàm regex bóc tách văn bản lỏng lẻo trên React Frontend nên v1 và v2 vẫn có thể "cào" được một số dòng dữ liệu. Trong khi đó, hệ thống production hiện tại dùng **Pydantic Model** và `json.loads()` nghiêm ngặt, do đó văn xuôi của v1 và bảng Markdown của v2 thất bại 100%, chỉ có v3 đạt 100%. |
| **Tỷ lệ ảo giác (Hallucination)** | - v1: 25.0%<br>- v2: 8.5%<br>- v3: 0.0% | - v1: **0.0%**<br>- v2: **0.0%**<br>- v3: **0.0%** | Mô hình `gemini-3.5-flash-lite` thế hệ mới có năng lực bám sát ngữ cảnh (Grounding) tốt hơn đáng kể so với `gemini-1.5-flash` đời đầu, nên cả khi dùng prompt tự do v1/v2, model không tự ý bịa thêm mặt hàng phi lý (như áo sơ mi, bút bi), mặc dù phong cách trả lời vẫn bị lan man. |
| **Độ trễ trung bình (Latency)** | - v1: 3.8s<br>- v2: 2.9s<br>- v3: 1.2s | - v1: **12.2s**<br>- v2: **5.1s**<br>- v3: **17.1s** | Khác biệt về hạ tầng: Thử nghiệm của tài liệu cũ sử dụng `gemini-1.5-flash` với server phản hồi nhanh. Trong khi đó, mô hình `gemini-3.5-flash-lite` qua cổng API đám mây có thời gian suy luận (Thinking / Reasoning token) và độ trễ mạng quốc tế dao động từ 5s đến 26s tùy theo tải của cụm máy chủ Google. |
| **Bảo mật giá mua (Zero Price Leak)** | v1: Thất bại<br>v2: Thất bại<br>v3: 100% | **Cả v1, v2, v3 đều đạt 100%** | Trong tài liệu cũ, tác giả giả định v1 gửi cả bảng DB thô. Trong thực nghiệm này, cả 3 prompt đều nhận dữ liệu từ cùng hàm `AIService.get_monthly_aggregated_data`, nơi tầng tiền xử lý SQL đã chủ động lọc sạch `unit_price`, chứng minh tính ưu việt của nguyên lý "Bảo mật ngay từ tầng kiến trúc dữ liệu (Security by Design)". |

---

## 6. KẾT LUẬN & KIẾN NGHỊ CHO TÀI LIỆU BÁO CÁO ĐỒ ÁN

1. **Hiệu lực của Prompt v3:** Thực nghiệm thực tế chứng minh quyết định thiết kế Prompt v3 (Production Structured JSON) tại commit `cf136bf` là hoàn toàn đúng đắn. Đây là phiên bản duy nhất đảm bảo tính tương thích phần mềm 100% với giao diện React và backend FastAPI.
2. **Vai trò của Fallback Heuristic:** Do độ trễ API đám mây dao động lớn (11s - 26s trên `gemini-3.5-flash-lite`), cơ chế Cache nhận xét (`AICacheManager`) và Heuristic Fallback (`FallbackService` phản hồi < 50ms) là bắt buộc phải có để đảm bảo trải nghiệm người dùng mượt mà và chống rủi ro rớt mạng khi demo bảo vệ đồ án.
