"""Công cụ sao lưu & phục hồi CSDL SQLite an toàn (Online Backup API).

Sử dụng cơ chế `sqlite3.Connection.backup()` chuẩn của SQLite C-API:
- Không gây khóa đọng (non-blocking) các giao dịch ghi đang chạy.
- Tự động bao gồm cả dữ liệu trong file WAL (-wal).
- Không bị rủi ro corrupt dữ liệu như lệnh `cp` file trực tiếp.
"""

import argparse
import os
import sqlite3
import sys
import time

def get_db_path():
    db_env = os.environ.get("DATABASE_URL", "")
    if db_env.startswith("sqlite:///"):
        return db_env.replace("sqlite:///", "")
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "warehouse.db"))

def backup_db(dest_path: str):
    src_path = get_db_path()
    if not os.path.exists(src_path):
        print(f"[LỖI] Không tìm thấy file nguồn: {src_path}")
        sys.exit(1)
        
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    if os.path.exists(dest_path):
        os.remove(dest_path)
        
    print(f"[*] Bắt đầu sao lưu Online: {src_path} -> {dest_path}")
    t0 = time.perf_counter()
    
    src_conn = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True, timeout=10.0)
    dst_conn = sqlite3.connect(dest_path, timeout=10.0)
    try:
        # SQLite Online Backup API: copy từng trang, thread-safe
        src_conn.backup(dst_conn, pages=100)
    finally:
        dst_conn.close()
        src_conn.close()
        
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    size_kb = os.path.getsize(dest_path) / 1024.0
    print(f"[THÀNH CÔNG] Đã sao lưu {size_kb:.1f} KB trong {elapsed_ms:.2f} ms!")
    return dest_path

def restore_db(src_backup_path: str):
    dst_path = get_db_path()
    if not os.path.exists(src_backup_path):
        print(f"[LỖI] Không tìm thấy file backup: {src_backup_path}")
        sys.exit(1)
        
    print(f"[*] Phục hồi CSDL từ backup: {src_backup_path} -> {dst_path}")
    t0 = time.perf_counter()
    
    src_conn = sqlite3.connect(f"file:{src_backup_path}?mode=ro", uri=True, timeout=10.0)
    dst_conn = sqlite3.connect(dst_path, timeout=30.0)
    try:
        src_conn.backup(dst_conn, pages=100)
    finally:
        dst_conn.close()
        src_conn.close()
        
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    size_kb = os.path.getsize(dst_path) / 1024.0
    print(f"[THÀNH CÔNG] Đã phục hồi {size_kb:.1f} KB trong {elapsed_ms:.2f} ms!")

def check_db():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"[LỖI] File CSDL không tồn tại: {db_path}")
        return
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    cur.execute("PRAGMA quick_check;")
    status = cur.fetchone()[0]
    wal_size = os.path.getsize(db_path + "-wal") if os.path.exists(db_path + "-wal") else 0
    shm_size = os.path.getsize(db_path + "-shm") if os.path.exists(db_path + "-shm") else 0
    print(f"CSDL: {db_path}")
    print(f"  • Kích thước DB : {os.path.getsize(db_path)/1024.0:.1f} KB")
    print(f"  • Kích thước WAL: {wal_size/1024.0:.1f} KB")
    print(f"  • Kích thước SHM: {shm_size/1024.0:.1f} KB")
    print(f"  • Toàn vẹn (PRAGMA quick_check): {status}")
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite Online Backup & Restore Manager")
    parser.add_argument("action", choices=["backup", "restore", "status"], default="status", nargs="?")
    parser.add_argument("--file", "-f", help="Đường dẫn file đích (backup) hoặc nguồn (restore)")
    args = parser.parse_args()
    
    if args.action == "backup":
        dest = args.file or "/var/lib/warehouse/backups/warehouse_manual_backup.db"
        backup_db(dest)
    elif args.action == "restore":
        if not args.file:
            print("[LỖI] Cần truyền --file <đường_dẫn_backup> để phục hồi")
            sys.exit(1)
        restore_db(args.file)
    elif args.action == "status":
        check_db()
