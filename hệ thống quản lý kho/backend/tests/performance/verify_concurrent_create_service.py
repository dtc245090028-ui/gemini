"""Verification script testing create_export_note in inventory_service under high concurrency.
Runs on an isolated SQLite database to verify Item B fix.
"""

import os
import sys
import threading
from datetime import datetime, timezone
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "test_create_service.db"))

if os.path.exists(TEST_DB_PATH):
    try:
        os.remove(TEST_DB_PATH)
    except Exception:
        pass

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
from app.models.user import User
from app.schemas.export_note import ExportNoteCreate, ExportNoteDetailCreate
from app.core.database import Base
from app.services.inventory_service import create_export_note

Base.metadata.create_all(bind=engine)

def setup_master():
    db = SessionLocal()
    u = User(username="test_creator", full_name="Creator User", password_hash="dummy", role="WAREHOUSE_KEEPER")
    c = Category(code="CAT-C", name="Cat Create")
    s = Supplier(code="SUP-C", name="Sup Create")
    db.add_all([u, c, s])
    db.flush()
    p = Product(code="SKU-CREATE-01", name="Product Create Test", category_id=c.id, unit="Cái", current_stock=1000, min_stock=5, standard_price=100000.0)
    db.add(p)
    db.commit()
    uid = u.id
    pid = p.id
    db.close()
    return uid, pid

def run_concurrent_create_test():
    uid, pid = setup_master()
    concurrency = 20
    print(f"=== KIỂM THỬ ĐỒNG THỜI create_export_note VỚI {concurrency} LUỒNG SONG SONG ===")
    
    barrier = threading.Barrier(concurrency)
    results = {"success": 0, "failed_409": 0, "other_errors": []}
    created_codes = []
    lock = threading.Lock()

    def worker(wid):
        session = SessionLocal()
        payload = ExportNoteCreate(
            recipient_name=f"Customer Concurrent {wid}",
            note="Test concurrency note",
            details=[ExportNoteDetailCreate(product_id=pid, quantity=1, unit_price=100000.0)]
        )
        try:
            barrier.wait()
            note = create_export_note(session, payload, uid)
            with lock:
                results["success"] += 1
                created_codes.append(note.code)
        except Exception as e:
            session.rollback()
            with lock:
                if "409" in str(e) or "Xung đột" in str(e):
                    results["failed_409"] += 1
                else:
                    results["other_errors"].append(str(e))
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(concurrency)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Kiểm tra CSDL sau khi tất cả các luồng hoàn tất
    db = SessionLocal()
    all_notes = db.query(ExportNote).all()
    unique_codes = set(n.code for n in all_notes)
    
    print(f"\n>> KẾT QUẢ THỰC TẾ:")
    print(f"• Số request thành công: {results['success']} / {concurrency}")
    print(f"• Số request bị lỗi HTTP 409 Conflict: {results['failed_409']} / {concurrency}")
    print(f"• Số lỗi khác: {len(results['other_errors'])}")
    print(f"• Tổng số phiếu tạo trong CSDL: {len(all_notes)}")
    print(f"• Số mã phiếu duy nhất: {len(unique_codes)}")
    print(f"• Bất biến mã phiếu duy nhất: {'ĐẠT' if len(all_notes) == len(unique_codes) else 'KHÔNG ĐẠT'}")

    db.close()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

    return results

if __name__ == "__main__":
    run_concurrent_create_test()
