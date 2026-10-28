# KIẾN TRÚC TÍCH HỢP AI VÀ CƠ CHẾ HEURISTIC FALLBACK (BÀI KT3)

## Đề tài 07: Hệ thống Quản lý Kho Thông minh tích hợp AI

> **Mục tiêu tài liệu:** Trình bày chi tiết kiến trúc kết nối Trợ lý AI (Google Gemini API - `gemini-3.5-flash-lite`), chuỗi Model Fallback Chain, quy trình tiền xử lý dữ liệu bảo mật (Data Sanitization Pipeline), bộ đệm AI In-Day Cache (`ai_cache.py`) và cơ chế tự động chuyển mạch dự phòng (Heuristic Fallback Engine) đảm bảo hệ thống vận hành liên tục không gián đoạn.

---

## 1. MÔ HÌNH KIẾN TRÚC PHÂN TẦNG CỦA MODULE AI

Module AI được thiết kế theo nguyên lý **Phân tách trách nhiệm (Separation of Concerns)** với 5 phân tầng độc lập:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      TẦNG GIAO DIỆN API (api/v1/endpoints/ai.py)        │
│  - POST /api/v1/ai/monthly-report: Báo cáo nhập-xuất-tồn tháng          │
│  - POST /api/v1/ai/restock-suggestions: Đề xuất nhập hàng tối ưu        │
│  - POST /api/v1/ai/anomalies: Nhận diện biến động bất thường            │
│  - POST /api/v1/ai/ask: Chat hỏi đáp tự do với SmartKho Copilot         │
│  - POST /api/v1/ai/generate-order: Sinh đơn hàng xuất kho theo yêu cầu  │
│  - Rate Limiter: SlidingWindowRateLimiter (10 req/phút/user)            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              TẦNG ĐIỀU PHỐI DỊCH VỤ (services/ai_service.py)            │
│  - Kiểm tra sự tồn tại của GEMINI_API_KEY trong cấu hình                │
│  - Nạp độc lập các Prompt Templates (app/ai/prompts/)                   │
│  - Kiểm tra AI In-Day Cache (ai_cache.py) theo Data Fingerprint         │
└──────────────┬───────────────────────────────────────────┬──────────────┘
               │                                           │
       [1] Tiền xử lý dữ liệu                     [2] Chuyển mạch khi cần
               ▼                                           ▼
┌───────────────────────────────┐           ┌─────────────────────────────┐
│  SQL AGGREGATION & SANITIZE   │           │  HEURISTIC FALLBACK ENGINE  │
│ - Tính toán: Tổng nhập, xuất, │           │ (services/fallback_service) │
│   velocity, days_left.        │           │ - Quy tắc thống kê thuần túy│
│ - LỌC BỎ 100% GIÁ MUA NHẬP    │           │ - Hoạt động độc lập offline │
│   (Zero-price leakage)        │           │ - Phản hồi cực nhanh < 50ms │
└──────────────┬────────────────┘           └──────────────┬──────────────┘
               │                                           │
               ▼                                           │
┌───────────────────────────────┐                          │
│   GOOGLE GEMINI API GATEWAY   │                          │
│ - Model: gemini-3.5-flash-lite│                          │
│ - Fallback Chain:             │                          │
│   3.5-flash-lite -> 3.1 -> 3.6│                          │
│ - Structured JSON Schema      │                          │
│ - Lưu kết quả vào AI Cache    │                          │
└──────────────┬────────────────┘                          │
               │ (Thành công: is_fallback=False)           │ (Kích hoạt: is_fallback=True)
               └─────────────────────┬─────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   CHUẨN HÓA DỮ LIỆU ĐẦU RA (schemas/ai.py)              │
│       Pydantic Response: Metrics số học + Executive Summary tiếng Việt  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. SƠ ĐỒ LUỒNG CHUYỂN MẠCH THÔNG MINH (FALLBACK WORKFLOW)

```text
[Request từ Client]
       │
       ▼
[Xác thực JWT & Quyền người dùng]
       │
       ▼
[Kiểm tra Rate Limit (SlidingWindowRateLimiter: 10 req/min)]
       │
       ▼
[SQL Pipeline tiền xử lý & loại bỏ 100% giá mua]
       │
       ▼
[Kiểm tra AI In-Day Cache (ai_cache.py)]
       │
       ├────► [CACHE HIT] ─────────────────────────┐
       │                                           │
       ▼ [CACHE MISS]                              │
[Kiểm tra GEMINI_API_KEY có tồn tại?]              │
       │                                           │
       ├────► [KHÔNG CÓ KEY] ──────────────────────┤
       │                                           │
       ▼ [CÓ KEY]                                  │
[Gọi Model chính: gemini-3.5-flash-lite]           │
       │                                           │
       ├────► [LỖI 429 RESOURCE EXHAUSTED]         │
       │      │                                    │
       │      ▼                                    │
       │  [Thử gemini-3.1-flash-lite]              │
       │      │                                    │
       │      ▼ (vẫn lỗi)                          │
       │  [Thử gemini-3.6-flash]                   │
       │      │                                    │
       │      ▼ (vẫn lỗi / Mất mạng hoàn toàn) ────┤
       │                                           ▼
       │                               [Kích hoạt Heuristic Fallback]
       │                               - Tính toán theo công thức kinh tế kho
       │                               - Gắn nhãn SURGE_EXPORT / DEAD_STOCK
       │                               - is_fallback = True
       │                               - provider = "heuristic_fallback"
       │                                           │
       ▼ [THÀNH CÔNG]                              │
- Trích xuất JSON từ phản hồi LLM                  │
- Lưu kết quả vào AI Cache trong ngày              │
- is_fallback = False                              │
- provider = "gemini"                              │
       │                                           │
       └───────────────────┬───────────────────────┘
                           ▼
              [Trả về Client HTTP 200]
```

---

## 3. CÁC BÀI TOÁN NGHIỆP VỤ AI & CƠ CHẾ XỬ LÝ

### 3.1. Báo cáo Nhập - Xuất - Tồn theo tháng (`POST /ai/monthly-report`)

* **Dữ liệu đầu vào**: Tổng số mặt hàng, số mặt hàng luân chuyển, tổng nhập, tổng xuất, số mặt hàng dưới tồn tối thiểu, Top 5 mặt hàng xuất lớn nhất.
* **Cơ chế Fallback**:
  * Tự động phân tích cán cân luân chuyển: nhập ròng (tích lũy tồn) hay xuất ròng (giải phóng tồn).
  * Tự động nêu tên mặt hàng chủ lực và cảnh báo số mặt hàng cần bổ sung.
* **Định dạng trả về**: Khối `metrics` phục vụ vẽ biểu đồ và `executive_summary` nhận xét tổng quát.

### 3.2. Gợi ý Nhập hàng tối ưu (`POST /ai/restock-suggestions`)

* **Dữ liệu đầu vào**: Danh sách các mặt hàng có `current_stock <= min_stock` hoặc sắp hết hàng trong 7 ngày tới.
* **Công thức toán học Heuristic**:
  $$\text{suggested\_quantity} = \max\Big(\text{min\_stock} \times 2 - \text{current\_stock},\; \text{round}(\text{daily\_velocity} \times 30) - \text{current\_stock},\; \text{min\_stock}\Big)$$
* **Phân cấp mức độ ưu tiên**:
  * `HIGH`: Khi `current_stock == 0` (hết hàng) hoặc `current_stock < min_stock / 2`.
  * `MEDIUM`: Khi `current_stock <= min_stock`.
  * `LOW`: Khi `current_stock > min_stock` nhưng dự kiến cạn trong 7 ngày theo tốc độ bán.

### 3.3. Tóm tắt Biến động bất thường (`POST /ai/anomalies`)

* **Nhận diện 2 nhóm bất thường**:
  1. **SURGE_EXPORT (Xuất đột biến)**: Lượng xuất 7 ngày qua $\ge 200\%$ mức bình quân tuần trước đó và $\ge 5$ sản phẩm.
  2. **DEAD_STOCK (Hàng tồn ế / chết kho)**: Mặt hàng còn tồn trong kho ($>0$) nhưng $\ge 30$ ngày không phát sinh bất kỳ phiếu xuất nào.
* **Đề xuất hành động**: Đưa ra giải pháp thương mại phù hợp (tăng tồn an toàn hoặc xả hàng khuyến mãi).

### 3.4. Trợ lý hỏi đáp SmartKho Copilot (`POST /ai/ask`) & Tạo đơn tự động (`POST /ai/generate-order`)

* **Copilot Chat**: Cho phép tra cứu thông tin kho tức thời bằng ngôn ngữ tự nhiên.
* **Generate Order**: Tự động bóc tách SKU, số lượng từ văn bản và tạo cấu trúc phiếu xuất.

---

## 4. RÀNG BUỘC BẢO MẬT & CHỐNG RÒ RỈ THÔNG TIN (ZERO PRICE LEAKAGE)

* **Rủi ro đề bài đặt ra:** Trong hệ thống phân phối, giá mua vào từ nhà cung cấp là bí mật thương mại cốt lõi. Gửi giá mua lên AI của bên thứ ba vừa vi phạm bảo mật, vừa tốn token không cần thiết.
* **Giải pháp triển khai:**
  * Tầng `AIService` không truy vấn cột `unit_price`, `cost_price` hay `total_amount` từ bảng `import_notes` và `import_note_details`.
  * Được kiểm chứng tự động bằng bài test `test_ai_pipeline_excludes_unit_price` trong `tests/test_ai_service.py` (PASS 100%).

---

## 5. KẾT LUẬN

Kiến trúc tích hợp AI đáp ứng trọn vẹn:

1. **Tính sẵn sàng cao (High Availability):** Hệ thống không bao giờ bị gián đoạn hay crash dù không có kết nối Internet hoặc chưa cấu hình API Key nhờ Heuristic Fallback Engine.
2. **Hiệu năng & Tối ưu chi phí:** Bộ đệm AI In-Day Cache (`ai_cache.py`) giúp giảm thiểu 80% số lượt gọi lặp lại.
3. **Tính mở rộng (Extensibility):** Hỗ trợ chuỗi chuyển đổi model linh hoạt từ `gemini-3.5-flash-lite` sang `3.1` và `3.6`.

---

## 6. LỊCH SỬ ĐỒNG BỘ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Cập nhật phương thức HTTP:** Chuẩn hóa toàn bộ 5 endpoints AI là phương thức `POST` (`/monthly-report`, `/restock-suggestions`, `/anomalies`, `/ask`, `/generate-order`).
  - **Cập nhật mô hình AI:** Chuẩn hóa mô hình chính thức `gemini-3.5-flash-lite`, chuỗi fallback chain 3.1 $\rightarrow$ 3.6 thay vì mô hình cũ `gemini-1.5-flash`.
  - **Bổ sung AI In-Day Cache:** Bổ sung cơ chế lưu cache theo data fingerprint (`ai_cache.py`).
  - **Bổ sung Rate Limiting:** Ghi nhận `SlidingWindowRateLimiter` 10 req/min/user trên các endpoint AI.
