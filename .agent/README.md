# Bộ Quy Chuẩn Tác Nhân AI (.agent) — PharmaCare AI

Bộ quy tắc và quy trình chuẩn hóa dành cho các tác nhân AI khi làm việc trên dự án PharmaCare AI (Hệ thống Quản lý Nhà thuốc Tích hợp AI).

## 1. Cấu Trúc Thư Mục
```text
.agent/
├── rules/
│   └── 00-core.md          # Bộ quy tắc cốt lõi: ngôn ngữ, an toàn dữ liệu, secret, commit
├── workflows/
│   ├── architect.md        # Lập kế hoạch kiến trúc, thiết kế phương án trước khi viết code
│   ├── dev.md              # Lập trình tính năng theo chuẩn FastAPI, SQLAlchemy, SPA
│   ├── tester.md           # Thiết kế và chạy test tự động, tìm edge case, KHÔNG sửa logic
│   ├── debugger.md         # Quy trình tái hiện lỗi -> tìm nguyên nhân gốc -> sửa triệt để
│   └── audit.md            # Chế độ CHỈ ĐỌC, rà soát an toàn & tuân thủ, xuất báo cáo
└── README.md               # Bản đồ hướng dẫn và cách kích hoạt từng chế độ
```

## 2. Cách Sử Dụng Từng Mode Làm Việc

| Mode | Mục đích | Cách kích hoạt / Từ khóa | Thư mục tác động |
| :--- | :--- | :--- | :--- |
| **Core** | Quy tắc nền tảng áp dụng mọi lúc | Mặc định luôn luôn kích hoạt | Toàn bộ dự án |
| **Architect** | Thiết kế giải pháp, vẽ sơ đồ, chọn phương án | *"Thiết kế...", "Lập kế hoạch...", "Thêm module mới"* | Chỉ xuất đề xuất & kế hoạch |
| **Dev** | Triển khai mã nguồn API và giao diện SPA | *"Làm S-xx", "Code tính năng...", "Tạo API..."* | `routers/`, `services/`, `database.py`, `schemas.py`, `static/` |
| **Tester** | Viết test case, tìm kiếm lỗi biên, đo kiểm | *"Kiểm thử S-xx", "Viết test...", "Test FEFO"* | `tests/`, `docs/testing/` |
| **Debugger** | Tái hiện lỗi và vá lỗi tận gốc | *"Sửa bug...", "Fix lỗi...", "API 500...", "Test fail"* | `tests/`, mã nguồn phát sinh lỗi |
| **Audit** | Kiểm toán an ninh, an toàn y tế và code | *"Audit code", "Rà soát bảo mật", "Kiểm tra GPP"* | **CHỈ ĐỌC**, chỉ ghi vào `docs/Audit/` |

## 3. Các Nguyên Tắc Bất Di Bất Dịch
1. **Bảo mật tuyệt đối:** Không commit API key, secret, mật khẩu (repo public).
2. **Bảo vệ CSDL:** Bắt buộc chạy `python scripts/backup_data.py backup` trước khi đụng vào schema trong `database.py`.
3. **Ưu tiên giao diện:** `static/` là giao diện chính (SPA Vanilla JS/HTML/CSS); `frontend/` (React) là phụ, không sửa nếu không được yêu cầu.
4. **Kiểm thử chuẩn:** Chạy kiểm thử bằng lệnh `pytest -v` hoặc `pytest`.
5. **Kế hoạch thực tế:** Tra cứu yêu cầu tính năng tại `docs/plans/implementation_plan.md` (kết hợp `docs/specs/yeu_cau.md`).
