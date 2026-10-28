# Bản đồ mã nguồn

> **File này bắt buộc cập nhật mỗi khi thêm, xóa hoặc đổi vai trò một file.**
> Xem `CLAUDE.md §11` — trigger "thêm/xóa/đổi vai trò file bất kỳ" $\rightarrow$ cập nhật ngay lập tức.

**Cập nhật lần cuối:** 2026-10-28 (Đồng bộ toàn diện theo thực tế mã nguồn & kiểm thử)

---

## Hiện có

### Gốc dự án

| File | Vai trò |
| --- | --- |
| `de_tai_07.md` | Đề bài gốc của giảng viên kèm Phụ lục ghi chú triển khai thực tế |
| `Prompt.md` | Đặc tả hợp nhất đầy đủ — nguồn sự thật về nghiệp vụ và kỹ thuật |
| `CLAUDE.md` | Hướng dẫn hành vi agent, quy trình làm việc, quy ước toàn dự án |
| `GEMINI.md` | Bộ chỉ dẫn hành vi, ranh giới kiến trúc và quy ước quản lý dự án |
| `README.md` | Hướng dẫn khởi chạy hệ thống (Docker & cục bộ), tài khoản mẫu và mục lục hồ sơ SDLC |
| `run.bat` | Script khởi chạy 1-Click đồng thời Backend và Frontend trên Windows |
| `docker-compose.yml` | File điều phối 2 Docker containers: `warehouse_backend` & `warehouse_frontend` |

### `docs/`

| File / Thư mục | Vai trò |
| --- | --- |
| `docs/codebase-map.md` | File này — bản đồ mã nguồn, cập nhật theo phiên |
| `docs/MASTER-ROADMAP.md` | Bức tranh toàn cảnh 8 giai đoạn — điều hướng sang Buoc-NN.md |
| `docs/architecture.md` | Sơ đồ kiến trúc 3 tầng và luồng dữ liệu nghiệp vụ kho + AI (44 endpoints) |
| `docs/implementation_plan.md` | Phân tích yêu cầu chi tiết và kế hoạch triển khai ban đầu |
| `docs/plans/TIEN-DO.md` | Nhật ký tiến độ — **nguồn sự thật về trạng thái** (11/11 Bước Hoàn thành) |
| `docs/plans/Buoc-01-*.md` đến `Buoc-11-*.md` | 11 file kế hoạch chi tiết từng bước (100% hoàn thành, có lịch sử đồng bộ) |
| `docs/SDLC/KT1/*.md` | Bộ hồ sơ đặc tả SRS, ERD, AI specs và Wireframes mốc KT1 |
| `docs/SDLC/KT2/*.md` | Bộ hồ sơ API Specs (44 endpoints), Transaction Design và AI Evidence mốc KT2 |
| `docs/SDLC/KT3/*.md` | Bộ hồ sơ Prompt Engineering, Test Plan (70 tests) và AI Integration Architecture mốc KT3 |
| `docs/SDLC/final/01_Final_Technical_Report.md` | Báo cáo kỹ thuật tổng kết toàn diện 10 chương mốc Cuối kỳ |
| `docs/SDLC/final/02_User_Guide_and_Demo_Script.md` | Hướng dẫn sử dụng 7 phân hệ và kịch bản demo 5 phút chấm thi |
| `docs/SDLC/final/03_Presentation_Slides.md` | Bản chép lời và nội dung 16 slide thuyết trình bảo vệ đồ án |
| `docs/SDLC/final/Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx` | Văn bản Báo cáo đặc tả kiến trúc định dạng Word chính thức (10 chương) |
| `docs/SDLC/final/Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx` | Bộ Slide thuyết trình định dạng PowerPoint chuẩn đồ họa (16 trang) |
| `docs/submissions/` | Bộ sản phẩm nộp bài đồng bộ 4 mốc (KT1, KT2, KT3, final) |

### `backend/`

| File | Vai trò |
| --- | --- |
| `backend/requirements.txt` | Python dependencies (FastAPI, SQLAlchemy, bcrypt, pyjwt, google-genai, pytest, openpyxl) |
| `backend/.env.example` | Mẫu biến môi trường backend |
| `backend/.env` | Cấu hình môi trường backend cục bộ (SQLite) |
| `backend/Dockerfile` | Dockerfile đóng gói backend FastAPI |
| `backend/seed_data.py` | Script nạp 76 SP, 7 nhóm, 10 NCC và lịch sử 5 tháng (150 ngày) nhập xuất |
| `backend/app/main.py` | Điểm vào FastAPI: Rate Limiter, CORS, static mounts, exception handlers |
| `backend/app/core/config.py` | Pydantic Settings: cấu hình JWT, DB URL, Gemini model `gemini-3.5-flash-lite` |
| `backend/app/core/database.py` | SQLAlchemy engine + SessionLocal + listener SQLite PRAGMA foreign_keys=ON |
| `backend/app/core/security.py` | Hàm hash password (bcrypt thuần) và tạo/giải mã JWT (pyjwt HS256) |
| `backend/app/core/seed.py` | Idempotent seed nạp 3 tài khoản mặc định (admin, thukho, ketoan) |
| `backend/app/api/deps.py` | Dependencies xác thực JWT (`get_current_user`) và phân quyền RBAC (`require_roles`) |
| `backend/app/api/v1/api.py` | Router gốc API v1 gom toàn bộ 42 sub-endpoints |
| `backend/app/api/v1/endpoints/auth.py` | Endpoints đăng nhập (/login, /login-form), profile (/me), tạo user (/users) |
| `backend/app/api/v1/endpoints/categories.py` | Endpoints CRUD nhóm hàng (chặn xóa nhóm có sản phẩm) |
| `backend/app/api/v1/endpoints/products.py` | Endpoints CRUD sản phẩm, upload ảnh (/image), lọc `is_low_stock` |
| `backend/app/api/v1/endpoints/suppliers.py` | Endpoints CRUD nhà cung cấp (soft-deactivation) |
| `backend/app/api/v1/endpoints/import_notes.py` | Endpoints lập phiếu nhập kho (ACID, idempotency), hủy phiếu có Guard-check |
| `backend/app/api/v1/endpoints/export_notes.py` | Endpoints lập phiếu xuất kho 3 bước, xóa phiếu CONFIRMED, trừ kho Atomic SQL |
| `backend/app/api/v1/endpoints/stock_ledger.py` | Endpoints tra cứu thẻ kho, điều chỉnh kiểm kê thực tế (/adjust) |
| `backend/app/api/v1/endpoints/reports.py` | Endpoints báo cáo NXT, xuất file Excel Thẻ kho và Báo cáo NXT (.xlsx) |
| `backend/app/api/v1/endpoints/ai.py` | 5 Endpoints AI: /monthly-report, /restock-suggestions, /anomalies, /ask, /generate-order |
| `backend/app/models/*.py` | 9 SQLAlchemy Models (users, categories, products, suppliers, import/export notes, stock_ledger) |
| `backend/app/schemas/*.py` | Pydantic v2 validation schemas cho toàn bộ các thực thể và AI |
| `backend/app/services/inventory_service.py` | Core Inventory Service: Transaction ACID, luồng xuất 3 bước, trừ kho Atomic SQL |
| `backend/app/services/ai_service.py` | AI Service: Pipeline SQL loại bỏ 100% giá vốn, Gemini 3.5 Client + Fallback Chain |
| `backend/app/services/ai_cache.py` | AI In-Day Cache: lưu đệm kết quả phân tích AI theo data fingerprint trong ngày |
| `backend/app/services/fallback_service.py` | Heuristic Fallback Engine: thuật toán quy tắc thống kê chạy offline < 50ms |
| `backend/app/ai/prompts/*.txt` | 4 Prompt Templates độc lập (inventory_report, reorder_suggestion, anomaly_detection, generate_order) |
| `backend/tests/test_auth.py` | 12 tests xác thực JWT, hash bcrypt, RBAC 3 vai trò, SlidingWindowRateLimiter |
| `backend/tests/test_master_data.py` | 5 tests CRUD Category, Product, Supplier, upload ảnh và RBAC |
| `backend/tests/test_stock_transactions.py` | 18 tests luồng xuất 3 bước, ACID, chặn tồn âm, Thẻ kho, Idempotency, xóa phiếu |
| `backend/tests/test_ai_service.py` | 31 tests AI pipeline (không lộ giá mua), Fallback Engine, AI Cache, Mock Gemini |
| `backend/tests/test_ai_empty_data.py` | 4 tests kiểm tra an toàn các endpoint AI khi kho hoàn toàn rỗng |

### `frontend/`

| File | Vai trò |
| --- | --- |
| `frontend/index.html` | Entry HTML cho Vite |
| `frontend/package.json` | Node dependencies: react 18, lucide-react, axios; devDeps: vite, tailwindcss |
| `frontend/vite.config.js` | Vite config (React plugin, proxy `/api` → backend) |
| `frontend/src/main.jsx` | React root — mount `<App />` vào `#root` |
| `frontend/src/tokens.css` | Design tokens cho Dark / Light mode |
| `frontend/src/index.css` | Tailwind directives + base styles |
| `frontend/src/App.jsx` | Ứng dụng gốc tích hợp AuthProvider, ToastProvider, ConfirmProvider |
| `frontend/src/api/client.js` | Axios client cấu hình baseURL, JWT interceptor, bắt 401 |
| `frontend/src/context/AuthContext.jsx` | Quản lý phiên JWT, chuyển đổi demo vai trò 1-click (Admin, Thủ kho, Kế toán) |
| `frontend/src/context/ConfirmContext.jsx` | Modal xác nhận thao tác bắt buộc lý do $\ge 5$ ký tự (hủy/xóa phiếu) |
| `frontend/src/context/ToastContext.jsx` | Hệ thống thông báo toast notification đa trạng thái |
| `frontend/src/components/Layout.jsx` | Sidebar + Header hiển thị vai trò, toggle Dark/Light theme, role switcher |
| `frontend/src/components/ProductSelect.jsx` | Component chọn sản phẩm gõ tắt thông minh, hiển thị tồn kho và ảnh |
| `frontend/src/components/Badge.jsx` | Component nhãn trạng thái cảnh báo đa màu |
| `frontend/src/components/Modal.jsx` | Component popup hộp thoại dùng chung |
| `frontend/src/components/Loader.jsx` | Spinner loading chống nhấp nháy UI |
| `frontend/src/components/ErrorBoundary.jsx` | Bắt lỗi crash UI toàn cục |
| `frontend/src/pages/Login.jsx` | Màn hình đăng nhập kèm 3 nút 1-click tài khoản mẫu |
| `frontend/src/pages/Dashboard.jsx` | Bảng điều khiển KPI tồn kho, hàng sắp hết, thao tác nhanh |
| `frontend/src/pages/Products.jsx` | CRUD hàng hóa, tìm kiếm, lọc danh mục & tồn thấp, upload ảnh sản phẩm |
| `frontend/src/pages/Suppliers.jsx` | Quản lý thông tin nhà cung cấp, thêm/sửa đối tác |
| `frontend/src/pages/ImportNotes.jsx` | Lập phiếu nhập kho đa dòng, tự tính tổng tiền, xem chi tiết và hủy phiếu |
| `frontend/src/pages/ExportNotes.jsx` | Lập & điều phối phiếu xuất 3 bước, xóa phiếu CONFIRMED, Defensive UI chống xuất âm |
| `frontend/src/pages/StockLedger.jsx` | Sổ cái thẻ kho chi tiết, lọc giao dịch, xuất file Excel Thẻ kho, kiểm kê thực tế |
| `frontend/src/pages/AIAssistant.jsx` | 4 Tabs: Báo cáo NXT & Xuất Excel, Gợi ý nhập hàng, Biến động bất thường, Copilot Chat |
| `frontend/src/utils/draftStorage.js` | Lưu trữ nháp phiếu vào localStorage |
| `frontend/src/utils/stockEvents.js` | Đồng bộ sự kiện cập nhật số lượng tồn real-time |
| `frontend/Dockerfile` | Dockerfile đóng gói frontend React + Nginx |
| `frontend/nginx.conf` | Cấu hình Nginx reverse proxy cho frontend |

---

## Chưa có — Dự án đã hoàn thành 100%

> 🎉 **Tất cả 44 endpoints API, 70/70 ca test tự động PASS 100% (83% coverage), dữ liệu mẫu 76 sản phẩm / 5 tháng, toàn bộ hồ sơ SDLC 4 mốc (KT1, KT2, KT3, Final), văn bản báo cáo Word (`.docx`) và Slide PowerPoint (`.pptx`) đều đã được hoàn thiện đầy đủ và kiểm thử nghiệm thu 100%.**
