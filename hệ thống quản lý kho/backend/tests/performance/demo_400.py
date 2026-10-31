"""STRESS TEST SmartKho: bắn liên tục 10 giây, tổng 400 giao dịch (200 Phiếu Nhập + 200 Phiếu Xuất).

Mục tiêu: đặt hệ thống dưới tải VƯỢT năng lực, rồi xem nó (1) có sống sót không, (2) dữ liệu có còn đúng không,
(3) năng lực thực đo là bao nhiêu và hàng đợi mất bao lâu để xả. "10 giây" là thời gian BẮN, không phải hạn chót hoàn tất.

File độc lập duy nhất:
- Không import bất kỳ module nào của repo; chỉ dùng thư viện chuẩn Python + httpx.
- Nội dung CỐ ĐỊNH: 1 sản phẩm SKU-D400, 200 phiếu nhập PN-D400-* (+5 đv), 200 phiếu xuất PX-D400-* (-3 đv).
- Lịch bắn Open-loop: 40 giao dịch/giây (20 nhập + 20 xuất đan xen), 1 giao dịch mỗi 25ms.
  (Mỗi giao dịch XUẤT gồm 2 lượt gọi API: tạo phiếu + /ship => tổng ~600 HTTP request.)
- Chế độ chạy:
    • python backend/tests/performance/demo_400.py           (Chạy demo và kiểm chứng)
    • python backend/tests/performance/demo_400.py --cleanup (Thu hồi sạch sẽ dữ liệu)
    • python backend/tests/performance/demo_400.py --verify-only (Chỉ kiểm toán CSDL hiện tại)

Báo cáo cuối gồm: bảng theo từng giây, biểu đồ phân bố độ trễ, xu hướng độ trễ theo giây phát,
mẫu phản hồi THẬT của server, đọc lại số liệu qua API (giống cái Dashboard sẽ hiển thị),
đối chiếu CSDL, và phần chẩn đoán được rút ra từ số đo thực tế (không viết sẵn).
"""

import argparse
import asyncio
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ==============================================================================
# 1. TỰ ĐỘNG ỦY QUYỀN VÀO DOCKER CONTAINER NẾU CHẠY TỪ WINDOWS
# ==============================================================================
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
            # Đồng bộ file demo_400.py vào container trước khi thực thi
            this_file_path = os.path.abspath(__file__)
            subprocess.run(
                ["docker", "cp", this_file_path, "warehouse_backend:/app/tests/performance/demo_400.py"],
                capture_output=True,
                check=False,
            )

            # Lọc các tham số Windows không tương thích
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
                "python", "-u", "/app/tests/performance/demo_400.py",
                *forwarded_args,
            ]
            res = subprocess.run(cmd, check=False)
            sys.exit(res.returncode)

import httpx

# ==============================================================================
# 2. CẤU HÌNH CỐ ĐỊNH (FIXED SPECIFICATION - KHÔNG DÙNG RANDOM)
# ==============================================================================
PERF_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(PERF_DIR, "..", ".."))

db_env = os.environ.get("DATABASE_URL", "")
if db_env.startswith("sqlite:///"):
    DEFAULT_DB_PATH = db_env.replace("sqlite:///", "")
elif os.path.exists("/var/lib/warehouse/warehouse.db"):
    DEFAULT_DB_PATH = "/var/lib/warehouse/warehouse.db"
else:
    DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "warehouse.db")

BACKUP_DIR = os.path.join(BACKEND_DIR, "backups")
PRE_D400_BACKUP_PATH = os.path.join(BACKUP_DIR, "warehouse_pre_d400_backup.db")
MANIFEST_PATH = os.path.join(PERF_DIR, "demo_400_manifest.json")
RESULT_PATH = os.path.join(PERF_DIR, "demo_400_result.json")

TOTAL_TX = 400
RATE = 40.0              # 40 giao dịch/giây (20 nhập + 20 xuất)
INTERVAL = 1.0 / RATE    # 0.025 giây

SKU_CODE = "SKU-D400"
SKU_NAME = "Sản phẩm Demo 400"
SKU_CATEGORY_ID = 1
SKU_SUPPLIER_ID = 1
SKU_UNIT = "Cái"
SKU_MIN_STOCK = 10
SKU_INITIAL_STOCK = 1000
SKU_STANDARD_PRICE = 100000.0
SKU_IMAGE_URL = "https://tse4.mm.bing.net/th/id/OIP.OpneO1xDmvuH8kkQpPP3iwHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3"

IMPORT_QTY = 5
IMPORT_PRICE = 80000.0
EXPORT_QTY = 3
EXPORT_PRICE = 100000.0

EXPECTED_IMPORT_COUNT = 200
EXPECTED_EXPORT_COUNT = 200
EXPECTED_IMPORT_SUM = EXPECTED_IMPORT_COUNT * IMPORT_QTY  # +1000
EXPECTED_EXPORT_SUM = EXPECTED_EXPORT_COUNT * EXPORT_QTY  # -600
EXPECTED_NET_CHANGE = EXPECTED_IMPORT_SUM - EXPECTED_EXPORT_SUM  # +400
EXPECTED_FINAL_STOCK = SKU_INITIAL_STOCK + EXPECTED_NET_CHANGE   # 1400

MAX_SCHEDULE_DRIFT_MS = 100.0  # bộ phát tải lệch lịch quá mức này => số đo không còn đáng tin

SNAPSHOT_TABLES = [
    "products",
    "import_notes",
    "import_note_details",
    "export_notes",
    "export_note_details",
    "stock_ledger",
]


# ==============================================================================
# 3. CÁC HÀM TIỆN ÍCH DỮ LIỆU & TOÁN HỌC
# ==============================================================================
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


def ascii_bar(value: float, vmax: float, width: int = 32) -> str:
    if vmax <= 0:
        return ""
    n = int(round(width * value / vmax))
    if value > 0 and n == 0:
        n = 1
    return "█" * n


def one_line(text: str, limit: int = 220) -> str:
    s = " ".join((text or "").split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def get_db_snapshot(db_path: str) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        snap = {}
        for tbl in SNAPSHOT_TABLES:
            cur.execute(f"SELECT count(*) FROM {tbl}")
            snap[tbl] = cur.fetchone()[0]
        cur.execute("SELECT sum(current_stock) FROM products")
        snap["total_stock"] = cur.fetchone()[0] or 0
        return snap
    finally:
        conn.close()


def get_all_table_counts(db_path: str) -> dict:
    """Số dòng của MỌI bảng người dùng (để phát hiện bảng phụ như nhật ký/thông báo bị server ghi thêm)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        names = [r[0] for r in cur.fetchall()]
        counts = {}
        for n in names:
            try:
                cur.execute(f'SELECT count(*) FROM "{n}"')
                counts[n] = cur.fetchone()[0]
            except sqlite3.Error:
                counts[n] = None
        return counts
    finally:
        conn.close()


def get_other_skus_stock(db_path: str) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT code, current_stock FROM products WHERE code != ?", (SKU_CODE,))
        return {code: stock for code, stock in cur.fetchall()}
    finally:
        conn.close()


def table_has_col(cur, table: str, col: str) -> bool:
    cur.execute(f'PRAGMA table_info("{table}")')
    return any(r[1] == col for r in cur.fetchall())


def write_manifest_sync(manifest_data: dict):
    tmp_path = f"{MANIFEST_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, MANIFEST_PATH)


def verify_environment_guard(base_url: str, db_path: str) -> str:
    parsed = urlparse(base_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    abs_db = os.path.abspath(db_path)

    print("=" * 78)
    print(" KIỂM TRA AN TOÀN MÔI TRƯỜNG & SAO LƯU DỰ PHÒNG (SAFETY GUARD)")
    print("=" * 78)
    print(f"  • Base URL mục tiêu : {base_url} (Port: {port})")
    print(f"  • CSDL mục tiêu     : {abs_db}")
    print(f"  • Giao diện Web     : http://localhost:5173 (Quan sát trực tiếp sau khi chạy)")

    if parsed.hostname not in ("127.0.0.1", "localhost", "backend", "warehouse_backend"):
        print("\n[GUARD BLOCKED] Chỉ cho phép chạy demo trên localhost / 127.0.0.1 / backend!")
        sys.exit(1)

    if not os.path.exists(abs_db):
        print(f"\n[GUARD BLOCKED] Không tìm thấy file CSDL tại: {abs_db}")
        sys.exit(1)

    # Kiểm tra xem có dữ liệu SKU-D400 cũ chưa dọn không
    conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, code FROM products WHERE code = ?", (SKU_CODE,))
        ex_prod = cur.fetchall()
        cur.execute("SELECT id, code FROM import_notes WHERE code LIKE 'PN-D400-%'")
        ex_imp = cur.fetchall()
        cur.execute("SELECT id, code FROM export_notes WHERE code LIKE 'PX-D400-%'")
        ex_exp = cur.fetchall()

        if ex_prod or ex_imp or ex_exp:
            print(f"\n[CẢNH BÁO] Phát hiện dữ liệu Demo 400 còn sót lại:")
            if ex_prod:
                print(f"  • Sản phẩm: {ex_prod}")
            if ex_imp:
                print(f"  • Phiếu nhập: {len(ex_imp)} phiếu")
            if ex_exp:
                print(f"  • Phiếu xuất: {len(ex_exp)} phiếu")
            print("Vui lòng chạy `python backend/tests/performance/demo_400.py --cleanup` trước khi chạy lượt mới.")
            sys.exit(1)
    finally:
        conn.close()

    # Sao lưu an toàn trực tuyến
    os.makedirs(BACKUP_DIR, exist_ok=True)
    src_conn = sqlite3.connect(abs_db, timeout=15.0)
    dst_conn = sqlite3.connect(PRE_D400_BACKUP_PATH, timeout=15.0)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    print(f"  • Bản sao lưu dự phòng: {PRE_D400_BACKUP_PATH}")
    print("  => [GUARD PASS] Môi trường sẵn sàng & đã sao lưu dự phòng an toàn.\n")
    return abs_db


# ==============================================================================
# 4. KẾ HOẠCH BẮN CỐ ĐỊNH & THỰC THI GIAO DỊCH
# ==============================================================================
def build_fixed_plan():
    """Tạo 400 giao dịch cố định:
    k = 0..399
    k chẵn: NHẬP, n = k//2 + 1 (1..200), PN-D400-{n:04d}, qty=5, price=80,000
    k lẻ:   XUẤT, n = k//2 + 1 (1..200), PX-D400-{n:04d}, qty=3, price=100,000
    """
    plan = []
    for k in range(TOTAL_TX):
        n = k // 2 + 1
        is_import = (k % 2 == 0)
        if is_import:
            plan.append({
                "k": k,
                "n": n,
                "tx_type": "IMPORT",
                "code": f"PN-D400-{n:04d}",
                "quantity": IMPORT_QTY,
                "unit_price": IMPORT_PRICE,
                "note": f"D400 nhap {n:04d}",
            })
        else:
            plan.append({
                "k": k,
                "n": n,
                "tx_type": "EXPORT",
                "code": f"PX-D400-{n:04d}",
                "recipient_name": "Khach D400",
                "quantity": EXPORT_QTY,
                "unit_price": EXPORT_PRICE,
                "note": f"D400 xuat {n:04d}",
            })
    return plan


async def execute_transaction(
    client: httpx.AsyncClient,
    item: dict,
    product_id: int,
    manifest: dict,
    manifest_dirty: list,
    sched_time: float,
) -> dict:
    t_send = time.perf_counter()
    drift_ms = (t_send - sched_time) * 1000.0 if sched_time is not None else 0.0

    tx_type = item["tx_type"]
    code = item["code"]
    qty = item["quantity"]

    status_code = 0
    err_detail = ""
    locked_hit = False
    note_id = None
    http_calls = 0
    server_response = ""

    try:
        if tx_type == "IMPORT":
            payload = {
                "code": code,
                "supplier_id": SKU_SUPPLIER_ID,
                "note": item["note"],
                "details": [
                    {
                        "product_id": product_id,
                        "quantity": qty,
                        "unit_price": item["unit_price"],
                    }
                ],
            }
            resp = await client.post("/api/v1/import-notes/", json=payload)
            http_calls += 1
            status_code = resp.status_code
            server_response = resp.text[:300]
            if status_code in (200, 201):
                data = resp.json()
                note_id = data.get("id")
                manifest["created_import_notes"].append({
                    "id": note_id,
                    "code": code,
                    "n": item["n"],
                    "quantity": qty,
                })
                manifest_dirty[0] = True
            else:
                err_detail = resp.text[:250]
                if "database is locked" in err_detail.lower():
                    locked_hit = True

        else:  # EXPORT
            payload = {
                "code": code,
                "recipient_name": item["recipient_name"],
                "note": item["note"],
                "details": [
                    {
                        "product_id": product_id,
                        "quantity": qty,
                        "unit_price": item["unit_price"],
                    }
                ],
            }
            resp_create = await client.post("/api/v1/export-notes/", json=payload)
            http_calls += 1
            if resp_create.status_code not in (200, 201):
                status_code = resp_create.status_code
                err_detail = resp_create.text[:250]
                server_response = f"create[{resp_create.status_code}] {resp_create.text[:250]}"
                if "database is locked" in err_detail.lower():
                    locked_hit = True
            else:
                c_data = resp_create.json()
                note_id = c_data.get("id")
                # Gọi tiếp /ship
                resp_ship = await client.post(f"/api/v1/export-notes/{note_id}/ship")
                http_calls += 1
                status_code = resp_ship.status_code
                server_response = (
                    f"create[{resp_create.status_code}] {resp_create.text[:140]} || "
                    f"ship[{resp_ship.status_code}] {resp_ship.text[:140]}"
                )
                if status_code in (200, 201):
                    manifest["created_export_notes"].append({
                        "id": note_id,
                        "code": code,
                        "n": item["n"],
                        "quantity": qty,
                        "shipped": True,
                    })
                    manifest_dirty[0] = True
                else:
                    err_detail = resp_ship.text[:250]
                    if "database is locked" in err_detail.lower():
                        locked_hit = True
                    # Nếu ship lỗi: xóa phiếu nháp
                    try:
                        del_r = await client.delete(f"/api/v1/export-notes/{note_id}")
                        http_calls += 1
                        if del_r.status_code not in (200, 204):
                            manifest["created_export_notes"].append({
                                "id": note_id,
                                "code": code,
                                "n": item["n"],
                                "quantity": qty,
                                "shipped": False,
                            })
                            manifest_dirty[0] = True
                    except Exception:
                        manifest["created_export_notes"].append({
                            "id": note_id,
                            "code": code,
                            "n": item["n"],
                            "quantity": qty,
                            "shipped": False,
                        })
                        manifest_dirty[0] = True

    except httpx.TimeoutException as exc:
        status_code = 599
        err_detail = f"Timeout: {exc}"
    except Exception as exc:
        status_code = 598
        err_detail = str(exc)[:250]
        if "database is locked" in err_detail.lower():
            locked_hit = True

    t_done = time.perf_counter()
    latency_ms = (t_done - t_send) * 1000.0
    is_success = status_code in (200, 201)

    return {
        "k": item["k"],
        "n": item["n"],
        "tx_type": tx_type,
        "code": code,
        "quantity": qty,
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
        "http_calls": http_calls,
        "server_response": server_response,
    }


# ==============================================================================
# 5. KIỂM TOÁN VÀ ĐỐI CHIẾU SỔ CÁI (READ-ONLY)
# ==============================================================================
def results_from_ledger(abs_db: str, product_id: int) -> list:
    """Dùng cho --verify-only khi không có file kết quả: dựng 'kết quả' từ chính Thẻ kho."""
    conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT reference_code, quantity_change FROM stock_ledger WHERE product_id = ? ORDER BY id ASC",
            (product_id,),
        )
        return [
            {
                "code": ref,
                "tx_type": "IMPORT" if q > 0 else "EXPORT",
                "quantity": abs(q),
                "success": True,
            }
            for ref, q in cur.fetchall()
        ]
    finally:
        conn.close()


def verify_ledger_invariants(
    abs_db: str,
    product_id: int,
    snapshot_before: dict,
    all_results: list,
    other_skus_before: dict = None,
    extra_drafts: int = 0,
    snapshot_after_product: dict = None,
):
    """Kiểm toán đối chiếu: tồn kho, số dòng 6 bảng (kỳ vọng tính từ kết quả THỰC TẾ),
    tồn các SKU khác, và các bất biến Thẻ kho."""
    conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
    cur = conn.cursor()

    try:
        # 1. Tồn SKU-D400
        cur.execute("SELECT current_stock FROM products WHERE id = ?", (product_id,))
        row_prod = cur.fetchone()
        actual_sku_stock = row_prod[0] if row_prod else None

        succ_imp_cnt = sum(1 for r in all_results if r["tx_type"] == "IMPORT" and r["success"])
        succ_exp_cnt = sum(1 for r in all_results if r["tx_type"] == "EXPORT" and r["success"])
        succ_imp_qty = sum(r["quantity"] for r in all_results if r["tx_type"] == "IMPORT" and r["success"])
        succ_exp_qty = sum(r["quantity"] for r in all_results if r["tx_type"] == "EXPORT" and r["success"])
        expected_stock_by_succ = SKU_INITIAL_STOCK + succ_imp_qty - succ_exp_qty

        # 2. Số dòng 6 bảng: kỳ vọng = baseline + những gì THỰC SỰ thành công
        cur_snapshot = {}
        for tbl in SNAPSHOT_TABLES:
            cur.execute(f"SELECT count(*) FROM {tbl}")
            cur_snapshot[tbl] = cur.fetchone()[0]

        # Mốc = số dòng NGAY SAU khi tạo SKU (đã gồm bản ghi tồn đầu hệ thống tự sinh, nếu có)
        base = snapshot_after_product or {}
        tables_checked = all(t in base for t in SNAPSHOT_TABLES)
        exp_tables = {}
        table_pass = {}
        if tables_checked:
            exp_tables = {
                "products": base["products"],
                "import_notes": base["import_notes"] + succ_imp_cnt,
                "import_note_details": base["import_note_details"] + succ_imp_cnt,
                "export_notes": base["export_notes"] + succ_exp_cnt + extra_drafts,
                "export_note_details": base["export_note_details"] + succ_exp_cnt + extra_drafts,
                "stock_ledger": base["stock_ledger"] + succ_imp_cnt + succ_exp_cnt,
            }
            table_pass = {t: cur_snapshot[t] == exp_tables[t] for t in SNAPSHOT_TABLES}
        tables_all_pass = (not tables_checked) or all(table_pass.values())

        # 3. Tổng tồn toàn kho
        cur.execute("SELECT sum(current_stock) FROM products")
        actual_total_stock = cur.fetchone()[0] or 0
        total_checked = "total_stock" in snapshot_before
        expected_total_stock = (snapshot_before["total_stock"] + expected_stock_by_succ) if total_checked else None
        total_stock_pass = (actual_total_stock == expected_total_stock) if total_checked else True

        # 4. Tồn các SKU khác không bị đụng tới
        sku_changes = []
        if other_skus_before:
            cur.execute("SELECT code, current_stock FROM products WHERE code != ?", (SKU_CODE,))
            for c_code, c_stock in cur.fetchall():
                if c_code in other_skus_before and other_skus_before[c_code] != c_stock:
                    sku_changes.append((c_code, other_skus_before[c_code], c_stock))
        others_pass = len(sku_changes) == 0

        # Đọc toàn bộ dòng thẻ kho của SKU-D400
        cur.execute(
            """
            SELECT id, product_id, transaction_type, reference_code, quantity_change, balance_after
            FROM stock_ledger
            WHERE product_id = ?
            ORDER BY id ASC
            """,
            (product_id,),
        )
        ledger_rows = cur.fetchall()

        # Tách dòng tồn đầu (hệ thống tự ghi khi tạo SKU, mã không thuộc PN/PX-D400) khỏi dòng giao dịch demo
        d400_prefixes = ("PN-D400-", "PX-D400-")
        opening_rows = [l for l in ledger_rows if not str(l[3] or "").startswith(d400_prefixes)]
        d400_rows = [l for l in ledger_rows if str(l[3] or "").startswith(d400_prefixes)]
        opening_sum = sum(l[4] for l in opening_rows)
        opening_ok = (len(opening_rows) == 0) or (opening_sum == SKU_INITIAL_STOCK)

        # Bất biến 1: Mỗi request thành công đúng 1 dòng ledger, lỗi 0 dòng
        ledger_by_ref = defaultdict(list)
        for l in ledger_rows:
            ledger_by_ref[l[3]].append(l)

        missing_ledger = []
        extra_ledger = []
        leaked_ledger = []
        for r in all_results:
            rows_ref = ledger_by_ref.get(r["code"], [])
            if r["success"]:
                if len(rows_ref) == 0:
                    missing_ledger.append(r["code"])
                elif len(rows_ref) > 1:
                    extra_ledger.append((r["code"], len(rows_ref)))
            else:
                if len(rows_ref) > 0:
                    leaked_ledger.append(r["code"])

        inv1_pass = (
            len(missing_ledger) == 0
            and len(extra_ledger) == 0
            and len(leaked_ledger) == 0
            and len(d400_rows) == (succ_imp_cnt + succ_exp_cnt)
        )

        # Bất biến 2: Lũy kế balance_after[i] = balance_after[i-1] + change[i]
        chain_errors = []
        prev_bal = 0 if opening_rows else SKU_INITIAL_STOCK
        for l in ledger_rows:
            lid, _, _, ref_c, q_chg, b_after = l
            if b_after != prev_bal + q_chg:
                chain_errors.append(f"ledger_id={lid} ({ref_c}): prev={prev_bal} + ({q_chg}) != {b_after}")
            prev_bal = b_after
        inv2_pass = len(chain_errors) == 0

        # Bất biến 3 (cũ: tồn âm) đã được hệ thống chặn ở tầng nghiệp vụ/giao diện nên bỏ khỏi bài này.
        neg_rows = [l for l in ledger_rows if l[5] < 0]
        inv3_pass = len(neg_rows) == 0  # vẫn đếm để in thông tin, nhưng không dùng để kết luận

        # Bất biến 4: Không trùng lặp mã phiếu
        cur.execute("SELECT code, count(*) FROM import_notes WHERE code LIKE 'PN-D400-%' GROUP BY code HAVING count(*) > 1")
        dup_imp = cur.fetchall()
        cur.execute("SELECT code, count(*) FROM export_notes WHERE code LIKE 'PX-D400-%' GROUP BY code HAVING count(*) > 1")
        dup_exp = cur.fetchall()
        inv4_pass = (len(dup_imp) == 0 and len(dup_exp) == 0)

        # Bất biến 5: Tổng change nhập/xuất khớp số lượng thành công
        sum_imp_ledger = sum(l[4] for l in d400_rows if l[4] > 0)
        sum_exp_ledger = sum(l[4] for l in d400_rows if l[4] < 0)
        inv5_pass = (sum_imp_ledger == succ_imp_qty and sum_exp_ledger == -succ_exp_qty)

        all_invariants_pass = (
            inv1_pass and inv2_pass and inv4_pass and inv5_pass and opening_ok
            and (actual_sku_stock == expected_stock_by_succ)
            and total_stock_pass
            and tables_all_pass
            and others_pass
        )

        return {
            "all_pass": all_invariants_pass,
            "actual_sku_stock": actual_sku_stock,
            "expected_sku_stock": expected_stock_by_succ,
            "sku_stock_pass": actual_sku_stock == expected_stock_by_succ,
            "actual_total_stock": actual_total_stock,
            "expected_total_stock": expected_total_stock,
            "total_checked": total_checked,
            "total_stock_pass": total_stock_pass,
            "cur_snapshot": cur_snapshot,
            "tables_checked": tables_checked,
            "exp_tables": exp_tables,
            "table_pass": table_pass,
            "tables_all_pass": tables_all_pass,
            "sku_changes": sku_changes,
            "others_pass": others_pass,
            "succ_imp_cnt": succ_imp_cnt,
            "succ_exp_cnt": succ_exp_cnt,
            "succ_imp_qty": succ_imp_qty,
            "succ_exp_qty": succ_exp_qty,
            "ledger_rows_count": len(ledger_rows),
            "d400_rows_count": len(d400_rows),
            "opening_rows_count": len(opening_rows),
            "opening_sum": opening_sum,
            "opening_ok": opening_ok,
            "inv1_pass": inv1_pass,
            "missing_ledger": missing_ledger,
            "extra_ledger": extra_ledger,
            "leaked_ledger": leaked_ledger,
            "inv2_pass": inv2_pass,
            "chain_errors": chain_errors,
            "inv3_pass": inv3_pass,
            "neg_rows": neg_rows,
            "inv4_pass": inv4_pass,
            "dup_imp": dup_imp,
            "dup_exp": dup_exp,
            "inv5_pass": inv5_pass,
            "sum_imp_ledger": sum_imp_ledger,
            "sum_exp_ledger": sum_exp_ledger,
        }
    finally:
        conn.close()


# ==============================================================================
# 6. CÁC HÀM IN BÁO CÁO TRỰC QUAN
# ==============================================================================
def print_latency_histogram(lats: list):
    print("\n--- PHÂN BỐ ĐỘ TRỄ (mỗi ▇ ≈ tỉ lệ giao dịch) ---")
    if not lats:
        print("  (không có dữ liệu)")
        return
    edges = [25, 50, 100, 250, 500, 1000, float("inf")]
    labels = ["≤ 25ms", "≤ 50ms", "≤ 100ms", "≤ 250ms", "≤ 500ms", "≤ 1s", "> 1s"]
    counts = [0] * len(edges)
    for v in lats:
        for i, e in enumerate(edges):
            if v <= e:
                counts[i] += 1
                break
    vmax = max(counts)
    total = len(lats)
    for lab, c in zip(labels, counts):
        print(f"  {lab:>8} | {ascii_bar(c, vmax, 36):<36} {c:>4} ({c * 100.0 / total:5.1f}%)")


def cohort_latency_by_send_second(answered: list, t0: float) -> dict:
    """Độ trễ theo 'giây mà giao dịch được gửi' -> thấy hàng đợi có dồn lên hay không."""
    cohorts = defaultdict(list)
    for r in answered:
        sec = int(r["t_send"] - t0)
        sec = min(max(sec, 0), 9)
        cohorts[sec].append(r["latency_ms"])
    return cohorts


def print_latency_trend(cohorts: dict):
    print("\n--- XU HƯỚNG ĐỘ TRỄ THEO GIÂY PHÁT (p95 của các giao dịch gửi ở giây đó) ---")
    if not cohorts:
        print("  (không có dữ liệu)")
        return
    p95s = {s: percentile(sorted(v), 95) for s, v in cohorts.items()}
    vmax = max(p95s.values()) if p95s else 0.0
    for s in sorted(p95s):
        lats = sorted(cohorts[s])
        print(
            f"  Giây {s + 1:<2} | {ascii_bar(p95s[s], vmax, 36):<36} "
            f"p95={p95s[s]:>7.1f}ms  p50={percentile(lats, 50):>7.1f}ms  (n={len(lats)})"
        )


def print_completion_timeline(buckets: Counter):
    print("\n--- TỐC ĐỘ HOÀN TẤT THEO GIÂY (giao dịch xong mỗi giây; theo kịp lịch = 40) ---")
    if not buckets:
        print("  (không có dữ liệu)")
        return
    last = max(buckets)
    vmax = max(max(buckets.values()), 40)
    for sec in range(last + 1):
        c = buckets.get(sec, 0)
        print(f"  Giây {sec + 1:<3}| {ascii_bar(c, vmax, 36):<36} {c:>3}")


def print_server_samples(all_results: list):
    print("\n--- MẪU PHẢN HỒI THẬT CỦA SERVER ---")
    ordered = sorted(all_results, key=lambda r: r["k"])
    imps = [r for r in ordered if r["tx_type"] == "IMPORT" and r.get("server_response")]
    exps = [r for r in ordered if r["tx_type"] == "EXPORT" and r.get("server_response")]

    picks = []
    for group in (imps, exps):
        if len(group) >= 2:
            picks += [group[0], group[-1]]
        else:
            picks += group

    for r in picks:
        print(
            f"  [{r['tx_type']:<6}] {r['code']} | HTTP {r['raw_status']} | {r['latency_ms']:.1f}ms\n"
            f"           {one_line(r['server_response'])}"
        )

    errs = [r for r in ordered if not r["success"]][:5]
    if errs:
        print("\n  ❌ 5 lỗi đầu tiên (nếu có):")
        for r in errs:
            print(
                f"  [{r['tx_type']:<6}] {r['code']} | HTTP {r['raw_status']} | {r['latency_ms']:.1f}ms\n"
                f"           {one_line(r.get('server_response') or r.get('err_detail', ''))}"
            )
    else:
        print("\n  ✅ Không có phản hồi lỗi nào từ server.")


async def fetch_api_readback(client: httpx.AsyncClient, product_id: int, all_results: list) -> dict:
    """Đọc lại qua API những gì Dashboard/Web sẽ thấy. Endpoint nào không có thì bỏ qua, không làm hỏng bài."""

    async def get(path):
        try:
            r = await client.get(path)
            ctype = r.headers.get("content-type", "")
            body = r.json() if ctype.startswith("application/json") else r.text[:200]
            return r.status_code, body
        except Exception as exc:
            return 0, str(exc)[:120]

    ordered = sorted(all_results, key=lambda r: r["k"])
    last_imp = next((r for r in reversed(ordered) if r["tx_type"] == "IMPORT" and r["success"] and r.get("note_id")), None)
    last_exp = next((r for r in reversed(ordered) if r["tx_type"] == "EXPORT" and r["success"] and r.get("note_id")), None)

    out = {"product": await get(f"/api/v1/products/{product_id}")}
    out["import_note"] = (
        (last_imp["code"], *(await get(f"/api/v1/import-notes/{last_imp['note_id']}"))) if last_imp else None
    )
    out["export_note"] = (
        (last_exp["code"], *(await get(f"/api/v1/export-notes/{last_exp['note_id']}"))) if last_exp else None
    )
    return out


def pick_fields(data, keys):
    if not isinstance(data, dict):
        return one_line(str(data), 160)
    return {k: data[k] for k in keys if k in data}


def print_api_readback(readback: dict, db_stock):
    print("\n--- SỐ LIỆU ĐỌC LẠI QUA API (giống những gì Web/Dashboard sẽ hiển thị) ---")
    st, body = readback["product"]
    if st == 200 and isinstance(body, dict):
        print(f"  • GET sản phẩm      : HTTP 200 -> {pick_fields(body, ['id', 'code', 'name', 'current_stock', 'min_stock', 'status'])}")
        api_stock = body.get("current_stock")
        if api_stock is not None:
            match = "KHỚP CSDL ✅" if api_stock == db_stock else f"LỆCH CSDL ({db_stock}) ⚠️"
            print(f"    Tồn theo API = {api_stock} | Tồn theo CSDL = {db_stock} -> {match}")
    else:
        print(f"  • GET sản phẩm      : không khả dụng (HTTP {st}) - bỏ qua")

    for label, key in (("phiếu nhập cuối", "import_note"), ("phiếu xuất cuối", "export_note")):
        item = readback.get(key)
        if not item:
            print(f"  • GET {label:<15}: (không có phiếu thành công)")
            continue
        code, st, body = item
        if st == 200:
            print(f"  • GET {label:<15}: {code} HTTP 200 -> {pick_fields(body, ['id', 'code', 'status', 'total_amount', 'recipient_name'])}")
        else:
            print(f"  • GET {label:<15}: {code} không khả dụng (HTTP {st}) - bỏ qua")


def diagnose(inflight_at_send_end, cohorts, locked_count, err_5xx, timeout_cnt, other_err, send_window, rate_during=None, rate_after=None) -> list:
    """Chẩn đoán RÚT RA TỪ SỐ ĐO. Không có số đo thì không kết luận."""
    notes = []
    if inflight_at_send_end > 20:
        notes.append(
            f"Hết cửa sổ phát ({send_window:.2f}s) vẫn còn {inflight_at_send_end} giao dịch chưa xong "
            f"-> server xử lý chậm hơn tốc độ phát, hàng đợi bị dồn."
        )
    if rate_during is not None and rate_after is not None and rate_after > 0 and rate_during < 0.7 * rate_after:
        notes.append(
            f"Trong lúc bị bắn tải server chỉ xong ~{rate_during:.1f} gd/s, nhưng sau khi ngừng bắn tăng lên ~{rate_after:.1f} gd/s "
            f"-> có thứ tranh tài nguyên khi đang bắn (máy chạy tải cùng container, trình duyệt Web đang mở nhận SSE, "
            f"hoặc quá nhiều kết nối đồng thời tranh khóa ghi). Nên thử chạy lại với trình duyệt đóng để so sánh."
        )
    p95s = [percentile(sorted(cohorts[s]), 95) for s in sorted(cohorts) if cohorts[s]]
    if len(p95s) >= 4:
        head = sum(p95s[:2]) / 2.0
        tail = sum(p95s[-2:]) / 2.0
        if tail > max(200.0, head * 3.0):
            notes.append(
                f"p95 tăng từ ~{head:.0f}ms (2 giây đầu) lên ~{tail:.0f}ms (2 giây cuối) "
                f"-> độ trễ leo dần theo thời gian, dấu hiệu quá tải hàng đợi chứ không phải chậm đều."
            )
    if locked_count:
        notes.append(f"Có {locked_count} lần 'database is locked' -> tranh chấp ghi SQLite (kiểm tra busy_timeout / số worker).")
    if err_5xx:
        notes.append(f"Có {err_5xx} lỗi 5xx từ server -> xem log backend (docker logs warehouse_backend) cho các mã lỗi ở mục mẫu phản hồi.")
    if timeout_cnt:
        notes.append(f"Có {timeout_cnt} timeout (>30s) -> server bị nghẽn nặng hoặc deadlock.")
    if other_err:
        notes.append(f"Có {other_err} lỗi phản hồi khác (4xx/lỗi kết nối) -> xem mẫu 5 lỗi đầu ở trên.")
    if not notes:
        notes.append("Không thấy dấu hiệu nghẽn: hàng đợi cuối cửa sổ phát gần như trống, độ trễ không leo dần, không có lỗi.")
    return notes


# ==============================================================================
# 7. TIẾN TRÌNH CHÍNH (DEMO RUN)
# ==============================================================================
async def run_demo(args):
    abs_db = verify_environment_guard(args.base_url, args.db_path)

    snapshot_before = get_db_snapshot(abs_db)
    other_skus_stock_before = get_other_skus_stock(abs_db)
    all_tables_before = get_all_table_counts(abs_db)

    print("==========================================================================")
    print(" KỲ VỌNG TRƯỚC KHI BẮN (ĐÁP ÁN CHUẨN ĐỂ ĐỐI CHIẾU)")
    print("==========================================================================")
    print(f"  • Sản phẩm Demo        : {SKU_CODE} ({SKU_NAME})")
    print(f"  • Tồn đầu kỳ           : {SKU_INITIAL_STOCK}")
    print(f"  • Kế hoạch giao dịch   : 400 giao dịch (200 Nhập x 5 đv | 200 Xuất x 3 đv)")
    print(f"  • Biến động tồn kho    : +{EXPECTED_IMPORT_SUM} (Nhập) - {EXPECTED_EXPORT_SUM} (Xuất) = +{EXPECTED_NET_CHANGE}")
    print(f"  • Tồn kỳ vọng cuối     : {EXPECTED_FINAL_STOCK} ({SKU_INITIAL_STOCK} -> {EXPECTED_FINAL_STOCK})")
    print(f"  • Tổng tồn kho Dashboard : Tăng đúng +{EXPECTED_FINAL_STOCK} ({snapshot_before['total_stock']} -> {snapshot_before['total_stock'] + EXPECTED_FINAL_STOCK}) = {SKU_INITIAL_STOCK} tồn đầu của SKU mới + {EXPECTED_NET_CHANGE} biến động")
    print(f"  • Kiểu bài             : STRESS - bắn liên tục 10s ở 40 giao dịch/s; độ trễ/thời gian xả hàng đợi chỉ để QUAN SÁT")
    print(f"  • Tiêu chí đạt         : dữ liệu đúng 100% + không lỗi/crash + bộ phát tải đúng lịch")
    print("\n--- BẢNG ĐỐI CHIẾU SỐ DÒNG 6 BẢNG CSDL (nếu cả 400 giao dịch thành công; chưa tính bản ghi hệ thống tự sinh khi tạo SKU) ---")
    print(f"{'Bảng CSDL':<24} | {'Trước chạy (Baseline)':>22} | {'Kỳ vọng sau chạy':>18} | {'Chênh lệch (+Delta)':>20}")
    print("-" * 92)
    deltas = {
        "products": 1,
        "import_notes": EXPECTED_IMPORT_COUNT,
        "import_note_details": EXPECTED_IMPORT_COUNT,
        "export_notes": EXPECTED_EXPORT_COUNT,
        "export_note_details": EXPECTED_EXPORT_COUNT,
        "stock_ledger": TOTAL_TX,
    }
    for tbl in SNAPSHOT_TABLES:
        before_cnt = snapshot_before[tbl]
        exp_cnt = before_cnt + deltas[tbl]
        print(f"{tbl:<24} | {before_cnt:>22} | {exp_cnt:>18} | {f'+{deltas[tbl]}':>20}")

    print("\n--- HƯỚNG DẪN QUAN SÁT TRỰC TIẾP TRÊN WEB (http://localhost:5173) ---")
    print("  1. Dashboard : Xem 'Tổng tồn kho' (+1400), 'Phiếu nhập kho' (+200, hoặc +201 nếu hệ thống tự sinh phiếu tồn đầu), 'Phiếu xuất kho' (+200)")
    print("  2. Thẻ kho   : Lọc 'SKU-D400' -> 400 dòng giao dịch (200 Nhập, 200 Xuất), có thể thêm 1 dòng tồn đầu do hệ thống tự ghi")
    print("  3. Phiếu nhập: Xuất hiện 200 phiếu mã từ PN-D400-0001 đến PN-D400-0200")
    print("  4. Phiếu xuất: Xuất hiện 200 phiếu mã từ PX-D400-0001 đến PX-D400-0200")

    limits = httpx.Limits(max_connections=250, max_keepalive_connections=250)
    timeout = httpx.Timeout(30.0, connect=10.0)

    async with httpx.AsyncClient(base_url=args.base_url, limits=limits, timeout=timeout) as client:
        # Đăng nhập lấy JWT Token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": args.username, "password": args.password},
        )
        if login_resp.status_code != 200:
            print(f"\n[LỖI] Đăng nhập thất bại ({login_resp.status_code}): {login_resp.text}")
            sys.exit(1)
        token = login_resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Tạo sản phẩm SKU-D400
        print(f"\n>>> Đang khởi tạo sản phẩm {SKU_CODE}...")
        prod_payload = {
            "code": SKU_CODE,
            "name": SKU_NAME,
            "category_id": SKU_CATEGORY_ID,
            "supplier_id": SKU_SUPPLIER_ID,
            "unit": SKU_UNIT,
            "min_stock": SKU_MIN_STOCK,
            "current_stock": SKU_INITIAL_STOCK,
            "standard_price": SKU_STANDARD_PRICE,
            "image_url": SKU_IMAGE_URL,
            "status": "ACTIVE",
        }
        p_resp = await client.post("/api/v1/products/", json=prod_payload)
        if p_resp.status_code not in (200, 201):
            print(f"[LỖI] Không thể tạo sản phẩm {SKU_CODE}: {p_resp.status_code} {p_resp.text}")
            sys.exit(1)
        product_id = p_resp.json()["id"]
        print(f"  + Đã tạo {SKU_CODE} thành công (ID = {product_id}, Tồn đầu = {SKU_INITIAL_STOCK})")

        # Chụp lại 6 bảng NGAY SAU khi tạo SKU: để biết hệ thống tự sinh thêm bản ghi tồn đầu nào
        snapshot_after_product = get_db_snapshot(abs_db)
        auto_deltas = {t: snapshot_after_product[t] - snapshot_before[t] for t in SNAPSHOT_TABLES}
        side_effects = {t: d for t, d in auto_deltas.items() if t != "products" and d != 0}
        if side_effects:
            print(f"  + Tạo SKU còn kéo theo bản ghi hệ thống tự sinh (tồn đầu): {side_effects}")
        else:
            print("  + Tạo SKU không sinh thêm bản ghi nào ngoài chính sản phẩm.")

        # Ghi manifest ban đầu
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "base_url": args.base_url,
            "db_path": abs_db,
            "backup_path": PRE_D400_BACKUP_PATH,
            "product": {
                "id": product_id,
                "code": SKU_CODE,
                "name": SKU_NAME,
                "initial_stock": SKU_INITIAL_STOCK,
            },
            "snapshot_before": snapshot_before,
            "snapshot_after_product": snapshot_after_product,
            "all_tables_before": all_tables_before,
            "other_skus_stock_before": other_skus_stock_before,
            "created_import_notes": [],
            "created_export_notes": [],
        }
        write_manifest_sync(manifest)
        print(f"  + Đã ghi manifest an toàn tại: {MANIFEST_PATH}")

        # Đếm ngược --wait giây
        if args.wait > 0:
            print(f"\n⏳ ĐẾM NGƯỢC {args.wait} GIÂY ĐỂ BẠN MỞ TRÌNH DUYỆT TRƯỚC KHI BẮN:")
            for s in range(int(args.wait), 0, -1):
                print(f"   ... Bắn tải sau {s} giây ...", flush=True)
                await asyncio.sleep(1.0)
            print("   🚀 BẮT ĐẦU BẮN TẢI 400 GIAO DỊCH!\n", flush=True)

        plan = build_fixed_plan()
        manifest_dirty = [False]
        stop_flush = asyncio.Event()

        async def periodic_flusher():
            while not stop_flush.is_set():
                await asyncio.sleep(2.0)
                if manifest_dirty[0]:
                    manifest_dirty[0] = False
                    write_manifest_sync(manifest)

        flusher_task = asyncio.create_task(periodic_flusher())

        # Vòng lặp bắn tải Open-loop 40 giao dịch/s trong 10 giây
        print(f"{'Giây':<7}| {'Đã gửi':>7} | {'Đã xong':>7} | {'Đang chờ':>8} | {'Gửi/s':>6} | {'Xong/s':>6} | {'p50(ms)':>8} | {'p95(ms)':>8} | {'Max(ms)':>8} | Lỗi theo mã HTTP")
        print("-" * 112)

        in_flight_tasks = []
        completed_results = []
        sent_timestamps = []

        t0 = time.perf_counter()
        t_first_send = None
        t_last_send = None

        last_sent_cnt = 0
        last_comp_cnt = 0
        inflight_at_send_end = 0
        completed_at_send_end = 0
        peak_inflight = 0

        async def worker(item, s_time):
            res = await execute_transaction(client, item, product_id, manifest, manifest_dirty, s_time)
            completed_results.append(res)
            return res

        try:
            # 10 giây phát lịch (mỗi giây phát 40 giao dịch)
            for sec_idx in range(1, 11):
                sec_end_t = t0 + sec_idx
                while len(sent_timestamps) < sec_idx * 40 and len(sent_timestamps) < TOTAL_TX:
                    k = len(sent_timestamps)
                    sched_t = t0 + (k * INTERVAL)
                    now_t = time.perf_counter()
                    wait_s = sched_t - now_t
                    if wait_s > 0:
                        await asyncio.sleep(wait_s)

                    t_now = time.perf_counter()
                    if t_first_send is None:
                        t_first_send = t_now
                    t_last_send = t_now
                    sent_timestamps.append(t_now)

                    task = asyncio.create_task(worker(plan[k], sched_t))
                    in_flight_tasks.append(task)

                rem = sec_end_t - time.perf_counter()
                if rem > 0:
                    await asyncio.sleep(rem)

                # Thu thập thống kê giây
                cur_sent = len(sent_timestamps)
                cur_comp_snap = list(completed_results)
                cur_comp = len(cur_comp_snap)

                s_sent = cur_sent - last_sent_cnt
                slice_comp = cur_comp_snap[last_comp_cnt:cur_comp]
                s_comp = len(slice_comp)

                last_sent_cnt = cur_sent
                last_comp_cnt = cur_comp
                inflight_now = cur_sent - cur_comp
                peak_inflight = max(peak_inflight, inflight_now)
                inflight_at_send_end = inflight_now
                completed_at_send_end = cur_comp

                lats = sorted(r["latency_ms"] for r in slice_comp)
                p50_l = percentile(lats, 50)
                p95_l = percentile(lats, 95)
                max_l = lats[-1] if lats else 0.0
                err_dict = dict(Counter(r["status_code"] for r in slice_comp if not r["success"]))

                print(
                    f"{'Giây ' + str(sec_idx):<7}| {cur_sent:>7} | {cur_comp:>7} | {inflight_now:>8} | "
                    f"{s_sent:>6} | {s_comp:>6} | "
                    f"{p50_l:>8.1f} | {p95_l:>8.1f} | {max_l:>8.1f} | {err_dict if err_dict else '{}'}",
                    flush=True,
                )

            # Chờ các task đang xử lý còn lại với timeout cứng 120 giây
            print(f"\n>>> Đã phát đủ lịch 10s. Còn {inflight_at_send_end} giao dịch đang xử lý, chờ xả hết phản hồi...")
            elapsed_so_far = time.perf_counter() - t0
            rem_timeout = max(1.0, 120.0 - elapsed_so_far)
            await asyncio.wait_for(asyncio.gather(*in_flight_tasks, return_exceptions=True), timeout=rem_timeout)

        except asyncio.TimeoutError:
            print(f"\n[TIMEOUT] Vượt quá thời hạn tối đa 120 giây! Dừng chờ.", flush=True)
        finally:
            stop_flush.set()
            try:
                await flusher_task
            except Exception:
                pass
            write_manifest_sync(manifest)

        t_last_done = time.perf_counter()
        total_time_span = t_last_done - t_first_send if t_first_send else 0.0
        send_window = t_last_send - t_first_send if (t_first_send and t_last_send) else 0.0

        # Giao dịch không nhận được phản hồi (bị hủy do timeout / chưa kịp gửi) => ghi nhận là THẤT BẠI,
        # không để báo cáo "đẹp giả" vì thiếu dòng.
        done_k = {r["k"] for r in completed_results}
        for item in plan:
            if item["k"] in done_k:
                continue
            k = item["k"]
            completed_results.append({
                "k": k, "n": item["n"], "tx_type": item["tx_type"], "code": item["code"],
                "quantity": item["quantity"], "note_id": None,
                "status_code": 597, "raw_status": 597, "success": False,
                "latency_ms": 0.0, "drift_ms": 0.0,
                "t_send": sent_timestamps[k] if k < len(sent_timestamps) else t0,
                "t_done": t_last_done, "locked_hit": False,
                "err_detail": "Không có phản hồi (hủy do timeout hoặc chưa kịp gửi)",
                "http_calls": 0, "server_response": "",
            })

        all_results = list(completed_results)

        # Đọc lại qua API trong lúc client còn sống
        try:
            readback = await fetch_api_readback(client, product_id, all_results)
        except Exception as exc:
            readback = {"product": (0, str(exc)[:120]), "import_note": None, "export_note": None}

    # Ghi toàn bộ kết quả chi tiết ra file demo_400_result.json
    result_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_requests": len(all_results),
        "total_time_span_sec": total_time_span,
        "send_window_sec": send_window,
        "requests": all_results,
    }
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    # ==============================================================================
    # 8. BÁO CÁO TỔNG HỢP VÀ ĐỐI CHIẾU
    # ==============================================================================
    total_req = len(all_results)
    succ_req = sum(1 for r in all_results if r["success"])
    fail_req = total_req - succ_req
    answered = [r for r in all_results if r["raw_status"] != 597]

    status_counts = Counter((r["tx_type"], r["raw_status"]) for r in all_results)
    locked_count = sum(1 for r in all_results if r["locked_hit"])
    conflict_409 = sum(1 for r in all_results if r["status_code"] == 409)
    err_5xx = sum(1 for r in all_results if 500 <= r["status_code"] < 600 and r["status_code"] not in (597, 598, 599))
    timeout_cnt = sum(1 for r in all_results if r["status_code"] in (597, 599))
    other_err = sum(
        1 for r in all_results
        if not r["success"] and not (500 <= r["status_code"] < 600 and r["status_code"] not in (597, 598, 599))
        and r["status_code"] not in (597, 599)
    )
    http_total = sum(r.get("http_calls", 0) for r in all_results)

    drifts = [r["drift_ms"] for r in answered]
    min_drift = min(drifts) if drifts else 0.0
    avg_drift = (sum(drifts) / len(drifts)) if drifts else 0.0
    max_drift = max(drifts) if drifts else 0.0

    lats_all = sorted(r["latency_ms"] for r in answered)
    lats_imp = sorted(r["latency_ms"] for r in answered if r["tx_type"] == "IMPORT")
    lats_exp = sorted(r["latency_ms"] for r in answered if r["tx_type"] == "EXPORT")
    p50_all = percentile(lats_all, 50)
    p95_all = percentile(lats_all, 95)
    p99_all = percentile(lats_all, 99)
    max_lat = lats_all[-1] if lats_all else 0.0

    actual_tps = (succ_req / total_time_span) if total_time_span > 0 else 0.0
    actual_http_rps = (http_total / total_time_span) if total_time_span > 0 else 0.0

    print("\n" + "=" * 78)
    print(" BÁO CÁO KẾT QUẢ THỰC HIỆN (THỜI GIAN THẬT & THỐNG KÊ)")
    print("=" * 78)
    print(f"  • Cửa sổ phát tải (40 giao dịch/s) : {send_window:.2f} giây (lý thuyết ~9.975s)")
    print(f"  • Thời gian hoàn tất toàn bộ       : {total_time_span:.2f} giây (từ giao dịch 1 đến phản hồi cuối)")
    print(f"  • Thông lượng hoàn tất             : {actual_tps:.1f} giao dịch/s  ({http_total} HTTP request ≈ {actual_http_rps:.1f} req/s)")
    print(f"  • Độ lệch lịch bắn (Drift)         : Min={min_drift:.2f}ms | Avg={avg_drift:.2f}ms | Max={max_drift:.2f}ms")
    print(f"  • Độ trễ chung                     : p50={p50_all:.1f}ms | p95={p95_all:.1f}ms | p99={p99_all:.1f}ms | Max={max_lat:.1f}ms")
    print(f"      - Nhập (1 request)             : p50={percentile(lats_imp, 50):.1f}ms | p95={percentile(lats_imp, 95):.1f}ms")
    print(f"      - Xuất (tạo + ship)            : p50={percentile(lats_exp, 50):.1f}ms | p95={percentile(lats_exp, 95):.1f}ms")
    print(f"  • Mã phản hồi (loại, HTTP)         : {dict(status_counts)}")
    print(f"  • 'database is locked'             : {locked_count} lần")
    print(f"  • 409 Conflict                     : {conflict_409} lần")
    print(f"  • 5xx Server Error                 : {err_5xx} lần")
    print(f"  • Timeout / không phản hồi         : {timeout_cnt} lần")

    cohorts = cohort_latency_by_send_second(answered, t0)
    print_latency_histogram(lats_all)
    print_latency_trend(cohorts)
    timeline = Counter(int(r["t_done"] - t0) for r in answered)
    print_completion_timeline(timeline)
    print_server_samples(all_results)

    rate_during = (completed_at_send_end / send_window) if send_window > 0 else None
    after_time = total_time_span - send_window
    rate_after = ((len(answered) - completed_at_send_end) / after_time) if after_time > 1.0 else None
    if rate_during is not None and rate_after is not None:
        print(f"\n  ℹ️ Tốc độ xong: trong lúc bắn ≈ {rate_during:.1f} gd/s | sau khi ngừng bắn ≈ {rate_after:.1f} gd/s")

    # Kiểm toán CSDL
    extra_drafts = sum(1 for e in manifest["created_export_notes"] if not e.get("shipped", True))
    audit = verify_ledger_invariants(
        abs_db, product_id, snapshot_before, all_results,
        other_skus_before=other_skus_stock_before, extra_drafts=extra_drafts,
        snapshot_after_product=snapshot_after_product,
    )

    print_api_readback(readback, audit["actual_sku_stock"])

    print("\n" + "=" * 78)
    print(" BẢNG ĐỐI CHIẾU THỰC TẾ VS KỲ VỌNG (kỳ vọng tính từ số giao dịch THẬT SỰ thành công)")
    print("=" * 78)
    print(f"{'Chỉ số kiểm tra':<32} | {'Kỳ vọng':>12} | {'Thực tế DB':>12} | {'Kết quả'}")
    print("-" * 78)
    print(f"{'Tồn kho SKU-D400':<32} | {audit['expected_sku_stock']:>12} | {audit['actual_sku_stock']:>12} | {'PASS' if audit['sku_stock_pass'] else 'FAIL'}")
    if audit["total_checked"]:
        print(f"{'Tổng tồn toàn kho (Dashboard)':<32} | {audit['expected_total_stock']:>12} | {audit['actual_total_stock']:>12} | {'PASS' if audit['total_stock_pass'] else 'FAIL'}")
    if audit["tables_checked"]:
        for tbl in SNAPSHOT_TABLES:
            print(f"{f'Số dòng bảng {tbl}':<32} | {audit['exp_tables'][tbl]:>12} | {audit['cur_snapshot'][tbl]:>12} | {'PASS' if audit['table_pass'][tbl] else 'FAIL'}")
    if audit["sku_changes"]:
        print(f"\n  ⚠️ Có {len(audit['sku_changes'])} SKU khác bị đổi tồn kho: {audit['sku_changes']}")
    else:
        print(f"{'Tồn các SKU khác':<32} | {'giữ nguyên':>12} | {'giữ nguyên':>12} | {'PASS'}")

    # Bảng phụ (nhật ký, thông báo...) do server tự ghi thêm
    all_tables_after = get_all_table_counts(abs_db)
    side_changes = [
        (t, all_tables_before.get(t), c) for t, c in all_tables_after.items()
        if t not in SNAPSHOT_TABLES and c is not None and all_tables_before.get(t) is not None
        and c != all_tables_before.get(t)
    ]
    if side_changes:
        print("\n--- BẢNG PHỤ SERVER TỰ GHI THÊM TRONG LÚC CHẠY (thông tin tham khảo) ---")
        for t, b, a in side_changes:
            print(f"  • {t:<28} {b} -> {a}  ({a - b:+d})")
        print("  (--cleanup KHÔNG tự xóa các bảng này; xem phần cảnh báo khi dọn dẹp.)")

    print("\n--- KIỂM TRA CÁC BẤT BIẾN SỔ CÁI & CHỨNG TỪ (THẺ KHO) ---")
    print(f"  1. Mỗi request thành công <-> đúng 1 dòng ledger, lỗi 0 dòng : {'PASS' if audit['inv1_pass'] else 'FAIL'} (Thành công: {succ_req}, dòng PN/PX trong thẻ kho: {audit['d400_rows_count']})")
    print(f"  2. Lũy kế balance_after[i] = balance_after[i-1] + change      : {'PASS' if audit['inv2_pass'] else 'FAIL'} ({len(audit['chain_errors'])} lỗi)")
    print(f"  3. Mã chứng từ phiếu nhập/xuất không trùng lặp                : {'PASS' if audit['inv4_pass'] else 'FAIL'} (Trùng PN={len(audit['dup_imp'])}, Trùng PX={len(audit['dup_exp'])})")
    print(f"  4. Tổng biến động Thẻ kho khớp số lượng thành công            : {'PASS' if audit['inv5_pass'] else 'FAIL'} (Nhập={audit['sum_imp_ledger']}, Xuất={audit['sum_exp_ledger']})")
    if audit["opening_rows_count"]:
        print(f"     ℹ️ Thẻ kho còn {audit['opening_rows_count']} dòng tồn đầu do hệ thống tự ghi khi tạo SKU (tổng {audit['opening_sum']:+d}) -> {'khớp tồn đầu ✅' if audit['opening_ok'] else 'KHÔNG khớp tồn đầu ❌'}")
    if audit["chain_errors"]:
        print("     Lỗi lũy kế đầu tiên: " + audit["chain_errors"][0])
    if audit["leaked_ledger"]:
        print(f"     ⚠️ {len(audit['leaked_ledger'])} giao dịch báo lỗi/không phản hồi nhưng VẪN có dòng thẻ kho (server đã xử lý): {audit['leaked_ledger'][:5]}")
    if audit["missing_ledger"]:
        print(f"     ⚠️ {len(audit['missing_ledger'])} giao dịch báo thành công nhưng THIẾU dòng thẻ kho: {audit['missing_ledger'][:5]}")

    # CÁC KẾT LUẬN TÁCH BIỆT
    data_correctness_pass = audit["all_pass"] and (succ_req == TOTAL_TX)
    survived = (total_req == TOTAL_TX) and (fail_req == 0)
    sched_ok = max_drift <= MAX_SCHEDULE_DRIFT_MS
    drain_time = max(total_time_span - send_window, 0.0)

    print("\n" + "=" * 78)
    print(" KẾT LUẬN CỦA BÀI STRESS TEST 400 GIAO DỊCH")
    print("=" * 78)
    print(f"  1. TÍNH ĐÚNG ĐẮN DỮ LIỆU        -> {'[PASS]' if data_correctness_pass else '[FAIL]'}")
    if data_correctness_pass:
        print("     • Tồn kho khớp sổ cái, 6 bảng khớp số giao dịch thành công, SKU khác không bị đụng tới.")
    else:
        print(f"     • Có sai lệch dữ liệu hoặc giao dịch thất bại ({fail_req}/{total_req} thất bại). Xem các mục FAIL ở trên.")

    print(f"\n  2. SỐNG SÓT DƯỚI TẢI QUÁ MỨC    -> {'[ĐẠT]' if survived else '[KHÔNG ĐẠT]'}")
    print(f"     • {succ_req}/{total_req} giao dịch hoàn tất, lỗi 5xx={err_5xx}, database locked={locked_count}, timeout/không phản hồi={timeout_cnt}.")

    print(f"\n  3. BỘ PHÁT TẢI ĐÚNG LỊCH        -> {'[ĐẠT]' if sched_ok else '[KHÔNG ĐÁNG TIN]'}  (drift tối đa {max_drift:.1f}ms, ngưỡng {MAX_SCHEDULE_DRIFT_MS:.0f}ms)")
    if not sched_ok:
        print("     • Máy chạy tải bị nghẽn nên tải thực tế bắn ra không đều 40/s -> coi số đo là tham khảo, nên chạy lại.")

    print("\n  SỐ ĐO QUAN SÁT (không chấm đạt/chưa đạt):")
    print(f"   • Tải đặt ra            : 40 gd/s trong {send_window:.1f}s")
    print(f"   • Thông lượng trung bình: {actual_tps:.1f} gd/s cả bài" + (f" | ≈ {rate_after:.1f} gd/s khi server chạy hết công suất (lúc xả hàng đợi)" if rate_after else ""))
    print(f"   • Hàng đợi đỉnh         : {peak_inflight} giao dịch đang chờ cùng lúc")
    print(f"   • Thời gian xả hàng đợi : {drain_time:.1f}s sau khi ngừng bắn")
    print(f"   • Độ trễ                : p50={p50_all:.0f}ms | p95={p95_all:.0f}ms | p99={p99_all:.0f}ms | max={max_lat:.0f}ms")

    print("\n  CHẨN ĐOÁN (rút ra từ số đo ở trên):")
    for line in diagnose(inflight_at_send_end, cohorts, locked_count, err_5xx, timeout_cnt, other_err, send_window, rate_during, rate_after):
        print(f"   - {line}")

    print("\n" + "=" * 78)
    print(" 💡 Dữ liệu đang được giữ nguyên để bạn quan sát trên Web (http://localhost:5173).")
    print(" 💡 Khi xem xong, chạy lệnh sau để thu hồi sạch sẽ:")
    print("    python backend/tests/performance/demo_400.py --cleanup")
    print("=" * 78)

    # Thoát mã 0 nếu dữ liệu đúng (kết luận 1 pass)
    sys.exit(0 if data_correctness_pass else 1)


# ==============================================================================
# 9. CHẾ ĐỘ THU HỒI DỮ LIỆU (--cleanup)
# ==============================================================================
def run_cleanup(args):
    abs_db = os.path.abspath(args.db_path)

    print("=" * 78)
    print(" TIẾN HÀNH THU HỒI VÀ DỌN DẸP DỮ LIỆU DEMO 400 (--cleanup)")
    print("=" * 78)
    print(f"  • CSDL mục tiêu: {abs_db}")

    manifest = None
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            print(f"  • Đã nạp manifest: {MANIFEST_PATH}")
        except Exception as e:
            print(f"  [!] Không đọc được manifest ({e}). Dọn dẹp theo tiền tố cố định SKU-D400.")

    conn = sqlite3.connect(abs_db, timeout=30.0)
    conn.isolation_level = None
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA busy_timeout=10000")

    try:
        cur.execute("BEGIN IMMEDIATE")

        # 1. Tìm ID sản phẩm SKU-D400
        cur.execute("SELECT id FROM products WHERE code = ?", (SKU_CODE,))
        prod_row = cur.fetchone()
        prod_id = prod_row[0] if prod_row else None

        # 2. Xóa Thẻ kho (stock_ledger)
        if prod_id:
            cur.execute("DELETE FROM stock_ledger WHERE product_id = ?", (prod_id,))
            del_ledger = cur.rowcount
        else:
            del_ledger = 0
        cur.execute("DELETE FROM stock_ledger WHERE reference_code LIKE 'PN-D400-%' OR reference_code LIKE 'PX-D400-%'")
        del_ledger += cur.rowcount

        # 3-4. Xóa chi tiết + phiếu nhập/xuất: theo tiền tố mã VÀ theo phiếu chỉ chứa SKU-D400
        #      (bắt cả phiếu nhập tồn đầu mà hệ thống tự sinh khi tạo SKU, mã không có tiền tố D400)
        def collect_note_ids(note_tbl, detail_tbl, fk_col, prefix):
            ids = set(r[0] for r in cur.execute(f"SELECT id FROM {note_tbl} WHERE code LIKE ?", (prefix,)).fetchall())
            if prod_id and table_has_col(cur, detail_tbl, "product_id"):
                rows = cur.execute(
                    f"SELECT DISTINCT {fk_col} FROM {detail_tbl} WHERE product_id = ? "
                    f"AND {fk_col} NOT IN (SELECT {fk_col} FROM {detail_tbl} WHERE product_id != ?)",
                    (prod_id, prod_id),
                ).fetchall()
                ids.update(r[0] for r in rows)
            return sorted(ids)

        def delete_by_ids(table, col, ids):
            n = 0
            for i in range(0, len(ids), 400):
                chunk = ids[i:i + 400]
                ph = ",".join("?" * len(chunk))
                cur.execute(f"DELETE FROM {table} WHERE {col} IN ({ph})", chunk)
                n += cur.rowcount
            return n

        imp_ids = collect_note_ids("import_notes", "import_note_details", "import_note_id", "PN-D400-%")
        exp_ids = collect_note_ids("export_notes", "export_note_details", "export_note_id", "PX-D400-%")
        del_ind = delete_by_ids("import_note_details", "import_note_id", imp_ids)
        del_end = delete_by_ids("export_note_details", "export_note_id", exp_ids)
        # chi tiết còn sót tham chiếu SKU-D400 phải xóa trước khi xóa sản phẩm (tránh vi phạm khóa ngoại)
        if prod_id:
            for dt in ("import_note_details", "export_note_details"):
                if table_has_col(cur, dt, "product_id"):
                    cur.execute(f"DELETE FROM {dt} WHERE product_id = ?", (prod_id,))
        del_in = delete_by_ids("import_notes", "id", imp_ids)
        del_en = delete_by_ids("export_notes", "id", exp_ids)

        # 5. Xóa sản phẩm SKU-D400
        if prod_id:
            cur.execute("DELETE FROM products WHERE id = ?", (prod_id,))
            del_prod = cur.rowcount
        else:
            del_prod = 0

        cur.execute("COMMIT")

        print("\n--- THỐNG KÊ BẢN GHI ĐÃ XÓA ---")
        print(f"  • stock_ledger        : {del_ledger} dòng")
        print(f"  • import_note_details : {del_ind} dòng")
        print(f"  • export_note_details : {del_end} dòng")
        print(f"  • import_notes        : {del_in} phiếu")
        print(f"  • export_notes        : {del_en} phiếu")
        print(f"  • products            : {del_prod} sản phẩm")

        # 6. Đối chiếu với baseline snapshot
        print("\n--- ĐỐI CHIẾU SỐ DÒNG SAU KHI DỌN DẸP ---")
        print(f"{'Bảng CSDL':<24} | {'Trước (Snapshot)':>18} | {'Sau khi Cleanup':>18} | {'Chênh lệch':>12} | {'Trạng thái'}")
        print("-" * 88)

        all_clean = True
        snapshot_before = manifest.get("snapshot_before") if manifest else None

        for tbl in SNAPSHOT_TABLES:
            cur.execute(f"SELECT count(*) FROM {tbl}")
            curr_cnt = cur.fetchone()[0]
            if snapshot_before and tbl in snapshot_before:
                base_cnt = snapshot_before[tbl]
                diff = curr_cnt - base_cnt
                status = "PASS" if diff == 0 else "FAIL"
                if diff != 0:
                    all_clean = False
                print(f"{tbl:<24} | {base_cnt:>18} | {curr_cnt:>18} | {f'{diff:+d}':>12} | {status}")
            else:
                print(f"{tbl:<24} | {'(N/A)':>18} | {curr_cnt:>18} | {'(N/A)':>12} | CHECK")

        # Kiểm tra tồn kho các SKU khác không bị ảnh hưởng
        if manifest and manifest.get("other_skus_stock_before"):
            other_stocks = manifest["other_skus_stock_before"]
            cur.execute("SELECT code, current_stock FROM products WHERE code != ?", (SKU_CODE,))
            diff_skus = []
            for c_code, c_stock in cur.fetchall():
                if c_code in other_stocks and other_stocks[c_code] != c_stock:
                    diff_skus.append((c_code, other_stocks[c_code], c_stock))
            if diff_skus:
                all_clean = False
                print(f"\n[CẢNH BÁO] Có {len(diff_skus)} SKU khác bị biến động tồn kho: {diff_skus}")
            else:
                print("\n  ✅ Tồn kho của 100% các SKU khác giữ nguyên vẹn tuyệt đối.")

        # Các bảng phụ (nhật ký, thông báo...) mà cleanup không tự xóa
        side_leftovers = []
        tables_before = manifest.get("all_tables_before") if manifest else None
        if tables_before:
            tables_after = get_all_table_counts(abs_db)
            for t, c in tables_after.items():
                b = tables_before.get(t)
                if t in SNAPSHOT_TABLES or c is None or b is None:
                    continue
                if c != b:
                    side_leftovers.append((t, b, c))
        if side_leftovers:
            print("\n⚠️  CÁC BẢNG PHỤ VẪN CÒN DỮ LIỆU DO DEMO GHI THÊM (cleanup không tự xóa):")
            for t, b, c in side_leftovers:
                print(f"  • {t:<28} trước={b} | hiện tại={c} | {c - b:+d}")
            print("  -> Nếu là nhật ký/thông báo thì vô hại; nếu cần sạch tuyệt đối, hãy khôi phục từ bản sao lưu:")
            print(f"     {PRE_D400_BACKUP_PATH}")

        if all_clean:
            print("\n" + "=" * 78)
            if side_leftovers:
                print(" ✅ KẾT QUẢ DỌN DẸP: SẠCH 6 BẢNG CHÍNH & TỒN KHO (còn bảng phụ lệch - xem cảnh báo trên)")
            else:
                print(" ✅ KẾT QUẢ DỌN DẸP: SẠCH HOÀN TOÀN (CSDL VỀ ĐÚNG 100% BASELINE)")
            print("=" * 78)
            if os.path.exists(MANIFEST_PATH):
                os.remove(MANIFEST_PATH)
            sys.exit(0)
        else:
            print("\n" + "=" * 78)
            print(" ❌ CẢNH BÁO: CSDL CÒN CHÊNH LỆCH SO VỚI BASELINE! GIỮ NGUYÊN MANIFEST.")
            print("=" * 78)
            sys.exit(1)

    except Exception as exc:
        try:
            cur.execute("ROLLBACK")
        except Exception:
            pass
        print(f"\n[LỖI DỌN DẸP] {exc}")
        sys.exit(1)
    finally:
        conn.close()


# ==============================================================================
# 10. CHẾ ĐỘ KIỂM TOÁN HIỆN TẠI (--verify-only)
# ==============================================================================
def run_verify_only(args):
    abs_db = os.path.abspath(args.db_path)
    if not os.path.exists(abs_db):
        print(f"[LỖI] Không tìm thấy file CSDL: {abs_db}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
    cur = conn.cursor()
    cur.execute("SELECT id FROM products WHERE code = ?", (SKU_CODE,))
    prod_row = cur.fetchone()
    conn.close()

    if not prod_row:
        print(f"[THÔNG BÁO] Không tìm thấy sản phẩm {SKU_CODE} trong CSDL ({abs_db}).")
        sys.exit(0)

    prod_id = prod_row[0]

    if os.path.exists(RESULT_PATH):
        with open(RESULT_PATH, "r", encoding="utf-8") as f:
            all_results = json.load(f).get("requests", [])
        source_note = "theo file kết quả lần chạy gần nhất"
    else:
        all_results = results_from_ledger(abs_db, prod_id)
        source_note = "KHÔNG có file kết quả -> dựng từ chính Thẻ kho (bất biến 1 chỉ mang tính nội bộ)"
        print(f"[CẢNH BÁO] Không tìm thấy {RESULT_PATH}; {source_note}.")

    manifest = {}
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    snapshot_before = manifest.get("snapshot_before", {})
    other_skus_before = manifest.get("other_skus_stock_before")
    extra_drafts = sum(1 for e in manifest.get("created_export_notes", []) if not e.get("shipped", True))

    audit = verify_ledger_invariants(
        abs_db, prod_id, snapshot_before, all_results,
        other_skus_before=other_skus_before, extra_drafts=extra_drafts,
        snapshot_after_product=manifest.get("snapshot_after_product"),
    )

    print("=" * 78)
    print(" KẾT QUẢ KIỂM TOÁN CƠ SỞ DỮ LIỆU (--verify-only)")
    print("=" * 78)
    print(f"  • Nguồn đối chiếu : {source_note}")
    print(f"  • Tồn SKU-D400    : {audit['actual_sku_stock']} (Kỳ vọng: {audit['expected_sku_stock']}) -> {'PASS' if audit['sku_stock_pass'] else 'FAIL'}")
    if audit["tables_checked"]:
        for tbl in SNAPSHOT_TABLES:
            print(f"  • Bảng {tbl:<22}: {audit['cur_snapshot'][tbl]} (Kỳ vọng: {audit['exp_tables'][tbl]}) -> {'PASS' if audit['table_pass'][tbl] else 'FAIL'}")
    else:
        print("  • Số dòng 6 bảng  : bỏ qua (không có manifest để làm mốc baseline)")
    print(f"  • Tồn các SKU khác: {'giữ nguyên' if audit['others_pass'] else 'CÓ BIẾN ĐỘNG ' + str(audit['sku_changes'])}")
    print(f"  • Bất biến 1 (1:1 Ledger)  : {'PASS' if audit['inv1_pass'] else 'FAIL'}")
    print(f"  • Bất biến 2 (Lũy kế)      : {'PASS' if audit['inv2_pass'] else 'FAIL'}")
    print(f"  • Bất biến 3 (Không trùng) : {'PASS' if audit['inv4_pass'] else 'FAIL'}")
    print(f"  • Bất biến 4 (Biến động)   : {'PASS' if audit['inv5_pass'] else 'FAIL'}")
    print(f"  => TỔNG THỂ : {'PASS 100%' if audit['all_pass'] else 'FAIL'}")
    sys.exit(0 if audit["all_pass"] else 1)


# ==============================================================================
# 11. CLI PARSER
# ==============================================================================
def parse_args():
    parser = argparse.ArgumentParser(description="Stress test 400 giao dịch (200 Nhập + 200 Xuất, bắn 10s) SmartKho")
    parser.add_argument("--cleanup", action="store_true", help="Dọn dẹp sạch sẽ toàn bộ dữ liệu do Demo 400 tạo ra")
    parser.add_argument("--verify-only", action="store_true", help="Chỉ kiểm toán đối chiếu CSDL hiện tại mà không bắn tải")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL API (mặc định: http://127.0.0.1:8000)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Đường dẫn file CSDL warehouse.db")
    parser.add_argument("--username", default="admin", help="Tài khoản đăng nhập API")
    parser.add_argument("--password", default="admin123", help="Mật khẩu đăng nhập API")
    parser.add_argument("--wait", type=int, default=10, help="Số giây đếm ngược trước khi bắn để mở sẵn Web (mặc định: 10s)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.cleanup:
        run_cleanup(args)
    elif args.verify_only:
        run_verify_only(args)
    else:
        asyncio.run(run_demo(args))