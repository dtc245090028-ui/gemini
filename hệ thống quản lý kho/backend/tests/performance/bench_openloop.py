"""Kịch bản kiểm thử tải Open-Loop xác định năng lực ghi thật của SmartKho Server.

Hỗ trợ:
1. Endpoint rỗng đối chứng (empty-async, empty-sync, auth-sync, write-gate)
2. Endpoint GHI THẬT (writes):
   - Tạo phiếu nhập (/api/v1/import-notes/)
   - Điều chỉnh kiểm kê (/api/v1/stock-ledger/adjust) kèm X-Idempotency-Key duy nhất mỗi request
   - Tạo phiếu xuất (/api/v1/export-notes/)
3. Đo đạc chi tiết theo từng giây:
   - Số client PHÁT
   - Số request ĐẾN server (WriteArrivalMiddleware)
   - Số request HOÀN TẤT
   - Độ trễ p50 / p95 / max
   - Số lỗi 503 (Write Gate rejected / backpressure) / 429 (Rate limit)
4. Tự động thu dọn dữ liệu sau mỗi lượt và đối soát 5 bất biến toàn vẹn.
"""

import argparse
import asyncio
from collections import Counter, defaultdict
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List
import uuid
import httpx

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c < len(sorted_vals):
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
    return sorted_vals[f]


def get_admin_token(base_url: str) -> str:
    res = httpx.post(f"{base_url}/api/v1/auth/login", json={"username": "admin", "password": "admin123"}, timeout=10.0)
    assert res.status_code == 200, f"Đăng nhập lấy token thất bại: {res.text}"
    return res.json()["access_token"]


def cleanup_bench_data_and_check_invariants(run_id: str):
    """Thu dọn dữ liệu test của lượt đo và chạy kiểm tra 5 bất biến."""
    cleanup_cmd = f"""
from app.core.database import SessionLocal
from app.models.import_note import ImportNote, ImportNoteDetail
from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.stock_ledger import StockLedger
from app.models.product import Product

db = SessionLocal()
try:
    # 1. Xóa phiếu nhập bench
    imps = db.query(ImportNote).filter(ImportNote.note.like('%BENCH_{run_id}%')).all()
    for imp in imps:
        db.query(StockLedger).filter(StockLedger.reference_code == imp.code).delete()
        db.query(ImportNoteDetail).filter(ImportNoteDetail.import_note_id == imp.id).delete()
        db.delete(imp)

    # 2. Xóa phiếu xuất bench
    exps = db.query(ExportNote).filter(ExportNote.note.like('%BENCH_{run_id}%')).all()
    for exp in exps:
        db.query(StockLedger).filter(StockLedger.reference_code == exp.code).delete()
        db.query(ExportNoteDetail).filter(ExportNoteDetail.export_note_id == exp.id).delete()
        db.delete(exp)

    # 3. Xóa các dòng kiểm kê điều chỉnh bench
    db.query(StockLedger).filter(
        StockLedger.note.like('%BENCH_{run_id}%') | StockLedger.idempotency_key.like('%{run_id}%')
    ).delete()

    # 4. Cân đối lại current_stock của Product 1 theo thẻ kho còn lại
    p1 = db.query(Product).filter(Product.id == 1).first()
    if p1:
        last_entry = db.query(StockLedger).filter(StockLedger.product_id == 1).order_by(StockLedger.id.desc()).first()
        if last_entry:
            p1.current_stock = last_entry.balance_after
    db.commit()
finally:
    db.close()
"""
    # Thực thi qua container
    subprocess.run(["docker", "exec", "warehouse_backend", "python", "-c", cleanup_cmd], check=True, encoding="utf-8", errors="replace")
    # Kiểm tra invariants
    inv_res = subprocess.run(
        ["docker", "exec", "warehouse_backend", "python", "/app/tests/performance/check_invariants.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert inv_res.stdout and "TỔNG KẾT BẤT BIẾN: TẤT CẢ ĐỀU ĐẠT" in inv_res.stdout, f"Lỗi bất biến sau dọn dẹp!\n{inv_res.stdout}"


async def run_benchmark(
    base_url: str,
    mode: str = "writes",
    rate: float = 50.0,
    duration: int = 10,
    workers: int = 200,
    token: str = None,
) -> Dict[str, Any]:
    run_id = uuid.uuid4().hex[:8]
    total_reqs = int(rate * duration)
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    limits = httpx.Limits(max_connections=workers, max_keepalive_connections=workers)
    timeout = httpx.Timeout(30.0, connect=10.0)

    # 1. Reset bộ đếm server
    async with httpx.AsyncClient(timeout=timeout) as setup_client:
        try:
            await setup_client.post(f"{base_url}/api/v1/bench/reset", headers=headers)
        except Exception:
            pass

    completed = []
    sent_by_sec = defaultdict(int)
    sem = asyncio.Semaphore(workers)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        async def worker(idx: int, sched_t: float, sec_idx: int):
            now_t = time.perf_counter()
            drift_ms = (now_t - sched_t) * 1000.0
            async with sem:
                t_send = time.perf_counter()
                status = 0
                err = ""

                try:
                    if mode == "writes":
                        req_type = idx % 3
                        if req_type == 0:
                            # 1. Tạo phiếu nhập
                            resp = await client.post(
                                f"{base_url}/api/v1/import-notes/",
                                json={
                                    "supplier_id": 1,
                                    "note": f"BENCH_{run_id}",
                                    "details": [{"product_id": 1, "quantity": 1, "unit_price": 50000.0}],
                                },
                                headers=headers,
                            )
                        elif req_type == 1:
                            # 2. Điều chỉnh kiểm kê với Idempotency Key duy nhất
                            resp = await client.post(
                                f"{base_url}/api/v1/stock-ledger/adjust",
                                json={
                                    "product_id": 1,
                                    "actual_stock": 100 + (idx % 20),
                                    "reason": f"BENCH_{run_id}",
                                },
                                headers={**headers, "X-Idempotency-Key": f"BENCH-ADJ-{run_id}-{idx}"},
                            )
                        else:
                            # 3. Tạo phiếu xuất
                            resp = await client.post(
                                f"{base_url}/api/v1/export-notes/",
                                json={
                                    "recipient_name": f"Khách Hàng Bench {idx}",
                                    "note": f"BENCH_{run_id}",
                                    "details": [{"product_id": 1, "quantity": 1, "unit_price": 100000.0}],
                                },
                                headers=headers,
                            )
                    elif mode == "import":
                        resp = await client.post(
                            f"{base_url}/api/v1/import-notes/",
                            json={
                                "supplier_id": 1,
                                "note": f"BENCH_{run_id}",
                                "details": [{"product_id": 1, "quantity": 1, "unit_price": 50000.0}],
                            },
                            headers=headers,
                        )
                    elif mode == "adjust":
                        resp = await client.post(
                            f"{base_url}/api/v1/stock-ledger/adjust",
                            json={
                                "product_id": 1,
                                "actual_stock": 100 + (idx % 20),
                                "reason": f"BENCH_{run_id}",
                            },
                            headers={**headers, "X-Idempotency-Key": f"BENCH-ADJ-{run_id}-{idx}"},
                        )
                    elif mode == "export":
                        resp = await client.post(
                            f"{base_url}/api/v1/export-notes/",
                            json={
                                "recipient_name": f"Khách Hàng Bench {idx}",
                                "note": f"BENCH_{run_id}",
                                "details": [{"product_id": 1, "quantity": 1, "unit_price": 100000.0}],
                            },
                            headers=headers,
                        )
                    elif mode == "empty-async":
                        resp = await client.get(f"{base_url}/api/v1/bench/empty-async", headers=headers)
                    elif mode == "empty-sync":
                        resp = await client.get(f"{base_url}/api/v1/bench/empty-sync", headers=headers)
                    elif mode == "auth-sync":
                        resp = await client.get(f"{base_url}/api/v1/bench/auth-sync", headers=headers)
                    elif mode == "write-gate":
                        resp = await client.post(f"{base_url}/api/v1/bench/write-gate", headers=headers)
                    else:
                        raise ValueError(f"Chế độ benchmark không hợp lệ: {mode}")

                    status = resp.status_code
                except Exception as exc:
                    status = 599
                    err = str(exc)

                t_done = time.perf_counter()
                res = {
                    "idx": idx,
                    "sec_idx": sec_idx,
                    "status": status,
                    "success": 200 <= status < 300,
                    "latency_ms": (t_done - t_send) * 1000.0,
                    "drift_ms": drift_ms,
                    "t_send": t_send,
                    "t_done": t_done,
                    "error": err,
                }
                completed.append(res)
                return res

        print(
            f"\n{'='*80}\n"
            f" BẮT ĐẦU BẮN TẢI GHI THẬT: Mode={mode.upper()} | Tải: {rate} RPS x {duration}s = {total_reqs} reqs | Run ID: {run_id}\n"
            f"{'='*80}",
            flush=True,
        )

        t0 = time.perf_counter()
        tasks = []
        for i in range(total_reqs):
            sched_t = t0 + (i / rate)
            sec_idx = int(i / rate) + 1
            sent_by_sec[sec_idx] += 1

            wait_s = sched_t - time.perf_counter()
            if wait_s > 0:
                await asyncio.sleep(wait_s)
            t = asyncio.create_task(worker(i, sched_t, sec_idx))
            tasks.append(t)

        await asyncio.gather(*tasks, return_exceptions=True)
        t_end = time.perf_counter()
        total_elapsed = t_end - t0

    # 2. Lấy số liệu lưu lượng từ WriteArrivalMiddleware phía Server
    server_stats = {}
    async with httpx.AsyncClient(timeout=timeout) as setup_client:
        try:
            s_res = await setup_client.get(f"{base_url}/api/v1/bench/traffic-stats", headers=headers)
            server_stats = s_res.json()
        except Exception as e:
            server_stats = {"error": str(e)}

    # 3. Tính toán số liệu từng giây
    # Gom nhóm kết quả hoàn tất theo giây thực tế hoàn thành
    done_by_sec = defaultdict(list)
    for r in completed:
        done_sec = max(1, int(r["t_done"] - t0) + 1)
        done_by_sec[done_sec].append(r)

    # Server timeline map
    server_timeline_map = {}
    if "timeline" in server_stats:
        for row in server_stats["timeline"]:
            server_timeline_map[row["relative_sec"]] = row

    all_secs = sorted(set(list(sent_by_sec.keys()) + list(done_by_sec.keys()) + list(server_timeline_map.keys())))
    sec_breakdown = []

    print("\n--- CHI TIẾT SỐ LIỆU TỪNG GIÂY (PER-SECOND TIMELINE) ---")
    print(
        f" {'Giây':<5} | {'Client Phát':<12} | {'Server Đến':<12} | {'Server Xong':<12} | "
        f"{'Client Xong':<12} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'Max (ms)':<9} | {'503 (Cổng)':<11} | {'429 (Rate)':<11}"
    )
    print("-" * 115)

    for s in all_secs:
        reqs_in_sec = done_by_sec.get(s, [])
        lats_in_sec = sorted(r["latency_ms"] for r in reqs_in_sec)
        p50_s = percentile(lats_in_sec, 50) if lats_in_sec else 0.0
        p95_s = percentile(lats_in_sec, 95) if lats_in_sec else 0.0
        max_s = lats_in_sec[-1] if lats_in_sec else 0.0

        c_503 = sum(1 for r in reqs_in_sec if r["status"] == 503)
        c_429 = sum(1 for r in reqs_in_sec if r["status"] == 429)

        srv_row = server_timeline_map.get(s, {})
        srv_arr = srv_row.get("arrivals", 0)
        srv_comp = srv_row.get("completions", 0)
        cl_sent = sent_by_sec.get(s, 0)
        cl_done = len(reqs_in_sec)

        sec_breakdown.append({
            "second": s,
            "client_sent": cl_sent,
            "server_arrivals": srv_arr,
            "server_completions": srv_comp,
            "client_completed": cl_done,
            "p50_ms": round(p50_s, 1),
            "p95_ms": round(p95_s, 1),
            "max_ms": round(max_s, 1),
            "status_503": c_503,
            "status_429": c_429,
        })

        print(
            f" {s:<5} | {cl_sent:<12} | {srv_arr:<12} | {srv_comp:<12} | "
            f"{cl_done:<12} | {p50_s:<9.1f} | {p95_s:<9.1f} | {max_s:<9.1f} | {c_503:<11} | {c_429:<11}"
        )

    # 4. Tính toán số liệu tổng hợp của toàn đợt
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
    succ_rps = succ_count / max(0.001, total_elapsed)

    summary = {
        "run_id": run_id,
        "mode": mode,
        "target_rate": rate,
        "duration": duration,
        "total_requests": len(completed),
        "success_count": succ_count,
        "error_count": err_count,
        "error_codes": dict(err_codes),
        "total_elapsed_s": round(total_elapsed, 2),
        "actual_done_rps": round(done_rps, 1),
        "actual_succ_rps": round(succ_rps, 1),
        "client_latency_ms": {
            "p50": round(p50, 1),
            "p95": round(p95, 1),
            "p99": round(p99, 1),
            "max": round(max_lat, 1),
        },
        "drift_ms": {
            "mean": round(sum(drifts) / len(drifts), 1) if drifts else 0.0,
            "max": round(max(drifts), 1) if drifts else 0.0,
        },
        "sec_breakdown": sec_breakdown,
        "server_stats": server_stats,
    }

    print("\n--- TỔNG KẾT ĐỢT ĐO ---")
    print(f"  • Tổng request hoàn tất  : {len(completed)}/{total_reqs} ({succ_count} thành công, {err_count} lỗi)")
    print(f"  • Thông lượng hoàn tất   : {done_rps:.1f} req/s (Thành công: {succ_rps:.1f} req/s)")
    print(f"  • Phân bố lỗi HTTP       : {dict(err_codes) if err_codes else 'Không có lỗi'}")
    print(f"  • Latency toàn đợt (ms)  : p50={p50:.1f} | p95={p95:.1f} | p99={p99:.1f} | max={max_lat:.1f}")

    # 5. Dọn dẹp CSDL sạch sẽ và xác thực 5 bất biến nếu là endpoint ghi
    if mode in ("writes", "import", "adjust", "export"):
        print("\n[Dọn dẹp] Đang thu dọn dữ liệu benchmark và kiểm tra 5 bất biến kế toán...")
        cleanup_bench_data_and_check_invariants(run_id)
        print("  ✅ Dọn dẹp hoàn tất & 5/5 Bất biến ĐẠT.")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Open-loop benchmark xác định năng lực ghi thật")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--mode", default="writes", choices=["writes", "import", "adjust", "export", "empty-async", "empty-sync", "auth-sync", "write-gate"])
    parser.add_argument("--rates", default="50,100,200", help="Danh sách mức RPS cần bắn (phân tách bởi dấu phẩy, vd: 50,100,200)")
    parser.add_argument("--duration", type=int, default=10)
    parser.add_argument("--workers", type=int, default=200)
    parser.add_argument("--runs", type=int, default=3, help="Số lần chạy mỗi mức RPS")
    args = parser.parse_args()

    token = get_admin_token(args.base_url)
    rates = [float(r.strip()) for r in args.rates.split(",") if r.strip()]

    all_results = {}

    for rate in rates:
        print(f"\n{'#'*85}\n### TIẾN HÀNH ĐO MỨC TẢI: {rate} RPS (Mỗi mức {args.runs} lần, mỗi lần {args.duration}s)\n{'#'*85}")
        rate_summaries = []
        for r in range(1, args.runs + 1):
            print(f"\n>>> Mức {rate} RPS - Lượt {r}/{args.runs} <<<")
            summary = asyncio.run(run_benchmark(
                base_url=args.base_url,
                mode=args.mode,
                rate=rate,
                duration=args.duration,
                workers=args.workers,
                token=token,
            ))
            rate_summaries.append(summary)
            time.sleep(1)

        all_results[rate] = rate_summaries

    print(f"\n{'='*85}\n BẢNG TỔNG HỢP NGHIỆM THU NĂNG LỰC GHI THẬT CỦA SERVER\n{'='*85}")
    print(f" {'Mức Tải':<10} | {'Lượt':<5} | {'RPS Hoàn Tất':<14} | {'Thành công':<12} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'Max (ms)':<9} | {'503':<6} | {'429':<6}")
    print("-" * 88)

    for rate, summaries in all_results.items():
        for idx, s in enumerate(summaries, 1):
            c_503 = s["error_codes"].get(503, 0)
            c_429 = s["error_codes"].get(429, 0)
            print(
                f" {rate:<10.0f} | {idx:<5} | {s['actual_done_rps']:<14.1f} | "
                f"{s['success_count']:<12} | {s['client_latency_ms']['p50']:<9.1f} | "
                f"{s['client_latency_ms']['p95']:<9.1f} | {s['client_latency_ms']['max']:<9.1f} | "
                f"{c_503:<6} | {c_429:<6}"
            )
        avg_done = sum(s["actual_done_rps"] for s in summaries) / len(summaries)
        avg_p50 = sum(s["client_latency_ms"]["p50"] for s in summaries) / len(summaries)
        avg_p95 = sum(s["client_latency_ms"]["p95"] for s in summaries) / len(summaries)
        print(f" -> TB {rate:.0f} RPS: Hoàn tất {avg_done:.1f} req/s | p50 = {avg_p50:.1f} ms | p95 = {avg_p95:.1f} ms\n")


if __name__ == "__main__":
    main()
