# KIẾN TRÚC HỆ THỐNG (SYSTEM ARCHITECTURE)
## Đề tài 07: Hệ thống Quản lý Kho Thông minh tích hợp AI

> **Mục đích tài liệu:** Cung cấp bức tranh toàn cảnh về cấu trúc phân tầng, luồng dữ liệu và các cơ chế nghiệp vụ cốt lõi của hệ thống để giảng viên và hội đồng có thể nắm bắt toàn bộ kiến trúc mà không cần đọc trực tiếp mã nguồn.

---

## 1. MÔ HÌNH KIẾN TRÚC PHÂN TẦNG (3-TIER ARCHITECTURE)

Hệ thống tuân thủ nghiêm ngặt nguyên lý phân tách trách nhiệm (Separation of Concerns) với 3 tầng độc lập:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      TẦNG CLIENT / PRESENTATION                         │
│             React 18 + Vite + Tailwind CSS (SPA Dashboard)              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP / RESTful API (JSON)
                                     │ Bearer JWT Token
┌────────────────────────────────────▼────────────────────────────────────┐
│                        TẦNG API & GIAO TIẾP (api/)                      │
│ - Chỉ xử lý giao thức HTTP, định dạng dữ liệu (Pydantic Request/Response)│
│ - Xác thực người dùng (Auth) và phân quyền vai trò RBAC                │
│ - Tuyệt đối KHÔNG chứa logic nghiệp vụ tính toán kho bãi               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Gọi hàm nghiệp vụ
┌────────────────────────────────────▼────────────────────────────────────┐
│                     TẦNG DỊCH VỤ NGHIỆP VỤ (services/)                  │
│ - inventory_service.py: Quản lý Transaction ACID, kiểm tồn, thẻ kho    │
│ - ai_service.py: Tích hợp Google Gemini & Heuristic Fallback Engine     │
│ - Điều phối toàn bộ luồng nghiệp vụ và quy tắc toàn vẹn                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Thao tác dữ liệu (SQLAlchemy 2.0)
┌────────────────────────────────────▼────────────────────────────────────┐
│                   TẦNG DỮ LIỆU & PERSISTENCE (models/ & core/)           │
│ - SQLAlchemy Models (9 bảng quan hệ chặt chẽ)                           │
│ - CheckConstraint("current_stock >= 0") chặn tồn âm ở mức CSDL          │
│ - SQLite Engine với PRAGMA foreign_keys = ON;                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Ranh giới trách nhiệm chi tiết:
1. **`app/api/` (HTTP Only):** Nhận request, xác thực JWT, kiểm tra phân quyền (RBAC qua `deps.py`), validate schema Pydantic và trả về HTTP Response tương ứng.
2. **`app/services/` (Business Logic):** Nơi chứa toàn bộ tri thức nghiệp vụ: Transaction ACID, kiểm tra chống tồn âm, sinh mã tự động theo ngày, cơ chế kiểm kê bù trừ và gọi AI Engine.
3. **`app/models/` & `app/core/` (ORM & Database):** Quản lý định nghĩa bảng, kết nối CSDL, Session, ràng buộc toàn vẹn dữ liệu (Unique, Foreign Key, CheckConstraint).

---

## 2. SƠ ĐỒ CÁC LUỒNG NGHIỆP VỤ CỐT LÕI

### 2.1. Luồng Nhập kho (Import Flow)
```
Request (POST /import-notes)
   │
   ▼
[API: import_notes.py] ── Xác thực JWT & Quyền Thủ kho/Admin
   │
   ▼
[Service: inventory_service.create_import_note]
   │
   ├─► Bắt đầu Database Transaction
   ├─► Tự động sinh mã phiếu PN-YYYYMMDD-XXXX (kèm Retry Pattern)
   ├─► Tạo bản ghi ImportNote & ImportNoteDetail
   ├─► Tăng current_stock của các mặt hàng
   ├─► Ghi nhận bản ghi Thẻ kho (StockLedger: type='IMPORT', qty > 0)
   ├─► COMMIT Transaction
   │
   ▼
Response (HTTP 201 Created)
```

---

### 2.2. Luồng Xuất kho & Chống tồn kho âm (Export Flow)
```
Request (POST /export-notes)
   │
   ▼
[API: export_notes.py] ── Xác thực JWT & Quyền Thủ kho/Admin
   │
   ▼
[Service: inventory_service.create_export_note]
   │
   ├─► Bắt đầu Database Transaction
   ├─► [ATOMIC CHECK]: Với từng sản phẩm, kiểm tra (current_stock >= qty)?
   │        │
   │        ├─► [KHÔNG ĐỦ]: Ném lỗi HTTP 400 Bad Request
   │        │               Tự động ROLLBACK toàn bộ 100%
   │        │               Số tồn kho giữ nguyên, kết thúc!
   │        │
   │        └─► [ĐỦ HÀNG]: Tiếp tục
   │
   ├─► Tự động sinh mã phiếu PX-YYYYMMDD-XXXX (kèm Retry Pattern)
   ├─► Tạo bản ghi ExportNote & ExportNoteDetail
   ├─► Giảm current_stock của các mặt hàng
   ├─► Ghi nhận bản ghi Thẻ kho (StockLedger: type='EXPORT', qty < 0)
   ├─► COMMIT Transaction
   │
   ▼
Response (HTTP 201 Created)
```

---

### 2.3. Luồng Xử lý AI & Fallback Engine (AI Flow - Chuẩn bị cho Giai đoạn 4)
```
Yêu cầu phân tích / gợi ý từ người dùng
   │
   ▼
[Service: ai_service.py]
   │
   ├─► Thu thập và tiền xử lý số liệu thật từ CSDL (StockLedger, Product)
   ├─► Chuẩn bị Prompt có cấu trúc (Strict JSON schema, Anti-hallucination)
   │
   ├─► [Bước 1]: Gửi yêu cầu tới Google Gemini API (gemini-1.5-flash)
   │        │
   │        ├─► [THÀNH CÔNG]: Trả về kết quả phân tích AI giàu ngữ cảnh
   │        │
   │        └─► [THẤT BẠI] (Mất mạng, hết quota, timeout...)
   │                 │
   │                 ▼
   │            [Bước 2 - FALLBACK HEURISTIC]:
   │            Kích hoạt fallback_service.py (tính toán thuần thống kê)
   │            - Phân tích Min/Max, tốc độ tiêu thụ bình quân
   │            - Đưa ra cảnh báo và đề xuất dựa trên quy tắc nghiệp vụ
   │            - Trả về kết quả với nhãn "Nguồn: Thuật toán Heuristic nội bộ"
   │
   ▼
Người dùng luôn nhận được kết quả (Đảm bảo độ sẵn sàng cao 100%)
```

---

## 3. TỔNG KẾT CƠ CHẾ BẢO MẬT & ĐỘ BỀN VỮNG
- **Bảo mật:** Mật khẩu hash bằng `bcrypt` thuần, xác thực bằng `PyJWT` (HS256, hạn 60 phút), phân quyền 3 tầng vai trò (`ADMIN`, `WAREHOUSE_KEEPER`, `ACCOUNTANT`).
- **Toàn vẹn CSDL:** SQLite Foreign Keys được cưỡng chế qua `PRAGMA foreign_keys = ON;`, CheckConstraint `current_stock >= 0` ngăn chặn triệt để dữ liệu rác.
- **Sổ cái kiểm toán:** Thẻ kho `StockLedger` lưu lại mọi biến động lịch sử, phục vụ đối soát kế toán và sinh báo cáo Nhập - Xuất - Tồn chính xác theo công thức bất biến.
