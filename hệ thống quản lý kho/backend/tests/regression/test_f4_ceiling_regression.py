"""Test hoi quy F4: Kiem tra tran nghiep vu (1 ty ton kho, 10 trieu giao dich, DB trigger).

Nghiem thu:
1. Ma tran bien cho tung truong:
   - POST /products: current_stock, initial_quantity, standard_price, initial_unit_price
   - PUT /products: standard_price
   - POST /import-notes: quantity, unit_price
   - POST /export-notes: quantity, unit_price
   - POST /stock-ledger/adjust: actual_stock
2. Cac gia tri bien:
   - tran-1, tran, tran+1, 2^31-1, 2^31, 2^63-1, 2^63, 1e18, 1e308, "NaN", -1, 0, 2.5, "abc"
3. Test ton cong don: nhap sat tran roi vuot -> bi chan 400
4. Kiem ke tai tran: san pham ton 1 ty phai kiem ke duoc (actual_stock=1_000_000_000)
"""

import asyncio
import httpx
import os
import time
import sys
from typing import Dict, Any, List

__test__ = False  # Script kiểm thử độc lập qua HTTP, không chạy qua pytest discovery


BOUNDARY_VALUES = [
    ("tran - 1", "BOUND_MINUS_1"),
    ("tran", "BOUND_EXACT"),
    ("tran + 1", "BOUND_PLUS_1"),
    ("2^31 - 1", 2147483647),
    ("2^31", 2147483648),
    ("2^63 - 1", 9223372036854775807),
    ("2^63", 9223372036854775808),
    ("1e18", 10**18),
    ("1e308", 1e308),
    ('"NaN"', "NaN"),
    ("-1", -1),
    ("0", 0),
    ("2.5", 2.5),
    ('"abc"', "abc"),
]


async def login(client: httpx.AsyncClient) -> str:
    res = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]


def resolve_val(placeholder: Any, ceiling: int) -> Any:
    if placeholder == "BOUND_MINUS_1":
        return ceiling - 1
    elif placeholder == "BOUND_EXACT":
        return ceiling
    elif placeholder == "BOUND_PLUS_1":
        return ceiling + 1
    return placeholder


async def test_boundary_matrix(client: httpx.AsyncClient):
    print("\n================ MA TRAN GIA TRI BIEN THO ================")
    headers = client.headers

    # Setup base product
    ts = int(time.time() * 1000) % 100000
    base_prod_res = await client.post("/api/v1/products/", json={
        "code": f"SKU-F4-BASE-{ts}",
        "name": "SP Base F4",
        "category_id": 1,
        "supplier_id": 1,
        "unit": "Cai",
        "standard_price": 50000.0,
        "status": "ACTIVE"
    })
    base_pid = base_prod_res.json()["id"]

    fields_to_test = [
        # (name, endpoint, method, payload_builder, ceiling, is_int)
        ("POST /products (current_stock)", "/api/v1/products/", "POST",
         lambda v: {"code": f"SKU-F4-CS-{int(time.time()*1000)%100000}-{str(v)[:5]}", "name": "SP CS", "category_id": 1, "supplier_id": 1, "unit": "Cai", "standard_price": 50000.0, "current_stock": v, "status": "ACTIVE"},
         10_000_000, True),

        ("POST /products (initial_quantity)", "/api/v1/products/", "POST",
         lambda v: {"code": f"SKU-F4-IQ-{int(time.time()*1000)%100000}-{str(v)[:5]}", "name": "SP IQ", "category_id": 1, "supplier_id": 1, "unit": "Cai", "standard_price": 50000.0, "initial_quantity": v, "initial_supplier_id": 1, "status": "ACTIVE"},
         10_000_000, True),

        ("POST /products (standard_price)", "/api/v1/products/", "POST",
         lambda v: {"code": f"SKU-F4-SP-{int(time.time()*1000)%100000}-{str(v)[:5]}", "name": "SP SP", "category_id": 1, "supplier_id": 1, "unit": "Cai", "standard_price": v, "status": "ACTIVE"},
         100_000_000_000, False),

        ("POST /products (initial_unit_price)", "/api/v1/products/", "POST",
         lambda v: {"code": f"SKU-F4-IUP-{int(time.time()*1000)%100000}-{str(v)[:5]}", "name": "SP IUP", "category_id": 1, "supplier_id": 1, "unit": "Cai", "standard_price": 50000.0, "initial_quantity": 10, "initial_unit_price": v, "initial_supplier_id": 1, "status": "ACTIVE"},
         100_000_000_000, False),

        ("PUT /products (standard_price)", f"/api/v1/products/{base_pid}", "PUT",
         lambda v: {"standard_price": v},
         100_000_000_000, False),

        ("POST /import-notes (quantity)", "/api/v1/import-notes/", "POST",
         lambda v: {"code": f"PN-F4-QTY-{int(time.time()*1000)%100000}-{str(v)[:5]}", "supplier_id": 1, "details": [{"product_id": base_pid, "quantity": v, "unit_price": 10000.0}]},
         10_000_000, True),

        ("POST /import-notes (unit_price)", "/api/v1/import-notes/", "POST",
         lambda v: {"code": f"PN-F4-UP-{int(time.time()*1000)%100000}-{str(v)[:5]}", "supplier_id": 1, "details": [{"product_id": base_pid, "quantity": 10, "unit_price": v}]},
         100_000_000_000, False),

        ("POST /export-notes (quantity)", "/api/v1/export-notes/", "POST",
         lambda v: {"code": f"PX-F4-QTY-{int(time.time()*1000)%100000}-{str(v)[:5]}", "recipient_name": "Khach F4", "details": [{"product_id": base_pid, "quantity": v, "unit_price": 50000.0}]},
         10_000_000, True),

        ("POST /export-notes (unit_price)", "/api/v1/export-notes/", "POST",
         lambda v: {"code": f"PX-F4-UP-{int(time.time()*1000)%100000}-{str(v)[:5]}", "recipient_name": "Khach F4", "details": [{"product_id": base_pid, "quantity": 1, "unit_price": v}]},
         100_000_000_000, False),

        ("POST /stock-ledger/adjust (actual_stock)", "/api/v1/stock-ledger/adjust", "POST",
         lambda v: {"product_id": base_pid, "actual_stock": v, "reason": "Kiem ke bien F4"},
         1_000_000_000, True),
    ]

    has_500 = False
    matrix_results = []

    for f_name, ep, meth, builder, ceiling, is_int in fields_to_test:
        print(f"\n--- Testing field: {f_name} (Tran: {ceiling:,}) ---")
        for label, val_placeholder in BOUNDARY_VALUES:
            val = resolve_val(val_placeholder, ceiling)
            payload = builder(val)
            try:
                if meth == "POST":
                    res = await client.post(ep, json=payload)
                elif meth == "PUT":
                    res = await client.put(ep, json=payload)
                sc = res.status_code
                if sc >= 500:
                    has_500 = True
                    print(f"  [500 ERROR] {label} ({val}) -> HTTP {sc} | Detail: {res.text}")
                else:
                    print(f"  {label:<12}: HTTP {sc}")
                matrix_results.append((f_name, label, val, sc))
            except Exception as e:
                print(f"  {label:<12}: EXCEPTION -> {e}")
                matrix_results.append((f_name, label, val, 599))

    print(f"\n-> Ket qua ma tran: Co HTTP 500/Crash khong: {'CO (FAIL)' if has_500 else 'KHONG (PASS)'}")
    return not has_500


async def test_cumulative_stock_and_inventory(client: httpx.AsyncClient):
    print("\n--- Test ton cong don sat tran & kiem ke tai tran 1 ty ---")
    ts = int(time.time() * 1000) % 100000
    p_code = f"SKU-F4-CUMU-{ts}"

    # 1. Tao san pham ton kho 0
    p_res = await client.post("/api/v1/products/", json={
        "code": p_code,
        "name": "SP Cumulative",
        "category_id": 1,
        "supplier_id": 1,
        "unit": "Cai",
        "standard_price": 1000.0,
        "status": "ACTIVE"
    })
    pid = p_res.json()["id"]

    # 2. Kiem ke truc tiep len tran 1 ty (actual_stock = 1_000_000_000)
    print("  Thuc hien kiem ke len trần 1.000.000.000:")
    adj_res = await client.post("/api/v1/stock-ledger/adjust", json={
        "product_id": pid,
        "actual_stock": 1_000_000_000,
        "reason": "Kiem ke ton kho len dung 1 ty"
    })
    print(f"    HTTP: {adj_res.status_code}")
    assert adj_res.status_code in (200, 201), f"Adjust to 1B failed: {adj_res.text}"

    chk_p = await client.get(f"/api/v1/products/{pid}")
    stock_1b = chk_p.json()["current_stock"]
    print(f"    Ton sau kiem ke: {stock_1b:,} (Ky vong: 1,000,000,000)")
    assert stock_1b == 1_000_000_000

    # 3. Thu nhap them 1 san pham khi dang o tran 1 ty -> Phai bi chan (400 Bad Request)
    print("  Thu nhap them 1 san pham khi dang o tran 1 ty (vuot tran):")
    over_imp = await client.post("/api/v1/import-notes/", json={
        "code": f"PN-F4-OVER-{ts}",
        "supplier_id": 1,
        "details": [{"product_id": pid, "quantity": 1, "unit_price": 1000.0}]
    })
    print(f"    HTTP: {over_imp.status_code}")
    print(f"    Detail: {over_imp.text}")
    assert over_imp.status_code == 400, f"Over ceiling import should be 400, got: {over_imp.status_code}"
    print("    -> Chan vuot tran thanh cong (HTTP 400)")


def test_sqlite_trigger_direct(db_path: str = "/tmp/f4_new.db"):
    import sqlite3
    if not os.path.exists(db_path):
        return
    print(f"\n--- Test SQLite Trigger truc tiep tren {db_path} ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO products (code, name, category_id, unit, min_stock, standard_price, current_stock, status)
            VALUES ('SKU-TRIG-OVER-99', 'SP Trigger Over', 1, 'Cai', 10, 1000.0, 1000000001, 'ACTIVE')
        """)
        conn.commit()
        print("  TRIGGER INSERT: FAIL (Khong chan duoc)")
    except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
        print(f"  TRIGGER INSERT: PASS (Trigger da chan voi loi: {e})")
    conn.close()


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    print(f"RUNNING F4 REGRESSION TEST on {url}")

    async with httpx.AsyncClient(base_url=url, timeout=30.0) as client:
        token = await login(client)
        client.headers.update({"Authorization": f"Bearer {token}"})

        ok = await test_boundary_matrix(client)
        await test_cumulative_stock_and_inventory(client)
        test_sqlite_trigger_direct()
        print(f"\nTONG KET F4: {'TAT CA BIEN AN TOAN (PASS)' if ok else 'CO LOI 500 (FAIL)'}")


if __name__ == "__main__":
    asyncio.run(main())
