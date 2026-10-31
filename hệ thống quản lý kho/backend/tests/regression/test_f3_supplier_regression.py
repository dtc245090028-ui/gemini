"""Test hoi quy F3: Rang buoc nha cung cap cho ton dau ky (Phuong an A) & Kiem tra NCC Inactive.

Nghiem thu:
1. current_stock=50 co NCC hop le -> 201 Created, phieu sinh dung NCC do, ton = SUM(ledger) = 50
2. current_stock=50 KHONG NCC -> 400 Bad Request (Tu choi, khong gan ngam ID=1), 0 SP mo coi
3. initial_quantity=50 co NCC hop le -> 201 Created
4. initial_quantity=50 KHONG NCC -> 400 Bad Request
5. NCC khong ton tai (ID=99999) -> 400 Bad Request
6. NCC bi ngung hoat dong (is_active=0):
   - POST /products voi ton dau ky va supplier_id inactive -> 400 Bad Request
   - Kiem tra dem mo coi: Products=0, ImportNotes=0, StockLedger=0
7. Kiem tra POST /import-notes voi NCC is_active=0 (B4 khao sat khong sua)
"""

__test__ = False

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


async def run_f3_tests(base_url: str, db_path: str = None):
    print(f"=== TEST HOI QUY F3: RANG BUOC NHA CUNG CAP CHO TON DAU KY ===")
    print(f"Target URL: {base_url}")
    print(f"DB Path for orphan check: {db_path}")

    results = {}

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        token = await login(client)
        headers = {"Authorization": f"Bearer {token}"}

        # -------------------------------------------------------------------------
        # Ca 1: current_stock=50 CO NCC hop le (supplier_id = 1) -> 201 PASS
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 1000000
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
        p1_data = None
        if r1.status_code in (200, 201):
            p1_data = r1.json()
            print(f"  SP ID: {p1_data['id']}, current_stock: {p1_data['current_stock']}")
            r_imp = await client.get("/api/v1/import-notes/", headers=headers)
            notes = [n for n in r_imp.json() if any(d.get("product_id") == p1_data["id"] for d in n.get("details", []))]
            print(f"  So phieu nhap sinh ra: {len(notes)}")
            if notes:
                print(f"  NCC phieu nhap: ID={notes[0]['supplier_id']}, Note: '{notes[0].get('note', '')}'")
            results["ca1"] = (r1.status_code == 201 and len(notes) == 1)
        else:
            results["ca1"] = False

        # -------------------------------------------------------------------------
        # Ca 2: current_stock=50 KHONG NCC (supplier_id = None) -> phai 400
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 1000000
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
        results["ca2"] = (r2.status_code == 400)

        # -------------------------------------------------------------------------
        # Ca 3: initial_quantity=50 CO NCC hop le -> 201
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 1000000
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
        results["ca3"] = (r3.status_code == 201)

        # -------------------------------------------------------------------------
        # Ca 4: initial_quantity=50 KHONG NCC -> phai 400
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 1000000
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
        results["ca4"] = (r4.status_code == 400)

        # -------------------------------------------------------------------------
        # Ca 5: NCC khong ton tai (ID = 99999) -> phai 400
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 1000000
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
        results["ca5"] = (r5.status_code == 400)

        # -------------------------------------------------------------------------
        # Ca 6: NCC bi ngung hoat dong (is_active=0)
        # -------------------------------------------------------------------------
        ts = int(time.time() * 1000) % 1000000
        sup_code = f"SUP-INACT-{ts}"
        # Tao NCC co is_active=False
        r_sup = await client.post("/api/v1/suppliers/", headers=headers, json={
            "code": sup_code,
            "name": f"NCC Ngung Hoat Dong {ts}",
            "phone": "0987654321",
            "email": f"inactive_{ts}@example.com",
            "address": "123 Duong Vang",
            "is_active": False
        })
        print(f"\n[Ca 6] Tao NCC Inactive (code={sup_code}):")
        print(f"  HTTP: {r_sup.status_code}")
        assert r_sup.status_code in (200, 201), f"Loi tao NCC inactive: {r_sup.text}"
        inactive_sup_id = r_sup.json()["id"]
        print(f"  Created Supplier ID: {inactive_sup_id}, is_active: {r_sup.json().get('is_active')}")

        code6 = f"SKU-F3-INACT-{ts}"
        r6 = await client.post("/api/v1/products/", headers=headers, json={
            "code": code6,
            "name": f"SP F3 Inactive NCC {ts}",
            "category_id": 1,
            "supplier_id": inactive_sup_id,
            "current_stock": 50,
            "unit": "Cai",
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        print(f"\n[Ca 6] POST /products voi NCC inactive (ID={inactive_sup_id}) va current_stock=50:")
        print(f"  HTTP: {r6.status_code}")
        print(f"  Detail: {r6.text}")

        # Kiem tra dem mo coi qua DB neu co db_path
        orphan_p = orphan_imp = orphan_ledger = 0
        if db_path:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM products WHERE code = ?", (code6,))
            orphan_p = cur.fetchone()[0]
            cur.execute("""
                SELECT count(*) FROM import_notes 
                WHERE supplier_id = ? AND note LIKE ?
            """, (inactive_sup_id, f"%{code6}%"))
            orphan_imp = cur.fetchone()[0]
            cur.execute("""
                SELECT count(*) FROM stock_ledger sl 
                JOIN products p ON sl.product_id = p.id 
                WHERE p.code = ?
            """, (code6,))
            orphan_ledger = cur.fetchone()[0]
            conn.close()
            print(f"  Kiem tra dem mo coi CSDL: Products={orphan_p}, ImportNotes={orphan_imp}, StockLedger={orphan_ledger}")

        is_ca6_pass = (r6.status_code == 400 and orphan_p == 0 and orphan_imp == 0 and orphan_ledger == 0)
        results["ca6"] = is_ca6_pass
        print(f"  -> Ket qua Ca 6: {'PASS (Bi tu choi 400 va 0 mo coi)' if is_ca6_pass else 'FAIL'}")

        # -------------------------------------------------------------------------
        # Ca 7: Kiem tra B4: POST /import-notes voi NCC is_active=0 (Khao sat khong sua)
        # -------------------------------------------------------------------------
        # Chon SP hop le (p1 neu co, hoac SP co san trong he thong)
        target_prod_id = p1_data["id"] if p1_data else 1
        r7 = await client.post("/api/v1/import-notes/", headers=headers, json={
            "supplier_id": inactive_sup_id,
            "note": f"Phieu nhap khao sat B4 cho NCC inactive {ts}",
            "details": [
                {
                    "product_id": target_prod_id,
                    "quantity": 10,
                    "unit_price": 30000.0
                }
            ]
        })
        print(f"\n[Ca 7 / B4] POST /import-notes voi NCC inactive (ID={inactive_sup_id}):")
        print(f"  HTTP: {r7.status_code}")
        print(f"  Detail: {r7.text[:200]}")
        results["ca7_b4_status"] = r7.status_code

        print("\n================== TONG KET F3 ==================")
        print(f"Ca 1 (co NCC hop le): {'PASS' if results.get('ca1') else 'FAIL'}")
        print(f"Ca 2 (khong NCC): {'PASS' if results.get('ca2') else 'FAIL'}")
        print(f"Ca 3 (init_qty co NCC): {'PASS' if results.get('ca3') else 'FAIL'}")
        print(f"Ca 4 (init_qty khong NCC): {'PASS' if results.get('ca4') else 'FAIL'}")
        print(f"Ca 5 (NCC fake): {'PASS' if results.get('ca5') else 'FAIL'}")
        print(f"Ca 6 (NCC inactive): {'PASS' if results.get('ca6') else 'FAIL'}")
        print(f"Ca 7 / B4 (Khao sat POST /import-notes voi NCC inactive): HTTP {results.get('ca7_b4_status')}")
        print("=================================================")

    return results


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    db = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(run_f3_tests(url, db))
