"""Verification script for Item C (SQLite PRAGMA tuning & Lock contention benchmark).
Compares synchronous=FULL vs synchronous=NORMAL under heavy concurrent write pressure.
"""

import os
import sys
import time
import threading
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

TEST_DB_FULL = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "test_sync_full.db"))
TEST_DB_NORMAL = os.path.abspath(os.path.join(os.path.dirname(__file__), "results", "test_sync_normal.db"))

def benchmark_pragma(db_path, sync_mode, users=20, ops_per_user=50):
    for sfx in ("", "-wal", "-shm"):
        p = f"{db_path}{sfx}"
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, echo=False)
    
    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_conn, record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute(f"PRAGMA synchronous={sync_mode}")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Session = sessionmaker(bind=engine)
    Base = declarative_base()

    class BenchmarkTable(Base):
        __tablename__ = "bench"
        id = Column(Integer, primary_key=True)
        val = Column(String(50))

    Base.metadata.create_all(bind=engine)

    barrier = threading.Barrier(users)
    latencies = []
    lock_errors = [0]
    start_total = time.time()

    def worker(wid):
        session = Session()
        barrier.wait()
        for i in range(ops_per_user):
            t0 = time.time()
            try:
                session.execute(text("INSERT INTO bench (val) VALUES (:v)"), {"v": f"u{wid}_{i}"})
                session.commit()
                latencies.append(time.time() - t0)
            except Exception as e:
                session.rollback()
                if "database is locked" in str(e):
                    lock_errors[0] += 1
        session.close()

    threads = [threading.Thread(target=worker, args=(u,)) for u in range(users)]
    for t in threads: t.start()
    for t in threads: t.join()
    total_time = time.time() - start_total

    total_ops = len(latencies)
    avg_lat = (sum(latencies) / total_ops * 1000) if total_ops else 0.0
    max_lat = (max(latencies) * 1000) if total_ops else 0.0
    rps = total_ops / total_time if total_time > 0 else 0.0

    print(f"\n[PRAGMA synchronous = {sync_mode}] (20 users x 50 ghi dồn dập = 1.000 ops ghi):")
    print(f"  • Tổng số ghi thành công: {total_ops} / {users * ops_per_user}")
    print(f"  • Số lỗi database is locked (HTTP 500 tương đương): {lock_errors[0]}")
    print(f"  • Tổng thời gian: {total_time:.2f} s")
    print(f"  • Thông lượng ghi (Write Throughput): {rps:.1f} ops/giây")
    print(f"  • Độ trễ ghi trung bình: {avg_lat:.2f} ms | Lớn nhất: {max_lat:.2f} ms")

    for sfx in ("", "-wal", "-shm"):
        p = f"{db_path}{sfx}"
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass

    return {"sync_mode": sync_mode, "total_time": total_time, "rps": rps, "avg_lat": avg_lat, "max_lat": max_lat, "lock_errors": lock_errors[0]}

if __name__ == "__main__":
    print("=========================================================================")
    print(" SO SÁNH HIỆU NĂNG GHI & KHÓA: PRAGMA synchronous FULL (2) VS NORMAL (1)")
    print("=========================================================================")
    r_full = benchmark_pragma(TEST_DB_FULL, sync_mode="FULL")
    r_normal = benchmark_pragma(TEST_DB_NORMAL, sync_mode="NORMAL")
