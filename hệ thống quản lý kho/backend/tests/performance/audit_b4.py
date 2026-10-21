"""Audit script for Tier 4 (Targeted Concurrency)."""

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=== 1. TỒN KHO HIỆN TẠI VÀ THẺ KHO BẬC 4 ===")
prods = db.execute(text("SELECT id, code, current_stock FROM products WHERE code LIKE 'SKU-PERF-%' ORDER BY id")).fetchall()
for p in prods:
    print(f"Product {p[1]} (ID {p[0]}): current_stock = {p[2]}")

print("\n=== 2. THỐNG KÊ STOCK_LEDGER THEO SKU ===")
ledgers = db.execute(text("""
    SELECT p.code, count(sl.id) as ledger_count, sum(sl.quantity_change) as total_qty_change, min(sl.balance_after) as min_bal, max(sl.balance_after) as max_bal
    FROM stock_ledger sl 
    JOIN products p ON sl.product_id = p.id
    WHERE p.code LIKE 'SKU-PERF-%'
    GROUP BY p.code
""")).fetchall()
for l in ledgers:
    print(f"Stats {l[0]}: count={l[1]}, sum_change={l[2]}, min_bal={l[3]}, max_bal={l[4]}")

print("\n=== 3. KIỂM TRA LŨY KẾ & SỐ DƯ LẶP LẠI ===")
p1 = [p for p in prods if p[1] == 'SKU-PERF-BULK-01'][0]
p2 = [p for p in prods if p[1] == 'SKU-PERF-BULK-02'][0]

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
            
    print(f"\n{code}: Tổng số dòng={len(rows)}, Số dòng vi phạm={len(violations)}")
    if violations:
        print(f"  5 ví dụ vi phạm đầu tiên:")
        for v in violations[:5]:
            print(f"    Prev: ID={v[0][0]}, Bal={v[0][3]} | Curr: ID={v[1][0]}, Chg={v[1][2]}, Bal={v[1][3]} | Kỳ vọng Bal={v[2]}")
            
    dups = db.execute(text(f"""
        SELECT balance_after, count(*) as cnt 
        FROM stock_ledger 
        WHERE product_id = {pid} 
        GROUP BY balance_after 
        HAVING count(*) > 1 
        ORDER BY cnt DESC
    """)).fetchall()
    print(f"  Số giá trị balance_after bị lặp lại: {len(dups)}")
    if dups:
        print(f"  Top 5 số dư lặp nhiều nhất: {dups[:5]}")

print("\n=== 4. PHIẾU XUẤT THEO TRẠNG THÁI ===")
notes_by_status = db.execute(text("""
    SELECT en.status, count(en.id) 
    FROM export_notes en 
    WHERE en.code LIKE 'PX-%' AND en.created_by IN (SELECT id FROM users WHERE username LIKE 'perf_%')
    GROUP BY en.status
""")).fetchall()
print(notes_by_status)

print("\n=== 5. KIỂM TRA MÃ PHIẾU TRÙNG LẶP ===")
dup_codes = db.execute(text("""
    SELECT code, count(*) FROM export_notes WHERE code LIKE 'PX-%' GROUP BY code HAVING count(*) > 1
""")).fetchall()
print("Duplicate codes count:", len(dup_codes))

db.close()
