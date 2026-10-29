# HƯỚNG DẪN VẬN HÀNH CƠ SỞ DỮ LIỆU SMARTKHO TRÊN DOCKER NAMED VOLUME

Tài liệu này hướng dẫn cách kiểm tra toàn vẹn, đo tải, sao lưu online và phục hồi cơ sở dữ liệu SQLite sau khi chuyển sang Docker Named Volume `warehouse_data` (ext4).

---

## 1. Vị trí CSDL và Biến Môi Trường

* **CSDL trong Named Volume:** `/var/lib/warehouse/warehouse.db` (Filesystem: `ext4` native trên Linux container, loại bỏ hoàn toàn độ trễ ảo hóa mạng 9p).
* **Biến môi trường:** `DATABASE_URL=sqlite:////var/lib/warehouse/warehouse.db`
* **Docker Compose:** Đã ánh xạ volume `warehouse_data:/var/lib/warehouse`.

---

## 2. Kiểm tra 5 Bất biến Toàn vẹn Dữ liệu (`check_invariants`)

Script có cơ chế tự động phát hiện môi trường:
* **Từ Windows Host:**
  ```powershell
  python backend/tests/performance/check_invariants.py
  ```
  *(Script tự động ủy quyền thực thi vào container `warehouse_backend` để tránh xung đột khóa WAL).*
* **Trực tiếp trong container:**
  ```bash
  docker exec warehouse_backend python /app/tests/performance/check_invariants.py
  ```

---

## 3. Chạy Kịch bản Đo Tải & Dọn dẹp Demo

* **Chạy kịch bản đo tải (Stress 100 RPS):**
  ```powershell
  python backend/tests/performance/demo_run.py --profile stress100
  ```
* **Dọn dẹp sạch dữ liệu demo sau khi quan sát:**
  ```powershell
  python backend/tests/performance/demo_cleanup.py --yes
  ```
  *(Tự động kiểm tra snapshot 6 bảng trọng yếu, đảm bảo đối chiếu lệch đúng 0 dòng).*

---

## 4. Sao lưu CSDL Online An toàn (Không khóa hệ thống)

> [!IMPORTANT]
> **TUYỆT ĐỐI KHÔNG** dùng lệnh copy file trực tiếp (`cp warehouse.db ...`) khi CSDL đang mở ở chế độ WAL, vì sẽ bỏ sót dữ liệu trong `-wal` hoặc gây hỏng file (file corruption).
> Hãy sử dụng công cụ Online Backup API được xây dựng sẵn:

* **Tạo bản sao lưu Online:**
  ```bash
  docker exec warehouse_backend python -m app.core.backup_db backup --file /var/lib/warehouse/backups/warehouse_manual_backup.db
  ```
* **Sao chép file sao lưu ra máy host Windows:**
  ```powershell
  docker cp warehouse_backend:/var/lib/warehouse/backups/warehouse_manual_backup.db ./backend/backups/warehouse_manual_backup.db
  ```
* **Kiểm tra trạng thái & tính toàn vẹn CSDL:**
  ```bash
  docker exec warehouse_backend python -m app.core.backup_db status
  ```

---

## 5. Phục hồi CSDL từ bản sao lưu

* **Phục hồi CSDL từ file backup đã lưu:**
  ```bash
  docker exec warehouse_backend python -m app.core.backup_db restore --file /var/lib/warehouse/backups/warehouse_manual_backup.db
  ```
* **Chạy kiểm tra bất biến ngay sau phục hồi:**
  ```powershell
  python backend/tests/performance/check_invariants.py
  ```
