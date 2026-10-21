"""Verification script for Item B (Document Code Generation).
Compares baseline (3 retries, 0ms) vs proposed fix (5 retries + Exponential Backoff & Jitter)
under 20 concurrent threads and 50 concurrent threads.
"""

import os
import sys
import time
import random
import threading
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, event, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "test_code_gen.db"))

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
Base = declarative_base()

class ExportNote(Base):
    __tablename__ = "export_notes"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)

Base.metadata.create_all(bind=engine)

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

def run_test_scenario(thread_count, max_retries, use_backoff, tag):
    # Dọn sạch bảng trước mỗi kịch bản
    db_clean = SessionLocal()
    db_clean.execute(text("DELETE FROM export_notes"))
    db_clean.commit()
    db_clean.close()

    success = [0]
    collisions = [0]
    exhausted_409 = [0]
    latencies = []
    barrier = threading.Barrier(thread_count)
    start_total = time.time()

    def worker(wid):
        db = SessionLocal()
        t_start = time.time()
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    barrier.wait()
                code = generate_code_naive(db)
                note = ExportNote(code=code)
                db.add(note)
                db.commit()
                success[0] += 1
                latencies.append(time.time() - t_start)
                break
            except IntegrityError:
                db.rollback()
                collisions[0] += 1
                if attempt == max_retries - 1:
                    exhausted_409[0] += 1
                elif use_backoff:
                    # Exponential Backoff + Jitter
                    delay = 0.015 * (2 ** attempt) + random.uniform(0.010, 0.035)
                    time.sleep(delay)
        db.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads: t.start()
    for t in threads: t.join()
    total_elapsed = time.time() - start_total

    db_check = SessionLocal()
    total_in_db = db_check.execute(text("SELECT count(*) FROM export_notes")).scalar()
    unique_codes = db_check.execute(text("SELECT count(DISTINCT code) FROM export_notes")).scalar()
    db_check.close()

    avg_lat = (sum(latencies) / len(latencies) * 1000) if latencies else 0.0
    max_lat = (max(latencies) * 1000) if latencies else 0.0

    print(f"\n[{tag}] Số luồng: {thread_count} | max_retries: {max_retries} | Backoff: {use_backoff}")
    print(f"  • Số request thành công: {success[0]} / {thread_count}")
    print(f"  • Số request thất bại (Lỗi 409): {exhausted_409[0]} / {thread_count} ({exhausted_409[0]/thread_count*100:.1f}%)")
    print(f"  • Số lần va chạm IntegrityError: {collisions[0]}")
    print(f"  • Số bản ghi lưu trong CSDL: {total_in_db} (Duy nhất: {unique_codes})")
    print(f"  • Độ trễ trung bình: {avg_lat:.1f} ms | Lớn nhất: {max_lat:.1f} ms | Tổng thời gian: {total_elapsed:.2f} s")
    
    return {
        "success": success[0],
        "exhausted": exhausted_409[0],
        "collisions": collisions[0],
        "total_in_db": total_in_db,
        "avg_lat": avg_lat,
        "max_lat": max_lat,
    }

if __name__ == "__main__":
    print("=========================================================================")
    print(" SO SÁNH ĐỐI ĐẦU: HIỆN TRẠNG VS HƯỚNG C (BACKOFF + JITTER)")
    print("=========================================================================")
    
    # Kịch bản 1: Baseline 20 luồng (giống Bậc 4)
    run_test_scenario(thread_count=20, max_retries=3, use_backoff=False, tag="BASELINE 20 USERS (Hiện trạng)")
    
    # Kịch bản 2: Hướng C 20 luồng (5 retries + Backoff + Jitter)
    run_test_scenario(thread_count=20, max_retries=5, use_backoff=True, tag="HƯỚNG C 20 USERS (Đề xuất)")

    # Kịch bản 3: Thử thách cực đại 50 luồng (stress test)
    run_test_scenario(thread_count=50, max_retries=5, use_backoff=True, tag="HƯỚNG C 50 USERS (Áp lực cao)")

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
