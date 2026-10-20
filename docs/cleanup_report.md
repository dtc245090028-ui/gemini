# Báo cáo Kiểm kê và Dọn dẹp File (CLEANUP REPORT)

Thời điểm thực hiện: 2026-10-21T01:27:00+07:00
Nhánh Git: `fix/concurrency-cleanup`

## 1. Bảng kiểm kê tổng thể các file mới / phát sinh

| Đường dẫn | Trạng thái Git | Nguồn gốc tạo ra | Còn được tham chiếu bởi | Nhóm phân loại |
|---|---|---|---|---|
| `backend/tests/performance/check_invariants.py` | Tracked (Commit PREP) | Tạo ở bước PREP | Cổng nghiệm thu tự động, RUN_STATE | **Giữ** |
| `backend/tests/performance/locustfile.py` | Untracked | Kịch bản kiểm thử tải Locust Tiers 0-5 | `run_tier.py`, `docker-compose` | **Giữ** |
| `backend/tests/performance/run_tier.py` | Untracked | Script điều phối chạy tải Locust theo Bậc | Bộ kiểm thử hiệu năng | **Giữ** |
| `backend/tests/performance/setup_perf_data.py` | Untracked | Sinh dữ liệu mẫu SKU-PERF-* | `run_tier.py`, test suite | **Giữ** |
| `backend/tests/performance/teardown_perf_data.py` | Untracked | Dọn dẹp dữ liệu SKU-PERF-* | `run_tier.py` | **Giữ** |
| `backend/tests/performance/run_diagnostics.py` | Untracked | Script đo đạc thông số hệ thống, CPU | Chẩn đoán Tiers 2-4 | **Giữ** |
| `backend/tests/performance/audit_b3.py` | Untracked | Kiểm tra kết quả Bậc 3 | Thẩm tra dữ liệu Bậc 3 | **Giữ** |
| `backend/tests/performance/audit_b4.py` | Untracked | Kiểm tra kết quả Bậc 4 | Thẩm tra dữ liệu Bậc 4 | **Giữ** |
| `backend/tests/performance/verify_b3.py` | Untracked | Đo đạc đối soát Bậc 3 | Thẩm tra dữ liệu | **Giữ** |
| `backend/tests/performance/verify_fix_item_a.py` | Untracked | Đo lường thực nghiệm Hướng a Item A | RUN_STATE (mục A) | **Giữ** |
| `backend/tests/performance/verify_concurrent_ship_service.py` | Untracked | Đo 30 luồng ship đồng thời trên service | Cổng nghiệm thu Invariants | **Giữ** |
| `backend/tests/performance/verify_fix_item_b.py` | Untracked | Benchmark so sánh Retry & Backoff | RUN_STATE (mục B) | **Giữ** |
| `backend/tests/performance/verify_concurrent_create_service.py` | Untracked | Đo 20 luồng create đồng thời trên service | Cổng nghiệm thu Item B | **Giữ** |
| `backend/tests/performance/verify_fix_item_c.py` | Untracked | Benchmark SQLite PRAGMA lock | RUN_STATE (mục C) | **Giữ** |
| `frontend/src/utils/stockEvents.js` | Untracked | Module phát/lắng nghe sự kiện cập nhật kho giao diện | Frontend pages | **Giữ** |
| `backend/seed_data.py.bak` | Untracked | File backup tạm thời của `seed_data.py` | Không | **Có thể chuyển** |
| `backend/tests/performance/results/baseline_check.db-shm` | Untracked | Tệp SQLite bộ nhớ chia sẻ tạm | Không | **Có thể chuyển** |
| `backend/tests/performance/results/baseline_check.db-wal` | Untracked | Tệp SQLite write-ahead log tạm | Không | **Có thể chuyển** |
| `backend/tests/performance/results/test_code_gen.db-shm` | Untracked | Tệp SQLite bộ nhớ chia sẻ tạm | Không | **Có thể chuyển** |
| `backend/tests/performance/results/test_code_gen.db-wal` | Untracked | Tệp SQLite write-ahead log tạm | Không | **Có thể chuyển** |
| `backend/tests/performance/results/test_create_service.db-shm` | Untracked | Tệp SQLite bộ nhớ chia sẻ tạm | Không | **Có thể chuyển** |
| `backend/tests/performance/results/test_create_service.db-wal` | Untracked | Tệp SQLite write-ahead log tạm | Không | **Có thể chuyển** |
| `backend/tests/performance/results/test_service_ship.db-shm` | Untracked | Tệp SQLite bộ nhớ chia sẻ tạm | Không | **Có thể chuyển** |
| `backend/tests/performance/results/test_service_ship.db-wal` | Untracked | Tệp SQLite write-ahead log tạm | Không | **Có thể chuyển** |
| `backend/backups/.../warehouse.db-shm` | Untracked | Tệp shm của thư mục backup | Không | **Có thể chuyển** |
| `backend/backups/.../warehouse.db-wal` | Untracked | Tệp wal của thư mục backup | Không | **Có thể chuyển** |
| `backend/tests/performance/results/*.csv` | Untracked | Dữ liệu đo Locust gốc Bậc 0-4 (20 files) | Báo cáo thẩm tra & đối soát | **Cần bạn quyết** |
| `backend/tests/performance/results/*.json` | Untracked | Báo cáo tóm tắt Locust Bậc 0-4 (5 files) | Báo cáo thẩm tra & đối soát | **Cần bạn quyết** |
| `backend/warehouse.db-shm` | Untracked | Runtime SQLite SHM của CSDL chính | Uvicorn / Container Backend | **Cần bạn quyết** (Không động vào) |
| `backend/warehouse.db-wal` | Untracked | Runtime SQLite WAL của CSDL chính | Uvicorn / Container Backend | **Cần bạn quyết** (Không động vào) |
| Các file tracked modified (`CLAUDE.md`, frontend, schemas) | Tracked modified | Thay đổi từ các phiên làm việc trước | Dự án | **Cần bạn quyết** (Không gỡ/sửa) |

---

## 2. Kế hoạch xử lý
- **Pha 2**: Chuyển các file thuộc nhóm **"Có thể chuyển"** vào thư mục `_quarantine/` theo đúng cấu trúc thư mục phân cấp.
- **Pha 3**: Cập nhật `.gitignore` với các quy tắc rõ ràng:
  - Bỏ qua thư mục kiểm dịch `_quarantine/`.
  - Bỏ qua các tệp tạm SQLite (`*.db-wal`, `*.db-shm`, `*.db-journal`).
  - Bỏ qua các tệp backup (`*.bak`).
  - Bỏ qua thư mục kết quả đo tải `backend/tests/performance/results/*.csv`, `*.json`.
