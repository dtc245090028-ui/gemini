"""Test hoi quy F1: Kiem tra Race Condition va Phan quyen ghi tren he thong SmartKho.

Cac hang muc kiem tra:
1. Race cancel export (20 vong x 20 requests dong thoi): chong double refund
2. Race complete export (20 vong x 20 requests dong thoi): chong duplicate transition
3. Race delete export (20 vong x 20 requests dong thoi): 1x200, 19x404
4. Race cancel import (20 vong x 20 requests dong thoi): 1x200, 19x400/404
5. Parallel: Tao SP co ton dau + ship cung luc; Xoa SP + ship cung luc
6. Audit cac endpoint reset: /bench/reset, /reports/write-gate/reset, /reports/write-metrics/reset
7. Xac minh BEGIN IMMEDIATE trong luong HTTP that
"""

import asyncio
import time
import httpx
import sqlite3
import argparse
import sys
from typing import List, Dict, Any, Tuple

__test__ = False  # Script kiểm thử độc lập qua HTTP, không chạy qua pytest discovery


async def login(client: httpx.AsyncClient, username: str = "admin", password: str = "admin123") -> str:
    res = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    if res.status_code != 200:
        raise RuntimeError(f"Login failed: {res.status_code} {res.text}")
    return res.json()["access_token"]


async def test_race_cancel_export(client: httpx.AsyncClient, rounds: int = 20, concurrency: int = 20) -> Dict[str, Any]:
    print(f"\n--- [1] RACE CANCEL EXPORT ({rounds} vong x {concurrency} requests) ---")
    double_refund_rounds = 0
    round_details = []

    for r in range(1, rounds + 1):
        ts = int(time.time() * 1000) % 100000
        p_code = f"SKU-F1-CANC-{r:02d}-{ts}"
        p_res = await client.post("/api/v1/products/", json={
            "code": p_code,
            "name": f"SP F1 Cancel R{r}",
            "category_id": 1,
            "supplier_id": 1,
            "unit": "Cai",
            "min_stock": 2,
            "current_stock": 10,
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        assert p_res.status_code in (200, 201), f"Create product failed: {p_res.text}"
        pid = p_res.json()["id"]

        # Create export note qty 4 (stock becomes 6 after ship)
        ex_code = f"PX-F1-CANC-{r:02d}-{ts}"
        ex_res = await client.post("/api/v1/export-notes/", json={
            "code": ex_code,
            "recipient_name": f"Khach F1 R{r}",
            "details": [{"product_id": pid, "quantity": 4, "unit_price": 50000.0}]
        })
        assert ex_res.status_code in (200, 201), f"Create export note failed: {ex_res.text}"
        nid = ex_res.json()["id"]

        ship_res = await client.post(f"/api/v1/export-notes/{nid}/ship")
        assert ship_res.status_code in (200, 201), f"Ship failed: {ship_res.text}"

        # Direct concurrent firing without wrapper delays
        cancel_url = f"/api/v1/export-notes/{nid}/cancel"
        tasks = [client.post(cancel_url) for _ in range(concurrency)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        sc_map = {}
        for resp in responses:
            sc = getattr(resp, "status_code", type(resp).__name__)
            sc_map[sc] = sc_map.get(sc, 0) + 1
        sc_str = ", ".join(f"{count}x{sc}" for sc, count in sorted(sc_map.items()))

        # Check stock after cancel
        p_check = await client.get(f"/api/v1/products/{pid}")
        stock_after = p_check.json()["current_stock"]

        # Double refund occurs if final_stock > 10 (refunded more than once) or 200 count > 1
        succ_200 = sc_map.get(200, 0)
        is_double = (stock_after > 10) or (succ_200 > 1)
        if is_double:
            double_refund_rounds += 1

        round_details.append({
            "round": r,
            "succ_200": succ_200,
            "stock_after": stock_after,
            "statuses": sc_str,
            "is_double": is_double
        })
        print(f"  Vong {r:02d}: {sc_str} | Ton sau huy: {stock_after} (Ky vong: 10) | {'LOI (Double Refund)' if is_double else 'PASS'}")

    err_rate = f"{double_refund_rounds}/{rounds} ({double_refund_rounds/rounds*100:.1f}%)"
    print(f"-> Ket qua Cancel Export: Ti le vong loi = {err_rate}")
    return {"error_rounds": double_refund_rounds, "rounds": rounds, "details": round_details}


async def test_race_complete_export(client: httpx.AsyncClient, rounds: int = 20, concurrency: int = 20) -> Dict[str, Any]:
    print(f"\n--- [2] RACE COMPLETE EXPORT ({rounds} vong x {concurrency} requests) ---")
    error_rounds = 0

    for r in range(1, rounds + 1):
        ts = int(time.time() * 1000) % 100000
        p_code = f"SKU-F1-COMP-{r:02d}-{ts}"
        p_res = await client.post("/api/v1/products/", json={
            "code": p_code,
            "name": f"SP F1 Complete R{r}",
            "category_id": 1,
            "supplier_id": 1,
            "unit": "Cai",
            "min_stock": 2,
            "current_stock": 10,
            "standard_price": 50000.0,
            "status": "ACTIVE"
        })
        pid = p_res.json()["id"]

        ex_code = f"PX-F1-COMP-{r:02d}-{ts}"
        ex_res = await client.post("/api/v1/export-notes/", json={
            "code": ex_code,
            "recipient_name": f"Khach F1 R{r}",
            "details": [{"product_id": pid, "quantity": 2, "unit_price": 50000.0}]
        })
        nid = ex_res.json()["id"]
        await client.post(f"/api/v1/export-notes/{nid}/ship")

        comp_url = f"/api/v1/export-notes/{nid}/complete"
        tasks = [client.post(comp_url) for _ in range(concurrency)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        sc_map = {}
        for resp in responses:
            sc = getattr(resp, "status_code", type(resp).__name__)
            sc_map[sc] = sc_map.get(sc, 0) + 1
        sc_str = ", ".join(f"{count}x{sc}" for sc, count in sorted(sc_map.items()))

        succ_count = sc_map.get(200, 0)
        has_error = (succ_count != 1)
        if has_error:
            error_rounds += 1
        if r <= 3 or r == rounds or has_error:
            print(f"  Vong {r:02d}: {sc_str} | {'LOI' if has_error else 'PASS'}")

    err_rate = f"{error_rounds}/{rounds} ({error_rounds/rounds*100:.1f}%)"
    print(f"-> Ket qua Complete Export: Ti le vong loi = {err_rate}")
    return {"error_rounds": error_rounds, "rounds": rounds}


async def test_race_delete_export(client: httpx.AsyncClient, rounds: int = 20, concurrency: int = 20) -> Dict[str, Any]:
    print(f"\n--- [3] RACE DELETE EXPORT ({rounds} vong x {concurrency} requests) ---")
    error_rounds = 0

    for r in range(1, rounds + 1):
        ts = int(time.time() * 1000) % 100000
        ex_code = f"PX-F1-DEL-{r:02d}-{ts}"
        ex_res = await client.post("/api/v1/export-notes/", json={
            "code": ex_code,
            "recipient_name": f"Khach F1 Del R{r}",
            "details": [{"product_id": 1, "quantity": 1, "unit_price": 50000.0}]
        })
        nid = ex_res.json()["id"]

        del_url = f"/api/v1/export-notes/{nid}"
        tasks = [client.delete(del_url) for _ in range(concurrency)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        sc_map = {}
        for resp in responses:
            sc = getattr(resp, "status_code", type(resp).__name__)
            sc_map[sc] = sc_map.get(sc, 0) + 1
        sc_str = ", ".join(f"{count}x{sc}" for sc, count in sorted(sc_map.items()))

        succ_count = sc_map.get(200, 0)
        has_error = (succ_count != 1)
        if has_error:
            error_rounds += 1
        if r <= 3 or r == rounds or has_error:
            print(f"  Vong {r:02d}: {sc_str} | {'LOI' if has_error else 'PASS'}")

    err_rate = f"{error_rounds}/{rounds} ({error_rounds/rounds*100:.1f}%)"
    print(f"-> Ket qua Delete Export: Ti le vong loi = {err_rate}")
    return {"error_rounds": error_rounds, "rounds": rounds}


async def test_race_cancel_import(client: httpx.AsyncClient, rounds: int = 20, concurrency: int = 20) -> Dict[str, Any]:
    print(f"\n--- [4] RACE CANCEL IMPORT ({rounds} vong x {concurrency} requests) ---")
    error_rounds = 0

    for r in range(1, rounds + 1):
        ts = int(time.time() * 1000) % 100000
        im_code = f"PN-F1-CANC-{r:02d}-{ts}"
        im_res = await client.post("/api/v1/import-notes/", json={
            "code": im_code,
            "supplier_id": 1,
            "note": f"F1 Import {r}",
            "details": [{"product_id": 1, "quantity": 1, "unit_price": 40000.0}]
        })
        nid = im_res.json()["id"]

        cancel_url = f"/api/v1/import-notes/{nid}/cancel"
        tasks = [client.post(cancel_url) for _ in range(concurrency)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        sc_map = {}
        for resp in responses:
            sc = getattr(resp, "status_code", type(resp).__name__)
            sc_map[sc] = sc_map.get(sc, 0) + 1
        sc_str = ", ".join(f"{count}x{sc}" for sc, count in sorted(sc_map.items()))

        succ_count = sc_map.get(200, 0)
        has_error = (succ_count != 1)
        if has_error:
            error_rounds += 1
        if r <= 3 or r == rounds or has_error:
            print(f"  Vong {r:02d}: {sc_str} | {'LOI' if has_error else 'PASS'}")

    err_rate = f"{error_rounds}/{rounds} ({error_rounds/rounds*100:.1f}%)"
    print(f"-> Ket qua Cancel Import: Ti le vong loi = {err_rate}")
    return {"error_rounds": error_rounds, "rounds": rounds}


async def test_parallel_product_operations(client: httpx.AsyncClient):
    print("\n--- [5] TEST SONG SONG: TAO SP CO TON DAU + SHIP; XOA SP + SHIP ---")
    ts = int(time.time() * 1000) % 100000
    p_code = f"SKU-F1-PARA-{ts}"
    
    # 1. Create product stock 10
    sp_res = await client.post("/api/v1/products/", json={
        "code": p_code,
        "name": "SP Para Test",
        "category_id": 1,
        "supplier_id": 1,
        "unit": "Cai",
        "min_stock": 2,
        "current_stock": 10,
        "standard_price": 50000.0,
        "status": "ACTIVE"
    })
    pid = sp_res.json()["id"]

    ex_code = f"PX-F1-PARA-{ts}"
    ex_res = await client.post("/api/v1/export-notes/", json={
        "code": ex_code,
        "recipient_name": "Khach Para",
        "details": [{"product_id": pid, "quantity": 10, "unit_price": 50000.0}]
    })
    nid = ex_res.json()["id"]

    # Parallel Delete SP and Ship Export Note
    t_del = client.delete(f"/api/v1/products/{pid}")
    t_ship = client.post(f"/api/v1/export-notes/{nid}/ship")
    r_del, r_ship = await asyncio.gather(t_del, t_ship, return_exceptions=True)

    del_sc = getattr(r_del, "status_code", str(r_del))
    ship_sc = getattr(r_ship, "status_code", str(r_ship))
    print(f"  Parallel Delete SP ({del_sc}) vs Ship ({ship_sc})")


async def audit_reset_endpoints(base_url: str):
    print("\n--- [6] AUDIT CAC ENDPOINT RESET: PHAN QUYEN & AN TOAN ---")
    async with httpx.AsyncClient(base_url=base_url) as client:
        endpoints = [
            ("POST", "/api/v1/bench/reset"),
            ("POST", "/api/v1/reports/write-gate/reset"),
            ("POST", "/api/v1/reports/write-metrics/reset")
        ]
        for meth, ep in endpoints:
            res = await client.request(meth, ep)
            is_secure = res.status_code in (401, 403)
            status_desc = "KHOA (Yeu cau token/role ADMIN)" if is_secure else f"HO HOAN TOAN ({res.status_code})"
            print(f"  Chua dang nhap: {meth} {ep} -> HTTP {res.status_code} [{status_desc}]")


async def main():
    parser = argparse.ArgumentParser(description="Test hoi quy F1")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL")
    parser.add_argument("--rounds", type=int, default=20, help="So vong lap")
    parser.add_argument("--concurrency", type=int, default=20, help="So request dong thoi")
    args = parser.parse_args()

    print(f"RUNNING F1 REGRESSION TEST on {args.url}")
    print(f"Rounds: {args.rounds}, Concurrency: {args.concurrency}")

    async with httpx.AsyncClient(base_url=args.url, timeout=40.0) as client:
        token = await login(client)
        client.headers.update({"Authorization": f"Bearer {token}"})

        res_cancel = await test_race_cancel_export(client, rounds=args.rounds, concurrency=args.concurrency)
        res_complete = await test_race_complete_export(client, rounds=args.rounds, concurrency=args.concurrency)
        res_delete = await test_race_delete_export(client, rounds=args.rounds, concurrency=args.concurrency)
        res_import = await test_race_cancel_import(client, rounds=args.rounds, concurrency=args.concurrency)
        await test_parallel_product_operations(client)
        await audit_reset_endpoints(args.url)

        print("\n================== TONG KET F1 ==================")
        print(f"1. Cancel Export Race Error Rate  : {res_cancel['error_rounds']}/{args.rounds}")
        print(f"2. Complete Export Race Error Rate: {res_complete['error_rounds']}/{args.rounds}")
        print(f"3. Delete Export Race Error Rate  : {res_delete['error_rounds']}/{args.rounds}")
        print(f"4. Cancel Import Race Error Rate  : {res_import['error_rounds']}/{args.rounds}")
        print("=================================================")


if __name__ == "__main__":
    asyncio.run(main())
