import sys
from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=== 1. TỒN KHO VÀ SẢN PHẨM ===")
prods = db.execute(text("SELECT id, code, name, current_stock FROM products WHERE code LIKE 'SKU-PERF-%' ORDER BY id")).fetchall()
for p in prods:
    print(p)

print("\n=== 2. SỐ DÒNG STOCK_LEDGER THEO SKU ===")
ledgers = db.execute(text("""
    SELECT p.code, count(sl.id) as ledger_count, sum(sl.quantity_change) as total_qty_change, min(sl.balance_after) as min_bal, max(sl.balance_after) as max_bal
    FROM stock_ledger sl 
    JOIN products p ON sl.product_id = p.id
    WHERE p.code LIKE 'SKU-PERF-%'
    GROUP BY p.code
""")).fetchall()
for l in ledgers:
    print(l)

print("\n=== 3. SỐ DƯ DÒNG CUỐI CÙNG TRONG STOCK_LEDGER ===")
for p in prods:
    last_sl = db.execute(text(f"SELECT id, reference_code, transaction_type, quantity_change, balance_after, transaction_date FROM stock_ledger WHERE product_id = {p[0]} ORDER BY id DESC LIMIT 1")).fetchone()
    print(f"Last ledger {p[1]}:", last_sl)

print("\n=== 4. PHIẾU XUẤT THEO TRẠNG THÁI ===")
notes_by_status = db.execute(text("""
    SELECT en.status, count(en.id) 
    FROM export_notes en 
    WHERE en.code LIKE 'PX-%' OR en.code LIKE 'PERF-%'
    GROUP BY en.status
""")).fetchall()
print(notes_by_status)

print("\n=== 5. PHIẾU LỬNG (CONFIRMED) THEO USER ===")
dangling = db.execute(text("""
    SELECT u.username, u.role, count(en.id) 
    FROM export_notes en 
    JOIN users u ON en.created_by = u.id 
    WHERE en.status = 'CONFIRMED'
    GROUP BY u.username, u.role
""")).fetchall()
print(dangling)

print("\n=== 6. KIỂM TRA TRÙNG MÃ PHIẾU XUẤT ===")
dup_codes = db.execute(text("""
    SELECT code, count(*) FROM export_notes GROUP BY code HAVING count(*) > 1
""")).fetchall()
print("Duplicate codes:", dup_codes)

print("\n=== 7. PHIẾU TẠO BỞI IDEMPOTENCY KEY ===")
idem_notes = db.execute(text("""
    SELECT idempotency_key, count(*) as cnt, min(id) as min_id, max(id) as max_id, min(status) as status
    FROM export_notes 
    WHERE idempotency_key LIKE 'PERF-REPLAY-%'
    GROUP BY idempotency_key
""")).fetchall()
print("Idempotency keys distinct:", len(idem_notes))
for im in idem_notes:
    print(im)

print("\n=== 8. CHI TIẾT TỔNG PHIẾU XUẤT TRONG BẬC 3 THEO USER ===")
user_notes = db.execute(text("""
    SELECT u.username, u.role, en.status, count(en.id)
    FROM export_notes en
    JOIN users u ON en.created_by = u.id
    WHERE u.username LIKE 'perf_%'
    GROUP BY u.username, u.role, en.status
    ORDER BY u.username, en.status
""")).fetchall()
for un in user_notes:
    print(un)

db.close()
