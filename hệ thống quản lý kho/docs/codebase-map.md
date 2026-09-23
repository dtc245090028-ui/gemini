# Bản đồ mã nguồn

> **File này bắt buộc cập nhật mỗi khi thêm, xóa hoặc đổi vai trò một file.**
> Xem `CLAUDE.md §11` — trigger "thêm/xóa/đổi vai trò file bất kỳ" → cập nhật ngay lập tức.

**Cập nhật lần cuối:** 2026-09-23 (Hoàn thành mốc KT3)

---

## Hiện có

### Gốc dự án

| File | Vai trò |
|---|---|
| `de_tai_07.md` | Đề bài gốc của giảng viên — **KHÔNG SỬA** |
| `Prompt.md` | Đặc tả hợp nhất đầy đủ — nguồn sự thật về nghiệp vụ và kỹ thuật |
| `CLAUDE.md` | Hướng dẫn hành vi agent, quy trình làm việc, quy ước toàn dự án |
| `GEMINI.md` | Bộ chỉ dẫn hành vi, ranh giới kiến trúc và quy ước quản lý dự án |
| `README.md` | Nhật ký vận hành phiên làm việc — hướng dẫn mở/đóng phiên cho người dùng |

### `docs/`

| File | Vai trò |
|---|---|
| `docs/codebase-map.md` | File này — bản đồ mã nguồn, cập nhật theo phiên |
| `docs/MASTER-ROADMAP.md` | Bức tranh toàn cảnh 8 giai đoạn — điều hướng sang Buoc-NN.md |
| `docs/architecture.md` | Sơ đồ kiến trúc 3 tầng và luồng dữ liệu nghiệp vụ kho + AI |
| `docs/implementation_plan.md` | Phân tích yêu cầu chi tiết và kế hoạch triển khai ban đầu |
| `docs/plans/TIEN-DO.md` | Nhật ký tiến độ — **nguồn sự thật về trạng thái** |
| `docs/plans/Buoc-01-*.md` đến `Buoc-11-*.md` | 11 file kế hoạch chi tiết từng bước |
| `docs/SDLC/KT1/*.md` | Bộ hồ sơ đặc tả SRS, ERD, AI specs và Wireframes mốc KT1 |
| `docs/SDLC/KT2/*.md` | Bộ hồ sơ API Specs, Transaction Design và AI Evidence mốc KT2 |
| `docs/SDLC/KT3/01_Prompt_Engineering_and_Evaluation.md` | Báo cáo so sánh định lượng các phiên bản Prompt mốc KT3 |
| `docs/SDLC/KT3/02_Test_Plan_and_Results.md` | Kế hoạch và kết quả kiểm thử tự động 30/30 tests mốc KT3 |
| `docs/SDLC/KT3/03_AI_Integration_Architecture.md` | Kiến trúc tích hợp Gemini API và Heuristic Fallback Engine |
| `docs/submissions/KT1/*.md` | Sản phẩm nộp bài chính thức mốc KT1 |

### Gốc dự án (Cấu hình)

| File | Vai trò |
|---|---|
| `.env.example` | Mẫu biến môi trường gốc |
| `.gitignore` | Cấu hình loại trừ file rác, file `.db` SQLite |
| `docker-compose.yml` | File điều phối Docker containers (Backend + Frontend) |

### `backend/`

| File | Vai trò |
|---|---|
| `backend/requirements.txt` | Python dependencies (FastAPI, SQLAlchemy, bcrypt, pyjwt, google-generativeai, pytest) |
| `backend/.env.example` | Mẫu biến môi trường backend |
| `backend/.env` | Cấu hình môi trường backend cục bộ (SQLite) |
| `backend/Dockerfile` | Dockerfile đóng gói backend FastAPI |
| `backend/seed_data.py` | Script nạp 22 SP, 3 users, 3 NCC và lịch sử 60 ngày nhập xuất theo 3 kịch bản cốt lõi |
| `backend/app/main.py` | Điểm vào FastAPI: CORS middleware, exception handler, lifespan seed users |
| `backend/app/__init__.py` | Package marker |
| `backend/app/core/config.py` | Pydantic Settings — đọc `.env`, cấu hình JWT, DB URL, Gemini API Key |
| `backend/app/core/database.py` | SQLAlchemy engine + SessionLocal + listener SQLite PRAGMA foreign_keys=ON |
| `backend/app/core/security.py` | Hàm hash password (bcrypt thuần) và tạo/giải mã JWT (pyjwt HS256) |
| `backend/app/core/seed.py` | Idempotent seed nạp 3 tài khoản mặc định (admin, thukho, ketoan) |
| `backend/app/api/deps.py` | Dependencies xác thực JWT (`get_current_user`) và phân quyền RBAC (`require_roles`) |
| `backend/app/api/v1/api.py` | Router gốc API v1 gom toàn bộ sub-routers |
| `backend/app/api/v1/endpoints/auth.py` | Endpoints đăng nhập (/login, /login-form), thông tin cá nhân (/me), quản lý user |
| `backend/app/api/v1/endpoints/categories.py` | Endpoints CRUD nhóm hàng |
| `backend/app/api/v1/endpoints/products.py` | Endpoints CRUD sản phẩm, tìm kiếm, lọc nhóm hàng, lọc `is_low_stock` |
| `backend/app/api/v1/endpoints/suppliers.py` | Endpoints CRUD nhà cung cấp |
| `backend/app/api/v1/endpoints/import_notes.py` | Endpoints lập phiếu nhập kho, tra cứu danh sách, chi tiết |
| `backend/app/api/v1/endpoints/export_notes.py` | Endpoints lập phiếu xuất kho (chống tồn âm), tra cứu danh sách, chi tiết |
| `backend/app/api/v1/endpoints/stock_ledger.py` | Endpoints tra cứu thẻ kho, điều chỉnh kiểm kê thực tế |
| `backend/app/api/v1/endpoints/reports.py` | Endpoints báo cáo nhập xuất tồn kho theo kỳ |
| `backend/app/api/v1/endpoints/ai.py` | Endpoints AI: /monthly-report, /restock-suggestions, /anomalies |
| `backend/app/models/*.py` | 9 SQLAlchemy Models (users, categories, products, suppliers, import/export notes, stock_ledger) |
| `backend/app/schemas/*.py` | Pydantic v2 validation schemas (user, category, product, supplier, import/export, report, ai) |
| `backend/app/services/inventory_service.py` | Core Inventory Service: Transaction ACID nhập/xuất, chống tồn âm, thẻ kho |
| `backend/app/services/ai_service.py` | AI Service: Pipeline SQL tiền xử lý (loại bỏ giá mua), Gemini API Client |
| `backend/app/services/fallback_service.py` | Heuristic Fallback Engine: thuật toán quy tắc thống kê chạy offline < 50ms |
| `backend/app/ai/prompts/*.txt` | 3 Prompt Templates độc lập (inventory_report, reorder_suggestion, anomaly_detection) |
| `backend/tests/test_foundation.py` | Test endpoint /health, tạo bảng CSDL và CheckConstraint chống tồn âm |
| `backend/tests/test_auth.py` | Test authentication JWT, hash bcrypt, RBAC 3 vai trò và SQLite FK |
| `backend/tests/test_master_data.py` | Test CRUD Category, Product, Supplier và phân quyền RBAC |
| `backend/tests/test_stock_transactions.py` | Test ACID Nhập/Xuất kho, chống tồn âm, state machine hủy phiếu, báo cáo tồn |
| `backend/tests/test_ai.py` | Test pipeline bảo mật (không lộ giá mua), Fallback Engine, Mock Gemini API, RBAC |

### `frontend/`

| File | Vai trò |
|---|---|
| `frontend/index.html` | Entry HTML cho Vite |
| `frontend/package.json` | Node dependencies: react 18, lucide-react, axios; devDeps: vite, tailwindcss |
| `frontend/vite.config.js` | Vite config (React plugin, proxy `/api` → backend) |
| `frontend/postcss.config.js` | PostCSS config cho Tailwind |
| `frontend/tailwind.config.js` | Tailwind config |
| `frontend/src/main.jsx` | React root — mount `<App />` vào `#root` |
| `frontend/src/index.css` | Tailwind directives + base styles |
| `frontend/src/App.jsx` | Ứng dụng gốc tích hợp AuthProvider, điều hướng tab và kết nối 7 phân hệ |
| `frontend/src/api/client.js` | Axios client cấu hình baseURL, JWT interceptor, bắt 401 và đóng gói API services |
| `frontend/src/context/AuthContext.jsx` | Quản lý phiên JWT, lưu localStorage, chuyển đổi demo vai trò 1-click (Admin, Thủ kho, Kế toán) |
| `frontend/src/components/Layout.jsx` | Sidebar thương hiệu SmartKho AI + Header hiển thị vai trò và bộ nút chuyển vai trò |
| `frontend/src/components/Badge.jsx` | Component nhãn trạng thái cảnh báo đa màu |
| `frontend/src/components/Modal.jsx` | Component popup hộp thoại dùng chung |
| `frontend/src/pages/Login.jsx` | Màn hình đăng nhập kèm 3 nút 1-click tài khoản mẫu |
| `frontend/src/pages/Dashboard.jsx` | Bảng điều khiển KPI tồn kho, hàng sắp hết, thao tác nhanh và giới thiệu AI |
| `frontend/src/pages/Products.jsx` | CRUD hàng hóa, tìm kiếm tức thời, lọc nhóm hàng & tồn thấp, chuyển nhanh sang thẻ kho |
| `frontend/src/pages/Suppliers.jsx` | Quản lý thông tin nhà cung cấp, thêm/sửa đối tác |
| `frontend/src/pages/ImportNotes.jsx` | Lập phiếu nhập kho đa dòng, tra giá tự động, tính tổng tiền, xem chi tiết và hủy phiếu |
| `frontend/src/pages/ExportNotes.jsx` | Lập phiếu xuất kho kèm Defensive UI chống xuất âm thời gian thực, hủy phiếu |
| `frontend/src/pages/StockLedger.jsx` | Sổ cái thẻ kho chi tiết, lọc giao dịch, modal điều chỉnh kiểm kê thực tế |
| `frontend/src/pages/AIAssistant.jsx` | 3 bài toán AI: Báo cáo tháng, Gợi ý nhập hàng, Biến động bất thường (kèm cờ Fallback Engine) |
| `frontend/Dockerfile` | Dockerfile đóng gói frontend React + Nginx |
| `frontend/nginx.conf` | Cấu hình Nginx reverse proxy cho frontend |

---

## Chưa có — sẽ thêm ở Giai đoạn tiếp theo

| File | Sẽ tạo ở Giai đoạn |
|---|:---:|
| `docs/SDLC/final/01_Final_Technical_Report.md` | 7 (Cuối kỳ) |
| `docs/SDLC/final/02_User_Guide_and_Demo_Script.md` | 7 (Cuối kỳ) |
| `docs/SDLC/final/03_Presentation_Slides.md` | 7 (Cuối kỳ) |
| `README.md` *(nâng cấp thành hướng dẫn cài đặt 1-click)* | 7 (Cuối kỳ) |
| `docs/SDLC/final/02_User_Guide_and_Demo_Script.md` | 7 (Cuối kỳ) |
| `docs/SDLC/final/03_Presentation_Slides.md` | 7 (Cuối kỳ) |
| `README.md` *(nâng cấp thành hướng dẫn cài đặt 1-click)* | 7 (Cuối kỳ) |
