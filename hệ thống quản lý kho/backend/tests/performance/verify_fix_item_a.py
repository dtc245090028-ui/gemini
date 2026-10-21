"""Verification script for Item A (Atomic relative SQL update with RETURNING).
Runs isolated measurements to test Hypothesis for Item A.
"""

import os
import sys
import time
import threading
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "test_item_a.db"))

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
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    current_stock = Column(Integer, default=0, nullable=False)

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

def run_test_item_a_atomic_update():
    print("=== PHÉP ĐO KIỂM CHỨNG HƯỚNG A: CẬP NHẬT TƯƠNG ĐỐI NGUYÊN TỬ Ở TẦNG SQL ===")
    db = SessionLocal()
    # Khởi tạo sản phẩm có tồn = 100
    p = Product(code="SKU-ATOMIC-01", name="Atomic Update Test", current_stock=100)
    db.add(p)
    db.commit()
    prod_id = p.id
    db.close()

    barrier = threading.Barrier(20)
    success_count = [0]
    rejected_count = [0]

    # Mô phỏng 20 luồng đồng thời xuất kho, mỗi luồng xuất 1 cái (tổng xuất kỳ vọng = 20)
    def worker_ship(wid):
        session = SessionLocal()
        try:
            barrier.wait()
            qty = 1
            # Áp dụng Hướng A: Cập nhật tương đối nguyên tử kèm RETURNING
            stmt = text("""
                UPDATE products 
                SET current_stock = current_stock - :qty 
                WHERE id = :prod_id AND current_stock >= :qty 
                RETURNING current_stock
            """)
            res = session.execute(stmt, {"qty": qty, "prod_id": prod_id}).fetchone()
            if res is None:
                # Không đủ tồn kho
                session.rollback()
                rejected_count[0] += 1
                return
            
            new_balance = res[0]
            ledger = StockLedger(
                product_id=prod_id,
                transaction_type="EXPORT",
                reference_code=f"PX-ATOMIC-{wid:02d}",
                quantity_change=-qty,
                balance_after=new_balance,
            )
            session.add(ledger)
            session.commit()
            success_count[0] += 1
        except Exception as e:
            session.rollback()
            print(f"Worker {wid} error: {e}")
        finally:
            session.close()

    threads = [threading.Thread(target=worker_ship, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Thẩm tra dữ liệu CSDL sau test
    db_check = SessionLocal()
    p_final = db_check.query(Product).filter(Product.id == prod_id).first()
    ledgers = db_check.query(StockLedger).filter(StockLedger.product_id == prod_id).order_by(StockLedger.id.asc()).all()
    
    print(f"\n>> KẾT QUẢ THẨM TRA:")
    print(f"   - Tồn kho ban đầu: 100")
    print(f"   - Số luồng gọi thành công: {success_count[0]}")
    print(f"   - Số luồng bị từ chối: {rejected_count[0]}")
    print(f"   - Tổng số dòng Thẻ kho: {len(ledgers)}")
    print(f"   - TỒN KHO THỰC TẾ TRONG BẢNG PRODUCTS: {p_final.current_stock}")
    print(f"   - Tồn kho kỳ vọng đúng (100 - {success_count[0]}): {100 - success_count[0]}")
    
    # Kiểm tra tính đơn điệu của balance_after
    balances = [l.balance_after for l in ledgers]
    dup_balances = [b for b in set(balances) if balances.count(b) > 1]
    monotonic_errors = []
    for i in range(1, len(ledgers)):
        expected = ledgers[i-1].balance_after + ledgers[i].quantity_change
        actual = ledgers[i].balance_after
        if actual != expected:
            monotonic_errors.append((ledgers[i-1].id, ledgers[i].id, actual, expected))

    print(f"   - Số giá trị balance_after bị lặp lại: {len(dup_balances)}")
    print(f"   - Số dòng vi phạm tính lũy kế balance_after: {len(monotonic_errors)}")
    print(f"   - Bất biến 1 (Tồn kho = Tồn đầu + Tổng change): {p_final.current_stock == 100 - len(ledgers)}")
    print(f"   - Bất biến 2 (Không lặp số dư, đơn điệu 100%): {len(dup_balances) == 0 and len(monotonic_errors) == 0}")
    print(f"   - Bất biến 5 (Không âm kho): {p_final.current_stock >= 0}")
    
    db_check.close()
    return {
        "final_stock": p_final.current_stock,
        "success_count": success_count[0],
        "dup_count": len(dup_balances),
        "monotonic_errors": len(monotonic_errors),
        "is_exact": p_final.current_stock == (100 - success_count[0])
    }

def run_test_item_a_guard_prevent_negative():
    print("\n=== PHÉP ĐO KIỂM CHỨNG BẢO VỆ CHỐNG TỒN ÂM DƯỚI CONCURRENCY ===")
    db = SessionLocal()
    # Khởi tạo sản phẩm chỉ có tồn = 5 cái
    p = Product(code="SKU-ATOMIC-LOW", name="Low Stock Test", current_stock=5)
    db.add(p)
    db.commit()
    prod_id = p.id
    db.close()

    barrier = threading.Barrier(20)
    success_count = [0]
    rejected_count = [0]

    # 20 luồng cùng tranh nhau xuất 1 cái, tồn chỉ có 5 cái -> Đúng 5 luồng được xuất, 15 luồng phải bị từ chối
    def worker_race(wid):
        session = SessionLocal()
        try:
            barrier.wait()
            qty = 1
            stmt = text("""
                UPDATE products 
                SET current_stock = current_stock - :qty 
                WHERE id = :prod_id AND current_stock >= :qty 
                RETURNING current_stock
            """)
            res = session.execute(stmt, {"qty": qty, "prod_id": prod_id}).fetchone()
            if res is None:
                session.rollback()
                rejected_count[0] += 1
                return
            new_balance = res[0]
            ledger = StockLedger(
                product_id=prod_id,
                transaction_type="EXPORT",
                reference_code=f"PX-RACE-{wid:02d}",
                quantity_change=-qty,
                balance_after=new_balance,
            )
            session.add(ledger)
            session.commit()
            success_count[0] += 1
        except Exception as e:
            session.rollback()
        finally:
            session.close()

    threads = [threading.Thread(target=worker_race, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    db_check = SessionLocal()
    p_final = db_check.query(Product).filter(Product.id == prod_id).first()
    ledgers = db_check.query(StockLedger).filter(StockLedger.product_id == prod_id).all()
    print(f">> KẾT QUẢ KIỂM THỬ TRANH CHẤP TỒN KHO THẤP:")
    print(f"   - Tồn ban đầu: 5")
    print(f"   - Số luồng thành công: {success_count[0]} (Kỳ vọng: 5)")
    print(f"   - Số luồng bị từ chối: {rejected_count[0]} (Kỳ vọng: 15)")
    print(f"   - Tồn cuối cùng: {p_final.current_stock} (Kỳ vọng: 0, tuyệt đối không được âm)")
    print(f"   - Bất biến 5 (Tồn không âm): {p_final.current_stock == 0}")
    db_check.close()
    return {
        "success": success_count[0],
        "rejected": rejected_count[0],
        "final_stock": p_final.current_stock
    }

if __name__ == "__main__":
    r1 = run_test_item_a_atomic_update()
    r2 = run_test_item_a_guard_prevent_negative()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
