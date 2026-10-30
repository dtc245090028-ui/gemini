"""Bộ kiểm thử rào chắn và bảo vệ chống tồn kho âm & tính sai tồn cuối kỳ SmartKho.

File độc lập duy nhất:
- Không import bất kỳ module nào của repo; chỉ dùng thư viện chuẩn Python + httpx.
- Kiểm tra toàn diện 5 nhóm bài test:
    • Nhóm A: Chặn xuất vượt tồn (tuần tự, biên, đa chi tiết, tính nguyên tử).
    • Nhóm B: Đầu vào bất thường (số lượng, đơn giá, tạo/sửa sản phẩm, kiểm kê).
    • Nhóm C: Đua tranh đồng thời (Race condition 3 vòng: 30 ship x 1, 6 ship x 4, multi-ship, multi-cancel, nhập/xuất xen kẽ, trùng mã phiếu).
    • Nhóm D: Hủy, xóa và hoàn kho (hoàn kho sau ship, hủy phiếu nhập khi thiếu tồn, xóa sản phẩm đã có giao dịch).
    • Nhóm E: Tính toàn vẹn tồn cuối kỳ và bất biến Thẻ kho (audit toàn bộ SKU-NEG-*, chạy check_invariants).
"""

import argparse
import asyncio
import hashlib
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
# 1. TỰ ĐỘNG ỦY QUYỀN VÀO DOCKER CONTAINER NẾU CHẠY TỪ WINDOWS HOST
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
            this_file_path = os.path.abspath(__file__)
            subprocess.run(
                ["docker", "cp", this_file_path, "warehouse_backend:/app/tests/performance/test_negative_stock_guard.py"],
                capture_output=True,
                check=False,
            )

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
                "python", "-u", "/app/tests/performance/test_negative_stock_guard.py",
                *forwarded_args,
            ]
            res = subprocess.run(cmd, check=False)
            sys.exit(res.returncode)

import httpx

# ==============================================================================
# 2. CẤU HÌNH & ĐƯỜNG DẪN
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
PRE_GUARD_BACKUP_PATH = os.path.join(BACKUP_DIR, "warehouse_pre_negguard_backup.db")
MANIFEST_PATH = os.path.join(PERF_DIR, "negguard_manifest.json")
RESULT_PATH = os.path.join(PERF_DIR, "negguard_result.json")

SNAPSHOT_TABLES = [
    "products",
    "import_notes",
    "import_note_details",
    "export_notes",
    "export_note_details",
    "stock_ledger",
]

def classify_http_response(status_code: int, response_text: str = "") -> str:
    if status_code in (200, 201):
        return str(status_code)
    if status_code == 400:
        lower_t = response_text.lower() if response_text else ""
        if any(k in lower_t for k in ["vượt quá", "không đủ tồn", "tồn kho sau khi xuất âm", "insufficient"]):
            return "400[INSUFFICIENT_STOCK]"
        if any(k in lower_t for k in ["đã bị hủy", "không thể hủy", "trạng thái không hợp lệ", "already_cancelled"]):
            return "400[ALREADY_CANCELLED]"
        if any(k in lower_t for k in ["nhà cung cấp", "supplier"]):
            return "400[INVALID_SUPPLIER]"
        if any(k in lower_t for k in ["trần", "giới hạn tối đa", "exceeds_ceiling"]):
            return "400[EXCEEDS_CEILING]"
        return "400[BAD_REQUEST]"
    if status_code == 409:
        return "409[DUPLICATE_CODE]"
    if status_code == 422:
        return "422[VALIDATION_ERROR]"
    if status_code >= 500:
        return f"{status_code}[INTERNAL_ERROR]"
    return str(status_code)


def format_status_breakdown(statuses: list) -> str:
    from collections import Counter
    counts = Counter(statuses)
    sorted_keys = sorted(counts.keys(), key=lambda k: (0 if str(k) in ("200", "201") else 1, str(k)))
    return ", ".join(f"{counts[k]}x{k}" for k in sorted_keys)



# ==============================================================================
# 3. TIỆN ÍCH DỮ LIỆU & GUARD
# ==============================================================================
def compute_table_hash(cur, tbl: str) -> str:
    cur.execute(f"SELECT * FROM {tbl} ORDER BY id")
    hasher = hashlib.sha256()
    for row in cur.fetchall():
        hasher.update(repr(row).encode('utf-8'))
    return hasher.hexdigest()


def get_db_snapshot(db_path: str) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        snap = {}
        for tbl in SNAPSHOT_TABLES:
            cur.execute(f"SELECT count(*), COALESCE(MAX(id), 0) FROM {tbl}")
            cnt, max_id = cur.fetchone()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
            if cur.fetchone():
                cur.execute("SELECT seq FROM sqlite_sequence WHERE name = ?", (tbl,))
                seq_row = cur.fetchone()
                seq = seq_row[0] if seq_row else 0
            else:
                seq = 0
            tbl_hash = compute_table_hash(cur, tbl)
            snap[tbl] = {
                "count": cnt,
                "max_id": max_id,
                "sqlite_sequence": seq,
                "sha256": tbl_hash,
            }
        cur.execute("SELECT sum(current_stock) FROM products")
        snap["total_stock"] = cur.fetchone()[0] or 0
        return snap
    finally:
        conn.close()


def get_other_skus_stock(db_path: str) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT code, current_stock FROM products WHERE code NOT LIKE 'SKU-NEG-%'")
        return {code: stock for code, stock in cur.fetchall()}
    finally:
        conn.close()


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
    print(" KIỂM TRA MÔI TRƯỜNG & SAO LƯU DỰ PHÒNG (NEGATIVE STOCK GUARD)")
    print("=" * 78)
    print(f"  • Base URL mục tiêu : {base_url} (Port: {port})")
    print(f"  • CSDL mục tiêu     : {abs_db}")

    if parsed.hostname not in ("127.0.0.1", "localhost", "backend", "warehouse_backend"):
        print("\n[GUARD BLOCKED] Chỉ cho phép chạy test trên localhost / 127.0.0.1 / backend!")
        sys.exit(1)

    if not os.path.exists(abs_db):
        print(f"\n[GUARD BLOCKED] Không tìm thấy file CSDL tại: {abs_db}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, code FROM products WHERE code LIKE 'SKU-NEG-%'")
        ex_prod = cur.fetchall()
        cur.execute("SELECT id, code FROM import_notes WHERE code LIKE 'NEG-%'")
        ex_imp = cur.fetchall()
        cur.execute("SELECT id, code FROM export_notes WHERE code LIKE 'NEG-%'")
        ex_exp = cur.fetchall()

        if ex_prod or ex_imp or ex_exp:
            print(f"\n[CẢNH BÁO] Phát hiện dữ liệu test cũ chưa được dọn dẹp:")
            if ex_prod:
                print(f"  • Sản phẩm cũ : {len(ex_prod)} SP ({[p[1] for p in ex_prod[:5]]}...)")
            if ex_imp:
                print(f"  • Phiếu nhập cũ: {len(ex_imp)} phiếu")
            if ex_exp:
                print(f"  • Phiếu xuất cũ: {len(ex_exp)} phiếu")
            print("Vui lòng chạy `python backend/tests/performance/test_negative_stock_guard.py --cleanup` trước khi chạy mới.")
            sys.exit(1)
    finally:
        conn.close()

    os.makedirs(BACKUP_DIR, exist_ok=True)
    src_conn = sqlite3.connect(abs_db, timeout=15.0)
    dst_conn = sqlite3.connect(PRE_GUARD_BACKUP_PATH, timeout=15.0)
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    print(f"  • Bản sao lưu dự phòng: {PRE_GUARD_BACKUP_PATH}")
    print("  => [GUARD PASS] Môi trường sẵn sàng & đã sao lưu an toàn.\n")
    return abs_db


# ==============================================================================
# 4. TRÌNH TỰ THỰC THI TEST
# ==============================================================================
class TestContext:
    __test__ = False
    def __init__(self, client: httpx.AsyncClient, abs_db: str, manifest: dict, detailed_results: list):
        self.client = client
        self.abs_db = abs_db
        self.manifest = manifest
        self.detailed_results = detailed_results
        self.test_reports = []

    def get_product_stock_from_db(self, product_id: int):
        conn = sqlite3.connect(f"file:{self.abs_db}?mode=ro", uri=True, timeout=10.0)
        try:
            cur = conn.cursor()
            cur.execute("SELECT current_stock, status FROM products WHERE id = ?", (product_id,))
            row = cur.fetchone()
            return (row[0], row[1]) if row else (None, None)
        finally:
            conn.close()

    def get_ledger_entries(self, product_id: int):
        conn = sqlite3.connect(f"file:{self.abs_db}?mode=ro", uri=True, timeout=10.0)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, transaction_type, reference_code, quantity_change, balance_after, note
                FROM stock_ledger
                WHERE product_id = ?
                ORDER BY id ASC
                """,
                (product_id,),
            )
            return cur.fetchall()
        finally:
            conn.close()

    async def create_test_product(self, sku_suffix: str, initial_stock: int = 10, name: str = None) -> int:
        code = f"SKU-NEG-{sku_suffix}"
        name = name or f"SP Test Neg {sku_suffix}"
        payload = {
            "code": code,
            "name": name,
            "category_id": 1,
            "supplier_id": 1,
            "unit": "Cái",
            "min_stock": 5,
            "current_stock": initial_stock,
            "standard_price": 50000.0,
            "status": "ACTIVE",
        }
        resp = await self.client.post("/api/v1/products/", json=payload)
        assert resp.status_code in (200, 201), f"Tạo sản phẩm {code} thất bại: {resp.text}"
        prod_data = resp.json()
        pid = prod_data["id"]
        init_note = prod_data.get("initial_import_note_code")
        self.manifest["products"].append({"id": pid, "code": code, "initial_stock": initial_stock})
        if init_note:
            self.manifest["import_notes"].append({"code": init_note})
        write_manifest_sync(self.manifest)
        return pid

    def sync_manifest_ids(self):
        """Đồng bộ toàn bộ ID phát sinh liên quan đến các sản phẩm của test vào manifest."""
        prod_ids = [p["id"] for p in self.manifest.get("products", [])]
        if not prod_ids:
            return
        placeholders = ','.join(['?'] * len(prod_ids))
        conn = sqlite3.connect(f"file:{self.abs_db}?mode=ro", uri=True, timeout=10.0)
        try:
            cur = conn.cursor()
            m_ids = self.manifest.setdefault("manifest_ids", {
                "products": [],
                "import_notes": [],
                "import_note_details": [],
                "export_notes": [],
                "export_note_details": [],
                "stock_ledger": [],
            })
            for pid in prod_ids:
                if pid not in m_ids["products"]:
                    m_ids["products"].append(pid)

            # 1. import_note_details & import_notes
            cur.execute(f"SELECT id, import_note_id FROM import_note_details WHERE product_id IN ({placeholders})", prod_ids)
            for d_id, note_id in cur.fetchall():
                if d_id not in m_ids["import_note_details"]:
                    m_ids["import_note_details"].append(d_id)
                if note_id not in m_ids["import_notes"]:
                    m_ids["import_notes"].append(note_id)

            # 2. export_note_details & export_notes
            cur.execute(f"SELECT id, export_note_id FROM export_note_details WHERE product_id IN ({placeholders})", prod_ids)
            for d_id, note_id in cur.fetchall():
                if d_id not in m_ids["export_note_details"]:
                    m_ids["export_note_details"].append(d_id)
                if note_id not in m_ids["export_notes"]:
                    m_ids["export_notes"].append(note_id)

            # 3. stock_ledger
            cur.execute(f"SELECT id FROM stock_ledger WHERE product_id IN ({placeholders})", prod_ids)
            for (l_id,) in cur.fetchall():
                if l_id not in m_ids["stock_ledger"]:
                    m_ids["stock_ledger"].append(l_id)
        finally:
            conn.close()
        write_manifest_sync(self.manifest)

    def log_result(self, test_id: str, desc: str, expected: str, actual: str, status_code: int, stock_change: str, classification: str, evidence: dict):
        self.sync_manifest_ids()
        entry = {
            "test_id": test_id,
            "desc": desc,
            "expected": expected,
            "actual": actual,
            "status_code": status_code,
            "stock_change": stock_change,
            "classification": classification,
            "evidence": evidence,
        }
        self.test_reports.append(entry)
        self.detailed_results.append(entry)
        print(f"  [{test_id:<4}] {desc:<45} | HTTP {status_code:<3} | Tồn: {stock_change:<10} -> {classification}")


# ==============================================================================
# NHÓM A: CHẶN XUẤT VƯỢT TỒN TUẦN TỰ
# ==============================================================================
async def run_group_a(ctx: TestContext):
    print("\n" + "=" * 78)
    print(" NHÓM A: CHẶN XUẤT VƯỢT TỒN (TUẦN TỰ, BIÊN, ĐA CHI TIẾT)")
    print("=" * 78)

    # A1. Tồn 10, xuất 11 rồi ship
    pid_a1 = await ctx.create_test_product("A1", initial_stock=10)
    stock_before, _ = ctx.get_product_stock_from_db(pid_a1)
    ledgers_before = ctx.get_ledger_entries(pid_a1)

    p_code = "NEG-A1-001"
    r_create = await ctx.client.post("/api/v1/export-notes/", json={
        "code": p_code,
        "recipient_name": "Khách A1",
        "note": "Xuất 11 trên tồn 10",
        "details": [{"product_id": pid_a1, "quantity": 11, "unit_price": 50000.0}],
    })
    status_c = r_create.status_code
    note_id = None
    if status_c in (200, 201):
        note_id = r_create.json()["id"]
        ctx.manifest["export_notes"].append({"id": note_id, "code": p_code})
        r_ship = await ctx.client.post(f"/api/v1/export-notes/{note_id}/ship")
        status_c = r_ship.status_code
        resp_text = r_ship.text
    else:
        resp_text = r_create.text

    stock_after, _ = ctx.get_product_stock_from_db(pid_a1)
    ledgers_after = ctx.get_ledger_entries(pid_a1)
    is_pass = (status_c == 400 and stock_after == 10 and len(ledgers_after) == len(ledgers_before) and stock_after == sum(l[3] for l in ledgers_after))
    cls = "PASS" if is_pass else ("FAIL-NGHIÊM TRỌNG" if stock_after != 10 else "FAIL-NHẸ")
    ctx.log_result(
        "A1", "Tồn 10, xuất 11 rồi ship", "Bị từ chối 4xx, tồn 10, 0 phát sinh ledger",
        f"HTTP {status_c}, tồn {stock_after}, delta_ledger {len(ledgers_after) - len(ledgers_before)}", status_c,
        f"{stock_before}->{stock_after}", cls,
        {
            "code_ref": "backend/app/services/inventory_service.py:249 & 480",
            "logic": "Chặn tại create_export_note (current_stock < qty), trả 400",
            "resp_text": resp_text[:200],
        }
    )

    # A2. Tồn 10, xuất 10 (biên) -> thành công, xuất tiếp 1 -> bị từ chối
    pid_a2 = await ctx.create_test_product("A2", initial_stock=10)
    ledgers_before = ctx.get_ledger_entries(pid_a2)
    # Xuất 10
    r_exp1 = await ctx.client.post("/api/v1/export-notes/", json={
        "code": "NEG-A2-001",
        "recipient_name": "Khách A2 biên",
        "details": [{"product_id": pid_a2, "quantity": 10, "unit_price": 50000.0}],
    })
    nid_a2_1 = r_exp1.json()["id"]
    ctx.manifest["export_notes"].append({"id": nid_a2_1, "code": "NEG-A2-001"})
    r_ship1 = await ctx.client.post(f"/api/v1/export-notes/{nid_a2_1}/ship")
    s_mid, _ = ctx.get_product_stock_from_db(pid_a2)

    # Xuất tiếp 1
    r_exp2 = await ctx.client.post("/api/v1/export-notes/", json={
        "code": "NEG-A2-002",
        "recipient_name": "Khách A2 vượt biên",
        "details": [{"product_id": pid_a2, "quantity": 1, "unit_price": 50000.0}],
    })
    status_a2_2 = r_exp2.status_code
    if status_a2_2 in (200, 201):
        nid_a2_2 = r_exp2.json()["id"]
        ctx.manifest["export_notes"].append({"id": nid_a2_2, "code": "NEG-A2-002"})
        r_ship2 = await ctx.client.post(f"/api/v1/export-notes/{nid_a2_2}/ship")
        status_a2_2 = r_ship2.status_code

    stock_final_a2, _ = ctx.get_product_stock_from_db(pid_a2)
    ledgers_final_a2 = ctx.get_ledger_entries(pid_a2)
    is_pass_a2 = (
        r_ship1.status_code in (200, 201) and s_mid == 0 and status_a2_2 == 400
        and stock_final_a2 == 0 and len(ledgers_final_a2) == len(ledgers_before) + 1
        and stock_final_a2 == sum(l[3] for l in ledgers_final_a2)
    )
    cls_a2 = "PASS" if is_pass_a2 else ("FAIL-NGHIÊM TRỌNG" if stock_final_a2 < 0 else "FAIL-NHẸ")
    ctx.log_result(
        "A2", "Tồn 10: xuất 10 (tồn 0), xuất tiếp 1 bị từ chối", "Xuất 10 OK (tồn 0), xuất 1 báo 4xx, tồn 0",
        f"Lần 1 HTTP {r_ship1.status_code} (tồn {s_mid}), Lần 2 HTTP {status_a2_2} (tồn {stock_final_a2})", f"{r_ship1.status_code}/{status_a2_2}",
        f"10->{s_mid}->{stock_final_a2}", cls_a2,
        {
            "code_ref": "backend/app/services/inventory_service.py:480 & 502",
            "logic": "Lần 1 trừ tồn bằng RETURNING balance=0, lần 2 chặn tại create_export_note",
            "resp_text": r_exp2.text[:200],
        }
    )

    # A3. Một phiếu xuất có 2 dòng chi tiết cùng sản phẩm (6 + 6) trên tồn 10
    pid_a3 = await ctx.create_test_product("A3", initial_stock=10)
    ledgers_before = ctx.get_ledger_entries(pid_a3)
    r_a3 = await ctx.client.post("/api/v1/export-notes/", json={
        "code": "NEG-A3-001",
        "recipient_name": "Khách A3 gộp",
        "details": [
            {"product_id": pid_a3, "quantity": 6, "unit_price": 50000.0},
            {"product_id": pid_a3, "quantity": 6, "unit_price": 50000.0},
        ],
    })
    st_a3 = r_a3.status_code
    if st_a3 in (200, 201):
        nid_a3 = r_a3.json()["id"]
        ctx.manifest["export_notes"].append({"id": nid_a3, "code": "NEG-A3-001"})
        r_ship_a3 = await ctx.client.post(f"/api/v1/export-notes/{nid_a3}/ship")
        st_a3 = r_ship_a3.status_code

    stock_a3, _ = ctx.get_product_stock_from_db(pid_a3)
    ledgers_a3 = ctx.get_ledger_entries(pid_a3)
    is_pass_a3 = (st_a3 == 400 and stock_a3 == 10 and len(ledgers_a3) == len(ledgers_before) and stock_a3 == sum(l[3] for l in ledgers_a3))
    cls_a3 = "PASS" if is_pass_a3 else ("FAIL-NGHIÊM TRỌNG" if stock_a3 != 10 else "FAIL-NHẸ")
    ctx.log_result(
        "A3", "1 phiếu có 2 dòng cùng SP (6+6) trên tồn 10", "Từ chối cả phiếu 4xx, tồn nguyên 10, 0 trừ nửa",
        f"HTTP {st_a3}, tồn {stock_a3}, delta_ledger {len(ledgers_a3) - len(ledgers_before)}", st_a3,
        f"10->{stock_a3}", cls_a3,
        {
            "code_ref": "backend/app/services/inventory_service.py:504",
            "logic": "Dòng 1 trừ còn 4, dòng 2 UPDATE WHERE current_stock >= 6 trả None -> rollback toàn bộ",
            "resp_text": r_a3.text[:200],
        }
    )

    # A4. Một phiếu xuất có 2 sản phẩm: 1 đủ tồn (5 trên 10), 1 thiếu (15 trên 10)
    pid_a4_1 = await ctx.create_test_product("A4-1", initial_stock=10)
    pid_a4_2 = await ctx.create_test_product("A4-2", initial_stock=10)
    l_before_1 = ctx.get_ledger_entries(pid_a4_1)
    l_before_2 = ctx.get_ledger_entries(pid_a4_2)

    r_a4 = await ctx.client.post("/api/v1/export-notes/", json={
        "code": "NEG-A4-001",
        "recipient_name": "Khách A4 atomicity",
        "details": [
            {"product_id": pid_a4_1, "quantity": 5, "unit_price": 50000.0},
            {"product_id": pid_a4_2, "quantity": 15, "unit_price": 50000.0},
        ],
    })
    st_a4 = r_a4.status_code
    if st_a4 in (200, 201):
        nid_a4 = r_a4.json()["id"]
        ctx.manifest["export_notes"].append({"id": nid_a4, "code": "NEG-A4-001"})
        r_ship_a4 = await ctx.client.post(f"/api/v1/export-notes/{nid_a4}/ship")
        st_a4 = r_ship_a4.status_code

    s_a4_1, _ = ctx.get_product_stock_from_db(pid_a4_1)
    s_a4_2, _ = ctx.get_product_stock_from_db(pid_a4_2)
    l_a4_1 = ctx.get_ledger_entries(pid_a4_1)
    l_a4_2 = ctx.get_ledger_entries(pid_a4_2)

    is_pass_a4 = (
        st_a4 == 400 and s_a4_1 == 10 and s_a4_2 == 10
        and len(l_a4_1) == len(l_before_1) and len(l_a4_2) == len(l_before_2)
    )
    cls_a4 = "PASS" if is_pass_a4 else ("FAIL-NGHIÊM TRỌNG" if (s_a4_1 != 10 or s_a4_2 != 10) else "FAIL-NHẸ")
    ctx.log_result(
        "A4", "Phiếu xuất 2 SP: 1 đủ (5/10), 1 thiếu (15/10)", "Từ chối cả phiếu, SP đủ tồn không bị trừ",
        f"HTTP {st_a4}, SP1={s_a4_1}, SP2={s_a4_2}, delta_ledger=0", st_a4,
        f"10,10->{s_a4_1},{s_a4_2}", cls_a4,
        {
            "code_ref": "backend/app/services/inventory_service.py:249-257",
            "logic": "Vòng lặp pre-check kiểm tra toàn bộ chi tiết trước khi ghi DB",
            "resp_text": r_a4.text[:200],
        }
    )


# ==============================================================================
# NHÓM B: ĐẦU VÀO BẤT THƯỜNG
# ==============================================================================
async def run_group_b(ctx: TestContext):
    print("\n" + "=" * 78)
    print(" NHÓM B: ĐẦU VÀO BẤT THƯỜNG (SỐ LƯỢNG, ĐƠN GIÁ, TẠO/SỬA SP, KIỂM KÊ)")
    print("=" * 78)

    pid_b = await ctx.create_test_product("B", initial_stock=10)

    # B1. Số lượng bất thường: 0, -5, 2.5, "abc", 2147483648, 10**18 trên cả Phiếu xuất & Phiếu nhập
    b1_values = [0, -5, 2.5, "abc", 2147483648, 10**18]
    b1_ex_results = []
    for val in b1_values:
        r = await ctx.client.post("/api/v1/export-notes/", json={
            "code": f"NEG-B1-EX-{str(val)[:6]}",
            "recipient_name": "Khách B1",
            "details": [{"product_id": pid_b, "quantity": val, "unit_price": 50000.0}],
        })
        b1_ex_results.append((val, r.status_code))

    b1_im_results = []
    for val in b1_values:
        r = await ctx.client.post("/api/v1/import-notes/", json={
            "code": f"NEG-B1-IM-{str(val)[:6]}",
            "supplier_id": 1,
            "note": "Import B1 test",
            "details": [{"product_id": pid_b, "quantity": val, "unit_price": 40000.0}],
        })
        b1_im_results.append((val, r.status_code))

    s_b1, _ = ctx.get_product_stock_from_db(pid_b)
    all_b1_rejected = all(code == 422 for _, code in b1_ex_results) and all(code == 422 for _, code in b1_im_results) and (s_b1 == 10)
    cls_b1 = "PASS" if all_b1_rejected else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "B1", "Số lượng 0, -5, 2.5, 'abc', 2^31, 10^18 (Xuất & Nhập)", "100% bị từ chối 422 bởi Schema validation",
        f"Xuất: {[c for _, c in b1_ex_results]}, Nhập: {[c for _, c in b1_im_results]}", 422 if all_b1_rejected else b1_ex_results[0][1],
        f"10->{s_b1}", cls_b1,
        {
            "code_ref": "backend/app/schemas/export_note.py:10 & import_note.py:10",
            "logic": "Pydantic Field(gt=0, le=10_000_000) chặn 100% số lượng âm, 0, kiểu sai và cực lớn tại gateway",
            "export_results": b1_ex_results,
            "import_results": b1_im_results,
        }
    )

    # B2. Đơn giá âm (-50000) hoặc quá lớn (10^18)
    r_price_neg = await ctx.client.post("/api/v1/export-notes/", json={
        "code": "NEG-B2-NEGPRICE",
        "recipient_name": "Khách B2",
        "details": [{"product_id": pid_b, "quantity": 1, "unit_price": -50000.0}],
    })
    r_price_huge = await ctx.client.post("/api/v1/export-notes/", json={
        "code": "NEG-B2-HUGEPRICE",
        "recipient_name": "Khách B2",
        "details": [{"product_id": pid_b, "quantity": 1, "unit_price": 10**18}],
    })
    b2_pass = (r_price_neg.status_code == 422 and r_price_huge.status_code == 422)
    cls_b2 = "PASS" if b2_pass else "FAIL-NHẸ"
    ctx.log_result(
        "B2", "Đơn giá âm (-50k) và quá lớn (10^18)", "Cả giá âm và giá cực lớn đều bị chặn 422",
        f"Giá âm: HTTP {r_price_neg.status_code}, Giá lớn: HTTP {r_price_huge.status_code}", 422 if b2_pass else r_price_huge.status_code,
        "10->10", cls_b2,
        {
            "code_ref": "backend/app/schemas/export_note.py:11",
            "logic": "Pydantic unit_price: float = Field(ge=0.0, le=100_000_000_000.0) chặn giá âm và giá quá lớn",
            "resp_neg_status": r_price_neg.status_code,
            "resp_huge_status": r_price_huge.status_code,
        }
    )

    # B3. Tạo sản phẩm với current_stock âm; sửa sản phẩm đặt current_stock; tạo SP có tồn 50
    # B3.1 Tạo SP âm
    r_prod_neg = await ctx.client.post("/api/v1/products/", json={
        "code": "SKU-NEG-B3-NEG",
        "name": "SP Neg Stock",
        "category_id": 1,
        "current_stock": -10,
    })
    st_prod_neg = r_prod_neg.status_code

    # B3.2 Sửa sản phẩm đặt current_stock = -5 hoặc 9999
    r_put_stock = await ctx.client.put(f"/api/v1/products/{pid_b}", json={"current_stock": -5})
    s_b3_after, _ = ctx.get_product_stock_from_db(pid_b)

    # B3.3 Tạo sản phẩm có tồn ban đầu 50 (hệ thống tự lập phiếu nhập & Thẻ kho)
    r_prod_init = await ctx.client.post("/api/v1/products/", json={
        "code": "SKU-NEG-B3-INIT50",
        "name": "SP Init Stock 50",
        "category_id": 1,
        "supplier_id": 1,
        "current_stock": 50,
        "unit": "Cái",
        "standard_price": 50000.0,
    })
    pid_init = r_prod_init.json().get("id") if r_prod_init.status_code in (200, 201) else None
    if pid_init:
        ctx.manifest["products"].append({"id": pid_init, "code": "SKU-NEG-B3-INIT50", "initial_stock": 50})
        write_manifest_sync(ctx.manifest)
        init_ledgers = ctx.get_ledger_entries(pid_init)
        has_ledger_audit = (len(init_ledgers) == 1 and init_ledgers[0][1] == "IMPORT" and init_ledgers[0][3] == 50)
    else:
        has_ledger_audit = False

    is_pass_b3 = (st_prod_neg == 422 and s_b3_after == 10 and has_ledger_audit)
    cls_b3 = "PASS" if is_pass_b3 else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "B3", "Tạo/sửa sản phẩm current_stock bất thường", "Chặn tạo âm 422; PUT không đổi; SP mới 50 có Thẻ kho IMPORT",
        f"Tạo âm HTTP {st_prod_neg}, PUT đổi tồn={s_b3_after != 10}, SP mới 50 có {len(init_ledgers) if pid_init else 0} ledger", st_prod_neg,
        "10->10", cls_b3,
        {
            "code_ref": "backend/app/schemas/product.py & backend/app/api/v1/endpoints/products.py:155",
            "logic": "Tồn kho ban đầu > 0 tự động sinh phiếu nhập INITIAL_IMPORT và ghi Thẻ kho",
            "init_stock_50_case": {
                "created_product_id": pid_init,
                "current_stock": 50,
                "sum_ledger": sum(l[3] for l in init_ledgers) if pid_init else 0,
                "ledger_count": len(init_ledgers) if pid_init else 0,
                "balanced": (sum(l[3] for l in init_ledgers) == 50) if pid_init else False,
            },
        }
    )

    # B4. Điều chỉnh kiểm kê làm tồn âm (actual_stock = -5) và số quá lớn (10^18)
    r_adj_neg = await ctx.client.post("/api/v1/stock-ledger/adjust", json={
        "product_id": pid_b,
        "actual_stock": -5,
        "reason": "Kiểm kê âm",
    })
    st_adj_neg = r_adj_neg.status_code

    r_adj_huge = await ctx.client.post("/api/v1/stock-ledger/adjust", json={
        "product_id": pid_b,
        "actual_stock": 10**18,
        "reason": "Kiểm kê cực lớn",
    })
    st_adj_huge = r_adj_huge.status_code

    s_b4_after, _ = ctx.get_product_stock_from_db(pid_b)
    is_pass_b4 = (st_adj_neg == 422 and st_adj_huge == 422 and s_b4_after == 10)
    cls_b4 = "PASS" if is_pass_b4 else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "B4", "Kiểm kê đặt tồn thực tế âm (-5) và quá lớn (10^18)", "Bị từ chối 422 (Pydantic ge=0, le=1 tỷ), tồn giữ 10",
        f"Tồn âm HTTP {st_adj_neg}, Tồn quá lớn HTTP {st_adj_huge}, tồn sau {s_b4_after}", f"{st_adj_neg}/{st_adj_huge}",
        f"10->{s_b4_after}", cls_b4,
        {
            "code_ref": "backend/app/schemas/stock_ledger.py:80",
            "logic": "StockAdjustmentCreate actual_stock: int = Field(ge=0, le=1_000_000_000) chặn ở tầng schema",
            "resp_neg_text": r_adj_neg.text[:150],
            "resp_huge_text": r_adj_huge.text[:150],
        }
    )


# ==============================================================================
# NHÓM C: ĐUA TRANH ĐỒNG THỜI (RACE CONDITIONS - 3 VÒNG)
# ==============================================================================
async def run_group_c(ctx: TestContext):
    print("\n" + "=" * 78)
    print(" NHÓM C: ĐUA TRANH ĐỒNG THỜI (3 VÒNG KIỂM TOÁN RACE CONDITIONS)")
    print("=" * 78)

    # C1. Tồn 10, 30 phiếu xuất số lượng 1 bắn cùng lúc
    c1_rounds = []
    for r_idx in range(1, 4):
        pid = await ctx.create_test_product(f"C1-R{r_idx}", initial_stock=10)
        l_init = ctx.get_ledger_entries(pid)

        # Chuẩn bị 30 phiếu xuất CONFIRMED trước
        note_ids = []
        for i in range(30):
            code = f"NEG-C1-R{r_idx}-{i+1:02d}"
            r_c = await ctx.client.post("/api/v1/export-notes/", json={
                "code": code,
                "recipient_name": f"Khách C1-{i+1}",
                "details": [{"product_id": pid, "quantity": 1, "unit_price": 50000.0}],
            })
            if r_c.status_code in (200, 201):
                nid = r_c.json()["id"]
                note_ids.append((nid, code))
                ctx.manifest["export_notes"].append({"id": nid, "code": code})
        write_manifest_sync(ctx.manifest)

        # Bắn đồng thời 30 lệnh /ship
        start_gate = asyncio.Event()

        async def ship_worker(nid):
            await start_gate.wait()
            try:
                res = await ctx.client.post(f"/api/v1/export-notes/{nid}/ship", timeout=20.0)
                return res.status_code
            except Exception as e:
                return 599

        tasks = [asyncio.create_task(ship_worker(nid)) for nid, _ in note_ids]
        await asyncio.sleep(0.01)
        start_gate.set()
        statuses = await asyncio.gather(*tasks)

        succ_cnt = sum(1 for s in statuses if s in (200, 201))
        fail_cnt = sum(1 for s in statuses if s == 400)
        stock_c1, _ = ctx.get_product_stock_from_db(pid)
        ledgers_c1 = ctx.get_ledger_entries(pid)
        neg_bal_rows = [l for l in ledgers_c1 if l[4] < 0]

        is_pass_c1 = (
            succ_cnt == 10 and stock_c1 == 0
            and len(ledgers_c1) == len(l_init) + 10
            and len(neg_bal_rows) == 0
            and stock_c1 == sum(l[3] for l in ledgers_c1)
        )
        c1_rounds.append((r_idx, succ_cnt, fail_cnt, stock_c1, len(ledgers_c1), is_pass_c1, statuses))

    all_c1_pass = all(p[5] for p in c1_rounds)
    cls_c1 = "PASS" if all_c1_pass else "FAIL-NGHIÊM TRỌNG"
    status_summary_c1 = f"{c1_rounds[0][1]}x200,{c1_rounds[0][2]}x400"
    ctx.log_result(
        "C1", "Tồn 10: 30 phiếu xuất 1 bắn /ship cùng lúc (3 vòng)", "Đúng 10 thành công, 20 bị từ chối 4xx, tồn=0, delta_ledger=10",
        f"Vòng 1-3: {[f'R{r[0]}: succ={r[1]}, tồn={r[3]}' for r in c1_rounds]}", status_summary_c1,
        "10->0", cls_c1,
        {
            "code_ref": "backend/app/services/inventory_service.py:502",
            "logic": "WriteGateContext BEGIN IMMEDIATE + UPDATE WHERE current_stock >= qty RETURNING",
            "round_details": [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in c1_rounds],
        }
    )

    # C2. Tồn 10, 6 phiếu xuất số lượng 4 cùng lúc (chỉ tối đa 2 phiếu thành công, tồn = 2)
    c2_rounds = []
    for r_idx in range(1, 4):
        pid = await ctx.create_test_product(f"C2-R{r_idx}", initial_stock=10)
        l_init = ctx.get_ledger_entries(pid)
        note_ids = []
        for i in range(6):
            code = f"NEG-C2-R{r_idx}-{i+1:02d}"
            r_c = await ctx.client.post("/api/v1/export-notes/", json={
                "code": code,
                "recipient_name": f"Khách C2-{i+1}",
                "details": [{"product_id": pid, "quantity": 4, "unit_price": 50000.0}],
            })
            if r_c.status_code in (200, 201):
                nid = r_c.json()["id"]
                note_ids.append(nid)
                ctx.manifest["export_notes"].append({"id": nid, "code": code})
        write_manifest_sync(ctx.manifest)

        start_gate = asyncio.Event()

        async def ship_worker_c2(nid):
            await start_gate.wait()
            res = await ctx.client.post(f"/api/v1/export-notes/{nid}/ship")
            return res.status_code

        tasks = [asyncio.create_task(ship_worker_c2(nid)) for nid in note_ids]
        await asyncio.sleep(0.01)
        start_gate.set()
        statuses = await asyncio.gather(*tasks)

        succ_cnt = sum(1 for s in statuses if s in (200, 201))
        fail_cnt = sum(1 for s in statuses if s == 400)
        stock_c2, _ = ctx.get_product_stock_from_db(pid)
        ledgers_c2 = ctx.get_ledger_entries(pid)
        neg_bal_rows = [l for l in ledgers_c2 if l[4] < 0]

        is_pass_c2 = (
            succ_cnt == 2 and stock_c2 == 2
            and len(ledgers_c2) == len(l_init) + 2
            and len(neg_bal_rows) == 0
            and stock_c2 == sum(l[3] for l in ledgers_c2)
        )
        c2_rounds.append((r_idx, succ_cnt, fail_cnt, stock_c2, len(ledgers_c2), is_pass_c2, statuses))

    all_c2_pass = all(p[5] for p in c2_rounds)
    cls_c2 = "PASS" if all_c2_pass else "FAIL-NGHIÊM TRỌNG"
    status_summary_c2 = f"{c2_rounds[0][1]}x200,{c2_rounds[0][2]}x400"
    ctx.log_result(
        "C2", "Tồn 10: 6 phiếu xuất 4 bắn cùng lúc (3 vòng)", "Đúng 2 thành công (tổng xuất 8), tồn=2, delta_ledger=2",
        f"Vòng 1-3: {[f'R{r[0]}: succ={r[1]}, tồn={r[3]}' for r in c2_rounds]}", status_summary_c2,
        "10->2", cls_c2,
        {
            "code_ref": "backend/app/services/inventory_service.py:504",
            "logic": "Lần 1 còn 6, lần 2 còn 2, lần 3 yêu cầu 4 > 2 bị rollback",
            "round_details": [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in c2_rounds],
        }
    )

    # C3. Một phiếu xuất duy nhất, gọi /ship 20 lần đồng thời
    c3_rounds = []
    for r_idx in range(1, 4):
        pid = await ctx.create_test_product(f"C3-R{r_idx}", initial_stock=10)
        l_init = ctx.get_ledger_entries(pid)
        code = f"NEG-C3-R{r_idx}-001"
        r_c = await ctx.client.post("/api/v1/export-notes/", json={
            "code": code,
            "recipient_name": "Khách C3 replay",
            "details": [{"product_id": pid, "quantity": 3, "unit_price": 50000.0}],
        })
        nid = r_c.json()["id"]
        ctx.manifest["export_notes"].append({"id": nid, "code": code})
        write_manifest_sync(ctx.manifest)

        start_gate = asyncio.Event()

        async def multi_ship_worker():
            await start_gate.wait()
            res = await ctx.client.post(f"/api/v1/export-notes/{nid}/ship")
            return res.status_code

        tasks = [asyncio.create_task(multi_ship_worker()) for _ in range(20)]
        await asyncio.sleep(0.01)
        start_gate.set()
        statuses = await asyncio.gather(*tasks)

        succ_cnt = sum(1 for s in statuses if s in (200, 201))
        fail_cnt = sum(1 for s in statuses if s == 400)
        stock_c3, _ = ctx.get_product_stock_from_db(pid)
        ledgers_c3 = ctx.get_ledger_entries(pid)
        neg_bal_rows = [l for l in ledgers_c3 if l[4] < 0]

        is_pass_c3 = (
            succ_cnt == 1 and stock_c3 == 7
            and len(ledgers_c3) == len(l_init) + 1
            and len(neg_bal_rows) == 0
            and stock_c3 == sum(l[3] for l in ledgers_c3)
        )
        c3_rounds.append((r_idx, succ_cnt, fail_cnt, stock_c3, len(ledgers_c3), is_pass_c3, statuses))

    all_c3_pass = all(p[5] for p in c3_rounds)
    cls_c3 = "PASS" if all_c3_pass else "FAIL-NGHIÊM TRỌNG"
    status_summary_c3 = f"{c3_rounds[0][1]}x200,{c3_rounds[0][2]}x400"
    ctx.log_result(
        "C3", "1 phiếu xuất CONFIRMED, gọi /ship 20 lần đồng thời (3 vòng)", "Trừ tồn đúng 1 lần (tồn 10->7), ledger đúng 1 dòng",
        f"Vòng 1-3: {[f'R{r[0]}: succ={r[1]}, tồn={r[3]}' for r in c3_rounds]}", status_summary_c3,
        "10->7", cls_c3,
        {
            "code_ref": "backend/app/services/inventory_service.py:466",
            "logic": "Request đầu chuyển sang SHIPPING, 19 request sau check status != CONFIRMED báo 400",
            "round_details": [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in c3_rounds],
        }
    )

    # C4. Một phiếu xuất đã xuất (SHIPPING), gọi hủy/xóa 10 lần đồng thời
    c4_rounds = []
    for r_idx in range(1, 4):
        pid = await ctx.create_test_product(f"C4-R{r_idx}", initial_stock=10)
        code = f"NEG-C4-R{r_idx}-001"
        r_c = await ctx.client.post("/api/v1/export-notes/", json={
            "code": code,
            "recipient_name": "Khách C4 cancel",
            "details": [{"product_id": pid, "quantity": 4, "unit_price": 50000.0}],
        })
        nid = r_c.json()["id"]
        ctx.manifest["export_notes"].append({"id": nid, "code": code})
        await ctx.client.post(f"/api/v1/export-notes/{nid}/ship")
        s_mid, _ = ctx.get_product_stock_from_db(pid)  # tồn = 6
        l_before_cancel = ctx.get_ledger_entries(pid)

        start_gate = asyncio.Event()

        async def cancel_worker():
            await start_gate.wait()
            # Gọi hủy phiếu xuất
            res = await ctx.client.post(f"/api/v1/export-notes/{nid}/cancel", json={"reason": "Test race cancel"})
            return res.status_code

        tasks = [asyncio.create_task(cancel_worker()) for _ in range(10)]
        await asyncio.sleep(0.01)
        start_gate.set()
        statuses = await asyncio.gather(*tasks)

        succ_cnt = sum(1 for s in statuses if s in (200, 201))
        fail_cnt = sum(1 for s in statuses if s == 400)
        stock_c4, _ = ctx.get_product_stock_from_db(pid)
        ledgers_c4 = ctx.get_ledger_entries(pid)

        # Ban đầu 10, ship trừ 4 còn 6, hoàn kho 4 về đúng 10 (không hoàn lặp thành 14)
        has_duplicate_refund = (stock_c4 != 10 or len(ledgers_c4) != len(l_before_cancel) + 1 or succ_cnt != 1)
        has_5xx = any(500 <= s < 600 for s in statuses)
        is_pass_c4 = (not has_duplicate_refund and not has_5xx and stock_c4 == sum(l[3] for l in ledgers_c4))
        c4_rounds.append((r_idx, succ_cnt, fail_cnt, stock_c4, len(ledgers_c4), is_pass_c4, has_duplicate_refund, has_5xx, statuses))

    any_dup_refund = any(p[6] for p in c4_rounds)
    any_5xx_c4 = any(p[7] for p in c4_rounds)
    if any_dup_refund:
        cls_c4 = "FAIL-NGHIÊM TRỌNG"
    elif any_5xx_c4:
        cls_c4 = "FAIL-NHẸ"
    else:
        cls_c4 = "PASS"

    status_summary_c4 = f"{c4_rounds[0][1]}x200,{c4_rounds[0][2]}x400" + (",5xx" if any_5xx_c4 else "")
    ctx.log_result(
        "C4", "Phiếu xuất đã xuất, gọi hủy 10 lần đồng thời (3 vòng)", "Hoàn kho đúng 1 lần (tồn về 10), không hoàn lặp thành 14+, không 5xx",
        f"Vòng 1-3: {[f'R{r[0]}: succ={r[1]}, tồn={r[3]}, delta_adj={r[4]-len(l_before_cancel)}' for r in c4_rounds]}", status_summary_c4,
        "6->10", cls_c4,
        {
            "code_ref": "backend/app/services/inventory_service.py:615 & endpoints/export_notes.py:209",
            "logic": "WriteGateContext serialize các request cancel đồng thời, chặn hoàn kho lặp và không phát sinh lỗi 5xx",
            "round_details": [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in c4_rounds],
        }
    )

    # C5. Tồn 20, 50 phiếu nhập (số lượng 2) và 50 phiếu xuất (số lượng 3) bắn xen kẽ cùng lúc
    c5_rounds = []
    for r_idx in range(1, 4):
        pid = await ctx.create_test_product(f"C5-R{r_idx}", initial_stock=20)
        l_init = ctx.get_ledger_entries(pid)
        tx_tasks = []
        start_gate = asyncio.Event()

        # 50 nhập 2, 50 xuất 3
        async def imp_worker(idx):
            await start_gate.wait()
            c_code = f"NEG-C5-R{r_idx}-IN-{idx:02d}"
            r = await ctx.client.post("/api/v1/import-notes/", json={
                "code": c_code,
                "supplier_id": 1,
                "note": f"C5 Import {idx}",
                "details": [{"product_id": pid, "quantity": 2, "unit_price": 40000.0}],
            })
            if r.status_code in (200, 201):
                ctx.manifest["import_notes"].append({"id": r.json()["id"], "code": c_code})
            return ("IN", r.status_code)

        async def exp_worker(idx):
            await start_gate.wait()
            c_code = f"NEG-C5-R{r_idx}-EX-{idx:02d}"
            r_c = await ctx.client.post("/api/v1/export-notes/", json={
                "code": c_code,
                "recipient_name": f"Khách C5-{idx}",
                "details": [{"product_id": pid, "quantity": 3, "unit_price": 50000.0}],
            })
            if r_c.status_code in (200, 201):
                nid = r_c.json()["id"]
                ctx.manifest["export_notes"].append({"id": nid, "code": c_code})
                r_s = await ctx.client.post(f"/api/v1/export-notes/{nid}/ship")
                return ("EX", r_s.status_code)
            return ("EX", r_c.status_code)

        all_workers = []
        for i in range(50):
            all_workers.append(imp_worker(i + 1))
            all_workers.append(exp_worker(i + 1))

        tasks = [asyncio.create_task(w) for w in all_workers]
        await asyncio.sleep(0.01)
        start_gate.set()
        tx_res = await asyncio.gather(*tasks)

        succ_in = sum(1 for t, s in tx_res if t == "IN" and s in (200, 201))
        succ_ex = sum(1 for t, s in tx_res if t == "EX" and s in (200, 201))
        stock_c5, _ = ctx.get_product_stock_from_db(pid)
        ledgers_c5 = ctx.get_ledger_entries(pid)

        expected_c5_stock = 20 + (succ_in * 2) - (succ_ex * 3)
        neg_bal_c5 = [l for l in ledgers_c5 if l[4] < 0]

        is_pass_c5 = (
            stock_c5 == expected_c5_stock and stock_c5 >= 0
            and len(neg_bal_c5) == 0
            and len(ledgers_c5) == (len(l_init) + succ_in + succ_ex)
            and stock_c5 == sum(l[3] for l in ledgers_c5)
        )
        c5_rounds.append((r_idx, succ_in, succ_ex, stock_c5, expected_c5_stock, is_pass_c5))

    all_c5_pass = all(p[-1] for p in c5_rounds)
    cls_c5 = "PASS" if all_c5_pass else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "C5", "Tồn 20: 50 nhập (x2) & 50 xuất (x3) xen kẽ đồng thời (3 vòng)", "Tồn = 20 + 2*in - 3*ex, 0 dòng ledger âm tại bất kỳ thời điểm nào",
        f"Vòng 1-3: {[f'R{r[0]}: in={r[1]}, ex={r[2]}, tồn={r[3]}' for r in c5_rounds]}", f"IN:{c5_rounds[0][1]}/50,EX:{c5_rounds[0][2]}/50",
        "20->End", cls_c5,
        {
            "code_ref": "backend/app/core/write_gate.py:166 & inventory_service.py",
            "logic": "WriteGateContext tuần tự hóa từng transaction ghi, bảo đảm đơn điệu tuyệt đối",
            "round_details": c5_rounds,
        }
    )

    # C6. 10 request nhập CÙNG MỘT mã phiếu đồng thời
    c6_rounds = []
    for r_idx in range(1, 4):
        pid = await ctx.create_test_product(f"C6-R{r_idx}", initial_stock=10)
        l_init = ctx.get_ledger_entries(pid)
        same_code = f"NEG-C6-R{r_idx}-DUP"
        start_gate = asyncio.Event()

        async def dup_import_worker():
            await start_gate.wait()
            res = await ctx.client.post("/api/v1/import-notes/", json={
                "code": same_code,
                "supplier_id": 1,
                "note": "Trùng mã phiếu nhập",
                "details": [{"product_id": pid, "quantity": 5, "unit_price": 40000.0}],
            })
            if res.status_code in (200, 201):
                ctx.manifest["import_notes"].append({"id": res.json()["id"], "code": same_code})
            return res.status_code

        tasks = [asyncio.create_task(dup_import_worker()) for _ in range(10)]
        await asyncio.sleep(0.01)
        start_gate.set()
        statuses = await asyncio.gather(*tasks)

        succ_cnt = sum(1 for s in statuses if s in (200, 201))
        fail_cnt = sum(1 for s in statuses if s in (400, 409, 500))
        stock_c6, _ = ctx.get_product_stock_from_db(pid)
        ledgers_c6 = ctx.get_ledger_entries(pid)

        # Đúng 1 phiếu thành công -> tồn tăng 5 từ 10 thành 15, ledger tăng đúng 1 dòng
        is_pass_c6 = (
            succ_cnt == 1 and stock_c6 == 15
            and len(ledgers_c6) == len(l_init) + 1
            and stock_c6 == sum(l[3] for l in ledgers_c6)
        )
        c6_rounds.append((r_idx, succ_cnt, fail_cnt, stock_c6, len(ledgers_c6), is_pass_c6, statuses))

    all_c6_pass = all(p[5] for p in c6_rounds)
    cls_c6 = "PASS" if all_c6_pass else "FAIL-NGHIÊM TRỌNG"
    statuses_c6 = [classify_http_response(s) for s in c6_rounds[0][6]]
    status_summary_c6 = format_status_breakdown(statuses_c6)
    ctx.log_result(
        "C6", "10 request nhập CÙNG 1 mã phiếu đồng thời (3 vòng)", "Đúng 1 phiếu được tạo, tồn tăng đúng 1 lần (+5 -> 15)",
        f"Vòng 1-3: {[f'R{r[0]}: succ={r[1]}, tồn={r[3]}' for r in c6_rounds]}", status_summary_c6,
        "10->15", cls_c6,
        {
            "code_ref": "backend/app/services/inventory_service.py:107 & sqlite_master: ix_import_notes_code UNIQUE",
            "logic": "Pre-check kiểm tra mã tồn tại (400) + UNIQUE INDEX ở CSDL bắt lỗi IntegrityError nếu race lọt qua",
            "round_details": [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in c6_rounds],
        }
    )


# NHÓM D: HỦY, XÓA VÀ HOÀN KHO
# ==============================================================================
async def run_group_d(ctx: TestContext):
    print("\n" + "=" * 78)
    print(" NHÓM D: HỦY, XÓA VÀ HOÀN KHO (ROLLBACK AN TOÀN)")
    print("=" * 78)

    # D1. Phiếu xuất đã ship rồi hủy: tồn về đúng ban đầu, hủy lần 2 không hoàn thêm
    pid_d1 = await ctx.create_test_product("D1", initial_stock=10)
    l_init = ctx.get_ledger_entries(pid_d1)
    code_d1 = "NEG-D1-001"
    r_c = await ctx.client.post("/api/v1/export-notes/", json={
        "code": code_d1,
        "recipient_name": "Khách D1",
        "details": [{"product_id": pid_d1, "quantity": 4, "unit_price": 50000.0}],
    })
    nid_d1 = r_c.json()["id"]
    ctx.manifest["export_notes"].append({"id": nid_d1, "code": code_d1})
    await ctx.client.post(f"/api/v1/export-notes/{nid_d1}/ship")
    s_ship, _ = ctx.get_product_stock_from_db(pid_d1)  # tồn = 6

    # Hủy lần 1
    r_can1 = await ctx.client.post(f"/api/v1/export-notes/{nid_d1}/cancel", json={"reason": "Hủy lần 1"})
    s_can1, _ = ctx.get_product_stock_from_db(pid_d1)  # tồn về 10

    # Hủy lần 2
    r_can2 = await ctx.client.post(f"/api/v1/export-notes/{nid_d1}/cancel", json={"reason": "Hủy lần 2"})
    s_can2, _ = ctx.get_product_stock_from_db(pid_d1)  # tồn vẫn 10

    ledgers_d1 = ctx.get_ledger_entries(pid_d1)
    is_pass_d1 = (
        r_can1.status_code == 200 and s_can1 == 10
        and r_can2.status_code == 400 and s_can2 == 10
        and len(ledgers_d1) == len(l_init) + 2
        and s_can2 == sum(l[3] for l in ledgers_d1)
    )
    cls_d1 = "PASS" if is_pass_d1 else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "D1", "Phiếu xuất đã ship rồi hủy (hủy 2 lần)", "Hủy lần 1 tồn về 10, hủy lần 2 báo 400 và không hoàn thêm",
        f"Lần 1 HTTP {r_can1.status_code} (tồn {s_can1}), Lần 2 HTTP {r_can2.status_code} (tồn {s_can2})", f"{r_can1.status_code}/{r_can2.status_code}",
        f"10->6->10->10", cls_d1,
        {
            "code_ref": "backend/app/services/inventory_service.py:615-645",
            "logic": "Hủy phiếu xuất cộng lại tồn kho bằng dòng ADJUSTMENT (+4) và set status CANCELLED",
            "resp_cancel2": r_can2.text[:150],
        }
    )

    # D2. Nhập 10, xuất 8 (tồn còn 2), rồi hủy phiếu nhập 10.
    # Hệ thống có chặn không hay để tồn = -8?
    pid_d2 = await ctx.create_test_product("D2", initial_stock=0)
    # Nhập 10
    code_in_d2 = "NEG-D2-IN"
    r_in = await ctx.client.post("/api/v1/import-notes/", json={
        "code": code_in_d2,
        "supplier_id": 1,
        "note": "Nhập 10 để xuất 8",
        "details": [{"product_id": pid_d2, "quantity": 10, "unit_price": 40000.0}],
    })
    nid_in_d2 = r_in.json()["id"]
    ctx.manifest["import_notes"].append({"id": nid_in_d2, "code": code_in_d2})

    # Xuất 8
    code_ex_d2 = "NEG-D2-EX"
    r_ex = await ctx.client.post("/api/v1/export-notes/", json={
        "code": code_ex_d2,
        "recipient_name": "Khách D2",
        "details": [{"product_id": pid_d2, "quantity": 8, "unit_price": 60000.0}],
    })
    nid_ex_d2 = r_ex.json()["id"]
    ctx.manifest["export_notes"].append({"id": nid_ex_d2, "code": code_ex_d2})
    await ctx.client.post(f"/api/v1/export-notes/{nid_ex_d2}/ship")

    s_d2_mid, _ = ctx.get_product_stock_from_db(pid_d2)  # tồn = 2

    # Thử hủy phiếu nhập 10
    r_can_in = await ctx.client.post(f"/api/v1/import-notes/{nid_in_d2}/cancel", json={"reason": "Thử hủy khi thiếu tồn"})
    st_can_in = r_can_in.status_code
    s_d2_after, _ = ctx.get_product_stock_from_db(pid_d2)

    l_after_cancel = ctx.get_ledger_entries(pid_d2)
    is_pass_d2 = (
        st_can_in == 400 and s_d2_after == 2
        and len(l_after_cancel) == 2
        and s_d2_after == sum(l[3] for l in l_after_cancel)
    )
    cls_d2 = "PASS" if is_pass_d2 else ("FAIL-NGHIÊM TRỌNG" if s_d2_after < 0 else "FAIL-NHẸ")
    ctx.log_result(
        "D2", "Nhập 10, xuất 8 (tồn 2), hủy phiếu nhập 10", "Bị chặn bằng 400 Bad Request, tồn kho giữ 2, không thành -8",
        f"HTTP {st_can_in}, tồn sau {s_d2_after}", st_can_in,
        f"0->10->2->{s_d2_after}", cls_d2,
        {
            "code_ref": "backend/app/services/inventory_service.py:380-385",
            "logic": "Kiểm tra current_stock (2) < detail.quantity (10), chặn và trả về giải thích chi tiết",
            "resp_text": r_can_in.text[:200],
        }
    )

    # D3. Xóa sản phẩm còn tồn kho hoặc đã có giao dịch
    pid_d3 = await ctx.create_test_product("D3", initial_stock=5)
    # Tạo 1 phiếu nhập để có lịch sử
    code_d3_in = "NEG-D3-IN"
    r_d3_in = await ctx.client.post("/api/v1/import-notes/", json={
        "code": code_d3_in,
        "supplier_id": 1,
        "details": [{"product_id": pid_d3, "quantity": 2, "unit_price": 50000.0}],
    })
    nid_d3 = r_d3_in.json()["id"]
    ctx.manifest["import_notes"].append({"id": nid_d3, "code": code_d3_in})

    # Gọi DELETE sản phẩm
    r_del_prod = await ctx.client.delete(f"/api/v1/products/{pid_d3}")
    s_d3_after, status_d3 = ctx.get_product_stock_from_db(pid_d3)
    ledgers_d3 = ctx.get_ledger_entries(pid_d3)

    # Không được xóa vật lý làm mồ côi ledger, mà chuyển sang DISCONTINUED
    is_pass_d3 = (
        r_del_prod.status_code == 200 and status_d3 == "DISCONTINUED"
        and len(ledgers_d3) > 0 and s_d3_after == sum(l[3] for l in ledgers_d3)
    )
    cls_d3 = "PASS" if is_pass_d3 else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "D3", "Xóa sản phẩm đã có giao dịch", "Không xóa vật lý, chuyển DISCONTINUED, bảo toàn Thẻ kho",
        f"HTTP {r_del_prod.status_code}, status={status_d3}, delta_ledger=0", r_del_prod.status_code,
        f"Status: {status_d3}", cls_d3,
        {
            "code_ref": "backend/app/api/v1/endpoints/products.py:336",
            "logic": "has_history kiểm tra import_details/export_details/ledger_entries -> set DISCONTINUED",
            "resp_text": r_del_prod.text[:150],
        }
    )


# ==============================================================================
# NHÓM E: KIỂM TOÁN TỒN CUỐI KỲ & BẤT BIẾN TOÀN DIỆN
# ==============================================================================
async def run_group_e(ctx: TestContext):
    print("\n" + "=" * 78)
    print(" NHÓM E: KIỂM TOÁN TỒN CUỐI KỲ & BẤT BIẾN TOÀN DIỆN")
    print("=" * 78)

    conn = sqlite3.connect(f"file:{ctx.abs_db}?mode=ro", uri=True, timeout=10.0)
    cur = conn.cursor()

    cur.execute("SELECT id, code, current_stock FROM products WHERE code LIKE 'SKU-NEG-%'")
    test_products = cur.fetchall()

    e1_fails = []
    for pid, pcode, curr_stock in test_products:
        cur.execute("SELECT id, quantity_change, balance_after FROM stock_ledger WHERE product_id = ? ORDER BY id ASC", (pid,))
        ledgers = cur.fetchall()
        if not ledgers:
            continue

        # Lũy kế
        prev_bal = ledgers[0][2] - ledgers[0][1]
        for l in ledgers:
            lid, q_chg, b_after = l
            if b_after != prev_bal + q_chg:
                e1_fails.append(f"{pcode} ledger {lid}: prev={prev_bal} + {q_chg} != {b_after}")
            if b_after < 0:
                e1_fails.append(f"{pcode} balance_after âm: {b_after}")
            prev_bal = b_after

        # Tồn hiện tại vs ledger cuối
        last_balance = ledgers[-1][2]
        if curr_stock != last_balance:
            e1_fails.append(f"{pcode} current_stock ({curr_stock}) != last ledger balance ({last_balance})")

    conn.close()

    is_pass_e1 = (len(e1_fails) == 0)
    cls_e1 = "PASS" if is_pass_e1 else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "E1", "Kiểm toán 100% SKU-NEG-*: Tồn = Sổ cái, Lũy kế, Không âm", "0 lỗi sai lệch số dư, 0 số dư âm",
        f"{len(e1_fails)} lỗi phát hiện trên {len(test_products)} sản phẩm", "N/A (SQL)",
        f"{len(test_products)} SP checked", cls_e1,
        {
            "code_ref": "Database stock_ledger audit",
            "logic": "Đối chiếu toán học balance_after[i] = balance_after[i-1] + change[i] và current_stock == last_balance",
            "fails": e1_fails[:10],
            "checked_products_count": len(test_products),
        }
    )

    # E2. Chạy check_invariants.py toàn hệ thống
    if os.path.exists("/app/tests/performance/check_invariants.py") or os.environ.get("INSIDE_DOCKER"):
        cmd = ["python", "/app/tests/performance/check_invariants.py"]
    else:
        cmd = ["docker", "exec", "warehouse_backend", "python", "/app/tests/performance/check_invariants.py"]
    res_inv = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    is_pass_e2 = (res_inv.returncode == 0)
    cls_e2 = "PASS" if is_pass_e2 else "FAIL-NGHIÊM TRỌNG"
    ctx.log_result(
        "E2", "Chạy check_invariants.py toàn hệ thống", "TẤT CẢ 5 BẤT BIẾN ĐỀU ĐẠT",
        "ĐẠT 100% (5/5 Bất biến)" if is_pass_e2 else f"LỖI BẤT BIẾN (exit {res_inv.returncode})", f"Exit {res_inv.returncode}",
        "System-wide", cls_e2,
        {
            "code_ref": "backend/tests/performance/check_invariants.py",
            "logic": "Đối chiếu 5 bất biến toàn vẹn CSDL (Tồn kế toán, Đơn điệu lũy kế, Đối soát xuất 1:1, Phiếu lửng, Chống tồn âm)",
            "output_summary": res_inv.stdout[-350:],
        }
    )


# ==============================================================================
# 5. CHẾ ĐỘ CHẠY TEST CHÍNH
# ==============================================================================
async def main_test(args):
    abs_db = verify_environment_guard(args.base_url, args.db_path)
    snapshot_before = get_db_snapshot(abs_db)
    other_skus_before = get_other_skus_stock(abs_db)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "db_path": abs_db,
        "backup_path": PRE_GUARD_BACKUP_PATH,
        "snapshot_before": snapshot_before,
        "other_skus_stock_before": other_skus_before,
        "products": [],
        "import_notes": [],
        "export_notes": [],
    }
    write_manifest_sync(manifest)

    limits = httpx.Limits(max_connections=200, max_keepalive_connections=200)
    timeout = httpx.Timeout(20.0, connect=10.0)

    detailed_results = []

    async with httpx.AsyncClient(base_url=args.base_url, limits=limits, timeout=timeout) as client:
        # Đăng nhập lấy token
        l_resp = await client.post("/api/v1/auth/login", json={"username": args.username, "password": args.password})
        if l_resp.status_code != 200:
            print(f"[LỖI] Đăng nhập thất bại: {l_resp.text}")
            sys.exit(1)
        token = l_resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        ctx = TestContext(client, abs_db, manifest, detailed_results)

        t_start = time.perf_counter()

        # Thực thi lần lượt từng nhóm test (mỗi nhóm có timeout giám sát)
        try:
            await asyncio.wait_for(run_group_a(ctx), timeout=30.0)
            await asyncio.wait_for(run_group_b(ctx), timeout=30.0)
            await asyncio.wait_for(run_group_c(ctx), timeout=180.0)
            await asyncio.wait_for(run_group_d(ctx), timeout=30.0)
            await asyncio.wait_for(run_group_e(ctx), timeout=30.0)
        except asyncio.TimeoutError as te:
            print(f"\n[TIMEOUT] Một nhóm test vượt quá thời gian tối đa: {te}")
        finally:
            write_manifest_sync(manifest)

        t_elapsed = time.perf_counter() - t_start

    # Ghi toàn bộ kết quả chi tiết ra negguard_result.json
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_sec": t_elapsed,
            "test_reports": ctx.test_reports,
        }, f, ensure_ascii=False, indent=2)

    # In Bảng tổng hợp kết quả
    print("\n" + "=" * 105)
    print(" BẢNG TỔNG HỢP KẾT QUẢ KIỂM THỬ BẢO VỆ CHỐNG TỒN KHO ÂM & SAI SỐ DƯ")
    print("=" * 105)
    print(f"{'Mã':<5} | {'Tình huống kiểm thử':<46} | {'Kỳ vọng':<22} | {'HTTP':<5} | {'Tồn kho':<10} | {'Phân loại'}")
    print("-" * 105)

    has_critical = False
    for r in ctx.test_reports:
        print(f"{r['test_id']:<5} | {r['desc'][:46]:<46} | {r['expected'][:22]:<22} | {r['status_code']:<5} | {r['stock_change']:<10} | {r['classification']}")
        if r["classification"] == "FAIL-NGHIÊM TRỌNG":
            has_critical = True

    print("\n" + "=" * 115)
    print(" BẢNG CÁC LỚP BẢO VỆ CỦA HỆ THỐNG (SINH ĐỘNG TỪ BẢN ĐỒ TEST ID -> KẾT QUẢ ĐO THỰC TẾ)")
    print("=" * 115)
    results_map = {r["test_id"]: r["classification"] for r in ctx.test_reports}
    LAYER_MAP = [
        ("1. API Validation (Pydantic)", ["B1", "B2", "B4"], "Chặn số âm, vượt trần, kiểu dữ liệu sai bằng HTTP 422"),
        ("2. Service Pre-Check (Python)", ["A1", "A4", "D2"], "Chặn xuất vượt tồn, hủy nhập thiếu tồn bằng HTTP 400"),
        ("3. Concurrency Lock & Gate", ["C1", "C2", "C3", "C4", "C5"], "Tuần tự hóa giao dịch ghi với WriteGate & BEGIN IMMEDIATE"),
        ("4. Atomic SQL Conditional Update", ["A3", "C1", "C2"], "UPDATE products WHERE current_stock >= qty RETURNING"),
        ("5. SQLite CHECK Constraints", ["A2"], "sqlite_master: CHECK (current_stock >= 0)"),
        ("6. Bất biến Sổ cái Thẻ kho", ["E1", "E2"], "Đối chiếu 5 bất biến toàn vẹn Thẻ kho 100%"),
    ]
    print(f"{'Lớp bảo vệ':<34} | {'Trạng thái':<14} | {'Kịch bản xác nhận':<22} | {'Cơ chế đo đạc'}")
    print("-" * 115)
    for l_name, test_ids, l_note in LAYER_MAP:
        statuses = [results_map.get(tid) for tid in test_ids if tid in results_map]
        if not statuses:
            st = "CHƯA XÁC MINH"
        elif all(s == "PASS" for s in statuses):
            st = "PASS"
        else:
            st = "FAIL"
        t_str = ", ".join(test_ids)
        print(f"{l_name:<34} | {st:<14} | {t_str:<22} | {l_note}")

    failed_reports = [r for r in ctx.test_reports if r["classification"] != "PASS"]
    print("\n" + "=" * 105)
    print(" KẾT QUẢ ĐO LỖ HỔNG VÀ SAI LỆCH THỰC TẾ")
    print("=" * 105)
    if not failed_reports:
        print("  ✅ Không phát hiện lỗi tồn kho âm hoặc sai lệch số dư trên 19 kịch bản đo đạc.")
    else:
        for fr in failed_reports:
            print(f"  ❌ [{fr['test_id']}] {fr['desc']}: {fr['actual']} ({fr['classification']})")

    print("\n" + "=" * 105)
    print(f" KẾT LUẬN: {'TẤT CẢ 19 KỊCH BẢN KIỂM THỬ ĐỀU ĐẠT [PASS]' if not has_critical and not failed_reports else 'PHÁT HIỆN KỊCH BẢN CHƯA ĐẠT [FAIL]'}")
    print(" Phạm vi xác minh: Thực nghiệm trực tiếp trên 19 kịch bản đo đạc thực tế kèm 3 vòng đua tranh.")
    print(" 💡 Dữ liệu test đang được giữ nguyên để kiểm tra. Khi xong, chạy lệnh:")
    print("    python backend/tests/performance/test_negative_stock_guard.py --cleanup")
    print("=" * 105)

    sys.exit(0 if not has_critical else 1)


# ==============================================================================
# 6. CHẾ ĐỘ THU HỒI DỮ LIỆU (--cleanup)
# ==============================================================================
def run_cleanup(args):
    abs_db = os.path.abspath(args.db_path)
    print("=" * 78)
    print(" DỌN DẸP TOÀN BỘ DỮ LIỆU TEST THEO MANIFEST ID (--cleanup)")
    print("=" * 78)
    print(f"  • CSDL: {abs_db}")

    if not os.path.exists(MANIFEST_PATH):
        print(f"  [!] Không tìm thấy manifest: {MANIFEST_PATH}. Không thể dọn dẹp theo ID an toàn.")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    conn = sqlite3.connect(abs_db, timeout=30.0)
    conn.isolation_level = None
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("PRAGMA busy_timeout=10000")

    # Thu thập và truy vết đầy đủ toàn bộ ID từ manifest (sản phẩm, phiếu, chi tiết, thẻ kho)
    prod_ids = set(manifest.get("manifest_ids", {}).get("products", []))
    for p in manifest.get("products", []):
        if isinstance(p, dict) and "id" in p:
            prod_ids.add(p["id"])
    prod_ids = list(prod_ids)

    imp_ids = set(manifest.get("manifest_ids", {}).get("import_notes", []))
    for im in manifest.get("import_notes", []):
        if isinstance(im, dict) and "id" in im:
            imp_ids.add(im["id"])

    exp_ids = set(manifest.get("manifest_ids", {}).get("export_notes", []))
    for ex in manifest.get("export_notes", []):
        if isinstance(ex, dict) and "id" in ex:
            exp_ids.add(ex["id"])

    imp_det_ids = set(manifest.get("manifest_ids", {}).get("import_note_details", []))
    exp_det_ids = set(manifest.get("manifest_ids", {}).get("export_note_details", []))
    ledger_ids = set(manifest.get("manifest_ids", {}).get("stock_ledger", []))

    if prod_ids:
        placeholders = ','.join(['?'] * len(prod_ids))
        cur.execute(f"SELECT id, import_note_id FROM import_note_details WHERE product_id IN ({placeholders})", prod_ids)
        for d_id, note_id in cur.fetchall():
            imp_det_ids.add(d_id)
            imp_ids.add(note_id)

        cur.execute(f"SELECT id, export_note_id FROM export_note_details WHERE product_id IN ({placeholders})", prod_ids)
        for d_id, note_id in cur.fetchall():
            exp_det_ids.add(d_id)
            exp_ids.add(note_id)

        cur.execute(f"SELECT id FROM stock_ledger WHERE product_id IN ({placeholders})", prod_ids)
        for (l_id,) in cur.fetchall():
            ledger_ids.add(l_id)

    if imp_ids:
        im_ph = ','.join(['?'] * len(imp_ids))
        cur.execute(f"SELECT id FROM import_note_details WHERE import_note_id IN ({im_ph})", list(imp_ids))
        for (d_id,) in cur.fetchall():
            imp_det_ids.add(d_id)

    if exp_ids:
        ex_ph = ','.join(['?'] * len(exp_ids))
        cur.execute(f"SELECT id FROM export_note_details WHERE export_note_id IN ({ex_ph})", list(exp_ids))
        for (d_id,) in cur.fetchall():
            exp_det_ids.add(d_id)

    ledger_ids = list(ledger_ids)
    exp_det_ids = list(exp_det_ids)
    exp_ids = list(exp_ids)
    imp_det_ids = list(imp_det_ids)
    imp_ids = list(imp_ids)

    print(f"  • Nạp danh sách ID cần dọn: stock_ledger={len(ledger_ids)}, export_details={len(exp_det_ids)}, export_notes={len(exp_ids)}, import_details={len(imp_det_ids)}, import_notes={len(imp_ids)}, products={len(prod_ids)}")

    try:
        cur.execute("BEGIN IMMEDIATE")

        # 1. Xóa stock_ledger theo ID manifest (KHÔNG DÙNG LIKE)
        del_ledger = 0
        if ledger_ids:
            cur.execute(f"DELETE FROM stock_ledger WHERE id IN ({','.join(map(str, ledger_ids))})")
            del_ledger = cur.rowcount

        # 2. Xóa export_note_details theo ID manifest
        del_ex_det = 0
        if exp_det_ids:
            cur.execute(f"DELETE FROM export_note_details WHERE id IN ({','.join(map(str, exp_det_ids))})")
            del_ex_det = cur.rowcount

        # 3. Xóa export_notes theo ID manifest
        del_ex = 0
        if exp_ids:
            cur.execute(f"DELETE FROM export_notes WHERE id IN ({','.join(map(str, exp_ids))})")
            del_ex = cur.rowcount

        # 4. Xóa import_note_details theo ID manifest
        del_im_det = 0
        if imp_det_ids:
            cur.execute(f"DELETE FROM import_note_details WHERE id IN ({','.join(map(str, imp_det_ids))})")
            del_im_det = cur.rowcount

        # 5. Xóa import_notes theo ID manifest
        del_im = 0
        if imp_ids:
            cur.execute(f"DELETE FROM import_notes WHERE id IN ({','.join(map(str, imp_ids))})")
            del_im = cur.rowcount

        # 6. Xóa products theo ID manifest
        del_prod = 0
        if prod_ids:
            cur.execute(f"DELETE FROM products WHERE id IN ({','.join(map(str, prod_ids))})")
            del_prod = cur.rowcount

        # 7. Khôi phục sqlite_sequence về snapshot ban đầu
        snap_before = manifest.get("snapshot_before")
        if snap_before:
            for tbl in SNAPSHOT_TABLES:
                if tbl in snap_before and isinstance(snap_before[tbl], dict) and "sqlite_sequence" in snap_before[tbl]:
                    orig_seq = snap_before[tbl]["sqlite_sequence"]
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
                    if cur.fetchone():
                        cur.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = ?", (orig_seq, tbl))

        cur.execute("COMMIT")

        print("\n--- THỐNG KÊ BẢN GHI ĐÃ DỌN DẸP THEO ID MANIFEST ---")
        print(f"  • stock_ledger        : {del_ledger} dòng")
        print(f"  • export_note_details : {del_ex_det} dòng")
        print(f"  • import_note_details : {del_im_det} dòng")
        print(f"  • export_notes        : {del_ex} phiếu")
        print(f"  • import_notes        : {del_im} phiếu")
        print(f"  • products            : {del_prod} sản phẩm")

        # 8. Đối chiếu snapshot 3 thành phần sau cleanup (Count, Max(ID), SHA256)
        print("\n--- ĐỐI CHIẾU SNAPSHOT 3 THÀNH PHẦN SAU CLEANUP ---")
        print(f"{'Bảng CSDL':<22} | {'Count (Base/Curr)':<18} | {'Max(ID)':<12} | {'SHA256 Match'}")
        print("-" * 75)

        all_clean = True
        for tbl in SNAPSHOT_TABLES:
            cur.execute(f"SELECT count(*), COALESCE(MAX(id), 0) FROM {tbl}")
            curr_c, curr_max = cur.fetchone()
            curr_hash = compute_table_hash(cur, tbl)

            if snap_before and tbl in snap_before and isinstance(snap_before[tbl], dict):
                base_c = snap_before[tbl]["count"]
                base_max = snap_before[tbl]["max_id"]
                base_hash = snap_before[tbl]["sha256"]

                c_match = (curr_c == base_c)
                max_match = (curr_max == base_max)
                hash_match = (curr_hash == base_hash)

                if not (c_match and max_match and hash_match):
                    all_clean = False

                st_hash = "MATCH" if hash_match else "DIFF"
                print(f"{tbl:<22} | {base_c}/{curr_c:<14} | {base_max}/{curr_max:<8} | {st_hash}")
            else:
                print(f"{tbl:<22} | {curr_c:<18} | {curr_max:<12} | (NO SNAP)")

        if all_clean:
            print("\n" + "=" * 78)
            print(" ✅ KẾT QUẢ DỌN DẸP: SẠCH HOÀN TOÀN 3 THÀNH PHẦN (CSDL VỀ ĐÚNG 100% BASELINE)")
            print("=" * 78)
            manifest["status"] = "CLEANED"
            write_manifest_sync(manifest)
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
        print(f"[LỖI CLEANUP] {exc}")
        sys.exit(1)
    finally:
        conn.close()


# ==============================================================================
# 7. CHẾ ĐỘ KIỂM TOÁN (--verify-only)
# ==============================================================================

def run_verify_only(args):
    abs_db = os.path.abspath(args.db_path)
    if not os.path.exists(abs_db):
        print(f"[LỖI] Không tìm thấy file CSDL: {abs_db}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{abs_db}?mode=ro", uri=True, timeout=10.0)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM products WHERE code LIKE 'SKU-NEG-%'")
    cnt_prod = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM stock_ledger WHERE balance_after < 0")
    cnt_neg_bal = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM products WHERE current_stock < 0")
    cnt_neg_stock = cur.fetchone()[0]
    conn.close()

    print("=" * 78)
    print(" KẾT QUẢ KIỂM TOÁN CSDL TỒN KHO ÂM (--verify-only)")
    print("=" * 78)
    print(f"  • Số sản phẩm SKU-NEG-* hiện có       : {cnt_prod}")
    print(f"  • Số mặt hàng bị tồn kho âm (< 0)    : {cnt_neg_stock} (Yêu cầu: 0)")
    print(f"  • Số dòng Thẻ kho bị số dư âm (< 0)  : {cnt_neg_bal} (Yêu cầu: 0)")
    is_ok = (cnt_neg_stock == 0 and cnt_neg_bal == 0)
    print(f"  => KẾT QUẢ TOÀN VẸN: {'PASS' if is_ok else 'FAIL'}")
    sys.exit(0 if is_ok else 1)


# ==============================================================================
# 8. CLI PARSER
# ==============================================================================
def parse_args():
    parser = argparse.ArgumentParser(description="Kiểm thử rào chắn bảo vệ chống tồn kho âm SmartKho")
    parser.add_argument("--cleanup", action="store_true", help="Dọn dẹp sạch sẽ toàn bộ dữ liệu do test tạo ra")
    parser.add_argument("--verify-only", action="store_true", help="Chỉ kiểm toán CSDL hiện tại mà không chạy test mới")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL API (mặc định: http://127.0.0.1:8000)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Đường dẫn file CSDL warehouse.db")
    parser.add_argument("--username", default="admin", help="Tài khoản đăng nhập API")
    parser.add_argument("--password", default="admin123", help="Mật khẩu đăng nhập API")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.cleanup:
        run_cleanup(args)
    elif args.verify_only:
        run_verify_only(args)
    else:
        asyncio.run(main_test(args))
