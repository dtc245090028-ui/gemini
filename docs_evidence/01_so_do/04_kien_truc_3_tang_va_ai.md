# SƠ ĐỒ KIẾN TRÚC 3 TẦNG VÀ LUỒNG DỮ LIỆU TỚI PHÂN HỆ AI

**Mã sơ đồ:** `04_kien_truc_3_tang_va_ai`  
**Tập tin Mermaid:** [`04_kien_truc_3_tang_va_ai.mmd`](04_kien_truc_3_tang_va_ai.mmd)  
**Ảnh render:** [`04_kien_truc_3_tang_va_ai.png`](04_kien_truc_3_tang_va_ai.png)  
**Phương pháp thu thập:** [TỪ GIT/FILE] Trích xuất từ toàn bộ kiến trúc mã nguồn Frontend (`src/`), Backend (`app/`), CSDL (`core/database.py`) và luồng tiền xử lý dữ liệu AI (`ai_service.py`).

---

## 1. Nguồn trích xuất từ mã nguồn thực tế
1. **Kiến trúc 4 phân tầng hệ thống (3-Tier + Database):**
   - **Tầng Giao diện:** [`frontend/src/`](file:///E:/gemini/hệ thống quản lý kho/frontend/src/) (React 18, Vite 5, Tailwind CSS, Context API).
   - **Tầng API Gateway & Routers:** [`backend/app/main.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/main.py), [`backend/app/api/v1/api.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/api/v1/api.py) (9 sub-routers, Pydantic Schemas, JWT Interceptors).
   - **Tầng Dịch vụ (Service Layer):**
     - Nghiệp vụ kho: [`backend/app/services/inventory_service.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/inventory_service.py).
     - Điều phối AI: [`backend/app/services/ai_service.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/ai_service.py).
     - Động cơ Heuristic Fallback: [`backend/app/services/fallback_service.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/fallback_service.py).
     - Bộ nhớ đệm AI: [`backend/app/services/ai_cache.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/ai_cache.py).
   - **Tầng CSDL (Persistence Layer):** [`backend/app/core/database.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/core/database.py) (SQLite WAL mode, SQLAlchemy 2.0 ORM, 9 Models, CheckConstraints).
2. **Luồng dữ liệu đến AI (AI Data Pipeline):**
   - **SQL Aggregation:** [`ai_service.py#L69-L163`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/ai_service.py#L69-L163) (Truy vấn đếm tổng mặt hàng, tổng nhập, tổng xuất, mặt hàng dưới min_stock, top 5 mặt hàng).
   - **Lọc bảo mật giá mua:** Tuyệt đối không `SELECT` trường `ImportNoteDetail.unit_price` hoặc `total_amount` (Bảo đảm Zero Price Leakage theo `de_tai_07.md §5`).
   - **Kiểm tra Fingerprint:** [`ai_service.py#L412-L439`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/ai_service.py#L412-L439) (Đối soát `ledger_count`, `max_ledger_id`, `net_change` trong `ai_cache.json`).
   - **Gọi Gemini API:** [`ai_service.py#L344-L379`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/ai_service.py#L344-L379) (Chuỗi model dự phòng: `gemini-3.5-flash-lite` $\rightarrow$ `gemini-3.1-flash-lite` $\rightarrow$ `gemini-3.6-flash`).
   - **Chuyển mạch Circuit Breaker:** Khi bắt ngoại lệ `RuntimeError` (hết hạn mức 429 hoặc mất mạng), chuyển mạch sang [`fallback_service.py`](file:///E:/gemini/hệ thống quản lý kho/backend/app/services/fallback_service.py), trả về `is_fallback: true` và `provider: "heuristic_fallback"`.

---

## 2. Ghi chú so sánh
- [SUY LUẬN] Sơ đồ này phản ánh chi tiết và chính xác hơn tài liệu kiến trúc sơ khai ở KT1 nhờ bổ sung cơ chế kiểm soát Fingerprint của bộ nhớ đệm `AICacheManager` và chuỗi Model Fallback Chain được hoàn thiện trong mốc KT3 và Final.
