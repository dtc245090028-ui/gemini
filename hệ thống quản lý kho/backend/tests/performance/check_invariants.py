"""Script kiểm tra 5 bất biến toàn vẹn dữ liệu (chỉ đọc CSDL).
Sử dụng: python check_invariants.py [đường_dẫn_db]
"""

import sys
import os
import subprocess
import sqlite3

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if os.name == "nt" and not os.environ.get("INSIDE_DOCKER"):
    chk = subprocess.run(
        ["docker", "ps", "--filter", "name=warehouse_backend", "--filter", "status=running", "-q"],
        capture_output=True, text=True, check=False
    )
    if chk.returncode == 0 and chk.stdout.strip():
        db_arg = [sys.argv[1]] if len(sys.argv) > 1 else []
        res = subprocess.run(
            ["docker", "exec", "-e", "INSIDE_DOCKER=1", "warehouse_backend", "python", "/app/tests/performance/check_invariants.py", *db_arg],
            check=False
        )
        sys.exit(res.returncode)

def check_invariants(db_path):
    if not os.path.exists(db_path):
        print(f"[LỖI] Không tìm thấy file CSDL: {db_path}")
        return False

    print(f"=========================================================================")
    print(f" KIỂM TRA 5 BẤT BIẾN TOÀN VẸN CƠ SỞ DỮ LIỆU")
    print(f" CSDL: {db_path}")
    print(f"=========================================================================\n")

    conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
    cur = conn.cursor()

    invariants_passed = True

    # ---------------------------------------------------------
    # BẤT BIẾN 1: Tồn hiện tại = Tồn đầu + Tổng thay đổi trong stock_ledger
    # ---------------------------------------------------------
    print("--- 1. BẤT BIẾN 1: CÂN BẰNG TỒN KHO KẾ TOÁN (Tồn = Tồn đầu + Sum Change) ---")
    cur.execute("""
        SELECT p.id, p.code, p.name, p.current_stock
        FROM products p
        ORDER BY p.id ASC
    """)
    products = cur.fetchall()

    inv1_fails = []
    inv1_perf_summary = []

    for pid, pcode, pname, curr_stock in products:
        cur.execute("""
            SELECT id, quantity_change, balance_after
            FROM stock_ledger
            WHERE product_id = ?
            ORDER BY id ASC
        """, (pid,))
        ledgers = cur.fetchall()

        if not ledgers:
            continue

        # Tồn đầu suy ra từ dòng đầu tiên: balance_after - quantity_change
        first_row = ledgers[0]
        initial_stock = first_row[2] - first_row[1]
        sum_change = sum(r[1] for r in ledgers)
        expected_stock = initial_stock + sum_change

        if curr_stock != expected_stock:
            inv1_fails.append({
                "code": pcode,
                "current": curr_stock,
                "expected": expected_stock,
                "diff": curr_stock - expected_stock,
                "ledger_count": len(ledgers)
            })
        if "SKU-PERF-" in pcode:
            inv1_perf_summary.append({
                "code": pcode,
                "current": curr_stock,
                "expected": expected_stock,
                "diff": curr_stock - expected_stock,
                "ledger_count": len(ledgers),
                "passed": curr_stock == expected_stock
            })

    if inv1_perf_summary:
        print("Chi tiết các mặt hàng kiểm thử (SKU-PERF-*):")
        for p in inv1_perf_summary:
            status = "ĐẠT" if p["passed"] else f"VI PHẠM (lệch {p['diff']} đơn vị)"
            print(f"  • {p['code']:<20}: Tồn={p['current']} | Kỳ vọng={p['expected']} | Thẻ kho={p['ledger_count']} dòng -> {status}")

    if inv1_fails:
        print(f"  >> KẾT QUẢ BẤT BIẾN 1: KHÔNG ĐẠT (Có {len(inv1_fails)} sản phẩm bị lệch tồn kho / Lost Update)")
        invariants_passed = False
    else:
        print("  >> KẾT QUẢ BẤT BIẾN 1: ĐẠT (100% SKU có tồn kho khớp chính xác sổ kế toán)")

    # ---------------------------------------------------------
    # BẤT BIẾN 2: Tính đơn điệu lũy kế của Thẻ kho (balance[n] = balance[n-1] + change[n])
    # ---------------------------------------------------------
    print("\n--- 2. BẤT BIẾN 2: TÍNH ĐƠN ĐIỆU LŨY KẾ CỦA THẺ KHO ---")
    total_violations = 0
    total_dup_balances = 0
    perf_sku_inv2 = []

    for pid, pcode, pname, curr_stock in products:
        cur.execute("""
            SELECT id, quantity_change, balance_after
            FROM stock_ledger
            WHERE product_id = ?
            ORDER BY id ASC
        """, (pid,))
        ledgers = cur.fetchall()

        if len(ledgers) < 2:
            continue

        violations = 0
        for i in range(1, len(ledgers)):
            prev_bal = ledgers[i-1][2]
            chg = ledgers[i][1]
            cur_bal = ledgers[i][2]
            if cur_bal != prev_bal + chg:
                violations += 1

        # Kiểm tra số dư lặp cho mặt hàng kiểm thử tải (SKU-PERF-*) hoặc mặt hàng chỉ biến động 1 chiều
        changes_after_init = [r[1] for r in ledgers[1:]]
        is_monotonic_dir = (
            all(c < 0 for c in changes_after_init) or all(c > 0 for c in changes_after_init)
        ) if changes_after_init else True

        dup_count = 0
        if "SKU-PERF-" in pcode or is_monotonic_dir:
            cur.execute("""
                SELECT balance_after, count(*) 
                FROM stock_ledger 
                WHERE product_id = ? 
                GROUP BY balance_after 
                HAVING count(*) > 1
            """, (pid,))
            dups = cur.fetchall()
            dup_count = len(dups)

        total_violations += violations
        total_dup_balances += dup_count

        if "SKU-PERF-" in pcode:
            perf_sku_inv2.append({
                "code": pcode,
                "lines": len(ledgers),
                "violations": violations,
                "dup_count": dup_count
            })

    if perf_sku_inv2:
        for p in perf_sku_inv2:
            status = "ĐẠT" if (p["violations"] == 0 and p["dup_count"] == 0) else f"VI PHẠM ({p['violations']} dòng lỗi, {p['dup_count']} số dư lặp)"
            print(f"  • {p['code']:<20}: {p['lines']} dòng thẻ kho -> {status}")

    if total_violations > 0 or total_dup_balances > 0:
        print(f"  >> KẾT QUẢ BẤT BIẾN 2: KHÔNG ĐẠT (Tổng {total_violations} dòng vi phạm lũy kế, {total_dup_balances} số dư lặp)")
        invariants_passed = False
    else:
        print("  >> KẾT QUẢ BẤT BIẾN 2: ĐẠT (0 dòng vi phạm lũy kế, 0 số dư lặp bất thường)")

    # ---------------------------------------------------------
    # BẤT BIẾN 3: ĐỐI SOÁT HAI CHIỀU PHIẾU XUẤT VS THẺ KHO (A + B + C)
    # ---------------------------------------------------------
    print("\n--- 3. BẤT BIẾN 3: ĐỐI SOÁT HAI CHIỀU PHIẾU XUẤT VS THẺ KHO ---")
    inv3_passed = True

    # 1. Chiều Xuôi (Phiếu xuất -> Thẻ kho) theo bảng trạng thái kỳ vọng
    # (a) Phiếu CONFIRMED: Không được có bất kỳ dòng EXPORT nào
    cur.execute("""
        SELECT n.code, count(l.id)
        FROM export_notes n
        JOIN stock_ledger l ON l.reference_code = n.code AND l.transaction_type = 'EXPORT'
        WHERE n.status = 'CONFIRMED'
        GROUP BY n.code
    """)
    confirmed_with_export = cur.fetchall()
    if confirmed_with_export:
        print(f"  [LỖI] Có {len(confirmed_with_export)} phiếu CONFIRMED nhưng đã sinh thẻ kho EXPORT:")
        for code, cnt in confirmed_with_export[:3]:
            print(f"    - Phiếu {code}: {cnt} dòng EXPORT")
        inv3_passed = False

    # (b) Phiếu SHIPPING / COMPLETED: Mỗi dòng chi tiết phải có đúng 1 dòng EXPORT đối ứng
    cur.execute("""
        SELECT n.code, d.product_id, d.quantity, count(l.id)
        FROM export_notes n
        JOIN export_note_details d ON d.export_note_id = n.id
        LEFT JOIN stock_ledger l ON l.reference_code = n.code 
            AND l.product_id = d.product_id 
            AND l.transaction_type = 'EXPORT'
            AND l.quantity_change = -d.quantity
        WHERE n.status IN ('SHIPPING', 'COMPLETED')
        GROUP BY n.code, d.product_id, d.quantity
        HAVING count(l.id) != 1
    """)
    missing_export = cur.fetchall()
    if missing_export:
        print(f"  [LỖI] Có {len(missing_export)} dòng chi tiết thuộc phiếu SHIPPING/COMPLETED thiếu hoặc thừa thẻ kho EXPORT đối ứng:")
        for code, pid, qty, cnt in missing_export[:3]:
            print(f"    - Phiếu {code}, SP {pid}, SL {qty}: có {cnt} thẻ kho EXPORT")
        inv3_passed = False

    # (c) Phiếu CANCELLED có thẻ kho EXPORT (hủy sau ship): Phải có đủ các dòng ADJUSTMENT (CANCEL-<code>) hoàn trả đúng số lượng
    cur.execute("""
        SELECT n.code, d.product_id, d.quantity,
               (SELECT count(*) FROM stock_ledger WHERE reference_code = n.code AND product_id = d.product_id AND transaction_type = 'EXPORT'),
               (SELECT coalesce(sum(quantity_change), 0) FROM stock_ledger WHERE reference_code = 'CANCEL-' || n.code AND product_id = d.product_id AND transaction_type = 'ADJUSTMENT')
        FROM export_notes n
        JOIN export_note_details d ON d.export_note_id = n.id
        WHERE n.status = 'CANCELLED'
          AND n.code IN (SELECT DISTINCT reference_code FROM stock_ledger WHERE transaction_type = 'EXPORT')
    """)
    cancelled_after_ship = cur.fetchall()
    for code, pid, qty, exp_cnt, refund_sum in cancelled_after_ship:
        if exp_cnt == 0:
            print(f"  [LỖI] Phiếu CANCELLED {code} không khớp logic EXPORT")
            inv3_passed = False
        if refund_sum != qty:
            print(f"  [LỖI] Phiếu CANCELLED {code}, SP {pid}: Đã xuất {qty} nhưng tổng hoàn trả CANCEL- chỉ có {refund_sum}")
            inv3_passed = False

    # (d) Phiếu CANCELLED chưa từng ship: Không được có thẻ kho EXPORT và không được có thẻ kho CANCEL-
    cur.execute("""
        SELECT n.code, count(l.id)
        FROM export_notes n
        JOIN stock_ledger l ON (l.reference_code = n.code AND l.transaction_type = 'EXPORT')
                            OR (l.reference_code = 'CANCEL-' || n.code AND l.transaction_type = 'ADJUSTMENT')
        WHERE n.status = 'CANCELLED'
          AND n.code NOT IN (SELECT DISTINCT reference_code FROM stock_ledger WHERE transaction_type = 'EXPORT')
        GROUP BY n.code
    """)
    cancelled_unshipped_err = cur.fetchall()
    if cancelled_unshipped_err:
        print(f"  [LỖI] Có {len(cancelled_unshipped_err)} phiếu CANCELLED chưa từng xuất nhưng phát sinh thẻ kho bất thường:")
        inv3_passed = False

    # 2. Chiều Ngược (Thẻ kho -> Phiếu xuất): Mọi dòng EXPORT phải trỏ về phiếu xuất có thật
    cur.execute("""
        SELECT l.id, l.reference_code, l.product_id, l.quantity_change
        FROM stock_ledger l
        LEFT JOIN export_notes n ON n.code = l.reference_code
        WHERE l.transaction_type = 'EXPORT' AND n.id IS NULL
    """)
    orphan_exports = cur.fetchall()
    if orphan_exports:
        print(f"  [LỖI] Có {len(orphan_exports)} dòng Thẻ kho EXPORT mồ côi (không tìm thấy phiếu xuất tương ứng):")
        for lid, ref, pid, qc in orphan_exports[:3]:
            print(f"    - Ledger ID {lid}: mã {ref}, SP {pid}, biến động {qc}")
        inv3_passed = False

    # Đếm tổng để báo cáo
    cur.execute("SELECT count(*) FROM export_notes WHERE status IN ('SHIPPING', 'COMPLETED')")
    total_active_notes = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM stock_ledger WHERE transaction_type = 'EXPORT'")
    total_export_ledger = cur.fetchone()[0]

    print(f"  • Tổng phiếu xuất SHIPPING/COMPLETED          : {total_active_notes}")
    print(f"  • Tổng dòng Thẻ kho loại EXPORT                : {total_export_ledger}")
    print(f"  • Kết quả kiểm tra đối soát 2 chiều            : {'HỢP LỆ (Khớp 100%)' if inv3_passed else 'VI PHẠM'}")

    if inv3_passed:
        print("  >> KẾT QUẢ BẤT BIẾN 3: ĐẠT")
    else:
        print("  >> KẾT QUẢ BẤT BIẾN 3: KHÔNG ĐẠT")
        invariants_passed = False

    # ---------------------------------------------------------
    # BẤT BIẾN 4: Số phiếu CONFIRMED lửng (chưa ship)
    # ---------------------------------------------------------
    print("\n--- 4. BẤT BIẾN 4: KIỂM SOÁT PHIẾU LỬNG & LỖI HỆ THỐNG ---")
    cur.execute("SELECT count(*) FROM export_notes WHERE status = 'CONFIRMED' AND code LIKE 'PX-%'")
    confirmed_notes = cur.fetchone()[0]
    print(f"  • Số phiếu xuất ở trạng thái CONFIRMED (chưa ship): {confirmed_notes}")

    # ---------------------------------------------------------
    # BẤT BIẾN 5: Không có tồn kho âm
    # ---------------------------------------------------------
    print("\n--- 5. BẤT BIẾN 5: BẢO VỆ CHỐNG TỒN KHO ÂM ---")
    cur.execute("SELECT count(*), min(current_stock) FROM products WHERE current_stock < 0")
    neg_row = cur.fetchone()
    neg_count = neg_row[0]
    min_stock = neg_row[1]

    if neg_count == 0:
        print("  • Không có mặt hàng nào bị tồn kho âm.")
        print("  >> KẾT QUẢ BẤT BIẾN 5: ĐẠT")
    else:
        print(f"  • CẢNH BÁO: Có {neg_count} mặt hàng bị tồn kho âm! Tồn nhỏ nhất: {min_stock}")
        print("  >> KẾT QUẢ BẤT BIẾN 5: KHÔNG ĐẠT")
        invariants_passed = False

    conn.close()

    print("\n" + "=" * 70)
    print(f" TỔNG KẾT BẤT BIẾN: {'TẤT CẢ ĐỀU ĐẠT' if invariants_passed else 'CÓ BẤT BIẾN VI PHẠM'}")
    print("=" * 70)
    return invariants_passed

if __name__ == "__main__":
    db_env = os.environ.get("DATABASE_URL", "")
    default_db = db_env.replace("sqlite:///", "") if db_env.startswith("sqlite:///") else "warehouse.db"
    db_file = sys.argv[1] if len(sys.argv) > 1 else default_db
    res = check_invariants(db_file)
    sys.exit(0 if res else 1)
