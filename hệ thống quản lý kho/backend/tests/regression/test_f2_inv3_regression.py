"""Test hoi quy F2: Kiem tra Checker Bat bien 3 (Chong False Negative).

Kiem chung 5 kich ban tren ban sao CSDL:
(1) ship -> cancel hop le: PASS
(2) CANCELLED chua tung ship: PASS
(3) Xoa ledger EXPORT cua 1 phieu COMPLETED: phai FAIL (Bat loi False Negative cua checker cu)
(4) Ledger EXPORT mo coi (orphan): phai FAIL
(5) Huy-sau-ship mat ADJUSTMENT hoan tra doi ung: phai FAIL
"""

import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

DB_SRC = "file:/var/lib/warehouse/warehouse.db?mode=ro"
DB_TEST = "/tmp/f2_inv3_test.db"


def reset_test_db():
    for p in [DB_TEST, f"{DB_TEST}-shm", f"{DB_TEST}-wal"]:
        if os.path.exists(p):
            os.remove(p)
    src = sqlite3.connect(DB_SRC, uri=True)
    dst = sqlite3.connect(DB_TEST)
    src.backup(dst)
    src.close()
    dst.close()


def run_checker(checker_path: str) -> tuple[int, str]:
    res = subprocess.run(
        [sys.executable, checker_path, DB_TEST],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    return res.returncode, res.stdout + res.stderr


def setup_scenario(scenario_idx: int):
    reset_test_db()
    conn = sqlite3.connect(DB_TEST)
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    if scenario_idx == 1:
        # Ca 1: ship -> cancel hop le
        c.execute("INSERT INTO products (code, name, category_id, supplier_id, unit, min_stock, current_stock, standard_price, status, created_at) VALUES ('SKU-F2-1', 'SP F2-1', 1, 1, 'Cai', 2, 10, 50000, 'ACTIVE', ?)", (now,))
        pid = c.lastrowid
        c.execute("INSERT INTO export_notes (code, recipient_name, created_by, note_date, total_amount, status) VALUES ('PX-F2-1', 'Khach 1', 1, ?, 100000, 'CANCELLED')", (now,))
        nid = c.lastrowid
        c.execute("INSERT INTO export_note_details (export_note_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 2, 50000, 100000)", (nid, pid))
        c.execute("INSERT INTO stock_ledger (product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date, note) VALUES (?, 'EXPORT', 'PX-F2-1', -2, 8, 1, ?, 'Xuat')", (pid, now))
        c.execute("INSERT INTO stock_ledger (product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date, note) VALUES (?, 'ADJUSTMENT', 'CANCEL-PX-F2-1', 2, 10, 1, ?, 'Huy')", (pid, now))
        conn.commit()

    elif scenario_idx == 2:
        # Ca 2: CANCELLED chua tung ship (0 ledger)
        c.execute("INSERT INTO products (code, name, category_id, supplier_id, unit, min_stock, current_stock, standard_price, status, created_at) VALUES ('SKU-F2-2', 'SP F2-2', 1, 1, 'Cai', 2, 10, 50000, 'ACTIVE', ?)", (now,))
        pid = c.lastrowid
        c.execute("INSERT INTO export_notes (code, recipient_name, created_by, note_date, total_amount, status) VALUES ('PX-F2-2', 'Khach 2', 1, ?, 100000, 'CANCELLED')", (now,))
        nid = c.lastrowid
        c.execute("INSERT INTO export_note_details (export_note_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 2, 50000, 100000)", (nid, pid))
        conn.commit()

    elif scenario_idx == 3:
        # Ca 3: Xoa ledger EXPORT cua 1 phieu COMPLETED (Phieu COMPLETED bi mat ledger)
        c.execute("INSERT INTO products (code, name, category_id, supplier_id, unit, min_stock, current_stock, standard_price, status, created_at) VALUES ('SKU-F2-3', 'SP F2-3', 1, 1, 'Cai', 2, 8, 50000, 'ACTIVE', ?)", (now,))
        pid = c.lastrowid
        c.execute("INSERT INTO export_notes (code, recipient_name, created_by, note_date, total_amount, status) VALUES ('PX-F2-3', 'Khach 3', 1, ?, 100000, 'COMPLETED')", (now,))
        nid = c.lastrowid
        c.execute("INSERT INTO export_note_details (export_note_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 2, 50000, 100000)", (nid, pid))
        # Khong insert stock_ledger EXPORT (hoac da bi xoa mat)
        conn.commit()

    elif scenario_idx == 4:
        # Ca 4: Ledger EXPORT mo coi (tro ve phieu khong ton tai)
        c.execute("INSERT INTO stock_ledger (product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date, note) VALUES (1, 'EXPORT', 'PX-F2-ORPHAN-999', -1, 5, 1, ?, 'Orphan ledger')", (now,))
        conn.commit()

    elif scenario_idx == 5:
        # Ca 5: Huy-sau-ship mat ADJUSTMENT hoan tra doi ung
        c.execute("INSERT INTO products (code, name, category_id, supplier_id, unit, min_stock, current_stock, standard_price, status, created_at) VALUES ('SKU-F2-5', 'SP F2-5', 1, 1, 'Cai', 2, 8, 50000, 'ACTIVE', ?)", (now,))
        pid = c.lastrowid
        c.execute("INSERT INTO export_notes (code, recipient_name, created_by, note_date, total_amount, status) VALUES ('PX-F2-5', 'Khach 5', 1, ?, 100000, 'CANCELLED')", (now,))
        nid = c.lastrowid
        c.execute("INSERT INTO export_note_details (export_note_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, 2, 50000, 100000)", (nid, pid))
        c.execute("INSERT INTO stock_ledger (product_id, transaction_type, reference_code, quantity_change, balance_after, created_by, transaction_date, note) VALUES (?, 'EXPORT', 'PX-F2-5', -2, 8, 1, ?, 'Xuat')", (pid, now))
        # Thieu dong CANCEL-PX-F2-5 hoan tra!
        conn.commit()

    conn.close()


def main():
    checker_path = sys.argv[1] if len(sys.argv) > 1 else "backend/tests/performance/check_invariants.py"
    print(f"TESTING CHECKER: {checker_path}")

    scenarios = [
        (1, "Ship -> Cancel hop le", True),
        (2, "CANCELLED chua tung ship (0 ledger)", True),
        (3, "Xoa ledger EXPORT cua 1 phieu COMPLETED", False),
        (4, "Ledger EXPORT mo coi", False),
        (5, "Huy-sau-ship mat ADJUSTMENT hoan tra", False),
    ]

    for idx, desc, expected_pass in scenarios:
        setup_scenario(idx)
        ret, out = run_checker(checker_path)
        actual_pass = (ret == 0) and ("KẾT QUẢ BẤT BIẾN 3: ĐẠT" in out)
        is_ok = (actual_pass == expected_pass)
        status_str = "DUNG KY VONG" if is_ok else "SAI KY VONG (FALSE NEGATIVE/POSITIVE)"
        print(f"\n[Ca {idx}] {desc}")
        print(f"  Ky vong: {'PASS' if expected_pass else 'FAIL'} | Thuc te: {'PASS' if actual_pass else 'FAIL'} -> {status_str}")
        if not is_ok:
            for l in out.split("\n"):
                if "BẤT BIẾN 3" in l or "ĐẠT" in l or "KHÔNG ĐẠT" in l or "chênh lệch" in l:
                    print(f"    {l.strip()}")


if __name__ == "__main__":
    main()
