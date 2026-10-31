"""Script dọn dẹp sạch sẽ toàn bộ dữ liệu kiểm thử hiệu năng (prefix PERF-, perf_, SKU-PERF-)."""

import os
import subprocess
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Nếu chạy trên Windows Host trong khi container warehouse_backend đang mở WAL,
# tự động ủy quyền vào trong container để tránh xung đột SQLite WAL shared-memory.
if os.name == "nt" and not os.environ.get("INSIDE_DOCKER"):
    chk = subprocess.run(
        ["docker", "ps", "--filter", "name=warehouse_backend", "--filter", "status=running", "-q"],
        capture_output=True, text=True, check=False
    )
    if chk.returncode == 0 and chk.stdout.strip():
        res = subprocess.run(
            ["docker", "exec", "-e", "INSIDE_DOCKER=1", "warehouse_backend", "python", "/app/tests/performance/teardown_perf_data.py"],
            check=False
        )
        sys.exit(res.returncode)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.user import User


def teardown_perf_data():
    db = SessionLocal()
    try:
        print("[TEARDOWN] Bắt đầu dọn dẹp dữ liệu kiểm thử hiệu năng...")

        # 1. Xóa chi tiết và phiếu xuất do user test tạo hoặc chứa sản phẩm test
        res_exp_dt = db.execute(text("""
            DELETE FROM export_note_details 
            WHERE export_note_id IN (
                SELECT id FROM export_notes 
                WHERE code LIKE 'PERF-%' 
                   OR code LIKE 'PX-GROUPA-%'
                   OR created_by IN (SELECT id FROM users WHERE username LIKE 'perf_%')
            )
            OR product_id IN (SELECT id FROM products WHERE code LIKE 'SKU-PERF-%')
        """))
        res_exp = db.execute(text("""
            DELETE FROM export_notes 
            WHERE code LIKE 'PERF-%' 
               OR code LIKE 'PX-GROUPA-%'
               OR created_by IN (SELECT id FROM users WHERE username LIKE 'perf_%')
        """))
        print(f"  - Đã xóa {res_exp.rowcount} phiếu xuất test và {res_exp_dt.rowcount} chi tiết.")

        # 2. Xóa chi tiết và phiếu nhập do user test tạo hoặc chứa sản phẩm test
        res_imp_dt = db.execute(text("""
            DELETE FROM import_note_details 
            WHERE import_note_id IN (
                SELECT id FROM import_notes 
                WHERE code LIKE 'PERF-%' 
                   OR created_by IN (SELECT id FROM users WHERE username LIKE 'perf_%')
            )
            OR product_id IN (SELECT id FROM products WHERE code LIKE 'SKU-PERF-%')
        """))
        res_imp = db.execute(text("""
            DELETE FROM import_notes 
            WHERE code LIKE 'PERF-%' 
               OR created_by IN (SELECT id FROM users WHERE username LIKE 'perf_%')
        """))
        print(f"  - Đã xóa {res_imp.rowcount} phiếu nhập test và {res_imp_dt.rowcount} chi tiết.")

        # 3. Xóa sổ cái thẻ kho liên quan đến SKU-PERF-* hoặc do user test tạo
        res_ledg = db.execute(text("""
            DELETE FROM stock_ledger 
            WHERE reference_code LIKE 'PERF-%'
               OR reference_code LIKE 'CANCEL-PERF-%'
               OR reference_code LIKE 'PX-GROUPA-%'
               OR reference_code LIKE 'INIT-SKU-PERF-%'
               OR product_id IN (SELECT id FROM products WHERE code LIKE 'SKU-PERF-%')
               OR created_by IN (SELECT id FROM users WHERE username LIKE 'perf_%')
        """))
        print(f"  - Đã xóa {res_ledg.rowcount} bản ghi thẻ kho test.")

        # 4. Xóa sản phẩm SKU-PERF-*
        res_prod = db.execute(text("DELETE FROM products WHERE code LIKE 'SKU-PERF-%'"))
        print(f"  - Đã xóa {res_prod.rowcount} sản phẩm test.")

        # 5. Xóa danh mục và nhà cung cấp test
        res_cat = db.execute(text("DELETE FROM categories WHERE code = 'CAT-PERF'"))
        res_sup = db.execute(text("DELETE FROM suppliers WHERE code = 'SUP-PERF'"))
        print(f"  - Đã xóa danh mục và NCC test: {res_cat.rowcount} cat, {res_sup.rowcount} sup.")

        # 6. Xóa 20 tài khoản test perf_*
        res_usr = db.execute(text("DELETE FROM users WHERE username LIKE 'perf_%'"))
        print(f"  - Đã xóa {res_usr.rowcount} tài khoản test.")

        db.commit()

        # 7. Checkpoint WAL và VACUUM
        db.execute(text("PRAGMA wal_checkpoint(TRUNCATE);"))
        print("  - Đã thực thi PRAGMA wal_checkpoint(TRUNCATE).")

        print("[TEARDOWN HOÀN TẤT] Hệ thống đã được dọn sạch về trạng thái ban đầu!")

    except Exception as e:
        db.rollback()
        print(f"[LỖI TEARDOWN] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    teardown_perf_data()
