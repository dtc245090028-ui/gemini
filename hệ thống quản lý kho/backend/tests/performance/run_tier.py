"""Runner điều phối từng bậc kiểm thử hiệu năng với Locust và thu thập Docker stats."""

import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time

# Đảm bảo in UTF-8 không bị lỗi trên Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
LOCUST_FILE = os.path.join(os.path.dirname(__file__), "locustfile.py")


def monitor_docker_stats(stop_event, stats_list, container_name="warehouse_backend", interval=2):
    """Lấy mẫu CPU và RAM của Docker container định kỳ trong lúc test chạy."""
    while not stop_event.is_set():
        try:
            res = subprocess.run(
                ["docker", "stats", container_name, "--no-stream", "--format", "{{.CPUPerc}}\t{{.MemUsage}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("\t")
                if len(parts) >= 2:
                    cpu_str = parts[0].replace("%", "").strip()
                    mem_part = parts[1].split("/")[0].strip()
                    # Chuyển đổi mem sang MB nếu cần
                    mem_val = 0.0
                    if "MiB" in mem_part:
                        mem_val = float(mem_part.replace("MiB", "").strip())
                    elif "GiB" in mem_part:
                        mem_val = float(mem_part.replace("GiB", "").strip()) * 1024
                    elif "kB" in mem_part:
                        mem_val = float(mem_part.replace("kB", "").strip()) / 1024

                    stats_list.append({
                        "timestamp": time.time(),
                        "cpu_percent": float(cpu_str) if cpu_str else 0.0,
                        "mem_mb": mem_val,
                        "raw_mem": mem_part,
                    })
        except Exception:
            pass
        time.sleep(interval)


def run_tier(tier: int, users: int, spawn_rate: float, duration: str, tag: str, user_classes: str = "", host: str = "http://127.0.0.1:8000"):
    print(f"\n=======================================================")
    print(f" BẮT ĐẦU THỰC THI BẬC {tier} [{tag.upper()}]")
    print(f" Users: {users} | Spawn rate: {spawn_rate}/s | Duration: {duration}")
    if user_classes:
        print(f" User Classes: {user_classes}")
    print(f" Target Host: {host}")
    print(f"=======================================================\n")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_prefix = os.path.join(RESULTS_DIR, f"tier_{tier}_{tag}")

    docker_stats = []
    stop_event = threading.Event()
    mon_thread = threading.Thread(target=monitor_docker_stats, args=(stop_event, docker_stats))
    mon_thread.daemon = True
    mon_thread.start()

    cmd = [
        "locust",
        "-f", LOCUST_FILE,
        "--headless",
        "-u", str(users),
        "-r", str(spawn_rate),
        "-t", duration,
        "--host", host,
        "--csv", csv_prefix,
        "--only-summary",
    ]
    if user_classes:
        cmd.extend(user_classes.strip().split())

    start_time = time.time()
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(cmd, text=True, env=env)
    end_time = time.time()

    stop_event.set()
    mon_thread.join(timeout=3)

    # Đọc kết quả stats từ CSV
    stats_file = f"{csv_prefix}_stats.csv"
    failures_file = f"{csv_prefix}_failures.csv"

    aggregated_row = None
    endpoint_rows = []

    if os.path.exists(stats_file):
        with open(stats_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Type") == "":
                    # Dòng tổng hợp
                    aggregated_row = row
                else:
                    endpoint_rows.append(row)

    # Đọc danh sách failure nếu có
    failures = []
    if os.path.exists(failures_file):
        with open(failures_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                failures.append(row)

    # Tính toán CPU / RAM stats
    max_cpu = max([s["cpu_percent"] for s in docker_stats]) if docker_stats else 0.0
    avg_cpu = sum([s["cpu_percent"] for s in docker_stats]) / len(docker_stats) if docker_stats else 0.0
    max_mem = max([s["mem_mb"] for s in docker_stats]) if docker_stats else 0.0
    avg_mem = sum([s["mem_mb"] for s in docker_stats]) / len(docker_stats) if docker_stats else 0.0

    print("\n" + "=" * 70)
    print(f" KẾT QUẢ TỔNG HỢP BẬC {tier} [{tag.upper()}]")
    print("=" * 70)

    if aggregated_row:
        total_reqs = int(aggregated_row.get("Request Count", 0))
        fail_count = int(aggregated_row.get("Failure Count", 0))
        fail_pct = (fail_count / total_reqs * 100) if total_reqs > 0 else 0.0
        avg_rt = float(aggregated_row.get("Average Response Time", 0))
        min_rt = float(aggregated_row.get("Min Response Time", 0))
        max_rt = float(aggregated_row.get("Max Response Time", 0))
        median_rt = float(aggregated_row.get("Median Response Time", 0))
        rps = float(aggregated_row.get("Requests/s", 0))

        print(f"• Tổng số yêu cầu (Total Requests): {total_reqs}")
        print(f"• Số yêu cầu thất bại (Failures): {fail_count} ({fail_pct:.2f}%)")
        print(f"• Thông lượng trung bình (RPS): {rps:.2f} req/s")
        print(f"• Độ trễ trung bình (Avg Latency): {avg_rt:.2f} ms")
        print(f"• Độ trễ trung vị (Median / p50): {median_rt:.2f} ms")
        print(f"• Độ trễ nhỏ nhất / lớn nhất (Min / Max): {min_rt:.2f} ms / {max_rt:.2f} ms")
        print(f"• Tài nguyên Container Backend: Max CPU: {max_cpu:.2f}%, Max RAM: {max_mem:.1f} MB (Avg: {avg_cpu:.1f}% CPU, {avg_mem:.1f} MB RAM)")
    else:
        print("[CẢNH BÁO] Không đọc được aggregated stats từ file CSV.")

    print("\n Chi tiết theo từng Endpoint:")
    print("-" * 90)
    print(f"{'Method/Endpoint':<50} | {'Reqs':>6} | {'Fails':>5} | {'Avg(ms)':>8} | {'p50(ms)':>8} | {'RPS':>6}")
    print("-" * 90)
    for ep in endpoint_rows:
        name = f"{ep.get('Type', '')} {ep.get('Name', '')}"
        print(f"{name:<50} | {ep.get('Request Count', ''):>6} | {ep.get('Failure Count', ''):>5} | {float(ep.get('Average Response Time', 0)):>8.1f} | {float(ep.get('Median Response Time', 0)):>8.1f} | {float(ep.get('Requests/s', 0)):>6.2f}")
    print("-" * 90)

    if failures:
        print(f"\n[DANH SÁCH LỖI GHI NHẬN ({len(failures)} lỗi)]:")
        for f_item in failures:
            print(f"  - {f_item.get('Method')} {f_item.get('Name')}: {f_item.get('Error')} ({f_item.get('Occurrences')} lần)")
    else:
        print("\n [ĐÁNH GIÁ]: 100% Request thành công (Không có lỗi nào).")

    # Lưu kết quả tổng hợp JSON cho bậc này
    summary_data = {
        "tier": tier,
        "tag": tag,
        "users": users,
        "spawn_rate": spawn_rate,
        "duration": duration,
        "aggregated": aggregated_row,
        "hardware": {
            "max_cpu_percent": max_cpu,
            "avg_cpu_percent": avg_cpu,
            "max_mem_mb": max_mem,
            "avg_mem_mb": avg_mem,
        },
        "failures": failures,
    }
    with open(os.path.join(RESULTS_DIR, f"summary_tier_{tier}.json"), "w", encoding="utf-8") as f_json:
        json.dump(summary_data, f_json, indent=2, ensure_ascii=False)

    print("=" * 70 + "\n")
    return summary_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy một bậc kiểm thử hiệu năng Locust")
    parser.add_argument("--tier", type=int, default=0, help="Số thứ tự bậc (0..6)")
    parser.add_argument("--users", type=int, default=2, help="Số lượng virtual users")
    parser.add_argument("--spawn-rate", type=float, default=1.0, help="Tốc độ spawn user/s")
    parser.add_argument("--duration", type=str, default="60s", help="Thời lượng test (ví dụ 60s, 3m)")
    parser.add_argument("--tag", type=str, default="smoke", help="Tag nhận diện bậc")
    parser.add_argument("--user-classes", type=str, default="", help="Các lớp User chỉ định (ví dụ: 'NormalUser ActiveUser')")

    args = parser.parse_args()
    run_tier(
        tier=args.tier,
        users=args.users,
        spawn_rate=args.spawn_rate,
        duration=args.duration,
        tag=args.tag,
        user_classes=args.user_classes,
    )
