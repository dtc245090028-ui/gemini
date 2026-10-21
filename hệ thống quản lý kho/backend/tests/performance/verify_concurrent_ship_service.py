"""Verification script testing ship_export_note in inventory_service under high concurrency.
Runs on an isolated SQLite database file to ensure no impact on warehouse.db.
"""

import os
import sys
import threading
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "test_service_ship.db"))

if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

engine = create_engine(
    f"sqlite:///{TEST_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from app.models.product import Product
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.stock_ledger import StockLedger
from app.models.user import User
from app.core.database import Base
from app.services.inventory_service import ship_export_note

Base.metadata.create_all(bind=engine)

def setup_data():
    db = SessionLocal()
    # 1. User
    u = User(username="test_wh", full_name="Test Warehouse", password_hash="dummy", role="WAREHOUSE_KEEPER")
    db.add(u)
    
    # 2. Category & Supplier
    c = Category(code="CAT-T", name="Cat Test")
    s = Supplier(code="SUP-T", name="Sup Test")
    db.add_all([c, s])
    db.flush()

    # 3. Product: initial stock = 50
    p = Product(code="SKU-CONCUR-01", name="Product Concurrency Test", category_id=c.id, unit="Cái", current_stock=50, min_stock=5, standard_price=100000.0)
    db.add(p)
    db.flush()

    # 4. Create 30 ExportNotes in CONFIRMED state, each requesting 1 item (Total request = 30)
    notes = []
    for i in range(1, 31):
        en = ExportNote(
            code=f"PX-20261021-{i:04d}",
            recipient_name=f"Customer {i}",
            created_by=u.id,
            status="CONFIRMED",
            total_amount=100000.0,
            note_date=datetime.now(timezone.utc),
        )
        db.add(en)
        db.flush()
        dt = ExportNoteDetail(
            export_note_id=en.id,
            product_id=p.id,
            quantity=1,
            unit_price=100000.0,
            subtotal=100000.0,
        )
        db.add(dt)
        notes.append(en.id)

    db.commit()
    user_id = u.id
    prod_id = p.id
    db.close()
    return user_id, prod_id, notes

def run_concurrent_ship_test():
    user_id, prod_id, note_ids = setup_data()
    print(f"=== KIỂM THỬ ĐỒNG THỜI ship_export_note VỚI 30 LUỒNG SONG SONG ===")
    print(f"Tồn kho ban đầu: 50. Số phiếu xuất CONFIRMED: 30 (mỗi phiếu 1 cái).")
    
    barrier = threading.Barrier(30)
    results = {"success": 0, "failed": 0, "errors": []}
    lock = threading.Lock()

    def worker(note_id):
        session = SessionLocal()
        try:
            barrier.wait()
            ship_export_note(session, note_id, user_id)
            with lock:
                results["success"] += 1
        except Exception as e:
            session.rollback()
            with lock:
                results["failed"] += 1
                results["errors"].append(str(e))
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(nid,)) for nid in note_ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Kiểm tra CSDL sau khi tất cả 30 luồng chạy xong
    db = SessionLocal()
    p = db.query(Product).filter(Product.id == prod_id).first()
    ledgers = db.query(StockLedger).filter(StockLedger.product_id == prod_id).order_by(StockLedger.id.asc()).all()
    shipping_notes = db.query(ExportNote).filter(ExportNote.status == "SHIPPING").all()

    print(f"\n>> KẾT QUẢ THỰC TẾ:")
    print(f"• Số lượt ship thành công: {results['success']} / 30")
    print(f"• Số lượt thất bại: {results['failed']} / 30")
    print(f"• Tồn kho cuối cùng: {p.current_stock} (Kỳ vọng đúng: 50 - 30 = 20)")
    print(f"• Số dòng Thẻ kho (StockLedger): {len(ledgers)}")
    print(f"• Số phiếu ở trạng thái SHIPPING: {len(shipping_notes)}")
    
    # Kiểm tra tính đơn điệu của Thẻ kho
    balances = [l.balance_after for l in ledgers]
    dup_balances = [b for b in set(balances) if balances.count(b) > 1]
    monotonic_errors = []
    for i in range(1, len(ledgers)):
        expected = ledgers[i-1].balance_after + ledgers[i].quantity_change
        actual = ledgers[i].balance_after
        if actual != expected:
            monotonic_errors.append((ledgers[i-1].id, ledgers[i].id, actual, expected))

    print(f"• Số giá trị balance_after bị lặp lại: {len(dup_balances)}")
    print(f"• Số dòng vi phạm tính lũy kế balance_after: {len(monotonic_errors)}")
    
    inv_1 = (p.current_stock == 50 - len(ledgers))
    inv_2 = (len(dup_balances) == 0 and len(monotonic_errors) == 0)
    inv_3 = (len(shipping_notes) == len(ledgers))
    inv_5 = (p.current_stock >= 0)

    print(f"\n>> ĐÁNH GIÁ CÁC BẤT BIẾN:")
    print(f"1. Tồn hiện tại = Tồn đầu + Tổng thay đổi: {'ĐẠT' if inv_1 else 'KHÔNG ĐẠT'} (Tồn={p.current_stock}, Kế toán={50 - len(ledgers)})")
    print(f"2. Tính đơn điệu lũy kế của Thẻ kho: {'ĐẠT' if inv_2 else 'KHÔNG ĐẠT'} (0 lỗi lũy kế, 0 số dư lặp)")
    print(f"3. Số phiếu SHIPPING = Số dòng thẻ kho: {'ĐẠT' if inv_3 else 'KHÔNG ĐẠT'} ({len(shipping_notes)} == {len(ledgers)})")
    print(f"5. Tồn kho không âm: {'ĐẠT' if inv_5 else 'KHÔNG ĐẠT'} (Tồn={p.current_stock} >= 0)")

    db.close()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

if __name__ == "__main__":
    run_concurrent_ship_test()
