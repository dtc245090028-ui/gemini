# BÁO CÁO KỸ THUẬT TỔNG KẾT ĐỒ ÁN (FINAL TECHNICAL REPORT)

## HỆ THỐNG QUẢN LÝ KHO THÔNG MINH TÍCH HỢP TRÍ TUỆ NHÂN TẠO (WMS AI)
### Đề tài 07 — Phiên bản chuẩn hóa Học phần & Nghiệm thu Hội đồng (2026)

> **Văn bản tổng hợp:** Báo cáo kỹ thuật chi tiết đã được biên soạn và chuẩn hóa toàn diện trong tệp văn bản:
> 📄 [`Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`](file:///E:/gemini/Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx) (kèm bản sao lưu tại `docs/SDLC/final/` và `docs/submissions/final/`).
> Tài liệu dưới đây tóm lược kiến trúc, đặc tả nghiệp vụ, cơ chế an toàn và kết quả kiểm định của toàn bộ dự án.

---

## MỤC LỤC TỔNG QUAN

1. [Chương 1: Giới thiệu dự án & Phạm vi hệ thống](#chương-1-giới-thiệu-dự-án--phạm-vi-hệ-thống)
2. [Chương 2: Bối cảnh, Thách thức & Ma trận phân quyền RBAC](#chương-2-bối-cảnh-thách-thức--ma-trận-phân-quyền-rbac)
3. [Chương 3: Nghiệp vụ cốt lõi & Cỗ máy trạng thái xuất kho 3 bước](#chương-3-nghiệp-vụ-cốt-lõi--cỗ-máy-trạng-thái-xuất-kho-3-bước)
4. [Chương 4: Thiết kế Cơ sở Dữ liệu chuẩn 3NF & Ràng buộc toàn vẹn](#chương-4-thiết-kế-cơ-sở-dữ-liệu-chuẩn-3nf--ràng-buộc-toàn-vẹn)
5. [Chương 5: Thiết kế Kiến trúc Hệ thống Clean Architecture 3 tầng](#chương-5-thiết-kế-kiến-trúc-hệ-thống-clean-architecture-3-tầng)
6. [Chương 6: Cơ chế Chốt chặn kép Chống tồn kho âm (ACID Guarantee)](#chương-6-cơ-chế-chốt-chặn-kép-chống-tồn-kho-âm-acid-guarantee)
7. [Chương 7: Phân hệ AI Copilot & Heuristic Fallback Engine](#chương-7-phân-hệ-ai-copilot--heuristic-fallback-engine)
8. [Chương 8: Thiết kế Giao diện Công thái học (Ergonomic Frontend)](#chương-8-thiết-kế-giao-diện-công-thái-học-ergonomic-frontend)
9. [Chương 9: Chiến lược Kiểm thử tự động & Đảm bảo chất lượng](#chương-9-chiến-lược-kiểm-thử-tự-động--đảm-bảo-chất-lượng)
10. [Chương 10: Kết luận, Giá trị thực tiễn & Hướng phát triển](#chương-10-kết-luận-giá-trị-thực-tiễn--hướng-phát-triển)
11. [Lịch sử đồng bộ](#lịch-sử-đồng-bộ)

---

## CHƯƠNG 1: GIỚI THIỆU DỰ ÁN & PHẠM VI HỆ THỐNG

### 1.1. Mục đích dự án
Dự án nhằm xây dựng một giải pháp Quản lý Kho bãi Hiện đại (Warehouse Management System - WMS AI) dành riêng cho các doanh nghiệp vừa và nhỏ (SMEs). Ứng dụng kết hợp giữa nền tảng phần mềm quản trị chặt chẽ (FastAPI, SQLite ACID, React 18 Tailwind) và sức mạnh phân tích dự báo của Trí tuệ Nhân tạo thế hệ mới (Google Gemini 3.5 Flash Lite), giúp tối ưu hóa luồng chu chuyển hàng hóa, hạn chế tối đa thất thoát và nâng cao năng lực ra quyết định của nhà quản lý.

### 1.2. Phạm vi hệ thống (System Scope)
- **Hệ thống API RESTful hoàn chỉnh:** Cung cấp tổng cộng **44 endpoints** (42 endpoints API v1 + 2 endpoints root & health check) phục vụ toàn diện các phân hệ nghiệp vụ.
- **Quản lý Danh mục & Hàng hóa:** Phân loại nhóm hàng (Category), sản phẩm (Product) với ngưỡng an toàn `min_stock`, giá tiêu chuẩn và tính năng tải ảnh sản phẩm (`image_url`).
- **Quản lý Nhà cung cấp (Suppliers):** Quản lý đối tác cung ứng, bảo toàn lịch sử giao dịch bằng soft-deactivation.
- **Quản lý Phiếu Nhập kho (Import Notes):** Nhập hàng đa dòng, lưu đơn giá vốn thực tế, tăng tồn kho và ghi Sổ cái thẻ kho qua giao dịch nguyên tử (ACID), hỗ trợ `idempotency_key`.
- **Cỗ máy Trạng thái Xuất kho 3 bước (3-Stage Export Flow):** Quy trình chuẩn gồm `CONFIRMED` $\rightarrow$ `SHIPPING` $\rightarrow$ `COMPLETED`, hỗ trợ xóa phiếu chưa xuất kho và hủy phiếu hoàn kho.
- **Sổ cái Thẻ kho bất biến (Immutable Stock Ledger):** Lưu vết kiểm toán mọi biến động (Audit Trail), chỉ lưu số lượng vật lý và số dư sau giao dịch; hỗ trợ xuất file Excel và điều chỉnh kiểm kê thực tế.
- **Trợ lý Thông minh AI Copilot (Gemini 3.5 Flash Lite & AI Cache):**
  - Báo cáo điều hành Nhập - Xuất - Tồn hàng tháng kèm xuất file Excel.
  - Gợi ý bổ sung hàng thông minh dựa trên vận tốc bán (Velocity 30 ngày).
  - Phát hiện dị thường: Hàng xuất đột biến (`SURGE_EXPORT` > 200%) và Hàng tồn chết (`DEAD_STOCK` > 30 ngày).
  - Hỏi đáp tự do SmartKho Copilot (`/ai/ask`) và sinh đơn hàng xuất kho theo yêu cầu (`/ai/generate-order`).
- **Cơ chế Dự phòng Heuristic Fallback Engine:** Đảm bảo hệ thống duy trì 100% chức năng phân tích ngay cả khi mất kết nối Internet hoặc lỗi dịch vụ AI ngoài.

---

## CHƯƠNG 2: BỐI CẢNH, THÁCH THỨC & MA TRẬN PHÂN QUYỀN RBAC

### 2.1. Ba bài toán nhức nhối của kho bãi truyền thống
1. **Lỗi tồn kho âm:** Do các thao tác xuất kho không được khóa giao dịch hoặc kiểm tra lỏng lẻo, dẫn đến số liệu phần mềm âm trong khi thực tế không còn hàng.
2. **Giam giữ hàng ảo (Phantom Stock Hold):** Nhiều phần mềm tự ý trừ tồn kho ngay khi vừa tạo đơn hàng, khiến kho bị "đóng băng" dù đơn chưa hề xuất kho vật lý.
3. **Thao tác SKU rườm rà & Nhập liệu sai sót:** Bắt buộc thủ kho phải nhớ chính xác mã SKU dài dòng dẫn đến thao tác chậm chạp và dễ chọn nhầm sản phẩm.

### 2.2. Ma trận Phân quyền 3 Cấp độ (RBAC Matrix)

| Chức năng / Quyền hạn | Quản trị viên (ADMIN) | Thủ kho (WAREHOUSE_KEEPER) | Kế toán (ACCOUNTANT) |
| :--- | :---: | :---: | :---: |
| Quản lý tài khoản người dùng (`/users`) | ✅ Toàn quyền | ❌ Chặn (403) | ❌ Chặn (403) |
| Quản lý Danh mục, Hàng hóa, Upload ảnh, NCC | ✅ Toàn quyền | ✅ Thêm / Sửa / Xem | 👁️ Chỉ xem (Read-only) |
| Lập & Hủy Phiếu Nhập kho | ✅ Toàn quyền | ✅ Lập / Hủy phiếu | 👁️ Chỉ xem |
| Lập & Điều phối Phiếu Xuất kho 3 bước | ✅ Toàn quyền | ✅ Điều phối 3 trạng thái | 👁️ Chỉ xem |
| Xóa Phiếu Xuất kho CONFIRMED | ✅ Toàn quyền | ✅ Xóa an toàn | 👁️ Chỉ xem |
| Thực hiện Điều chỉnh Kiểm kê | ✅ Phê duyệt & Điều chỉnh | ✅ Báo cáo & Cân đối | 👁️ Chỉ xem |
| Tra cứu Báo cáo Nhập-Xuất-Tồn & Thẻ kho | ✅ Đầy đủ | ✅ Đầy đủ | ✅ Đầy đủ (chuyên trách) |
| Xuất Báo cáo & Thẻ kho ra file Excel (.xlsx) | ✅ Toàn quyền | ✅ Xuất file | ✅ Xuất file |
| Phân hệ Trợ lý AI (5 tính năng) | ✅ Toàn quyền phân tích | ✅ Nhận khuyến nghị nhập | ✅ Phân tích số liệu tồn |

---

## CHƯƠNG 3: NGHIỆP VỤ CỐT LÕI & CỖ MÁY TRẠNG THÁI XUẤT KHO 3 BƯỚC

### 3.1. Quy trình Nhập kho Chuẩn (Import Workflow)
1. Thủ kho chọn Nhà cung cấp và lập phiếu nhập gồm danh sách sản phẩm, số lượng và đơn giá nhập thực tế (hỗ trợ `idempotency_key`).
2. Hệ thống sinh mã phiếu chuẩn `PN-YYYYMMDD-XXXX` (với cơ chế Retry chống trùng mã khi tải cao).
3. Mở giao dịch CSDL: Ghi phiếu nhập, ghi chi tiết phiếu nhập, cộng `current_stock` tương ứng cho từng mặt hàng, ghi nhận bản ghi biến động dương vào Sổ cái thẻ kho (`stock_ledger`).
4. Commit giao dịch thành công. Nếu có bất kỳ lỗi nào, Rollback toàn bộ để đảm bảo tính nhất quán.

### 3.2. Cỗ máy Trạng thái Xuất kho 3 Bước (3-Stage State Machine)

```mermaid
stateDiagram-v2
    [*] --> CONFIRMED: 1. Tạo phiếu xuất (Kiểm tra đủ tồn kho, CHƯA trừ tồn)
    CONFIRMED --> CANCELLED_VOID: Thủ kho bấm Hủy & Xóa (DELETE /export-notes/{id})
    CONFIRMED --> SHIPPING: 2. Hàng rời kho vật lý (Trừ tồn kho nguyên tử & ghi Thẻ kho)
    SHIPPING --> CANCELLED_REFUND: Giao thất bại / Khách trả (Đổi trạng thái & Hoàn kho 100%)
    SHIPPING --> COMPLETED: 3. Ký nhận biên bản (Khóa phiếu vĩnh viễn)
    COMPLETED --> [*]
    CANCELLED_VOID --> [*]
    CANCELLED_REFUND --> [*]
```

- **Giai đoạn 1 (`CONFIRMED`):** Tiếp nhận yêu cầu xuất hàng. Hệ thống xác nhận đủ tồn khả dụng nhưng **chưa trừ tồn kho thực tế**. Người dùng có thể xóa phiếu (`DELETE /api/v1/export-notes/{id}`) nếu chưa xuất kho.
- **Giai đoạn 2 (`SHIPPING`):** Khi kiện hàng rời kho, thủ kho kích hoạt chuyển trạng thái sang `SHIPPING`. Hệ thống thực hiện trừ tồn kho nguyên tử bằng Atomic SQL `RETURNING current_stock` và ghi bản ghi xuất vào Thẻ kho. Nếu giao hàng thất bại, có thể hủy phiếu: hệ thống tự động hoàn trả 100% số lượng về kho và ghi Thẻ kho hoàn ứng.
- **Giai đoạn 3 (`COMPLETED`):** Khách hàng đã nhận và ký biên bản. Phiếu chuyển sang Hoàn thành và bị khóa chỉnh sửa vĩnh viễn.

---

## CHƯƠNG 4: THIẾT KẾ CƠ SỞ DỮ LIỆU CHUẨN 3NF & RÀNG BUỘC TOÀN VẸN

### 4.1. Sơ đồ Quan hệ Thực thể (ERD 9 Bảng)

```mermaid
erDiagram
    USERS ||--o{ IMPORT_NOTES : "creates"
    USERS ||--o{ EXPORT_NOTES : "creates"
    USERS ||--o{ STOCK_LEDGER : "creates"
    CATEGORIES ||--o{ PRODUCTS : "contains"
    SUPPLIERS ||--o{ IMPORT_NOTES : "supplies"
    IMPORT_NOTES ||--|{ IMPORT_NOTE_DETAILS : "includes"
    PRODUCTS ||--o{ IMPORT_NOTE_DETAILS : "specified_in"
    EXPORT_NOTES ||--|{ EXPORT_NOTE_DETAILS : "includes"
    PRODUCTS ||--o{ EXPORT_NOTE_DETAILS : "specified_in"
    PRODUCTS ||--o{ STOCK_LEDGER : "tracked_by"

    USERS {
        int id PK
        string username UK
        string password_hash
        string full_name
        string role "ADMIN | WAREHOUSE_KEEPER | ACCOUNTANT"
        boolean is_active
        datetime created_at
    }
    CATEGORIES {
        int id PK
        string code UK
        string name
        string description
    }
    PRODUCTS {
        int id PK
        int category_id FK
        string code UK
        string name
        string unit
        int min_stock
        int current_stock "CHECK(current_stock >= 0)"
        float standard_price
        string image_url
        string status "ACTIVE | DISCONTINUED"
        datetime created_at
    }
    SUPPLIERS {
        int id PK
        string code UK
        string name
        string phone
        string email
        string address
        boolean is_active
    }
    IMPORT_NOTES {
        int id PK
        string code UK "PN-YYYYMMDD-XXXX"
        string idempotency_key UK
        int supplier_id FK
        int created_by FK
        float total_amount
        string status "COMPLETED | CANCELLED"
        string note
        datetime note_date
    }
    IMPORT_NOTE_DETAILS {
        int id PK
        int import_note_id FK
        int product_id FK
        int quantity "CHECK(quantity > 0)"
        float unit_price "CHECK(unit_price >= 0)"
        float subtotal
    }
    EXPORT_NOTES {
        int id PK
        string code UK "PX-YYYYMMDD-XXXX"
        string idempotency_key UK
        int created_by FK
        string recipient_name
        float total_amount
        string status "CONFIRMED | SHIPPING | COMPLETED | CANCELLED"
        string note
        datetime note_date
    }
    EXPORT_NOTE_DETAILS {
        int id PK
        int export_note_id FK
        int product_id FK
        int quantity "CHECK(quantity > 0)"
        float unit_price "CHECK(unit_price >= 0)"
        float subtotal
    }
    STOCK_LEDGER {
        int id PK
        int product_id FK
        string transaction_type "IMPORT | EXPORT | ADJUSTMENT"
        string reference_code
        int quantity_change
        int balance_after "CHECK(balance_after >= 0)"
        int created_by FK
        string note
        datetime transaction_date
    }
```

---

## CHƯƠNG 5: THIẾT KẾ KIẾN TRÚC HỆ THỐNG CLEAN ARCHITECTURE 3 TẦNG

```mermaid
graph TD
    subgraph Presentation_Layer ["Presentation Layer"]
        UI["React 18 SPA (Vite + Tailwind CSS + Lucide Icons + Tokens Dark/Light)"]
        API["FastAPI REST Endpoints (44 Endpoints, api/v1/endpoints/*.py)"]
        DEP["Dependencies, SlidingWindowRateLimiter & RBAC Guard (api/deps.py)"]
    end

    subgraph Service_Layer ["Core Business Logic (Services)"]
        IS["InventoryService (ACID Transactions & Atomic SQL Negative Stock Guard)"]
        AIS["AIService (SQL Aggregation Pipeline, Grounding & AI In-Day Cache)"]
        FBS["FallbackService (Heuristic Math Engine)"]
    end

    subgraph Persistence_Layer ["Data & Infrastructure Layer"]
        ORM["SQLAlchemy 2.0 ORM Models"]
        DB[(SQLite Engine with PRAGMA foreign_keys=ON)]
        GEMINI["Google Gemini 3.5 Flash Lite (Fallback: 3.1 -> 3.6)"]
    end

    UI -->|HTTP / JSON with JWT| API
    API --> DEP
    API --> IS
    API --> AIS
    AIS -->|Fallback when offline| FBS
    AIS -->|Aggregated Data| GEMINI
    IS --> ORM
    ORM --> DB
```

---

## CHƯƠNG 6: CƠ CHẾ CHỐT CHẶN KÉP CHỐNG TỒN KHO ÂM (ACID GUARANTEE)

Hệ thống thiết kế cơ chế bảo vệ 2 lớp (Two-Tier Defense) loại trừ 100% rủi ro tồn âm:

1. **Chốt chặn Tầng 1 — Atomic SQL Update tại bước giao hàng (`SHIPPING`):**
   - Thực thi câu lệnh SQL trừ kho nguyên tử cấp độ Database Engine:
     ```sql
     UPDATE products
     SET current_stock = current_stock - :qty
     WHERE id = :product_id AND current_stock >= :qty
     RETURNING current_stock;
     ```
   - Nếu tồn kho không đủ, câu lệnh trả về `None`, hệ thống lập tức ném lỗi HTTP 400 và Rollback toàn bộ giao dịch.
2. **Chốt chặn Tầng 2 — Database CheckConstraint:**
   - Tầng cơ sở dữ liệu định nghĩa ràng buộc cứng tại bảng `products`:
     `CheckConstraint('current_stock >= 0', name='check_positive_stock')`
   - Kể cả khi có truy vấn ngoài luồng, cơ sở dữ liệu sẽ lập tức từ chối và Rollback giao dịch nếu số dư nhỏ hơn 0.

---

## CHƯƠNG 7: PHÂN HỆ AI COPILOT & HEURISTIC FALLBACK ENGINE

### 7.1. Năm Năng lực Phân tích AI Chuyên sâu
1. **Báo cáo Tháng Thông minh (Executive Inventory Report - `/ai/monthly-report`):**
   - Đánh giá luân chuyển hàng hóa, cơ cấu hàng bán chạy và đưa ra khuyến nghị điều hành thực tế.
2. **Gợi ý Bổ sung Hàng hóa (Reorder Suggestions - `/ai/restock-suggestions`):**
   - Phân tích vận tốc bán trong 30 ngày (`daily_velocity`), dự báo nhu cầu và đề xuất số lượng cần nhập:
     $$\text{Suggested Qty} = \max\Big(\text{min\_stock} \times 2 - \text{current\_stock},\; \text{round}(\text{daily\_velocity} \times 30) - \text{current\_stock},\; \text{min\_stock}\Big)$$
3. **Phát hiện Dị thường Biến động (Anomaly Detection - `/ai/anomalies`):**
   - Nhận diện xuất đột biến (`SURGE_EXPORT` > 200%).
   - Nhận diện hàng chết / ứ đọng (`DEAD_STOCK` > 30 ngày).
4. **Trợ lý SmartKho Copilot (`/ai/ask`):** Tra cứu thông tin kho tức thời qua ngôn ngữ tự nhiên.
5. **Sinh Đơn hàng Xuất kho Tự động (`/ai/generate-order`):** Soạn thảo nhanh phiếu xuất từ văn bản yêu cầu.

### 7.2. Bảo mật Thông tin Tuyệt đối & AI In-Day Cache
- **Tách lọc giá vốn:** Toàn bộ thông tin giá nhập (`unit_price` trong phiếu nhập) đều bị loại bỏ 100% tại `ai_service.py` trước khi gửi sang Gemini.
- **AI In-Day Cache (`ai_cache.py`):** Lưu trữ kết quả phân tích theo Data Fingerprint trong ngày, giảm thiểu 80% số lần gọi trùng lặp và tăng tốc độ phản hồi.
- **Mô hình AI & Fallback Chain:** Sử dụng `gemini-3.5-flash-lite`, tự động fallback sang `gemini-3.1-flash-lite` $\rightarrow$ `gemini-3.6-flash` khi gặp lỗi 429.

### 7.3. Bộ Dự phòng Heuristic Fallback Engine
- Khi không có Internet, không có `GEMINI_API_KEY` hoặc API quá tải, hệ thống tự động chuyển mạch sang `fallback_service.py` trong vòng $< 50$ms. Cấu trúc phản hồi JSON hoàn toàn trùng khớp với API AI.

---

## CHƯƠNG 8: THIẾT KẾ GIAO DIỆN CÔNG THÁI HỌC (ERGONOMIC FRONTEND)

- **Frontend Tech-stack:** React 18, Vite, Tailwind CSS, Lucide Icons, Axios.
- **Hỗ trợ Dark / Light Theme:** Tích hợp nút chuyển đổi giao diện sáng/tối qua hệ thống Design Tokens (`tokens.css`).
- **Xác nhận thao tác an toàn với ConfirmModal:** Bắt buộc nhập lý do $\ge 5$ ký tự khi hủy phiếu hoặc xóa phiếu xuất chưa giao.
- **Component Đột phá `ProductSelect`:**
  - Hỗ trợ gõ tắt theo chữ cái đầu (VD: gõ `blv` tìm thấy *Bàn Làm Việc*).
  - Tích hợp bộ lọc nhóm hàng tức thời, hiển thị trực quan tồn kho và tải ảnh sản phẩm.
- **Gộp phân hệ Báo cáo:** Tích hợp Báo cáo Nhập-Xuất-Tồn tại Tab 1 của trang Trợ lý AI, hỗ trợ xuất file Excel trực quan.
- **Thanh Công cụ Chuyển Vai Trò Demo (1-Click Role Switcher):**
  - Giúp sinh viên thuyết trình linh hoạt luân chuyển giữa Quản trị viên, Thủ kho và Kế toán mà không cần đăng nhập lại.

---

## CHƯƠNG 9: CHIẾN LƯỢC KIỂM THỬ TỰ ĐỘNG & ĐẢM BẢO CHẤT LƯỢNG

- **Công cụ:** Pytest, SQLite in-memory, TestClient FastAPI, Coverage.
- **Quy mô:** Toàn bộ hệ thống được bảo vệ bởi **70 bài kiểm thử tự động toàn diện** (Độ bao phủ code đạt **83%**):
  - `test_auth.py`: Xác thực JWT, hash bcrypt, RBAC 3 vai trò, Rate Limiting (12 tests).
  - `test_master_data.py`: CRUD Hàng hóa, Nhóm hàng, Nhà cung cấp, Upload ảnh (5 tests).
  - `test_stock_transactions.py`: Transaction ACID, cỗ máy trạng thái xuất kho 3 bước, Chặn tồn âm, Hủy phiếu, Thẻ kho, Báo cáo, Idempotency Key, Xóa phiếu CONFIRMED (18 tests).
  - `test_ai_service.py`: Bảo mật giá vốn, Mock Gemini, Fallback Heuristic, AI Cache, RBAC (31 tests).
  - `test_ai_empty_data.py`: Kiểm thử an toàn các endpoint AI khi kho hoàn toàn rỗng (4 tests).
- **Kết quả nghiệm thu:** **70/70 tests PASS 100%**, tỷ lệ lỗi 0%.
- **Dữ liệu mẫu (`seed_data.py`):** **76 sản phẩm**, **7 nhóm hàng**, **10 nhà cung cấp**, lịch sử **5 tháng (150 ngày)**.

---

## CHƯƠNG 10: KẾT LUẬN, GIÁ TRỊ THỰC TIỄN & HƯỚNG PHÁT TRIỂN

### 10.1. Đánh giá Kết quả Đạt được
Dự án **Đề tài 07: Hệ thống quản lý kho có tích hợp AI** đã hoàn thành 100% mục tiêu đề ra:
1. Đảm bảo toàn vẹn dữ liệu kho bãi tuyệt đối qua giao dịch ACID và cơ chế chốt chặn kép chống tồn âm (Atomic SQL `RETURNING`).
2. Thiết kế cỗ máy trạng thái xuất kho 3 bước khoa học, xóa bỏ triệt để hiện tượng giữ hàng ảo và hỗ trợ xóa phiếu chưa xuất.
3. Ứng dụng AI thực chất vào quản trị tồn kho với mô hình Gemini 3.5 Flash Lite kèm cơ chế Fallback offline sẵn sàng 24/7.
4. Giao diện người dùng hiện đại, hỗ trợ Dark mode, ConfirmModal, xuất Excel và tích hợp toàn diện.
5. Hồ sơ tài liệu SDLC 4 giai đoạn chuẩn mực, đầy đủ báo cáo tổng kết DOCX và Slide bảo vệ đồ án PPTX.

---

## LỊCH SỬ ĐỒNG BỘ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Chuẩn hóa số lượng endpoint:** Cập nhật chính xác **44 endpoints** toàn hệ thống.
  - **Cập nhật mô hình AI:** Chuẩn hóa sang `gemini-3.5-flash-lite`, chuỗi fallback chain 3.1 $\rightarrow$ 3.6, bổ sung `ai_cache.py` và 2 endpoints `/ai/ask`, `/ai/generate-order`.
  - **Đồng bộ CSDL:** Bổ sung `image_url` cho sản phẩm, `idempotency_key` cho phiếu nhập/xuất, chuẩn hóa trạng thái phiếu xuất 3 bước.
  - **Đồng bộ giao diện:** Bổ sung Dark mode, ConfirmModal, gộp Báo cáo NXT vào AIAssistant (kèm xuất Excel) và xuất Excel Thẻ kho.
  - **Đồng bộ kiểm thử & dữ liệu mẫu:** Cập nhật **70 tests PASS 100%** (83% coverage) và **Seed data 76 sản phẩm / 5 tháng (150 ngày)**.
