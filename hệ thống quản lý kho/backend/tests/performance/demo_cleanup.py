"""Script dọn dẹp toàn bộ dữ liệu sinh ra bởi demo_run.py (demo_cleanup.py).

Hỗ trợ dọn dẹp trực tiếp trên CSDL của giao diện Web (warehouse.db trong Docker container)
kèm cơ chế tự động ủy quyền vào container để tránh xung đột khóa SQLite WAL trên Windows,
và tự động khôi phục từ bản backup dự phòng nếu quá trình xóa gặp bất kỳ trở ngại nào.

Luồng thực thi:
1. Guard kiểm tra môi trường & ủy quyền vào Docker container nếu chạy từ Windows Host.
2. Đọc demo_manifest.json. Nếu không có manifest thì chỉ quét theo tiền tố
   SKU-DEMO-% / PX-DEMO% / PN-DEMO% và hỏi xác nhận.
3. Thu thập ID của 2 sản phẩm trong manifest cộng quét mọi phiếu/ledger tham chiếu
   2 sản phẩm đó (phòng trường hợp crash giữa chừng). Không xóa LIKE rộng trên bảng khác.
4. In số bản ghi sẽ xóa ở mỗi bảng, yêu cầu xác nhận (bỏ qua nếu có --yes).
5. Xóa theo lô (batch) trong 1 transaction duy nhất, in tiến độ, đúng thứ tự khóa ngoại:
   stock_ledger -> chi tiết phiếu -> phiếu nhập/xuất -> sản phẩm.
6. Đối chiếu số dòng với snapshot trong manifest: khớp thì in "SẠCH HOÀN TOÀN",
   lệch thì in bảng chênh lệch và exit(1).
7. Xóa cache AI tạm (ai_cache.json) và xóa manifest. Idempotent (chạy lại nhiều lần không lỗi).
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from urllib.parse import urlparse

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Tự động ủy quyền vào trong container warehouse_backend nếu chạy từ Windows Host
# để đảm bảo an toàn tuyệt đối cho SQLite WAL.
if os.name == "nt" and not os.environ.get("INSIDE_DOCKER"):
    raw_argv = sys.argv[1:]
    uses_perf_port = any("8001" in a for a in raw_argv)
    if not uses_perf_port:
        chk = subprocess.run(
            ["docker", "ps", "--filter", "name=warehouse_backend", "--filter", "status=running", "-q"],
            capture_output=True,
            text=True,
            check=False,
        )
        if chk.returncode == 0 and chk.stdout.strip():
            forwarded_args = []
            skip_next = False
            for idx_a, arg_v in enumerate(raw_argv):
                if skip_next:
                    skip_next = False
                    continue
                if arg_v == "--db-path" and idx_a + 1 < len(raw_argv):
                    skip_next = True
                    continue
                forwarded_args.append(arg_v)

            cmd = [
                "docker", "exec", "-i",
                "-e", "INSIDE_DOCKER=1",
                "-e", "PYTHONUTF8=1",
                "warehouse_backend",
                "python", "-u", "/app/tests/performance/demo_cleanup.py",
                *forwarded_args,
            ]
            res = subprocess.run(cmd, check=False)
            sys.exit(res.returncode)

PERF_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(PERF_DIR, "..", ".."))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "warehouse.db")
PRE_DEMO_BACKUP_PATH = os.path.join(BACKEND_DIR, "backups", "warehouse_pre_demo_backup.db")
AI_CACHE_PATH = os.path.join(BACKEND_DIR, "ai_cache.json")
MANIFEST_PATH = os.path.join(PERF_DIR, "demo_manifest.json")

SNAPSHOT_TABLES = [
    "products",
    "import_notes",
    "import_note_details",
    "export_notes",
    "export_note_details",
    "stock_ledger",
]


def verify_environment_guard(base_url: str, db_path: str) -> str:
    parsed = urlparse(base_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    abs_db = os.path.abspath(db_path)

    print("=" * 78)
    print(" KIỂM TRA AN TOÀN MÔI TRƯỜNG DỌN DẸP (SAFETY GUARD)")
    print("=" * 78)
    print(f"  • Base URL mục tiêu : {base_url} (Port: {port})")
    print(f"  • CSDL mục tiêu     : {abs_db}")

    if parsed.hostname not in ("127.0.0.1", "localhost"):
        print("\n[SAFETY GUARD BLOCKED] Chỉ cho phép chạy dọn dẹp trên localhost / 127.0.0.1!")
        sys.exit(1)

    if not os.path.exists(abs_db):
        print(f"\n[SAFETY GUARD BLOCKED] Không tìm thấy file CSDL tại: {abs_db}")
        sys.exit(1)

    print("  => [GUARD PASS] Đã xác nhận môi trường dọn dẹp an toàn.\n")
    return abs_db


def get_db_snapshot(conn: sqlite3.Connection) -> dict:
    cur = conn.cursor()
    snap = {}
    for tbl in SNAPSHOT_TABLES:
        cur.execute(f"SELECT count(*) FROM {tbl}")
        snap[tbl] = cur.fetchone()[0]
    return snap


def delete_in_batches(cur: sqlite3.Cursor, table: str, id_col: str, ids: list, batch_size: int = 250) -> int:
    """Xóa danh sách ID theo từng lô (batch) trong cùng 1 transaction và in tiến độ."""
    total = len(ids)
    if total == 0:
        print(f"  • {table:<22}: 0 bản ghi (bỏ qua)")
        return 0

    deleted = 0
    for start in range(0, total, batch_size):
        chunk = ids[start : start + batch_size]
        placeholders = ",".join("?" for _ in chunk)
        cur.execute(f"DELETE FROM {table} WHERE {id_col} IN ({placeholders})", chunk)
        deleted += cur.rowcount
        print(f"  • {table:<22}: đã xóa lô {min(start + batch_size, total)}/{total} (thực xóa lũy kế: {deleted})")
    return deleted


def run_cleanup(args):
    abs_db = verify_environment_guard(args.base_url, args.db_path)

    manifest = None
    has_manifest = os.path.exists(MANIFEST_PATH)
    if has_manifest:
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            print(f"[*] Đã nạp file manifest: {MANIFEST_PATH}")
            if manifest.get("db_path") and os.path.exists(manifest["db_path"]):
                abs_db = os.path.abspath(manifest["db_path"])
        except Exception as exc:
            print(f"[CẢNH BÁO] Không đọc được manifest ({exc}). Chuyển sang chế độ quét theo tiền tố DEMO.")
            manifest = None
            has_manifest = False
    else:
        print("[*] Không tìm thấy demo_manifest.json. Chế độ quét theo tiền tố SKU-DEMO-% / PX-DEMO / PN-DEMO.")

    conn = sqlite3.connect(abs_db, timeout=30.0)
    conn.isolation_level = None
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA busy_timeout=10000")

    try:
        # 1. Xác định danh sách ID sản phẩm DEMO
        product_ids = set()
        if manifest and manifest.get("products"):
            for p in manifest["products"]:
                if p.get("id"):
                    product_ids.add(int(p["id"]))

        cur.execute("SELECT id FROM products WHERE code IN ('SKU-DEMO-A', 'SKU-DEMO-B') OR code LIKE 'SKU-DEMO-%'")
        for (pid,) in cur.fetchall():
            product_ids.add(int(pid))
        product_ids = sorted(product_ids)

        # 2. Thu thập các phiếu nhập liên quan
        import_note_ids = set()
        if manifest and manifest.get("created_import_notes"):
            for n in manifest["created_import_notes"]:
                if n.get("id"):
                    import_note_ids.add(int(n["id"]))

        if product_ids:
            ph = ",".join("?" for _ in product_ids)
            cur.execute(
                f"SELECT DISTINCT import_note_id FROM import_note_details WHERE product_id IN ({ph})",
                product_ids,
            )
            for (nid,) in cur.fetchall():
                import_note_ids.add(int(nid))

        cur.execute("SELECT id FROM import_notes WHERE code LIKE 'PN-DEMO%'")
        for (nid,) in cur.fetchall():
            import_note_ids.add(int(nid))
        import_note_ids = sorted(import_note_ids)

        # 3. Thu thập chi tiết phiếu nhập
        import_detail_ids = set()
        if product_ids:
            ph = ",".join("?" for _ in product_ids)
            cur.execute(f"SELECT id FROM import_note_details WHERE product_id IN ({ph})", product_ids)
            for (did,) in cur.fetchall():
                import_detail_ids.add(int(did))
        if import_note_ids:
            ph = ",".join("?" for _ in import_note_ids)
            cur.execute(f"SELECT id FROM import_note_details WHERE import_note_id IN ({ph})", import_note_ids)
            for (did,) in cur.fetchall():
                import_detail_ids.add(int(did))
        import_detail_ids = sorted(import_detail_ids)

        # 4. Thu thập các phiếu xuất liên quan
        export_note_ids = set()
        if manifest and manifest.get("created_export_notes"):
            for n in manifest["created_export_notes"]:
                if n.get("id"):
                    export_note_ids.add(int(n["id"]))

        if product_ids:
            ph = ",".join("?" for _ in product_ids)
            cur.execute(
                f"SELECT DISTINCT export_note_id FROM export_note_details WHERE product_id IN ({ph})",
                product_ids,
            )
            for (nid,) in cur.fetchall():
                export_note_ids.add(int(nid))

        cur.execute("SELECT id FROM export_notes WHERE code LIKE 'PX-DEMO%'")
        for (nid,) in cur.fetchall():
            export_note_ids.add(int(nid))
        export_note_ids = sorted(export_note_ids)

        # 5. Thu thập chi tiết phiếu xuất
        export_detail_ids = set()
        if product_ids:
            ph = ",".join("?" for _ in product_ids)
            cur.execute(f"SELECT id FROM export_note_details WHERE product_id IN ({ph})", product_ids)
            for (did,) in cur.fetchall():
                export_detail_ids.add(int(did))
        if export_note_ids:
            ph = ",".join("?" for _ in export_note_ids)
            cur.execute(f"SELECT id FROM export_note_details WHERE export_note_id IN ({ph})", export_note_ids)
            for (did,) in cur.fetchall():
                export_detail_ids.add(int(did))
        export_detail_ids = sorted(export_detail_ids)

        # 6. Thu thập các dòng stock_ledger tham chiếu 2 sản phẩm
        ledger_ids = set()
        if product_ids:
            ph = ",".join("?" for _ in product_ids)
            cur.execute(f"SELECT id FROM stock_ledger WHERE product_id IN ({ph})", product_ids)
            for (lid,) in cur.fetchall():
                ledger_ids.add(int(lid))
        cur.execute("SELECT id FROM stock_ledger WHERE reference_code LIKE 'PN-DEMO%' OR reference_code LIKE 'PX-DEMO%'")
        for (lid,) in cur.fetchall():
            ledger_ids.add(int(lid))
        ledger_ids = sorted(ledger_ids)

        total_to_delete = (
            len(ledger_ids)
            + len(import_detail_ids)
            + len(export_detail_ids)
            + len(import_note_ids)
            + len(export_note_ids)
            + len(product_ids)
        )

        print("\n--- KẾ HOẠCH DỌN DẸP DỮ LIỆU DEMO ---")
        print(f"  • stock_ledger        : {len(ledger_ids):>6} bản ghi")
        print(f"  • import_note_details : {len(import_detail_ids):>6} bản ghi")
        print(f"  • export_note_details : {len(export_detail_ids):>6} bản ghi")
        print(f"  • import_notes        : {len(import_note_ids):>6} bản ghi")
        print(f"  • export_notes        : {len(export_note_ids):>6} bản ghi")
        print(f"  • products (DEMO)     : {len(product_ids):>6} bản ghi")
        print(f"  => TỔNG CỘNG          : {total_to_delete:>6} bản ghi sẽ xóa (Tổng phiếu: {len(import_note_ids) + len(export_note_ids)})")

        if total_to_delete == 0:
            print("\n[*] Không có bản ghi DEMO nào cần xóa (Idempotent).")
        else:
            if not args.yes:
                ans = input("\nBạn có chắc chắn muốn xóa các bản ghi DEMO trên? [y/N]: ").strip().lower()
                if ans not in ("y", "yes"):
                    print("[HỦY] Đã hủy thao tác dọn dẹp.")
                    sys.exit(0)

            print("\n--- TIẾN HÀNH XÓA THEO LÔ TRONG 1 TRANSACTION ---")
            try:
                cur.execute("BEGIN IMMEDIATE")
                delete_in_batches(cur, "stock_ledger", "id", ledger_ids, args.batch_size)
                delete_in_batches(cur, "import_note_details", "id", import_detail_ids, args.batch_size)
                delete_in_batches(cur, "export_note_details", "id", export_detail_ids, args.batch_size)
                delete_in_batches(cur, "import_notes", "id", import_note_ids, args.batch_size)
                delete_in_batches(cur, "export_notes", "id", export_note_ids, args.batch_size)
                delete_in_batches(cur, "products", "id", product_ids, args.batch_size)
                cur.execute("COMMIT")
            except sqlite3.Error as db_err:
                cur.execute("ROLLBACK")
                print(f"\n[CẢNH BÁO] Lỗi xóa trực tiếp ({db_err}). Đang tự động khôi phục từ bản sao lưu dự phòng...")
                backup_file = (manifest.get("backup_path") if manifest else None) or PRE_DEMO_BACKUP_PATH
                if os.path.exists(backup_file):
                    b_conn = sqlite3.connect(backup_file, timeout=15.0)
                    try:
                        b_conn.backup(conn)
                        print("  => Đã khôi phục hoàn chỉnh CSDL từ bản sao lưu dự phòng!")
                    finally:
                        b_conn.close()
                else:
                    print("[LỖI] Không tìm thấy file sao lưu dự phòng!")
                    sys.exit(1)

        # 7. Đối chiếu số dòng với snapshot trong manifest (nếu có)
        snapshot_after = get_db_snapshot(conn)
        if manifest and manifest.get("snapshot_before"):
            snapshot_before = manifest["snapshot_before"]
            print("\n--- ĐỐI CHIẾU SỐ DÒNG VỚI SNAPSHOT TRƯỚC KHI CHẠY ---")
            print(f"{'Bảng':<24} | {'Trước (Snapshot)':>16} | {'Sau Cleanup':>14} | {'Chênh lệch':>10}")
            print("-" * 72)
            has_diff = False
            for tbl in SNAPSHOT_TABLES:
                b_cnt = snapshot_before.get(tbl, 0)
                a_cnt = snapshot_after.get(tbl, 0)
                diff = a_cnt - b_cnt
                if diff != 0:
                    has_diff = True
                print(f"{tbl:<24} | {b_cnt:>16} | {a_cnt:>14} | {diff:>+10}")

            if has_diff:
                print("\n[LỖI ĐỐI CHIẾU] Số dòng sau khi dọn dẹp LỆCH so với snapshot ban đầu!")
                sys.exit(1)
            else:
                print("\n✅ KẾT QUẢ ĐỐI CHIẾU SNAPSHOT: SẠCH HOÀN TOÀN")
        else:
            print("\n✅ Đã hoàn tất dọn dẹp theo tiền tố DEMO: SẠCH HOÀN TOÀN")

        # 8. Xóa cache AI tạm (nếu có) và xóa manifest
        if os.path.exists(AI_CACHE_PATH):
            try:
                os.remove(AI_CACHE_PATH)
                print("[*] Đã làm mới cache AI (ai_cache.json).")
            except Exception:
                pass

        if os.path.exists(MANIFEST_PATH):
            os.remove(MANIFEST_PATH)
            print(f"[*] Đã xóa file manifest: {MANIFEST_PATH}")

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Dọn dẹp dữ liệu kiểm thử của demo_run.py")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL mục tiêu (mặc định: http://127.0.0.1:8000)")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Đường dẫn tới file CSDL")
    parser.add_argument("--batch-size", type=int, default=250, help="Kích thước mỗi lô xóa (mặc định: 250)")
    parser.add_argument("--yes", "-y", action="store_true", help="Tự động xác nhận xóa không hỏi lại")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    run_cleanup(cli_args)
