"""Test hoi quy F6: Kiem chung chuc nang Cleanup an toan P6.4 (bao ve du lieu baseline).

Muc tieu kiem chung:
1. Goi truc tiep ham CLEANUP THUAT tren ban sao /tmp/p6_protect_test.db da chen:
   - 1 dong ADJ-BASELINE-MOCK tren san pham 1 (du lieu baseline mo phong, KHONG nam trong manifest).
   - 1 dong Thẻ kho NEG-TOUCH-BASELINE tren san pham 1 do test thao tac (CO nam trong manifest).
   - Cac san pham SKU-NEG-* va phieu nhap/xuat do test tao.
2. Thuc hien Cleanup lan 1:
   - Chi xoa dung cac ID trong manifest (ke ca dong ledger NEG-TOUCH-BASELINE).
   - Dong ADJ-BASELINE-MOCK phai con nguyen ven (khong bi xoa nham vi cung product_id 1).
3. Thuc hien Cleanup lan 2 (tinh luong dang/idempotent):
   - 0 dong bi xoa, khong gay loi.
4. So sanh snapshot 3 thanh phan (count, MAX(id), sha256) khong con cot sqlite_sequence.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import sys

SNAPSHOT_TABLES = [
    "products",
    "import_notes",
    "import_note_details",
    "export_notes",
    "export_note_details",
    "stock_ledger",
]


def compute_table_hash(cur, tbl: str) -> str:
    cur.execute(f"SELECT * FROM {tbl} ORDER BY id")
    hasher = hashlib.sha256()
    for row in cur.fetchall():
        hasher.update(repr(row).encode("utf-8"))
    return hasher.hexdigest()


def get_db_snapshot(db_path: str) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10.0)
    cur = conn.cursor()
    snap = {}
    for tbl in SNAPSHOT_TABLES:
        cur.execute(f"SELECT count(*), COALESCE(MAX(id), 0) FROM {tbl}")
        c, m = cur.fetchone()
        h = compute_table_hash(cur, tbl)
        snap[tbl] = {"count": c, "max_id": m, "sha256": h}
    conn.close()
    return snap


def main():
    test_db = "/tmp/p6_protect_test.db"
    manifest_file = "/tmp/p6_mock_manifest.json"

    print("================ TEST HOI QUY F6: CLEANUP P6.4 ================")
    print(f"CSDL Thu nghiem: {test_db}")

    # 1. Khoi tao tu warehouse.db
    if os.path.exists(test_db):
        os.remove(test_db)
    shutil.copyfile("/var/lib/warehouse/warehouse.db", test_db)

    # Chup snapshot baseline
    snap_baseline = get_db_snapshot(test_db)
    print("-> Da chup snapshot baseline 6 bang thanh cong.")

    # 2. Chen du lieu thu nghiem
    conn = sqlite3.connect(test_db, timeout=10.0)
    cur = conn.cursor()

    # a. Dong mock baseline (KHONG DUOC MAT)
    cur.execute("""
        INSERT INTO stock_ledger (product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date)
        VALUES (1, 'ADJUSTMENT', 'ADJ-BASELINE-MOCK', 0, 79, 1, '2026-10-30T10:00:00')
    """)
    mock_ledger_id = cur.lastrowid

    # b. San pham test SKU-NEG
    cur.execute("""
        INSERT INTO products (code, name, category_id, supplier_id, unit, min_stock, standard_price, current_stock, status, created_at)
        VALUES ('SKU-NEG-P6-TEST', 'SP Test P6', 1, 1, 'Cai', 10, 50000.0, 10, 'ACTIVE', '2026-10-30T10:00:00')
    """)
    test_pid = cur.lastrowid

    # c. Phieu nhap test
    cur.execute("""
        INSERT INTO import_notes (code, supplier_id, created_by, note_date, total_amount, status)
        VALUES ('PN-NEG-P6-01', 1, 1, '2026-10-30T10:01:00', 500000.0, 'COMPLETED')
    """)
    test_in_id = cur.lastrowid

    cur.execute("""
        INSERT INTO import_note_details (import_note_id, product_id, quantity, unit_price, subtotal)
        VALUES (?, ?, 10, 50000.0, 500000.0)
    """, (test_in_id, test_pid))
    test_in_det_id = cur.lastrowid

    cur.execute("""
        INSERT INTO stock_ledger (product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date)
        VALUES (?, 'IMPORT', 'PN-NEG-P6-01', 10, 10, 1, '2026-10-30T10:01:00')
    """, (test_pid,))
    test_ledger_prod_id = cur.lastrowid

    # d. Dong Thẻ kho NEG-TOUCH tren san pham 1 baseline (DO TEST TAO, PHAI XOA)
    cur.execute("""
        INSERT INTO stock_ledger (product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date)
        VALUES (1, 'ADJUSTMENT', 'NEG-TEST-BASELINE-TOUCH', -1, 78, 1, '2026-10-30T10:02:00')
    """)
    test_touch_ledger_id = cur.lastrowid

    conn.commit()
    conn.close()

    print(f"-> Da chen mock baseline ledger ID={mock_ledger_id} (ADJ-BASELINE-MOCK)")
    print(f"-> Da chen test records: SP ID={test_pid}, PN ID={test_in_id}, Touch Ledger ID={test_touch_ledger_id}")

    # 3. Tao manifest theo ID
    manifest = {
        "db_path": test_db,
        "snapshot_before": snap_baseline,
        "manifest_ids": {
            "products": [test_pid],
            "import_notes": [test_in_id],
            "import_note_details": [test_in_det_id],
            "export_notes": [],
            "export_note_details": [],
            "stock_ledger": [test_ledger_prod_id, test_touch_ledger_id],
        },
        "products": [{"id": test_pid, "code": "SKU-NEG-P6-TEST"}],
        "import_notes": [{"id": test_in_id, "code": "PN-NEG-P6-01"}],
        "export_notes": [],
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # 4. Goi truc tiep ham run_cleanup
    # Import ham run_cleanup tu test_negative_stock_guard
    sys.path.insert(0, "/app/tests/performance")
    from test_negative_stock_guard import run_cleanup, MANIFEST_PATH

    # Override MANIFEST_PATH de test_negative_stock_guard doc dung manifest test
    import test_negative_stock_guard
    test_negative_stock_guard.MANIFEST_PATH = manifest_file

    class CleanupArgs:
        db_path = test_db

    print("\n--- THUC HIEN CLEANUP LAN 1 ---")
    try:
        run_cleanup(CleanupArgs())
    except SystemExit as se:
        print(f"  Cleanup lan 1 exit code: {se.code}")

    # Kiem tra dong mock baseline ledger
    conn = sqlite3.connect(test_db, timeout=10.0)
    cur = conn.cursor()
    cur.execute("SELECT id, reference_code FROM stock_ledger WHERE reference_code = 'ADJ-BASELINE-MOCK'")
    mock_row = cur.fetchone()
    print(f"  Kiem tra dong ADJ-BASELINE-MOCK sau cleanup 1: {'TON TAI (PASS)' if mock_row else 'BI XOA MAT (FAIL)'}")
    assert mock_row is not None, "FAIL: Dong ADJ-BASELINE-MOCK bi xoa nham!"

    cur.execute("SELECT id FROM stock_ledger WHERE reference_code = 'NEG-TEST-BASELINE-TOUCH'")
    touch_row = cur.fetchone()
    print(f"  Kiem tra dong NEG-TEST-BASELINE-TOUCH sau cleanup 1: {'DA XOA (PASS)' if not touch_row else 'CHUA XOA (FAIL)'}")
    assert touch_row is None, "FAIL: Dong NEG-TEST-BASELINE-TOUCH chua duoc xoa!"

    cur.execute("SELECT id FROM products WHERE code = 'SKU-NEG-P6-TEST'")
    sp_row = cur.fetchone()
    print(f"  Kiem tra SP test SKU-NEG-P6-TEST sau cleanup 1: {'DA XOA (PASS)' if not sp_row else 'CHUA XOA (FAIL)'}")
    assert sp_row is None, "FAIL: SP test chua duoc xoa!"

    conn.close()

    print("\n--- THUC HIEN CLEANUP LAN 2 (IDEMPOTENCY) ---")
    try:
        run_cleanup(CleanupArgs())
    except SystemExit as se:
        print(f"  Cleanup lan 2 exit code: {se.code}")

    # Kiem tra lai dong mock baseline
    conn = sqlite3.connect(test_db, timeout=10.0)
    cur = conn.cursor()
    cur.execute("SELECT id FROM stock_ledger WHERE reference_code = 'ADJ-BASELINE-MOCK'")
    assert cur.fetchone() is not None, "FAIL: Mock row mat sau cleanup 2!"

    # Don dep dong mock baseline de so sanh voi baseline goc
    cur.execute("DELETE FROM stock_ledger WHERE reference_code = 'ADJ-BASELINE-MOCK'")
    conn.commit()

    # So sanh snapshot 3 thanh phan voi baseline
    snap_after = get_db_snapshot(test_db)
    print("\n--- DOI CHIEU SNAPSHOT 3 THANH PHAN VOI BASELINE GOC ---")
    print(f"{'Bang':<24} | {'Count Match':<14} | {'Max(ID) Match':<14} | {'SHA256 Match'}")
    print("-" * 70)
    all_snap_ok = True
    for tbl in SNAPSHOT_TABLES:
        c_m = snap_after[tbl]["count"] == snap_baseline[tbl]["count"]
        m_m = snap_after[tbl]["max_id"] == snap_baseline[tbl]["max_id"]
        h_m = snap_after[tbl]["sha256"] == snap_baseline[tbl]["sha256"]
        if not (c_m and m_m and h_m):
            all_snap_ok = False
        print(f"{tbl:<24} | {str(c_m):<14} | {str(m_m):<14} | {str(h_m)}")

    conn.close()

    if os.path.exists(manifest_file):
        os.remove(manifest_file)
    if os.path.exists(test_db):
        os.remove(test_db)

    print(f"\nTONG KET F6 CLEANUP REGRESSION: {'PASS (100% AN TOAN DULIEU BASELINE)' if all_snap_ok else 'FAIL'}")
    assert all_snap_ok, "Snapshot mismatch after cleanup!"


if __name__ == "__main__":
    main()
