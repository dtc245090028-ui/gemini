"""Diagnostic measurements script for root-cause analysis (Step 4).
Runs isolated tests on an independent temporary database to verify hypotheses.
"""

import os
import sys
import time
import threading
import sqlite3
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import OperationalError, IntegrityError, SQLAlchemyError
from fastapi import HTTPException

DIAG_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "diag_test.db"))

if os.path.exists(DIAG_DB_PATH):
    os.remove(DIAG_DB_PATH)

engine = create_engine(
    f"sqlite:///{DIAG_DB_PATH}",
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
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    current_stock = Column(Integer, default=0, nullable=False)

class ExportNote(Base):
    __tablename__ = "export_notes"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    status = Column(String(20), default="CONFIRMED")
    recipient_name = Column(String(200))
    note_date = Column(DateTime)
    total_amount = Column(Float, default=0.0)

class StockLedger(Base):
    __tablename__ = "stock_ledger"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    reference_code = Column(String(50), nullable=False)
    quantity_change = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def test_measurement_1_busy_timeout():
    print("\n--- PHÉP ĐO 1: SQLite busy_timeout=5000 & database is locked ---")
    results = {}
    
    def thread_a_hold_lock():
        db_a = SessionLocal()
        try:
            # Chiếm độc quyền khóa ghi SQLite
            db_a.execute(text("BEGIN IMMEDIATE"))
            db_a.execute(text("INSERT INTO products (code, name, current_stock) VALUES ('P-LOCK', 'Lock Test', 10)"))
            print("  [Thread A] Đã lấy EXCLUSIVE lock, giữ khóa trong 8 giây...")
            time.sleep(8)
            db_a.commit()
            print("  [Thread A] Commit thành công và giải phóng khóa.")
        except Exception as e:
            db_a.rollback()
            print(f"  [Thread A Error] {e}")
        finally:
            db_a.close()

    def thread_b_wait_and_fail():
        time.sleep(1) # Bắt đầu sau khi Thread A đã giữ khóa
        db_b = SessionLocal()
        start_t = time.time()
        print("  [Thread B] Cố gắng ghi vào DB (bắt đầu chờ khóa)...")
        try:
            db_b.execute(text("BEGIN IMMEDIATE"))
            db_b.execute(text("INSERT INTO products (code, name, current_stock) VALUES ('P-LOCK-B', 'Lock Test B', 20)"))
            db_b.commit()
            elapsed = time.time() - start_t
            results["status"] = "SUCCESS"
            results["elapsed"] = elapsed
            print(f"  [Thread B] Thành công bất ngờ sau {elapsed:.2f}s!")
        except OperationalError as exc:
            elapsed = time.time() - start_t
            db_b.rollback()
            results["status"] = "OPERATIONAL_ERROR"
            results["error"] = str(exc)
            results["elapsed"] = elapsed
            # Kiểm tra xem có kế thừa từ SQLAlchemyError không (để xem handler main.py có bắt được không)
            results["is_sqlalchemy_error"] = isinstance(exc, SQLAlchemyError)
            print(f"  [Thread B] Bị chặn chính xác: {elapsed:.3f} giây. Lỗi: {exc.orig}")
            print(f"  [Thread B] Kế thừa SQLAlchemyError: {results['is_sqlalchemy_error']} -> Sẽ bị main.py biến thành HTTP 500 DATABASE_ERROR!")
        finally:
            db_b.close()

    t_a = threading.Thread(target=thread_a_hold_lock)
    t_b = threading.Thread(target=thread_b_wait_and_fail)
    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()
    return results

def test_measurement_2_lost_update():
    print("\n--- PHÉP ĐO 2: Tái hiện Lost Update & Lặp balance_after ---")
    db = SessionLocal()
    # Khởi tạo sản phẩm có tồn = 100
    p = Product(code="SKU-LOST-01", name="Lost Update Test", current_stock=100)
    db.add(p)
    db.commit()
    prod_id = p.id
    db.close()

    barrier = threading.Barrier(2)
    results = {}

    def simulate_ship(thread_id):
        session = SessionLocal()
        try:
            # 1. Đọc Product (DEFERRED transaction)
            prod = session.query(Product).filter(Product.id == prod_id).first()
            read_stock = prod.current_stock
            print(f"  [Thread {thread_id}] Đã đọc current_stock = {read_stock}")
            
            # Đồng bộ cả 2 luồng cùng đọc xong rồi mới trừ và commit
            barrier.wait()

            # 2. Trừ tồn kho trong RAM Python (giống hệt inventory_service.py L401)
            qty = 1
            prod.current_stock -= qty

            # 3. Ghi thẻ kho với balance_after = prod.current_stock (L408)
            ledger = StockLedger(
                product_id=prod.id,
                transaction_type="EXPORT",
                reference_code=f"PX-TEST-{thread_id}",
                quantity_change=-qty,
                balance_after=prod.current_stock,
            )
            session.add(ledger)

            # 4. Commit
            session.commit()
            print(f"  [Thread {thread_id}] Commit thành công với balance_after = {ledger.balance_after}")
        except Exception as e:
            session.rollback()
            print(f"  [Thread {thread_id} Error] {e}")
        finally:
            session.close()

    t1 = threading.Thread(target=simulate_ship, args=(1,))
    t2 = threading.Thread(target=simulate_ship, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Kiểm tra lại DB sau khi 2 luồng kết thúc
    db_check = SessionLocal()
    p_final = db_check.query(Product).filter(Product.id == prod_id).first()
    ledgers = db_check.query(StockLedger).filter(StockLedger.product_id == prod_id).all()
    
    print(f"  >> KẾT QUẢ CSDL:")
    print(f"     - Tồn kho ban đầu: 100")
    print(f"     - Số lượt xuất kho (mỗi lượt 1 cái): {len(ledgers)}")
    print(f"     - Tồn kho kỳ vọng đúng (100 - 2): 98")
    print(f"     - TỒN KHO THỰC TẾ TRONG BẢNG PRODUCTS: {p_final.current_stock}")
    print(f"     - Chi tiết thẻ kho:")
    for l in ledgers:
        print(f"       + ID={l.id}, Ref={l.reference_code}, Change={l.quantity_change}, Balance_after={l.balance_after}")
    
    is_lost = (p_final.current_stock != 98)
    has_dup_balance = (len(set(l.balance_after for l in ledgers)) < len(ledgers))
    print(f"     - Xảy ra Lost Update: {is_lost} (Thất thoát: {p_final.current_stock - 98} đơn vị)")
    print(f"     - Bị lặp balance_after: {has_dup_balance}")
    db_check.close()
    return {"final_stock": p_final.current_stock, "is_lost": is_lost, "has_dup_balance": has_dup_balance}

def test_measurement_3_code_collision():
    print("\n--- PHÉP ĐO 3: Tái hiện Xung đột mã phiếu (UNIQUE collision & 409) ---")
    
    def generate_code_naive(db):
        prefix = "PX"
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        code_pattern = f"{prefix}-{today_str}-%"
        last_code = db.execute(text(f"SELECT max(code) FROM export_notes WHERE code LIKE '{code_pattern}'")).scalar()
        if last_code:
            seq = int(last_code.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{today_str}-{seq:04d}"

    collision_count = [0]
    exhausted_retries = [0]
    barrier = threading.Barrier(20)

    def worker(wid):
        db = SessionLocal()
        max_retries = 3
        succeeded = False
        for attempt in range(max_retries):
            try:
                # Barrier chỉ ở lần thử đầu tiên để dồn đồng thời
                if attempt == 0:
                    barrier.wait()
                code = generate_code_naive(db)
                note = ExportNote(code=code, recipient_name=f"Worker {wid}")
                db.add(note)
                db.commit()
                succeeded = True
                break
            except IntegrityError:
                db.rollback()
                collision_count[0] += 1
                if attempt == max_retries - 1:
                    exhausted_retries[0] += 1
        db.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"  >> KẾT QUẢ MÔ PHỎNG 20 LUỒNG ĐỒNG THỜI:")
    print(f"     - Số lần xảy ra IntegrityError (va chạm mã): {collision_count[0]}")
    print(f"     - Số luồng cạn sạch 3 lần retry (sinh mã lỗi 409): {exhausted_retries[0]}")
    return {"collisions": collision_count[0], "exhausted": exhausted_retries[0]}

if __name__ == "__main__":
    r1 = test_measurement_1_busy_timeout()
    r2 = test_measurement_2_lost_update()
    r3 = test_measurement_3_code_collision()
    if os.path.exists(DIAG_DB_PATH):
        try:
            os.remove(DIAG_DB_PATH)
        except Exception:
            pass
