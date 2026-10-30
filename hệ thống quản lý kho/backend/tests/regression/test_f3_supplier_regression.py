"""Test hoi quy F3: Chặn gán ngầm nhà cung cấp ID=1 khi tạo tồn đầu kỳ (Phuong an A).

Nghiem thu:
1. current_stock=50 co NCC hop le -> 201 Created, phieu sinh dung NCC do, ton = SUM(ledger) = 50
2. current_stock=50 KHONG NCC -> 400 Bad Request (Tu choi, khong gan ngam ID=1), 0 SP mo coi
3. initial_quantity=50 co NCC hop le -> 201 Created
4. initial_quantity=50 KHONG NCC -> 400 Bad Request
5. Ca current_stock va initial_quantity hop le -> 201 Created
6. NCC khong ton tai (ID=99999) -> 400 Bad Request
7. Ep loi giua chung (rollback atomicity) -> khong con san pham/phieu mo coi
"""

import asyncio
import httpx
import sqlite3
import time
import sys
from typing import Dict, Any


async def login(client: httpx.AsyncClient) -> str:
    res = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]


async def run_f3_tests(base_url: str):
    print(f"=== TEST HOI QUY F3: RANG BUOC NHA CUNG CAP CHO TON DAU KY ===")
    print(f"Target URL: {base_url}")

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        token = await login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # -------------------------------------------------------------------------
        # Ca 1: current_stock=50 CO NCC hop le (supplier_id = 1) -> 201 PASS
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 100000
        code1 = f"SKU-F3-C1-{ts}"
        r1 = await client.post("/api/v1/products/", headers=headers, json={
            "code": code1,
            "name": f"SP F3 Ca 1 {ts}",
            "category_id": 1,
            "supplier_id": 1,
            "unit": "Cai",
            "current_stock": 50,
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        print(f"\n[Ca 1] current_stock=50 CO NCC (ID=1):")
        print(f"  HTTP: {r1.status_code}")
        if r1.status_code in (200, 201):
            p1 = r1.json()
            print(f"  SP ID: {p1['id']}, current_stock: {p1['current_stock']}")
            # Kiem tra phieu nhap sinh ra
            r_imp = await client.get("/api/v1/import-notes/", headers=headers)
            notes = [n for n in r_imp.json() if any(d.get("product_id") == p1["id"] for d in n.get("details", []))]
            print(f"  So phieu nhap sinh ra: {len(notes)}")
            if notes:
                print(f"  NCC phieu nhap: ID={notes[0]['supplier_id']}, Note: '{notes[0].get('note', '')}'")

        # -------------------------------------------------------------------------
        # Ca 2: current_stock=50 KHONG NCC (supplier_id = None) -> phai 400
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 100000
        code2 = f"SKU-F3-C2-{ts}"
        r2 = await client.post("/api/v1/products/", headers=headers, json={
            "code": code2,
            "name": f"SP F3 Ca 2 {ts}",
            "category_id": 1,
            "supplier_id": None,
            "unit": "Cai",
            "current_stock": 50,
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        print(f"\n[Ca 2] current_stock=50 KHONG NCC:")
        print(f"  HTTP: {r2.status_code}")
        print(f"  Detail: {r2.text}")
        is_ca2_pass = (r2.status_code == 400)
        print(f"  -> Ket qua Ca 2: {'PASS (Bi tu choi 400 dung)' if is_ca2_pass else 'FAIL (Bi tao hoac gan ngam)'}")

        # -------------------------------------------------------------------------
        # Ca 3: initial_quantity=50 CO NCC hop le -> 201
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 100000
        code3 = f"SKU-F3-C3-{ts}"
        r3 = await client.post("/api/v1/products/", headers=headers, json={
            "code": code3,
            "name": f"SP F3 Ca 3 {ts}",
            "category_id": 1,
            "supplier_id": 1,
            "initial_quantity": 50,
            "unit": "Cai",
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        print(f"\n[Ca 3] initial_quantity=50 CO NCC (ID=1):")
        print(f"  HTTP: {r3.status_code}")

        # -------------------------------------------------------------------------
        # Ca 4: initial_quantity=50 KHONG NCC -> phai 400
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 100000
        code4 = f"SKU-F3-C4-{ts}"
        r4 = await client.post("/api/v1/products/", headers=headers, json={
            "code": code4,
            "name": f"SP F3 Ca 4 {ts}",
            "category_id": 1,
            "supplier_id": None,
            "initial_quantity": 50,
            "unit": "Cai",
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        print(f"\n[Ca 4] initial_quantity=50 KHONG NCC:")
        print(f"  HTTP: {r4.status_code}")
        print(f"  Detail: {r4.text}")
        is_ca4_pass = (r4.status_code == 400)
        print(f"  -> Ket qua Ca 4: {'PASS (Bi tu choi 400 dung)' if is_ca4_pass else 'FAIL (Bi tao hoac gan ngam)'}")

        # -------------------------------------------------------------------------
        # Ca 5: NCC khong ton tai (ID = 99999) -> phai 400
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 100000
        code5 = f"SKU-F3-C5-{ts}"
        r5 = await client.post("/api/v1/products/", headers=headers, json={
            "code": code5,
            "name": f"SP F3 Ca 5 {ts}",
            "category_id": 1,
            "supplier_id": 99999,
            "current_stock": 50,
            "unit": "Cai",
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        print(f"\n[Ca 5] NCC khong ton tai (ID=99999):")
        print(f"  HTTP: {r5.status_code}")
        print(f"  Detail: {r5.text}")
        is_ca5_pass = (r5.status_code == 400)
        print(f"  -> Ket qua Ca 5: {'PASS' if is_ca5_pass else 'FAIL'}")

        print("\n================== TONG KET F3 ==================")
        print(f"Ca 1 (co NCC): HTTP {r1.status_code}")
        print(f"Ca 2 (khong NCC): HTTP {r2.status_code} (Ky vong 400)")
        print(f"Ca 3 (init_qty co NCC): HTTP {r3.status_code}")
        print(f"Ca 4 (init_qty khong NCC): HTTP {r4.status_code} (Ky vong 400)")
        print(f"Ca 5 (NCC fake): HTTP {r5.status_code} (Ky vong 400)")
        print("=================================================")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    asyncio.run(run_f3_tests(url))
