"""Group C Test Runner: Mở rộng kiểm thử tải đồng thời sang Module Nhập kho (POST /import-notes/).
So sánh trực tiếp với kết quả Bậc 5 của POST /export-notes/:
- Số lượng request, RPS, tỷ lệ lỗi 409 (đụng độ mã) và 500 (lỗi khóa CSDL).
- Phân vị độ trễ p50, p95, p99.
- Bất biến CSDL trước và sau test (check_invariants).
"""

import sys
import os
import time
import subprocess
import shutil
import csv
import json
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
LOCUST_FILE = os.path.join(os.path.dirname(__file__), "locustfile_import.py")
DB_FILE = os.path.join(PROJECT_ROOT, "warehouse.db")
CHECK_INVARIANTS = os.path.join(os.path.dirname(__file__), "check_invariants.py")

USERS = 20
SPAWN_RATE = 20.0
DURATION = 60
TAG = "group_c_import_spike"


def create_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(PROJECT_ROOT, "backups", f"backup_before_group_c_{ts}")
    os.makedirs(backup_dir, exist_ok=True)
    res = subprocess.run(
        ["docker", "exec", "warehouse_backend", "python", "-c",
         f"import sqlite3; s=sqlite3.connect('/app/warehouse.db'); d=sqlite3.connect('/app/backups/backup_before_group_c_{ts}/warehouse.db'); s.backup(d); d.close(); s.close()"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    print(f"[*] Đã tạo snapshot CSDL trước Nhóm C: {backup_dir} (mã: {res.returncode})")
    return backup_dir


def run_invariants(label):
    print(f"\n--- KIỂM TRA BẤT BIẾN CSDL ({label}) ---")
    res = subprocess.run(
        ["docker", "exec", "warehouse_backend", "python", "/app/tests/performance/check_invariants.py", "/app/warehouse.db"],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(f"[ERR] {res.stderr.strip()}")


def run_group_c():
    print("======================================================================")
    print(" NHÓM C: KIỂM THỬ TẢI ĐỒNG THỜI MODULE NHẬP KHO (POST /import-notes/)")
    print(f" Cấu hình: {USERS} Virtual Users | Spawn: {SPAWN_RATE}/s | Duration: {DURATION}s")
    print(f" Kịch bản: 80% tạo phiếu nhập liên tục (tăng tồn kho), 20% replay idempotency")
    print("======================================================================\n")

    create_backup()
    run_invariants("TRƯỚC KHI BẮN TẢI NHÓM C")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_prefix = os.path.join(RESULTS_DIR, f"tier_{TAG}")

    cmd = [
        "locust",
        "-f", LOCUST_FILE,
        "ImportSpikeUser",
        "--headless",
        "-u", str(USERS),
        "-r", str(SPAWN_RATE),
        "-t", f"{DURATION}s",
        "--host", "http://127.0.0.1:8000",
        "--csv", csv_prefix,
        "--csv-full-history",
        "--only-summary",
    ]

    print(f"[*] Bắt đầu bắn tải 60s...")
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.run(cmd, text=True, env=env)
    print(f"[*] Bắn tải hoàn tất!")

    run_invariants("SAU KHI BẮN TẢI NHÓM C")

    # Đọc kết quả
    stats_file = f"{csv_prefix}_stats.csv"
    failures_file = f"{csv_prefix}_failures.csv"

    print("\n======================================================================")
    print(" KẾT QUẢ ĐO LƯỜNG CHI TIẾT NHÓM C")
    print("======================================================================")

    if os.path.exists(stats_file):
        with open(stats_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("Name")
                req_count = row.get("Request Count")
                fail_count = row.get("Failure Count")
                rps = row.get("Requests/s")
                avg = row.get("Average Response Time")
                min_lat = row.get("Min Response Time")
                max_lat = row.get("Max Response Time")
                p50 = row.get("50%")
                p95 = row.get("95%")
                p99 = row.get("99%")
                print(f"Endpoint: {name}")
                print(f"  - Requests: {req_count} | Failures: {fail_count} | RPS: {float(rps or 0):.2f}")
                print(f"  - Latency (ms): Min={float(min_lat or 0):.1f} | Avg={float(avg or 0):.1f} | Max={float(max_lat or 0):.1f}")
                print(f"  - Percentiles: p50={p50}ms | p95={p95}ms | p99={p99}ms")
                print("-" * 50)

    if os.path.exists(failures_file):
        print("\n--- CHI TIẾT LỖI GẶP PHẢI ---")
        with open(failures_file, "r", encoding="utf-8") as f:
            print(f.read().strip())


if __name__ == "__main__":
    run_group_c()
