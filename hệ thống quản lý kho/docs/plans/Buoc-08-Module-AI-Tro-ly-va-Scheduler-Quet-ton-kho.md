# BƯỚC 08: MODULE AI TRỢ LÝ, HEURISTIC FALLBACK & AI CACHE (AI INTEGRATION)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-08-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - `docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md`: SẢN PHẨM BÀN GIAO THẬT (Deliverable) đánh giá Prompt cho bài KT3.
> - `docs/SDLC/KT3/03_AI_Integration_Architecture.md`: SẢN PHẨM BÀN GIAO THẬT (Deliverable) kiến trúc Tích hợp AI và Fallback cho bài KT3.
> - Mã nguồn được sinh trực tiếp vào thư mục `backend/app/` (ai, services, endpoints).

---

## 1. Mục tiêu bước 8

- Tích hợp Trợ lý AI (Google Gemini API - Model chính: `gemini-3.5-flash-lite`) để giải quyết 3 bài toán thông minh cốt lõi của Đề tài 07:
  1. AI sinh báo cáo Nhập - Xuất - Tồn theo tháng kèm nhận xét xu hướng.
  2. AI gợi ý nhập hàng tối ưu (dựa trên tồn kho, tồn tối thiểu và vận tốc xuất 30 ngày).
  3. AI tóm tắt biến động bất thường (xuất tăng đột biến $>200\%$ và hàng tồn kho lâu $>30$ ngày).
- Xây dựng Data Pre-processing Pipeline: SQL tính toán trước các chỉ số thống kê, **loại bỏ 100% thông tin giá mua nhạy cảm** (`unit_price`) khỏi prompt.
- Xây dựng **Heuristic Fallback Engine**: Tự động sinh báo cáo theo công thức thống kê nếu không có mạng hoặc chưa có API Key, phản hồi $< 50$ms.
- Xây dựng **AI In-Day Cache** (`ai_cache.py`): Lưu bộ nhớ đệm kết quả AI trong ngày theo chữ ký dữ liệu (Data Fingerprint) để tối ưu chi phí token và tốc độ tải trang.
- Mở rộng phân hệ Trợ lý AI nâng cao: Endpoint hỏi đáp tự do (`/ai/ask` - SmartKho Copilot) và sinh đơn hàng xuất kho theo kịch bản (`/ai/generate-order`).

---

## 2. Nội dung công việc chi tiết

### 2.1. Pipeline Tổng hợp Dữ liệu cho AI

- Hàm `get_aggregated_inventory_data(db, month, year)` trong `ai_service.py`:
  - Tính vận tốc xuất bình quân ngày trong 30 ngày gần nhất (`daily_velocity`).
  - Lọc danh sách hàng `current_stock <= min_stock`.
  - Lọc hàng không phát sinh phiếu xuất trong 30 ngày gần nhất (`DEAD_STOCK`).
  - Lọc hàng có lượng xuất tuần này tăng vọt so với bình quân (`SURGE_EXPORT` > 200%).
  - **Bảo mật tuyệt đối**: Loại bỏ hoàn toàn trường giá nhập `unit_price`.

### 2.2. Prompt Engineering & Gemini API Client

- Tách biệt Prompt Template độc lập tại `app/ai/prompts/`:
  - `inventory_report_prompt.txt`: Template sinh báo cáo Nhập-Xuất-Tồn.
  - `reorder_suggestion_prompt.txt`: Template sinh gợi ý bổ sung hàng.
  - `anomaly_detection_prompt.txt`: Template nhận diện biến động bất thường.
  - `generate_order_prompt.txt`: Template sinh đơn hàng xuất kho theo kịch bản.
- Mô hình AI: Sử dụng `gemini-3.5-flash-lite` làm model chính thức.
- Chuỗi Model Fallback Chain khi gặp lỗi 429 Resource Exhausted:
  $$\text{gemini-3.5-flash-lite} \longrightarrow \text{gemini-3.1-flash-lite} \longrightarrow \text{gemini-3.6-flash}$$
- Ép kiểu đầu ra: Cấu hình `response_mime_type="application/json"` khớp chuẩn Pydantic schema.

### 2.3. Heuristic Fallback Engine (`fallback_service.py`)

- Khi không có API Key, mất mạng, hoặc API bên ngoài gặp sự cố:
  - Tính toán số lượng nhập đề xuất theo công thức chuỗi cung ứng:
    $$\text{suggested\_qty} = \max(0, \text{target\_stock} - \text{current\_stock})$$
    Trong đó: $\text{target\_stock} = \max(\text{min\_stock} \times 2, \lceil \text{daily\_velocity} \times \text{lead\_time} \rceil)$ kết hợp ngưỡng an toàn $\text{safety\_stock} = \lceil 1.65 \times \sigma \times \sqrt{\text{lead\_time}} \rceil$.
  - Tự động gắn cờ `is_fallback: true` và hiển thị nhãn dự phòng minh bạch trên UI mà không gây sập ứng dụng.

---

## 3. Cấu trúc file/thư mục cần sinh

Khi thực hiện bước này, các file và thư mục sau phải được tạo ra:

```text
backend/
├── app/
│   ├── ai/
│   │   ├── __init__.py
│   │   └── prompts/
│   │       ├── inventory_report_prompt.txt   # Template prompt báo cáo tháng
│   │       ├── reorder_suggestion_prompt.txt # Template prompt gợi ý nhập hàng
│   │       ├── anomaly_detection_prompt.txt  # Template prompt tóm tắt bất thường
│   │       └── generate_order_prompt.txt     # Template prompt sinh đơn hàng mẫu
│   ├── schemas/
│   │   └── ai.py                             # Schemas dữ liệu yêu cầu & phản hồi AI
│   ├── services/
│   │   ├── ai_service.py                     # Client gọi Gemini API & Pipeline tổng hợp
│   │   ├── fallback_service.py               # Thuật toán Heuristic dự phòng khi offline
│   │   └── ai_cache.py                       # Cơ chế lưu cache kết quả AI trong ngày
│   └── api/
│       └── v1/
│           └── endpoints/
│               └── ai.py                     # Routers /monthly-report, /restock-suggestions, /anomalies, /ask, /generate-order
docs/
└── SDLC/
    └── KT3/
        ├── 01_Prompt_Engineering_and_Evaluation.md  # Báo cáo đánh giá prompt KT3
        └── 03_AI_Integration_Architecture.md        # Kiến trúc Tích hợp AI và Fallback KT3
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Không gửi giá mua nhạy cảm vào prompt AI (được assert tự động trong `tests/test_ai.py`).
- [x] Khi ngắt mạng hoặc xóa API key, hệ thống vẫn trả về báo cáo phân tích thông minh qua bộ Fallback Engine trong $< 500$ms (< 50ms thực tế).
- [x] Prompt AI trả về đúng schema định dạng cấu trúc rõ ràng (Pydantic models).
- [x] Tích hợp cơ chế In-Day Cache theo fingerprint dữ liệu, bỏ qua cache khi có tham số `force_refresh=true`.

> 📝 **Cập nhật kiến trúc [2026-09-23]:**
>
> - Chức năng quét hàng tồn tối thiểu đã được giải quyết trọn vẹn từ Bước 06 qua `@computed_field is_low_stock` và bộ lọc `is_low_stock` trên endpoint `/products`. Do đó không tạo background job Scheduler thừa thãi để tránh feature creep, giữ hệ thống tinh gọn theo đúng nguyên tắc Simplicity First (GEMINI.md §2).

---

## 5. Cập nhật tiến độ

Sau khi hoàn thành bước này, mở file [docs/plans/TIEN-DO.md](file:///E:/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) và cập nhật dòng **Bước 08** theo đúng mẫu sau:

```markdown
| YYYY-MM-DD | Bước 08 | Module AI Trợ lý, Fallback & Cache | Hoàn thành | `backend/app/services/ai_service.py`, `services/fallback_service.py`, `services/ai_cache.py` | Đã hoàn thiện Module AI (Gemini 3.5 Flash Lite + Heuristic Fallback + In-Day Cache) cho các bài toán phân tích kho |
```

---

## 6. Lịch sử đồng bộ (Reconciliation History)

- **Ngày thực hiện:** 2026-10-28
- **Căn cứ:** Báo cáo sai lệch [`docs_evidence/09_bao_cao_sai_lech.md`](file:///e:/gemini/docs_evidence/09_bao_cao_sai_lech.md) (Mục #6, #12, #13, #18, #22, #27, #28, #33).
- **Nội dung điều chỉnh:**
  1. *[Mục #6 - Nhóm A]:* Bỏ Scheduler chạy ngầm; làm rõ cảnh báo tồn tối thiểu được tính động qua `@computed_field is_low_stock` tại [`backend/app/schemas/product.py` L44](file:///e:/gemini/hệ thống quản lý kho/backend/app/schemas/product.py#L44).
  2. *[Mục #22 - Nhóm C]:* Đồng bộ tên model AI chính thành `gemini-3.5-flash-lite` và chuỗi fallback (`gemini-3.1-flash-lite` $\rightarrow$ `gemini-3.6-flash`) theo [`backend/app/core/config.py` L24](file:///e:/gemini/hệ thống quản lý kho/backend/app/core/config.py#L24) và [`backend/app/services/ai_service.py` L352-359](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/ai_service.py#L352-L359).
  3. *[Mục #12, #13 - Nhóm B]:* Bổ sung 2 endpoint AI nâng cao: `POST /api/v1/ai/ask` (Hỏi đáp tự do SmartKho) và `POST /api/v1/ai/generate-order` (Sinh đơn hàng thông minh) theo [`backend/app/api/v1/endpoints/ai.py` L167, L242](file:///e:/gemini/hệ thống quản lý kho/backend/app/api/v1/endpoints/ai.py#L167).
  4. *[Mục #18 - Nhóm B]:* Bổ sung cơ chế In-Day Cache theo fingerprint dữ liệu trong [`backend/app/services/ai_cache.py` L1-150](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/ai_cache.py#L1-L150).
  5. *[Mục #27 - Nhóm C]:* Cập nhật công thức gợi ý nhập hàng chuẩn xác theo độ lệch chuẩn và lead time trong [`backend/app/services/fallback_service.py` L85-98](file:///e:/gemini/hệ thống quản lý kho/backend/app/services/fallback_service.py#L85-L98).
  6. *[Mục #28, #33 - Nhóm C, D]:* Đổi tên file deliverable KT3 thành `03_AI_Integration_Architecture.md` cho khớp với tệp thực tế trên đĩa.
- **Lý do:** Đồng bộ toàn diện đặc tả Module AI và cơ chế Fallback/Cache khớp chính xác với mã nguồn thực tế.
