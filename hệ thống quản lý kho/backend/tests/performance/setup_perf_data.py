"""Script khởi tạo và reset dữ liệu kiểm thử hiệu năng (20 users và các SKU-PERF-*)."""

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
            ["docker", "exec", "-e", "INSIDE_DOCKER=1", "warehouse_backend", "python", "/app/tests/performance/setup_perf_data.py"],
            check=False
        )
        sys.exit(res.returncode)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.user import User

PERF_PASSWORD = "Perf@123"

PERF_USERS = [
    # Nhóm 1: Bình thường (10 users)
    {"username": "perf_admin_01", "role": "ADMIN", "full_name": "Perf Admin 01 (USR-01)"},
    {"username": "perf_admin_02", "role": "ADMIN", "full_name": "Perf Admin 02 (USR-02)"},
    {"username": "perf_acct_01", "role": "ACCOUNTANT", "full_name": "Perf Kế toán 01 (USR-03)"},
    {"username": "perf_acct_02", "role": "ACCOUNTANT", "full_name": "Perf Kế toán 02 (USR-04)"},
    {"username": "perf_acct_03", "role": "ACCOUNTANT", "full_name": "Perf Kế toán 03 (USR-05)"},
    {"username": "perf_wh_01", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 01 (USR-06)"},
    {"username": "perf_wh_02", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 02 (USR-07)"},
    {"username": "perf_wh_03", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 03 (USR-08)"},
    {"username": "perf_wh_04", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 04 (USR-09)"},
    {"username": "perf_wh_05", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 05 (USR-10)"},

    # Nhóm 2: Hoạt động mạnh (5 users)
    {"username": "perf_wh_06", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 06 (USR-11)"},
    {"username": "perf_wh_07", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 07 (USR-12)"},
    {"username": "perf_wh_08", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 08 (USR-13)"},
    {"username": "perf_acct_04", "role": "ACCOUNTANT", "full_name": "Perf Kế toán 04 (USR-14)"},
    {"username": "perf_admin_03", "role": "ADMIN", "full_name": "Perf Admin 03 (USR-15)"},

    # Nhóm 3: Gây áp lực dồn điểm (3 users)
    {"username": "perf_wh_09", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 09 (USR-16)"},
    {"username": "perf_wh_10", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 10 (USR-17)"},
    {"username": "perf_admin_04", "role": "ADMIN", "full_name": "Perf Admin 04 (USR-18)"},

    # Nhóm 4: Dữ liệu xấu & Replay (2 users)
    {"username": "perf_wh_11", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 11 (USR-19)"},
    {"username": "perf_wh_12", "role": "WAREHOUSE_KEEPER", "full_name": "Perf Thủ kho 12 (USR-20)"},
]

PERF_PRODUCTS = [
    {
        "code": "SKU-PERF-RACE",
        "name": "Mặt hàng kiểm thử Race Condition (Tồn kho = 1)",
        "unit": "Cái",
        "min_stock": 5,
        "current_stock": 1,
        "standard_price": 500000.0,
    },
    {
        "code": "SKU-PERF-BULK-01",
        "name": "Mặt hàng kiểm thử Tải lớn 01 (USR-11, 12, 13, 20)",
        "unit": "Cái",
        "min_stock": 100,
        "current_stock": 20000,
        "standard_price": 100000.0,
    },
    {
        "code": "SKU-PERF-BULK-02",
        "name": "Mặt hàng kiểm thử Tải lớn 02 (USR-15, 16, 17)",
        "unit": "Cái",
        "min_stock": 100,
        "current_stock": 20000,
        "standard_price": 150000.0,
    },
    {
        "code": "SKU-PERF-FLOW",
        "name": "Mặt hàng kiểm thử Luồng chéo (USR-14, 18)",
        "unit": "Cái",
        "min_stock": 50,
        "current_stock": 10000,
        "standard_price": 200000.0,
    },
    {
        "code": "SKU-PERF-BAD",
        "name": "Mặt hàng kiểm thử Dữ liệu xấu (USR-19)",
        "unit": "Cái",
        "min_stock": 10,
        "current_stock": 100,
        "standard_price": 50000.0,
    },
]


def setup_perf_data():
    db = SessionLocal()
    try:
        print("[SETUP] Bắt đầu thiết lập dữ liệu kiểm thử hiệu năng...")

        # 1. Tạo Category và Supplier kiểm thử nếu chưa có
        cat = db.query(Category).filter(Category.code == "CAT-PERF").first()
        if not cat:
            cat = Category(code="CAT-PERF", name="Danh mục Kiểm thử Hiệu năng")
            db.add(cat)
            db.flush()
            print(f"  + Đã tạo danh mục: {cat.name} (ID: {cat.id})")

        sup = db.query(Supplier).filter(Supplier.code == "SUP-PERF").first()
        if not sup:
            sup = Supplier(
                code="SUP-PERF",
                name="Nhà cung ứng Kiểm thử Hiệu năng",
                phone="0988889999",
                email="perf@test.local",
                address="Khu thực nghiệm ảo",
                is_active=True,
            )
            db.add(sup)
            db.flush()
            print(f"  + Đã tạo nhà cung cấp: {sup.name} (ID: {sup.id})")

        # 2. Tạo 20 tài khoản test
        pw_hash = get_password_hash(PERF_PASSWORD)
        user_created_count = 0
        for u in PERF_USERS:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if not existing:
                new_u = User(
                    username=u["username"],
                    password_hash=pw_hash,
                    full_name=u["full_name"],
                    role=u["role"],
                    is_active=True,
                )
                db.add(new_u)
                user_created_count += 1
            else:
                existing.password_hash = pw_hash
                existing.is_active = True
                existing.role = u["role"]
        db.commit()
        print(f"  + Đã đồng bộ 20 tài khoản test (Tạo mới: {user_created_count}, Cập nhật: {20 - user_created_count})")

        # 3. Tạo 5 SKU-PERF-*
        prod_created_count = 0
        for p in PERF_PRODUCTS:
            prod = db.query(Product).filter(Product.code == p["code"]).first()
            if not prod:
                new_prod = Product(
                    code=p["code"],
                    name=p["name"],
                    category_id=cat.id,
                    unit=p["unit"],
                    min_stock=p["min_stock"],
                    current_stock=p["current_stock"],
                    standard_price=p["standard_price"],
                    status="ACTIVE",
                )
                db.add(new_prod)
                prod_created_count += 1
            else:
                prod.name = p["name"]
                prod.current_stock = p["current_stock"]
                prod.standard_price = p["standard_price"]
                prod.status = "ACTIVE"
        db.commit()
        print(f"  + Đã đồng bộ 5 SKU test (Tạo mới: {prod_created_count}, Reset: {5 - prod_created_count})")

        # In danh sách ID sản phẩm để script test tiện map
        products = db.query(Product).filter(Product.code.like("SKU-PERF-%")).all()
        mapping = {p.code: p.id for p in products}
        print(f"[SETUP HOÀN TẤT] Mapping SKU -> ID: {mapping}")
        return mapping

    except Exception as e:
        db.rollback()
        print(f"[LỖI SETUP] {e}")
        raise
    finally:
        db.close()


def reset_race_stock():
    """Reset riêng tồn kho SKU-PERF-RACE về đúng 1 trước mỗi đợt chạy Race Condition."""
    db = SessionLocal()
    try:
        race_prod = db.query(Product).filter(Product.code == "SKU-PERF-RACE").first()
        if race_prod:
            race_prod.current_stock = 1
            db.commit()
            print(f"[RESET] SKU-PERF-RACE (ID: {race_prod.id}) đã được reset về tồn kho: 1")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset_race":
        reset_race_stock()
    else:
        setup_perf_data()
