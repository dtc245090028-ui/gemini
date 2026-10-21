"""Script thẩm tra chi tiết dữ liệu sau Bậc 3: Thẻ kho, số dư lũy kế, và Schema."""

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=== 1. TỒN ĐẦU & 5 DÒNG ĐẦU TIÊN CỦA BULK-01 VÀ BULK-02 ===")
p1 = db.execute(text("SELECT id, code, current_stock FROM products WHERE code = 'SKU-PERF-BULK-01'")).fetchone()
p2 = db.execute(text("SELECT id, code, current_stock FROM products WHERE code = 'SKU-PERF-BULK-02'")).fetchone()

print(f"Product BULK-01 (ID: {p1[0]}): current_stock = {p1[2]}")
first_5_b1 = db.execute(text(f"SELECT id, reference_code, transaction_type, quantity_change, balance_after, transaction_date FROM stock_ledger WHERE product_id = {p1[0]} ORDER BY id ASC LIMIT 5")).fetchall()
for r in first_5_b1:
    print("  BULK-01 first:", r)

print(f"\nProduct BULK-02 (ID: {p2[0]}): current_stock = {p2[2]}")
first_5_b2 = db.execute(text(f"SELECT id, reference_code, transaction_type, quantity_change, balance_after, transaction_date FROM stock_ledger WHERE product_id = {p2[0]} ORDER BY id ASC LIMIT 5")).fetchall()
for r in first_5_b2:
    print("  BULK-02 first:", r)

print("\n=== 2. TỔNG SỐ LƯỢNG DÒNG VÀ TỔNG THAY ĐỔI ===")
stats = db.execute(text(f"""
    SELECT product_id, count(id), sum(quantity_change), min(balance_after), max(balance_after)
    FROM stock_ledger 
    WHERE product_id IN ({p1[0]}, {p2[0]})
    GROUP BY product_id
""")).fetchall()
for s in stats:
    print(f"Stats product_id {s[0]}: count={s[1]}, sum_change={s[2]}, min_bal={s[3]}, max_bal={s[4]}")

print("\n=== 3. KIỂM TRA LŨY KẾ: balance_after(n) = balance_after(n-1) + quantity_change(n) ===")
for pid, code in [(p1[0], 'SKU-PERF-BULK-01'), (p2[0], 'SKU-PERF-BULK-02')]:
    rows = db.execute(text(f"""
        SELECT id, reference_code, quantity_change, balance_after 
        FROM stock_ledger 
        WHERE product_id = {pid} 
        ORDER BY id ASC
    """)).fetchall()
    
    violations = []
    for i in range(1, len(rows)):
        prev_bal = rows[i-1][3]
        change = rows[i][2]
        curr_bal = rows[i][3]
        expected_bal = prev_bal + change
        if curr_bal != expected_bal:
            violations.append((rows[i-1], rows[i], expected_bal))
            
    print(f"Vi phạm lũy kế {code}: Tổng số dòng={len(rows)}, Số dòng vi phạm={len(violations)}")
    if violations:
        print(f"  10 ví dụ vi phạm đầu tiên của {code}:")
        for v in violations[:10]:
            print(f"    Prev: ID={v[0][0]}, Bal={v[0][3]} | Curr: ID={v[1][0]}, Chg={v[1][2]}, Bal={v[1][3]} | Kỳ vọng Bal={v[2]}")

print("\n=== 4. CÁC GIÁ TRỊ BALANCE_AFTER BỊ LẶP (DUPLICATE BALANCE_AFTER) ===")
for pid, code in [(p1[0], 'SKU-PERF-BULK-01'), (p2[0], 'SKU-PERF-BULK-02')]:
    dups = db.execute(text(f"""
        SELECT balance_after, count(*) as cnt 
        FROM stock_ledger 
        WHERE product_id = {pid} 
        GROUP BY balance_after 
        HAVING count(*) > 1 
        ORDER BY cnt DESC, balance_after DESC
    """)).fetchall()
    print(f"\n{code}: Có {len(dups)} giá trị balance_after bị lặp lại!")
    print(f"  10 ví dụ đầu tiên (balance_after, số lần lặp):")
    for d in dups[:10]:
        print(f"    balance_after = {d[0]}: xuất hiện {d[1]} lần")

print("\n=== 5. KIỂM TRA RESET TRƯỚC BẬC 3 ===")
# Kiểm tra thời gian tạo user hoặc reset bảng
perf_users = db.execute(text("SELECT min(created_at), max(created_at), count(*) FROM users WHERE username LIKE 'perf_%'")).fetchone()
print("Perf users created_at range:", perf_users)
oldest_perf_note = db.execute(text("SELECT min(note_date), max(note_date), count(*) FROM export_notes WHERE code LIKE 'PX-%' AND created_by IN (SELECT id FROM users WHERE username LIKE 'perf_%')")).fetchone()
print("Export notes note_date range:", oldest_perf_note)
oldest_ledger = db.execute(text(f"SELECT min(transaction_date), max(transaction_date), count(*) FROM stock_ledger WHERE product_id IN ({p1[0]}, {p2[0]})")).fetchone()
print("Stock ledger transaction_date range:", oldest_ledger)

db.close()
