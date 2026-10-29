"""Demo chịu tải Xuất / Nhập kho đồng thời (Burst + Open-loop Sustained Load).

Hỗ trợ chạy trực tiếp trên instance Web đang mở (http://127.0.0.1:8000 / warehouse.db)
kèm cơ chế tự động sao lưu an toàn (warehouse_pre_demo_backup.db) và ủy quyền thực thi
trong Docker container để tránh xung đột khóa SQLite WAL trên Windows, giúp bạn quan sát
trực tiếp kết quả trên giao diện Web (http://localhost:5173) rồi dọn sạch bằng demo_cleanup.py.

Luồng thực thi:
1. Guard kiểm tra môi trường & tự động tạo bản sao lưu an toàn trước khi chạy.
2. Chụp snapshot số dòng của 6 bảng: products, import_notes, import_note_details,
   export_notes, export_note_details, stock_ledger.
3. Tạo 2 sản phẩm SKU-DEMO-A và SKU-DEMO-B qua API (cách nhau --gap giây), tồn đầu --initial.
4. Ghi ngay demo_manifest.json trước khi bắn tải để đảm bảo dọn dẹp được nếu dừng giữa chừng.
5. Đếm ngược --wait giây trên màn hình.
6. Lập kế hoạch deterministic (theo --seed) cho toàn bộ request Pha 1 (Burst) và Pha 2 (Sustained),
   đan xen DEMO-A / DEMO-B và IMPORT / EXPORT, kiểm tra tồn đầu đủ xuất và in bảng kế hoạch.
7. Pha 1 (Burst): Bắn đồng thời --burst request cùng một thời điểm.
8. Pha 2 (Sustained): Bắn open-loop theo lịch cố định (t0 + i / rate) với asyncio + httpx connection pool dùng chung.
   Đo độ trễ lịch bắn, in tiến độ mỗi giây, tự dừng nếu lỗi 5xx > 30% trong 2 giây liên tiếp.
9. Flush manifest định kỳ mỗi 0.5s và khi bắt KeyboardInterrupt.
10. Báo cáo tổng hợp từng pha, bảng theo từng giây, thống kê lỗi (database is locked, 409, 5xx)
    và đối chiếu toán học tồn kho + 4 bất biến sổ cái Thẻ kho (PASS / FAIL).
"""

import argparse
import asyncio
import json
import math
import os
import random
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Tự động ủy quyền vào trong container warehouse_backend nếu chạy từ Windows Host nhắm vào cổng 8000 / warehouse.db
# nhằm ngăn chặn xung đột bộ nhớ chia sẻ SQLite WAL (-shm) giữa Windows Host và Linux Container.
if os.name == "nt" and not os.environ.get("INSIDE_DOCKER"):
    raw_argv = sys.argv[1:]
    uses_perf_port = any("8001" in a for a in raw_argv)
    if not uses_perf_port:
        chk = subprocess.run(
            ["docker", "ps", "--filter", "name=warehouse_backend", "--filter", "status=running", "-q"],
            capture_output=True,
            text=True,
            check=False,
        )
        if chk.returncode == 0 and chk.stdout.strip():
            # Chuyển đổi đường dẫn --db-path nếu người dùng truyền đường dẫn Windows
            forwarded_args = []
            skip_next = False
            for idx_a, arg_v in enumerate(raw_argv):
                if skip_next:
                    skip_next = False
                    continue
                if arg_v == "--db-path" and idx_a + 1 < len(raw_argv):
                    skip_next = True
                    continue
                forwarded_args.append(arg_v)

            cmd = [
                "docker", "exec", "-i",
                "-e", "INSIDE_DOCKER=1",
                "-e", "PYTHONUTF8=1",
                "warehouse_backend",
                "python", "-u", "/app/tests/performance/demo_run.py",
                *forwarded_args,
            ]
            res = subprocess.run(cmd, check=False)
            sys.exit(res.returncode)

import httpx

PERF_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(PERF_DIR, "..", ".."))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "warehouse.db")
BACKUP_DIR = os.path.join(BACKEND_DIR, "backups")
PRE_DEMO_BACKUP_PATH = os.path.join(BACKUP_DIR, "warehouse_pre_demo_backup.db")
MANIFEST_PATH = os.path.join(PERF_DIR, "demo_manifest.json")

PROFILES = {
    "demo": {"rate": 5, "duration": 10, "burst": 20, "initial": 2000, "workers": 50},
    "medium": {"rate": 20, "duration": 15, "burst": 20, "initial": 2000, "workers": 100},
    "heavy": {"rate": 50, "duration": 20, "burst": 20, "initial": 2000, "workers": 150},
    "stress100": {"rate": 100, "duration": 10, "burst": 20, "initial": 2000, "workers": 200},
}

SNAPSHOT_TABLES = [
    "products",
    "import_notes",
    "import_note_details",
    "export_notes",
    "export_note_details",
    "stock_ledger",
]

DEMO_PRODUCT_IMAGES = {
    "SKU-DEMO-A": "https://tse4.mm.bing.net/th/id/OIP.OpneO1xDmvuH8kkQpPP3iwHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
    "SKU-DEMO-B": "https://tse4.mm.bing.net/th/id/OIP.hrX9V9HvG0HkxeIvFvzPiwHaFR?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
}


def verify_environment_guard(base_url: str, db_path: str) -> str:
    """Kiểm tra môi trường, in rõ Base URL & DB đang dùng và tạo bản backup an toàn trước khi chạy."""
    parsed = urlparse(base_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    abs_db = os.path.abspath(db_path)

    print("=" * 78)
    print(" KIỂM TRA AN TOÀN MÔI TRƯỜNG & SAO LƯU DỰ PHÒNG (SAFETY GUARD)")
    print("=" * 78)
    print(f"  • Base URL mục tiêu : {base_url} (Port: {port})")
    print(f"  • CSDL mục tiêu     : {abs_db}")
    print(f"  • Giao diện Web     : http://localhost:5173 (Có thể quan sát trực tiếp sau khi chạy)")

    if parsed.hostname not in ("127.0.0.1", "localhost"):
        print("\n[SAFETY GUARD BLOCKED] Chỉ cho phép chạy demo trên localhost / 127.0.0.1!")
        sys.exit(1)

    if not os.path.exists(abs_db):
        print(f"\n[SAFETY GUARD BLOCKED] Không tìm thấy file CSDL tại: {abs_db}")
        sys.exit(1)

    # Kiểm tra xem có dữ liệu DEMO cũ chưa dọn không trước khi ghi đè bản backup
    conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, code FROM products WHERE code IN ('SKU-DEMO-A', 'SKU-DEMO-B') OR code LIKE 'SKU-DEMO-%'")
        existing = cur.fetchall()
        if existing:
            print(f"\n[CẢNH BÁO] Phát hiện sản phẩm DEMO từ lần chạy trước chưa được dọn: {existing}")
            print("Vui lòng chạy `python backend/tests/performance/demo_cleanup.py --yes` trước khi chạy lượt mới.")
            sys.exit(1)
    finally:
        conn.close()

    # Tạo bản sao lưu trực tuyến an toàn (Online Backup) trước khi thêm bất kỳ bản ghi DEMO nào
    os.makedirs(BACKUP_DIR, exist_ok=True)
    src_conn = sqlite3.connect(abs_db, timeout=15.0)
    dst_conn = sqlite3.connect(PRE_DEMO_BACKUP_PATH, timeout=15.0)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    print(f"  • Bản sao lưu dự phòng: {PRE_DEMO_BACKUP_PATH}")
    print("  => [GUARD PASS] Môi trường sẵn sàng & đã sao lưu dự phòng an toàn.\n")
    return abs_db


def get_db_snapshot(db_path: str) -> dict:
    """Chụp số lượng bản ghi của 6 bảng trọng yếu."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        snap = {}
        for tbl in SNAPSHOT_TABLES:
            cur.execute(f"SELECT count(*) FROM {tbl}")
            snap[tbl] = cur.fetchone()[0]
        return snap
    finally:
        conn.close()


def write_manifest_sync(manifest_data: dict):
    """Ghi nguyên tử demo_manifest.json thông qua file tạm."""
    tmp_path = f"{MANIFEST_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, MANIFEST_PATH)


def percentile(sorted_vals: list, pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_vals[int(k)])
    return float(sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f))


def build_deterministic_plan(seed: int, burst_count: int, sustained_count: int, initial_stock: int):
    """Sinh kế hoạch request tiền định (deterministic) cho cả 2 pha:
    - Đan xen DEMO-A / DEMO-B và đan xen IMPORT / EXPORT (không dồn cục).
    - Số lượng mỗi request từ 1..5.
    - Đảm bảo tồn_đầu - tổng_xuất >= 0 cho từng sản phẩm.
    """
    rng = random.Random(seed)
    skus = ["SKU-DEMO-A", "SKU-DEMO-B"]

    # Pha 1: Burst (mặc định 20 request: 10 DEMO-A, 10 DEMO-B, đan xen IMPORT/EXPORT)
    phase1_plan = []
    for i in range(burst_count):
        sku = skus[i % 2]
        pair_idx = i // 2
        if (pair_idx % 2 == 0 and i % 2 == 0) or (pair_idx % 2 == 1 and i % 2 == 1):
            tx_type = "IMPORT"
        else:
            tx_type = "EXPORT"
        qty = rng.randint(1, 5)
        prefix = "PN-DEMO" if tx_type == "IMPORT" else "PX-DEMO"
        code = f"{prefix}-B{i + 1:04d}"
        phase1_plan.append({
            "req_idx": i + 1,
            "phase": 1,
            "sku": sku,
            "tx_type": tx_type,
            "quantity": qty,
            "code": code,
        })

    # Pha 2: Sustained (mặc định 1000 request, đan xen DEMO-A/DEMO-B và IMPORT/EXPORT)
    phase2_plan = []
    for i in range(sustained_count):
        sku = skus[i % 2]
        pair_idx = i // 2
        if (pair_idx + (i % 2)) % 2 == 0:
            tx_type = "IMPORT"
        else:
            tx_type = "EXPORT"
        qty = rng.randint(1, 5)
        prefix = "PN-DEMO" if tx_type == "IMPORT" else "PX-DEMO"
        code = f"{prefix}-S{i + 1:04d}"
        phase2_plan.append({
            "req_idx": burst_count + i + 1,
            "phase": 2,
            "sku": sku,
            "tx_type": tx_type,
            "quantity": qty,
            "code": code,
        })

    all_plan = phase1_plan + phase2_plan

    plan_summary = {}
    adjusted_initial = initial_stock
    for sku in skus:
        imp_reqs = [r for r in all_plan if r["sku"] == sku and r["tx_type"] == "IMPORT"]
        exp_reqs = [r for r in all_plan if r["sku"] == sku and r["tx_type"] == "EXPORT"]
        imp_qty = sum(r["quantity"] for r in imp_reqs)
        exp_qty = sum(r["quantity"] for r in exp_reqs)
        if exp_qty > adjusted_initial:
            adjusted_initial = exp_qty + 100
        plan_summary[sku] = {
            "import_reqs": len(imp_reqs),
            "import_qty": imp_qty,
            "export_reqs": len(exp_reqs),
            "export_qty": exp_qty,
        }

    for sku in skus:
        s = plan_summary[sku]
        s["initial_stock"] = adjusted_initial
        s["expected_final"] = adjusted_initial + s["import_qty"] - s["export_qty"]

    return phase1_plan, phase2_plan, plan_summary, adjusted_initial


async def execute_single_item(
    client: httpx.AsyncClient,
    item: dict,
    sku_to_id: dict,
    manifest: dict,
    manifest_dirty: list,
    sched_time: float = None,
) -> dict:
    """Thực thi 1 giao dịch IMPORT hoặc EXPORT hoàn chỉnh."""
    t_send = time.perf_counter()
    drift_ms = (t_send - sched_time) * 1000.0 if sched_time is not None else 0.0

    pid = sku_to_id[item["sku"]]
    tx_type = item["tx_type"]
    qty = item["quantity"]
    code = item["code"]

    status_code = 0
    err_detail = ""
    locked_hit = False
    note_id = None

    try:
        if tx_type == "IMPORT":
            payload = {
                "code": code,
                "supplier_id": 1,
                "note": f"Nhập kho Demo Chịu Tải ({code})",
                "details": [
                    {
                        "product_id": pid,
                        "quantity": qty,
                        "unit_price": 80000.0,
                    }
                ],
            }
            resp = await client.post("/api/v1/import-notes/", json=payload)
            status_code = resp.status_code
            if status_code in (200, 201):
                data = resp.json()
                note_id = data.get("id")
                manifest["created_import_notes"].append({
                    "id": note_id,
                    "code": code,
                    "req_idx": item["req_idx"],
                    "sku": item["sku"],
                    "quantity": qty,
                })
                manifest_dirty[0] = True
            else:
                err_detail = resp.text[:300]
                if "database is locked" in err_detail.lower():
                    locked_hit = True
        else:
            payload = {
                "code": code,
                "recipient_name": "Khách hàng Demo Chịu Tải",
                "note": f"Xuất kho Demo Chịu Tải ({code})",
                "details": [
                    {
                        "product_id": pid,
                        "quantity": qty,
                        "unit_price": 100000.0,
                    }
                ],
            }
            resp_create = await client.post("/api/v1/export-notes/", json=payload)
            if resp_create.status_code not in (200, 201):
                status_code = resp_create.status_code
                err_detail = resp_create.text[:300]
                if "database is locked" in err_detail.lower():
                    locked_hit = True
            else:
                c_data = resp_create.json()
                note_id = c_data.get("id")
                resp_ship = await client.post(f"/api/v1/export-notes/{note_id}/ship")
                status_code = resp_ship.status_code
                if status_code in (200, 201):
                    manifest["created_export_notes"].append({
                        "id": note_id,
                        "code": code,
                        "req_idx": item["req_idx"],
                        "sku": item["sku"],
                        "quantity": qty,
                        "shipped": True,
                    })
                    manifest_dirty[0] = True
                else:
                    err_detail = resp_ship.text[:300]
                    if "database is locked" in err_detail.lower():
                        locked_hit = True
                    try:
                        del_resp = await client.delete(f"/api/v1/export-notes/{note_id}")
                        if del_resp.status_code not in (200, 204):
                            manifest["created_export_notes"].append({
                                "id": note_id,
                                "code": code,
                                "req_idx": item["req_idx"],
                                "sku": item["sku"],
                                "quantity": qty,
                                "shipped": False,
                            })
                            manifest_dirty[0] = True
                    except Exception:
                        manifest["created_export_notes"].append({
                            "id": note_id,
                            "code": code,
                            "req_idx": item["req_idx"],
                            "sku": item["sku"],
                            "quantity": qty,
                            "shipped": False,
                        })
                        manifest_dirty[0] = True

    except httpx.TimeoutException as exc:
        status_code = 599
        err_detail = f"Timeout: {exc}"
    except Exception as exc:
        status_code = 598
        err_detail = str(exc)[:300]
        if "database is locked" in err_detail.lower():
            locked_hit = True

    t_done = time.perf_counter()
    latency_ms = (t_done - t_send) * 1000.0
    is_success = status_code in (200, 201)

    return {
        "req_idx": item["req_idx"],
        "phase": item["phase"],
        "sku": item["sku"],
        "tx_type": tx_type,
        "quantity": qty,
        "code": code,
        "note_id": note_id,
        "status_code": status_code if not is_success else 200,
        "raw_status": status_code,
        "success": is_success,
        "latency_ms": latency_ms,
        "drift_ms": drift_ms,
        "t_send": t_send,
        "t_done": t_done,
        "locked_hit": locked_hit,
        "err_detail": err_detail,
    }


def format_phase_report(phase_name: str, results: list):
    total = len(results)
    succ = sum(1 for r in results if r["success"])
    fail = total - succ
    status_counts = Counter(r["status_code"] for r in results if not r["success"])
    lats = sorted(r["latency_ms"] for r in results)

    min_l = lats[0] if lats else 0.0
    avg_l = (sum(lats) / len(lats)) if lats else 0.0
    p50_l = percentile(lats, 50)
    p95_l = percentile(lats, 95)
    max_l = lats[-1] if lats else 0.0

    print(f"\n--- BẢNG TỔNG HỢP {phase_name} ---")
    print(f"  • Tổng số request : {total}")
    print(f"  • Thành công (2xx): {succ} ({(succ / total * 100) if total else 0:.2f}%)")
    print(f"  • Thất bại        : {fail} {dict(status_counts) if status_counts else '{}'}")
    print(
        f"  • Độ trễ (ms)     : Min={min_l:.1f} | Avg={avg_l:.1f} | "
        f"p50={p50_l:.1f} | p95={p95_l:.1f} | Max={max_l:.1f}"
    )


async def run_demo(args):
    abs_db = verify_environment_guard(args.base_url, args.db_path)

    # 1. Chụp snapshot trước khi tạo bất kỳ dữ liệu nào
    snapshot_before = get_db_snapshot(abs_db)
    print("1. SNAPSHOT SỐ DÒNG TRƯỚC KHI CHẠY:")
    for tbl, cnt in snapshot_before.items():
        print(f"   - {tbl:<22}: {cnt:>6} dòng")

    # 2. Lập kế hoạch trước để biết có cần nâng tồn đầu hay không
    burst_count = args.burst
    sustained_count = int(args.rate * args.duration)
    phase1_plan, phase2_plan, plan_summary, effective_initial = build_deterministic_plan(
        seed=args.seed,
        burst_count=burst_count,
        sustained_count=sustained_count,
        initial_stock=args.initial,
    )
    if effective_initial > args.initial:
        print(
            f"\n[CẢNH BÁO] Tồn đầu yêu cầu ({args.initial}) nhỏ hơn tổng xuất kế hoạch! "
            f"Đã tự động nâng tồn đầu lên {effective_initial} để đảm bảo tồn_đầu - tổng_xuất >= 0."
        )

    limits = httpx.Limits(
        max_connections=max(args.workers, 200),
        max_keepalive_connections=max(args.workers, 200),
    )
    timeout = httpx.Timeout(30.0, connect=10.0)

    async with httpx.AsyncClient(base_url=args.base_url, limits=limits, timeout=timeout) as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": args.username, "password": args.password},
        )
        if login_resp.status_code != 200:
            print(f"[LỖI] Đăng nhập thất bại ({login_resp.status_code}): {login_resp.text}")
            sys.exit(1)
        token = login_resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # 2 & 3. Tạo sản phẩm SKU-DEMO-A, chờ --gap giây, tạo SKU-DEMO-B
        print(f"\n2. KHỞI TẠO 2 SẢN PHẨM DEMO (Tồn đầu = {effective_initial}, Gap = {args.gap}s):")
        sku_to_id = {}
        created_products_meta = []

        for idx, (sku, name) in enumerate([
            ("SKU-DEMO-A", "Sản phẩm Demo Chịu Tải A"),
            ("SKU-DEMO-B", "Sản phẩm Demo Chịu Tải B"),
        ]):
            if idx == 1 and args.gap > 0:
                print(f"   ... Chờ --gap {args.gap}s trước khi tạo {sku} ...")
                await asyncio.sleep(args.gap)

            prod_payload = {
                "code": sku,
                "name": name,
                "category_id": 1,
                "supplier_id": 1,
                "unit": "Cái",
                "min_stock": 10,
                "current_stock": effective_initial,
                "standard_price": 100000.0,
                "image_url": DEMO_PRODUCT_IMAGES.get(sku),
                "status": "ACTIVE",
            }
            p_resp = await client.post("/api/v1/products/", json=prod_payload)
            if p_resp.status_code not in (200, 201):
                print(f"[LỖI] Không thể tạo sản phẩm {sku}: {p_resp.status_code} {p_resp.text}")
                sys.exit(1)
            p_data = p_resp.json()
            sku_to_id[sku] = p_data["id"]
            created_products_meta.append({
                "id": p_data["id"],
                "code": sku,
                "name": name,
                "initial_stock": effective_initial,
            })
            print(f"   + Đã tạo {sku} -> ID={p_data['id']} | Tồn đầu={p_data['current_stock']}")

        # 4. Ghi demo_manifest.json NGAY SAU KHI tạo sản phẩm, trước khi bắn
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "base_url": args.base_url,
            "db_path": abs_db,
            "backup_path": PRE_DEMO_BACKUP_PATH,
            "profile": args.profile,
            "seed": args.seed,
            "initial_stock": effective_initial,
            "snapshot_before": snapshot_before,
            "products": created_products_meta,
            "plan_summary": plan_summary,
            "created_import_notes": [],
            "created_export_notes": [],
        }
        write_manifest_sync(manifest)
        print(f"   + Đã ghi manifest an toàn tại: {MANIFEST_PATH}")

        # 6. In bảng kế hoạch trước khi bắn
        print("\n3. BẢNG KẾ HOẠCH TRƯỚC KHI BẮN (DETERMINISTIC PLAN):")
        print(
            f"   Tổng số request kế hoạch: {len(phase1_plan) + len(phase2_plan)} "
            f"(Pha 1 Burst: {len(phase1_plan)} | Pha 2 Sustained: {len(phase2_plan)} @ {args.rate} RPS x {args.duration}s)"
        )
        for sku in ["SKU-DEMO-A", "SKU-DEMO-B"]:
            ps = plan_summary[sku]
            label = sku.replace("SKU-", "")
            print(
                f"   • {label} ({sku}): tồn đầu {ps['initial_stock']} | "
                f"nhập {ps['import_reqs']} request / {ps['import_qty']} đv | "
                f"xuất {ps['export_reqs']} request / {ps['export_qty']} đv "
                f"=> tồn kỳ vọng cuối = {ps['expected_final']}"
            )

        # 5. Chờ --wait giây, in đếm ngược trên màn hình
        if args.wait > 0:
            print(f"\n4. ĐẾM NGƯỢC {args.wait} GIÂY TRƯỚC KHI BẮN TẢI:")
            for sec in range(int(args.wait), 0, -1):
                print(f"   ⏳ Bắn tải sau {sec} giây...", flush=True)
                await asyncio.sleep(1.0)
            print("   🚀 BẮT ĐẦU BẮN TẢI!\n", flush=True)

        manifest_dirty = [False]
        stop_flush_event = asyncio.Event()

        async def periodic_manifest_flusher():
            while not stop_flush_event.is_set():
                await asyncio.sleep(0.5)
                if manifest_dirty[0]:
                    manifest_dirty[0] = False
                    write_manifest_sync(manifest)

        flusher_task = asyncio.create_task(periodic_manifest_flusher())

        phase1_results = []
        phase2_results = []
        per_second_stats = []
        aborted_reason = None

        try:
            # =========================================================
            # 7. PHA 1 - BURST: 20 request bắn cùng lúc
            # =========================================================
            print(f"5. PHA 1 - BURST ({len(phase1_plan)} request đồng thời):")
            start_gate = asyncio.Event()

            async def burst_worker(item):
                await start_gate.wait()
                return await execute_single_item(
                    client, item, sku_to_id, manifest, manifest_dirty, sched_time=time.perf_counter()
                )

            burst_tasks = [asyncio.create_task(burst_worker(it)) for it in phase1_plan]
            await asyncio.sleep(0.02)
            t_burst_start = time.perf_counter()
            start_gate.set()
            phase1_results = list(await asyncio.gather(*burst_tasks))
            t_burst_end = time.perf_counter()
            p1_succ = sum(1 for r in phase1_results if r["success"])
            print(
                f"   + Hoàn tất Pha 1 trong {(t_burst_end - t_burst_start) * 1000:.1f} ms: "
                f"Thành công {p1_succ}/{len(phase1_results)}"
            )

            # =========================================================
            # 8. PHA 2 - SUSTAINED: Open-loop theo lịch cố định t0 + i/rate
            # =========================================================
            print(
                f"\n6. PHA 2 - SUSTAINED OPEN-LOOP ({args.rate} RPS x {args.duration}s = {len(phase2_plan)} request):"
            )
            print(
                f"{'Giây':<6} | {'Đã gửi':>8} | {'Đã xong':>8} | {'RPS gửi':>8} | {'RPS xong':>8} | "
                f"{'p50(ms)':>8} | {'p95(ms)':>8} | {'Max(ms)':>8} | {'Lỗi theo mã HTTP'}"
            )
            print("-" * 102)

            sem = asyncio.Semaphore(args.workers)
            in_flight_tasks = []
            completed_p2 = []
            sent_timestamps = []

            t0 = time.perf_counter()
            rate = float(args.rate)
            duration_sec = int(args.duration)

            async def sustained_worker(item, sched_t):
                async with sem:
                    res = await execute_single_item(
                        client, item, sku_to_id, manifest, manifest_dirty, sched_time=sched_t
                    )
                    completed_p2.append(res)
                    return res

            next_idx = 0
            total_p2 = len(phase2_plan)
            consecutive_high_5xx_secs = 0
            last_completed_idx = 0
            last_sent_idx = 0

            for sec_idx in range(1, duration_sec + 1):
                sec_end_t = t0 + sec_idx
                while next_idx < total_p2:
                    sched_t = t0 + (next_idx / rate)
                    if sched_t >= sec_end_t and sec_idx < duration_sec:
                        break
                    now_t = time.perf_counter()
                    wait_s = sched_t - now_t
                    if wait_s > 0:
                        await asyncio.sleep(wait_s)
                    sent_timestamps.append(time.perf_counter())
                    t_task = asyncio.create_task(sustained_worker(phase2_plan[next_idx], sched_t))
                    in_flight_tasks.append(t_task)
                    next_idx += 1
                    if next_idx >= sec_idx * int(rate):
                        break

                rem = sec_end_t - time.perf_counter()
                if rem > 0:
                    await asyncio.sleep(rem)

                cur_sent_total = len(sent_timestamps)
                cur_comp_snapshot = list(completed_p2)
                cur_comp_total = len(cur_comp_snapshot)

                sent_this_sec = cur_sent_total - last_sent_idx
                comp_slice = cur_comp_snapshot[last_completed_idx:cur_comp_total]
                comp_this_sec = len(comp_slice)

                last_sent_idx = cur_sent_total
                last_completed_idx = cur_comp_total

                sec_lats = sorted(r["latency_ms"] for r in comp_slice)
                s_p50 = percentile(sec_lats, 50)
                s_p95 = percentile(sec_lats, 95)
                s_max = sec_lats[-1] if sec_lats else 0.0
                sec_errs = Counter(r["status_code"] for r in comp_slice if not r["success"])
                err_str = dict(sec_errs) if sec_errs else "{}"

                print(
                    f"Giây {sec_idx:<2}| {cur_sent_total:>8} | {cur_comp_total:>8} | "
                    f"{sent_this_sec:>8.1f} | {comp_this_sec:>8.1f} | "
                    f"{s_p50:>8.1f} | {s_p95:>8.1f} | {s_max:>8.1f} | {err_str}",
                    flush=True,
                )

                per_second_stats.append({
                    "sec": sec_idx,
                    "cum_sent": cur_sent_total,
                    "cum_done": cur_comp_total,
                    "rps_sent": sent_this_sec,
                    "rps_done": comp_this_sec,
                    "p50": s_p50,
                    "p95": s_p95,
                    "max": s_max,
                    "errors": dict(sec_errs),
                })

                if comp_this_sec > 0:
                    cnt_5xx = sum(
                        1 for r in comp_slice if not r["success"] and 500 <= r["status_code"] < 600
                    )
                    ratio_5xx = cnt_5xx / comp_this_sec
                    if ratio_5xx > 0.30:
                        consecutive_high_5xx_secs += 1
                    else:
                        consecutive_high_5xx_secs = 0

                    if consecutive_high_5xx_secs >= 2:
                        aborted_reason = (
                            f"Tự động dừng bắn tải: Tỷ lệ lỗi 5xx > 30% trong 2 giây liên tiếp "
                            f"(Giây {sec_idx - 1} & Giây {sec_idx})."
                        )
                        print(f"\n[CIRCUIT BREAKER] {aborted_reason}", flush=True)
                        break

            if in_flight_tasks:
                await asyncio.gather(*in_flight_tasks, return_exceptions=True)
            t_p2_end = time.perf_counter()
            p2_total_elapsed = t_p2_end - t0
            phase2_results = list(completed_p2)

        except KeyboardInterrupt:
            aborted_reason = "Người dùng nhấn Ctrl+C (KeyboardInterrupt) — Dừng bắn tải, giữ manifest và in báo cáo một phần."
            print(f"\n[KEYBOARD INTERRUPT] {aborted_reason}", flush=True)
            phase2_results = list(completed_p2)
            p2_total_elapsed = max(0.001, time.perf_counter() - t0) if "t0" in locals() else 1.0
        finally:
            stop_flush_event.set()
            try:
                await flusher_task
            except Exception:
                pass
            write_manifest_sync(manifest)

        # =========================================================
        # 10. BÁO CÁO CUỐI & ĐỐI CHIẾU TOÀN VẸN
        # =========================================================
        print("\n" + "=" * 78)
        print(" 7. BÁO CÁO TỔNG KẾT CHI TIẾT")
        print("=" * 78)
        if aborted_reason:
            print(f"  [!] Trạng thái dừng sớm: {aborted_reason}")

        format_phase_report("PHA 1 (BURST)", phase1_results)
        format_phase_report("PHA 2 (SUSTAINED)", phase2_results)

        if phase2_results:
            drifts = [r["drift_ms"] for r in phase2_results]
            avg_drift = sum(drifts) / len(drifts)
            max_drift = max(drifts)
            actual_send_rps = len(phase2_results) / max(0.001, float(args.duration))
            actual_done_rps = len(phase2_results) / max(0.001, p2_total_elapsed)
            print(f"\n--- ĐÁNH GIÁ LỊCH BẮN OPEN-LOOP (PHA 2) ---")
            print(f"  • Mục tiêu RPS                : {args.rate:.1f} req/s")
            print(f"  • RPS phát thực tế trung bình : {actual_send_rps:.1f} req/s")
            print(f"  • RPS hoàn tất trung bình     : {actual_done_rps:.1f} req/s (Tổng thời gian hoàn tất: {p2_total_elapsed:.2f}s)")
            print(f"  • Độ trễ lịch bắn (Drift)     : Trung bình = {avg_drift:.2f} ms | Cực đại = {max_drift:.2f} ms")
            if avg_drift > 20.0:
                print(
                    "  ⚠️ [CẢNH BÁO BOTTLENECK CLIENT] Độ trễ lịch bắn trung bình > 20ms! "
                    "Client là nút thắt, không phải Server; RPS thực tế đạt được có thể thấp hơn mục tiêu."
                )
            else:
                print("  ✅ [CLIENT OK] Độ trễ lịch bắn <= 20ms (Lịch phát Open-Loop chính xác).")

        all_results = phase1_results + phase2_results
        locked_count = sum(1 for r in all_results if r["locked_hit"])
        conflict_409_count = sum(1 for r in all_results if not r["success"] and r["status_code"] == 409)
        err_5xx_count = sum(1 for r in all_results if not r["success"] and 500 <= r["status_code"] < 600)

        print("\n--- THỐNG KÊ RIÊNG CÁC LỖI TRỌNG YẾU ---")
        print(f"  • Số lần gặp 'database is locked' : {locked_count}")
        print(f"  • Số lần gặp lỗi 409 Conflict     : {conflict_409_count}")
        print(f"  • Số lần gặp lỗi 5xx Server Error : {err_5xx_count}")

        print("\n" + "=" * 78)
        print(" 8. ĐỐI CHIẾU TỒN KHO & KIỂM TOÁN BẤT BIẾN SỔ CÁI (THẺ KHO)")
        print("=" * 78)

        conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
        try:
            cur = conn.cursor()
            all_checks_passed = True

            for sku in ["SKU-DEMO-A", "SKU-DEMO-B"]:
                pid = sku_to_id[sku]
                ps = plan_summary[sku]

                succ_in_qty = sum(
                    r["quantity"] for r in all_results
                    if r["sku"] == sku and r["tx_type"] == "IMPORT" and r["success"]
                )
                succ_out_qty = sum(
                    r["quantity"] for r in all_results
                    if r["sku"] == sku and r["tx_type"] == "EXPORT" and r["success"]
                )
                expected_by_success = ps["initial_stock"] + succ_in_qty - succ_out_qty

                cur.execute("SELECT current_stock FROM products WHERE id = ?", (pid,))
                row = cur.fetchone()
                actual_db_stock = row[0] if row else None

                sku_pass = (actual_db_stock == expected_by_success)
                if not sku_pass:
                    all_checks_passed = False

                print(f"\n[{sku}] (Product ID = {pid}):")
                print(f"  Tồn đầu                         : {ps['initial_stock']}")
                print(f"  Kỳ vọng theo kế hoạch           : {ps['expected_final']} (Nhập +{ps['import_qty']}, Xuất -{ps['export_qty']})")
                print(f"  Kỳ vọng theo request thành công : {expected_by_success} (Nhập +{succ_in_qty}, Xuất -{succ_out_qty})")
                print(f"  Thực tế đọc từ DB               : {actual_db_stock}")
                print(f"  => {'PASS' if sku_pass else 'FAIL'}")

            p_ids = (sku_to_id["SKU-DEMO-A"], sku_to_id["SKU-DEMO-B"])
            cur.execute(
                """
                SELECT id, product_id, transaction_type, reference_code, quantity_change, balance_after
                FROM stock_ledger
                WHERE product_id IN (?, ?)
                ORDER BY id ASC
                """,
                p_ids,
            )
            ledger_rows = cur.fetchall()
            ledger_by_ref = defaultdict(list)
            for l_row in ledger_rows:
                ledger_by_ref[l_row[3]].append(l_row)

            missing_in_ledger = []
            extra_for_success = []
            leaked_failed_in_ledger = []

            for r in all_results:
                ref_rows = ledger_by_ref.get(r["code"], [])
                if r["success"]:
                    if len(ref_rows) == 0:
                        missing_in_ledger.append(r["code"])
                    elif len(ref_rows) > 1:
                        extra_for_success.append((r["code"], len(ref_rows)))
                else:
                    if len(ref_rows) > 0:
                        leaked_failed_in_ledger.append(r["code"])

            check1_pass = (
                len(missing_in_ledger) == 0
                and len(extra_for_success) == 0
                and len(leaked_failed_in_ledger) == 0
                and len(ledger_rows) == sum(1 for r in all_results if r["success"])
            )
            if not check1_pass:
                all_checks_passed = False

            chain_errors = []
            for sku in ["SKU-DEMO-A", "SKU-DEMO-B"]:
                pid = sku_to_id[sku]
                sku_ledgers = [row for row in ledger_rows if row[1] == pid]
                prev_balance = plan_summary[sku]["initial_stock"]
                for l_row in sku_ledgers:
                    l_id, _, _, ref_c, q_chg, bal_after = l_row
                    if bal_after != prev_balance + q_chg:
                        chain_errors.append(
                            f"{sku} ledger_id={l_id} ({ref_c}): prev={prev_balance} + ({q_chg}) != {bal_after}"
                        )
                    prev_balance = bal_after
            check2_pass = len(chain_errors) == 0
            if not check2_pass:
                all_checks_passed = False

            neg_ledger_rows = [row for row in ledger_rows if row[5] < 0]
            check3_pass = len(neg_ledger_rows) == 0
            if not check3_pass:
                all_checks_passed = False

            cur.execute("SELECT code, count(*) FROM import_notes GROUP BY code HAVING count(*) > 1")
            dup_imp = cur.fetchall()
            cur.execute("SELECT code, count(*) FROM export_notes GROUP BY code HAVING count(*) > 1")
            dup_exp = cur.fetchall()
            check4_pass = (len(dup_imp) == 0 and len(dup_exp) == 0)
            if not check4_pass:
                all_checks_passed = False

            print("\n--- KIỂM TRA 4 BẤT BIẾN SỔ CÁI & CHỨNG TỪ ---")
            print(
                f"  1. Request 200 <-> đúng 1 dòng ledger, request lỗi = 0 dòng : "
                f"{'PASS' if check1_pass else 'FAIL'} (Tổng 200 OK = {sum(1 for r in all_results if r['success'])}, Tổng dòng ledger = {len(ledger_rows)})"
            )
            if not check1_pass:
                if missing_in_ledger:
                    print(f"     [!] Nhận 200 nhưng thiếu ledger: {missing_in_ledger[:20]}")
                if extra_for_success:
                    print(f"     [!] Nhận 200 nhưng ghi lặp ledger: {extra_for_success[:20]}")
                if leaked_failed_in_ledger:
                    print(f"     [!] Request lỗi nhưng vẫn có ledger: {leaked_failed_in_ledger[:20]}")

            print(
                f"  2. Lũy kế balance_after[i] = balance_after[i-1] + change[i] : "
                f"{'PASS' if check2_pass else 'FAIL'} ({len(chain_errors)} lỗi)"
            )
            if not check2_pass:
                for ce in chain_errors[:10]:
                    print(f"     [!] {ce}")

            print(
                f"  3. Không có tồn âm ở bất kỳ thời điểm nào trong ledger       : "
                f"{'PASS' if check3_pass else 'FAIL'} ({len(neg_ledger_rows)} dòng âm)"
            )

            print(
                f"  4. Mã phiếu nhập/xuất không trùng lặp                        : "
                f"{'PASS' if check4_pass else 'FAIL'} (Trùng PN={len(dup_imp)}, Trùng PX={len(dup_exp)})"
            )

            print("\n" + "=" * 78)
            print(f" KẾT LUẬN CUỐI CÙNG: {'PASS TOÀN BỘ (100% CHÍNH XÁC)' if all_checks_passed else 'FAIL (CÓ BẤT BIẾN VI PHẠM)'}")
            print(" 💡 Bạn có thể mở http://localhost:5173 (bấm F5 / Làm mới) để quan sát trực tiếp")
            print("    SKU-DEMO-A, SKU-DEMO-B, các phiếu PN-DEMO / PX-DEMO và Thẻ kho ngay trên Web!")
            print(" 💡 Khi xem xong, chạy `python backend/tests/performance/demo_cleanup.py --yes` để thu hồi sạch sẽ.")
            print("=" * 78)

        finally:
            conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Demo chịu tải Xuất/Nhập kho đồng thời")
    parser.add_argument(
        "--profile",
        choices=list(PROFILES.keys()),
        default="stress100",
        help="Profile cấu hình tải (demo=5x10s, medium=20x15s, heavy=50x20s, stress100=100x10s)",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL mục tiêu (mặc định: http://127.0.0.1:8000 để hiển thị trực tiếp trên Web)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Đường dẫn tới file CSDL")
    parser.add_argument("--gap", type=float, default=1.0, help="Số giây chờ giữa khi tạo DEMO-A và DEMO-B (mặc định: 1)")
    parser.add_argument("--wait", type=int, default=5, help="Số giây đếm ngược trước khi bắn (mặc định: 5)")
    parser.add_argument("--burst", type=int, default=None, help="Số request bắn cùng lúc ở Pha 1 (mặc định: 20)")
    parser.add_argument("--rate", type=int, default=None, help="Số request/giây ở Pha 2 (mặc định theo profile)")
    parser.add_argument("--duration", type=int, default=None, help="Thời lượng giây ở Pha 2 (mặc định theo profile)")
    parser.add_argument("--initial", type=int, default=None, help="Tồn kho đầu kỳ của DEMO-A và DEMO-B (mặc định: 2000)")
    parser.add_argument("--workers", type=int, default=None, help="Số worker / kết nối đồng thời tối đa (mặc định: 200)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed lập kế hoạch tiền định (mặc định: 42)")
    parser.add_argument("--username", default="admin", help="Tài khoản đăng nhập API")
    parser.add_argument("--password", default="admin123", help="Mật khẩu đăng nhập API")

    args = parser.parse_args()
    prof = PROFILES[args.profile]
    if args.burst is None:
        args.burst = prof["burst"]
    if args.rate is None:
        args.rate = prof["rate"]
    if args.duration is None:
        args.duration = prof["duration"]
    if args.initial is None:
        args.initial = prof["initial"]
    if args.workers is None:
        args.workers = prof["workers"]
    return args


if __name__ == "__main__":
    cli_args = parse_args()
    asyncio.run(run_demo(cli_args))
