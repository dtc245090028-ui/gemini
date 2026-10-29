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
        res = subprocess.run(
            ["docker", "exec", "-e", "INSIDE_DOCKER=1", "warehouse_backend", "python", "/app/tests/performance/check_invariants.py", "/app/warehouse.db"],
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
    # BẤT BIẾN 3: Tổng dòng chi tiết phiếu xuất đã xuất kho (SHIPPING/COMPLETED) = Số dòng thẻ kho EXPORT
    # ---------------------------------------------------------
    print("\n--- 3. BẤT BIẾN 3: ĐỐI SOÁT DÒNG PHIẾU XUẤT ĐÃ XUẤT KHO VS THẺ KHO ---")
    cur.execute("""
        SELECT count(*)
        FROM export_note_details d
        JOIN export_notes n ON n.id = d.export_note_id
        WHERE n.status IN ('SHIPPING', 'COMPLETED')
    """)
    shipped_detail_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM stock_ledger WHERE transaction_type = 'EXPORT'")
    export_ledger_count = cur.fetchone()[0]

    print(f"  • Tổng dòng hàng thuộc phiếu SHIPPING/COMPLETED: {shipped_detail_count}")
    print(f"  • Tổng dòng Thẻ kho loại EXPORT                : {export_ledger_count}")
    print(f"  • Độ chênh lệch                                : {shipped_detail_count - export_ledger_count}")

    if shipped_detail_count == export_ledger_count:
        print("  >> KẾT QUẢ BẤT BIẾN 3: ĐẠT (Khớp 100% tỷ lệ 1:1)")
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
    db_file = sys.argv[1] if len(sys.argv) > 1 else "warehouse.db"
    res = check_invariants(db_file)
    sys.exit(0 if res else 1)
