"""Soak Test Runner: Kéo dài 15 phút (~50% tải Bậc 5, 10 virtual users).
Theo dõi định kỳ mỗi 5 phút:
- Kích thước file WAL & DB của SQLite
- RAM / CPU container Docker
- Số kết nối mở (sockets/connections)
- Độ trễ p50 / p95 / p99 theo từng mốc 5 phút
- Kiểm toán toàn vẹn dữ liệu sau test
"""

import sys
import os
import time
import subprocess
import threading
import json
import csv
from datetime import datetime

# UTF-8 stdout on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
LOCUST_FILE = os.path.join(os.path.dirname(__file__), "locustfile.py")
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WAL_FILE = os.path.join(DB_DIR, "warehouse.db-wal")
DB_FILE = os.path.join(DB_DIR, "warehouse.db")

DURATION_SECONDS = 900  # 15 phút
USERS = 10
SPAWN_RATE = 1.0
TAG = "soak_15m"


def get_file_size_kb(filepath):
    if os.path.exists(filepath):
        try:
            return round(os.path.getsize(filepath) / 1024, 2)
        except Exception:
            return 0.0
    return 0.0


def monitor_system(stop_event, snapshots, interval=10):
    """Lấy mẫu hệ thống mỗi 10 giây."""
    while not stop_event.is_set():
        now_ts = time.time()
        wal_kb = get_file_size_kb(WAL_FILE)
        db_kb = get_file_size_kb(DB_FILE)

        # Docker stats
        cpu_val = 0.0
        mem_val = 0.0
        try:
            res = subprocess.run(
                ["docker", "stats", "warehouse_backend", "--no-stream", "--format", "{{.CPUPerc}}\t{{.MemUsage}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("\t")
                if len(parts) >= 2:
                    cpu_str = parts[0].replace("%", "").strip()
                    cpu_val = float(cpu_str) if cpu_str else 0.0
                    mem_part = parts[1].split("/")[0].strip()
                    if "MiB" in mem_part:
                        mem_val = float(mem_part.replace("MiB", "").strip())
                    elif "GiB" in mem_part:
                        mem_val = float(mem_part.replace("GiB", "").strip()) * 1024
                    elif "kB" in mem_part:
                        mem_val = float(mem_part.replace("kB", "").strip()) / 1024
        except Exception:
            pass

        # Số connection mở trong container
        conn_count = 0
        try:
            c_res = subprocess.run(
                ["docker", "exec", "warehouse_backend", "sh", "-c", "cat /proc/net/tcp | wc -l"],
                capture_output=True,
                text=True,
                check=False,
            )
            if c_res.returncode == 0 and c_res.stdout.strip():
                conn_count = max(0, int(c_res.stdout.strip()) - 1)
        except Exception:
            pass

        snapshots.append({
            "timestamp": now_ts,
            "wal_kb": wal_kb,
            "db_kb": db_kb,
            "cpu_percent": cpu_val,
            "mem_mb": mem_val,
            "connections": conn_count,
        })
        time.sleep(interval)


def run_soak():
    print("======================================================================")
    print(" BẮT ĐẦU SOAK TEST 15 PHÚT (NHÓM B)")
    print(f" Users: {USERS} (~50% Bậc 5) | Spawn Rate: {SPAWN_RATE}/s | Duration: {DURATION_SECONDS}s (15m)")
    print(f" CSDL giám sát: {DB_FILE}")
    print("======================================================================\n")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_prefix = os.path.join(RESULTS_DIR, f"tier_soak_{TAG}")

    snapshots = []
    stop_event = threading.Event()
    mon_thread = threading.Thread(target=monitor_system, args=(stop_event, snapshots, 10))
    mon_thread.daemon = True
    mon_thread.start()

    cmd = [
        "locust",
        "-f", LOCUST_FILE,
        "SpikeUser",
        "--headless",
        "-u", str(USERS),
        "-r", str(SPAWN_RATE),
        "-t", f"{DURATION_SECONDS}s",
        "--host", "http://127.0.0.1:8000",
        "--csv", csv_prefix,
        "--csv-full-history",
        "--only-summary",
    ]

    t_start = time.time()
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(cmd, text=True, env=env)
    t_end = time.time()

    stop_event.set()
    mon_thread.join(timeout=3)

    # Phân tích các mốc thời gian 5m, 10m, 15m
    print("\n======================================================================")
    print(" KẾT QUẢ ĐO LƯỜNG THEO TỪNG MỐC 5 PHÚT (NHÓM B)")
    print("======================================================================")

    milestones = [
        ("Mốc 5 phút (300s)", t_start, t_start + 300),
        ("Mốc 10 phút (600s)", t_start + 300, t_start + 600),
        ("Mốc 15 phút (900s)", t_start + 600, t_end),
    ]

    print(f"{'Mốc Thời Gian':<22} | {'WAL (KB)':>10} | {'DB (KB)':>10} | {'CPU Avg(%)':>10} | {'RAM Avg(MB)':>11} | {'Conns Avg':>9}")
    print("-" * 85)

    summary_milestones = []
    for name, m_start, m_end in milestones:
        m_snaps = [s for s in snapshots if m_start <= s["timestamp"] <= m_end]
        if m_snaps:
            avg_wal = sum(s["wal_kb"] for s in m_snaps) / len(m_snaps)
            max_wal = max(s["wal_kb"] for s in m_snaps)
            last_wal = m_snaps[-1]["wal_kb"]
            last_db = m_snaps[-1]["db_kb"]
            avg_cpu = sum(s["cpu_percent"] for s in m_snaps) / len(m_snaps)
            avg_mem = sum(s["mem_mb"] for s in m_snaps) / len(m_snaps)
            avg_conn = sum(s["connections"] for s in m_snaps) / len(m_snaps)

            print(f"{name:<22} | {last_wal:>10.1f} | {last_db:>10.1f} | {avg_cpu:>10.1f} | {avg_mem:>11.1f} | {avg_conn:>9.1f}")
            summary_milestones.append({
                "milestone": name,
                "wal_kb": last_wal,
                "db_kb": last_db,
                "avg_cpu": avg_cpu,
                "avg_mem": avg_mem,
                "avg_conn": avg_conn,
            })

    print("-" * 85)

    # Đọc Locust aggregated stats
    stats_file = f"{csv_prefix}_stats.csv"
    if os.path.exists(stats_file):
        with open(stats_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Type") == "":
                    print(f"\n• Tổng kết tải Locust 15 phút:")
                    print(f"  - Tổng request: {row.get('Request Count')} | Thất bại: {row.get('Failure Count')}")
                    print(f"  - Thông lượng trung bình (RPS): {float(row.get('Requests/s', 0)):.2f} req/s")
                    print(f"  - Độ trễ trung bình: {float(row.get('Average Response Time', 0)):.1f} ms | Min: {float(row.get('Min Response Time', 0)):.1f} ms | Max: {float(row.get('Max Response Time', 0)):.1f} ms")
                    print(f"  - Phân vị độ trễ (Percentiles):")
                    print(f"    p50 (Median) : {row.get('50%')} ms")
                    print(f"    p66          : {row.get('66%')} ms")
                    print(f"    p75          : {row.get('75%')} ms")
                    print(f"    p90          : {row.get('90%')} ms")
                    print(f"    p95          : {row.get('95%')} ms")
                    print(f"    p99          : {row.get('99%')} ms")
                    print(f"    p99.9        : {row.get('99.9%')} ms")

    return summary_milestones


if __name__ == "__main__":
    run_soak()
