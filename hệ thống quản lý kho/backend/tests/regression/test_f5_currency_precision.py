"""Test hoi quy F5: Do chinh xac tien te va tran tai chinh 9e15 (duoi 2^53).

Nghiem thu:
1. Don gia le o dai thuc te:
   - quantity=3, unit_price=10000.33 -> subtotal=30000.99, total=30000.99
   - quantity=3, unit_price=10.3333333333 -> quantize lam tron ke toan 0.01 -> subtotal=31.00
2. Tran tai chinh an toan (<= 9e15):
   - quantity=9_000_000, unit_price=1_000_000_000.0 -> total=9,000,000,000,000,000.0 (HTTP 201)
3. Vuot tran tai chinh an toan (> 9e15):
   - quantity=10_000_000, unit_price=1_000_000_000.0 -> total=1e16 > 9e15 -> Bi chan HTTP 400
"""

import asyncio
import httpx
import sys
import time


async def login(client: httpx.AsyncClient) -> str:
    res = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    print(f"RUNNING F5 FINANCIAL PRECISION REGRESSION TEST on {url}")

    async with httpx.AsyncClient(base_url=url, timeout=30.0) as client:
        token = await login(client)
        client.headers.update({"Authorization": f"Bearer {token}"})

        ts = int(time.time() * 1000) % 100000

        # Tao san pham test
        p_res = await client.post("/api/v1/products/", json={
            "code": f"SKU-F5-{ts}",
            "name": "SP Test F5",
            "category_id": 1,
            "supplier_id": 1,
            "unit": "Cai",
            "standard_price": 10000.0,
            "status": "ACTIVE"
        })
        assert p_res.status_code == 201, f"Create product failed: {p_res.text}"
        pid = p_res.json()["id"]

        print("\n--- Ca 1: Don gia le o dai thuc te (qty=3, price=10000.33) ---")
        imp1 = await client.post("/api/v1/import-notes/", json={
            "code": f"PN-F5-LE1-{ts}",
            "supplier_id": 1,
            "details": [{"product_id": pid, "quantity": 3, "unit_price": 10000.33}]
        })
        print(f"  HTTP: {imp1.status_code}")
        assert imp1.status_code == 201, f"Import failed: {imp1.text}"
        d1 = imp1.json()
        sub1 = d1["details"][0]["subtotal"]
        tot1 = d1["total_amount"]
        print(f"  Subtotal: {sub1} (Ky vong: 30000.99)")
        print(f"  Total   : {tot1} (Ky vong: 30000.99)")
        assert sub1 == 30000.99, f"Subtotal mismatch: got {repr(sub1)}, expected 30000.99"
        assert tot1 == 30000.99, f"Total mismatch: got {repr(tot1)}, expected 30000.99"
        print("  -> Ca 1: PASS")

        print("\n--- Ca 2: Don gia nhieu chu so thap phan (qty=3, price=10.3333333333) ---")
        imp2 = await client.post("/api/v1/import-notes/", json={
            "code": f"PN-F5-LE2-{ts}",
            "supplier_id": 1,
            "details": [{"product_id": pid, "quantity": 3, "unit_price": 10.3333333333}]
        })
        print(f"  HTTP: {imp2.status_code}")
        assert imp2.status_code == 201, f"Import failed: {imp2.text}"
        d2 = imp2.json()
        sub2 = d2["details"][0]["subtotal"]
        tot2 = d2["total_amount"]
        print(f"  Subtotal: {sub2} (Ky vong: 31.00 sau quantize 0.01)")
        print(f"  Total   : {tot2} (Ky vong: 31.00 sau quantize 0.01)")
        assert sub2 == 31.0, f"Subtotal quantize mismatch: got {repr(sub2)}, expected 31.0"
        assert tot2 == 31.0, f"Total quantize mismatch: got {repr(tot2)}, expected 31.0"
        print("  -> Ca 2: PASS")

        print("\n--- Ca 3: Tran tai chinh an toan sat 9e15 (qty=9_000_000, price=1_000_000_000) ---")
        imp3 = await client.post("/api/v1/import-notes/", json={
            "code": f"PN-F5-CEIL-{ts}",
            "supplier_id": 1,
            "details": [{"product_id": pid, "quantity": 9_000_000, "unit_price": 1_000_000_000.0}]
        })
        print(f"  HTTP: {imp3.status_code}")
        assert imp3.status_code == 201, f"Expected 201 at ceiling 9e15, got: {imp3.text}"
        tot3 = imp3.json()["total_amount"]
        print(f"  Total amount: {tot3:,.1f} (Ky vong: 9,000,000,000,000,000.0)")
        assert tot3 == 9_000_000_000_000_000.0
        print("  -> Ca 3: PASS")

        print("\n--- Ca 4: Vuot tran tai chinh an toan (> 9e15: qty=10_000_000, price=1_000_000_000) ---")
        imp4 = await client.post("/api/v1/import-notes/", json={
            "code": f"PN-F5-OVER-{ts}",
            "supplier_id": 1,
            "details": [{"product_id": pid, "quantity": 10_000_000, "unit_price": 1_000_000_000.0}]
        })
        print(f"  HTTP: {imp4.status_code}")
        print(f"  Detail: {imp4.text}")
        assert imp4.status_code == 400, f"Expected HTTP 400 for total > 9e15, got: {imp4.status_code}"
        print("  -> Ca 4: PASS (Chan vuot tran tai chinh thanh cong voi HTTP 400)")

        print("\nTONG KET F5: TAT CA PHEP TINH TIEN TE VA TRAN TAI CHINH DAT CHUAN (PASS)")


if __name__ == "__main__":
    asyncio.run(main())
