import asyncio
import time
import argparse
import sys
import json
from collections import Counter
from typing import List, Dict, Any
import httpx

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c < len(sorted_vals):
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
    return sorted_vals[f]

async def run_benchmark(
    url: str,
    method: str = "GET",
    rate: float = 100.0,
    duration: int = 10,
    workers: int = 200,
    token: str = None,
    client_inside_container: bool = False
) -> Dict[str, Any]:
    total_reqs = int(rate * duration)
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    limits = httpx.Limits(max_connections=workers, max_keepalive_connections=workers)
    timeout = httpx.Timeout(30.0, connect=10.0)

    # 1. Reset server traffic stats
    async with httpx.AsyncClient(timeout=timeout) as setup_client:
        base_url = url.split("/api/v1/")[0]
        try:
            await setup_client.post(f"{base_url}/api/v1/bench/reset")
            await setup_client.post(f"{base_url}/api/v1/reports/write-gate/reset")
        except Exception:
            pass

    results = []
    completed = []
    sem = asyncio.Semaphore(workers)

    async with httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers) as client:
        async def worker(idx: int, sched_t: float):
            now_t = time.perf_counter()
            drift_ms = (now_t - sched_t) * 1000.0
            async with sem:
                t_send = time.perf_counter()
                status = 0
                err = ""
                try:
                    if method.upper() == "POST":
                        resp = await client.post(url, json={})
                    else:
                        resp = await client.get(url)
                    status = resp.status_code
                except Exception as exc:
                    status = 599
                    err = str(exc)
                t_done = time.perf_counter()
                res = {
                    "idx": idx,
                    "status": status,
                    "success": 200 <= status < 300,
                    "latency_ms": (t_done - t_send) * 1000.0,
                    "drift_ms": drift_ms,
                    "t_send": t_send,
                    "t_done": t_done,
                    "error": err
                }
                completed.append(res)
                return res

        print(f"\n{'='*75}\nBẮT ĐẦU BẮN TẢI: {url}\nMục tiêu: {rate} RPS x {duration}s = {total_reqs} requests (workers={workers})\n{'='*75}", flush=True)

        t0 = time.perf_counter()
        tasks = []
        for i in range(total_reqs):
            sched_t = t0 + (i / rate)
            wait_s = sched_t - time.perf_counter()
            if wait_s > 0:
                await asyncio.sleep(wait_s)
            t = asyncio.create_task(worker(i, sched_t))
            tasks.append(t)

        await asyncio.gather(*tasks, return_exceptions=True)
        t_end = time.perf_counter()
        total_elapsed = t_end - t0

    # 2. Get server traffic & limiter stats
    server_stats = {}
    async with httpx.AsyncClient(timeout=timeout) as setup_client:
        try:
            s_res = await setup_client.get(f"{base_url}/api/v1/bench/traffic-stats")
            server_stats = s_res.json()
        except Exception as e:
            server_stats = {"error": str(e)}

    # 3. Calculate client metrics
    lats = sorted(r["latency_ms"] for r in completed)
    drifts = [r["drift_ms"] for r in completed]
    succ_count = sum(1 for r in completed if r["success"])
    err_count = len(completed) - succ_count
    err_codes = Counter(r["status"] for r in completed if not r["success"])

    p50 = percentile(lats, 50)
    p95 = percentile(lats, 95)
    p99 = percentile(lats, 99)
    max_lat = lats[-1] if lats else 0.0

    done_rps = len(completed) / max(0.001, total_elapsed)
    send_rps = len(completed) / max(0.001, float(duration))

    summary = {
        "url": url,
        "total_requests": len(completed),
        "success_count": succ_count,
        "error_count": err_count,
        "error_codes": dict(err_codes),
        "total_elapsed_s": round(total_elapsed, 2),
        "actual_done_rps": round(done_rps, 1),
        "actual_send_rps": round(send_rps, 1),
        "client_latency_ms": {
            "p50": round(p50, 1),
            "p95": round(p95, 1),
            "p99": round(p99, 1),
            "max": round(max_lat, 1)
        },
        "drift_ms": {
            "mean": round(sum(drifts) / len(drifts), 1) if drifts else 0.0,
            "max": round(max(drifts), 1) if drifts else 0.0
        },
        "server_stats": server_stats
    }

    print("\n--- KẾT QUẢ PHÍA CLIENT ---")
    print(f"  • Hoàn tất              : {len(completed)}/{total_reqs} ({succ_count} thành công, {err_count} lỗi)")
    print(f"  • RPS hoàn tất          : {done_rps:.1f} req/s (Thời gian: {total_elapsed:.2f}s)")
    print(f"  • Latency client (ms)   : p50={p50:.1f} | p95={p95:.1f} | p99={p99:.1f} | max={max_lat:.1f}")
    print(f"  • Độ trễ drift (ms)     : mean={summary['drift_ms']['mean']} | max={summary['drift_ms']['max']}")

    print("\n--- THỐNG KÊ SERVER TẦNG TRUNG GIAN & THREADPOOL ---")
    if "timeline" in server_stats:
        print("  Giây | Server Nhận (Arrivals) | Server Xong (Completions)")
        print("  ---------------------------------------------------------")
        for row in server_stats["timeline"]:
            print(f"  {row['relative_sec']:<4} | {row['arrivals']:<22} | {row['completions']:<22}")
    if "limiter" in server_stats:
        lim = server_stats["limiter"]
        print(f"  • AnyIO Limiter Tokens  : Total={lim.get('total_tokens')} | Max Borrowed={lim.get('max_borrowed_tokens')} | Max Tasks Waiting={lim.get('max_tasks_waiting')}")

    return summary

def main():
    parser = argparse.ArgumentParser(description="Open-loop benchmark for control experiments")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/bench/empty-async")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"])
    parser.add_argument("--rate", type=float, default=100.0)
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--workers", type=int, default=200)
    parser.add_argument("--token", default=None)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    all_summaries = []
    for r in range(1, args.runs + 1):
        print(f"\n>>> LƯỢT {r}/{args.runs} <<<")
        s = asyncio.run(run_benchmark(
            url=args.url,
            method=args.method,
            rate=args.rate,
            duration=args.duration,
            workers=args.workers,
            token=args.token
        ))
        all_summaries.append(s)
        time.sleep(1)

    print(f"\n{'='*75}\nTỔNG HỢP {args.runs} LƯỢT CHO: {args.url}\n{'='*75}")
    for idx, s in enumerate(all_summaries, 1):
        print(f"  Lượt {idx}: RPS={s['actual_done_rps']} | p50={s['client_latency_ms']['p50']}ms | p95={s['client_latency_ms']['p95']}ms | Time={s['total_elapsed_s']}s")

    avg_rps = sum(s["actual_done_rps"] for s in all_summaries) / len(all_summaries)
    avg_p50 = sum(s["client_latency_ms"]["p50"] for s in all_summaries) / len(all_summaries)
    avg_p95 = sum(s["client_latency_ms"]["p95"] for s in all_summaries) / len(all_summaries)
    print(f"\n  >> TRUNG BÌNH: RPS = {avg_rps:.1f} req/s | p50 = {avg_p50:.1f} ms | p95 = {avg_p95:.1f} ms")

if __name__ == "__main__":
    main()
