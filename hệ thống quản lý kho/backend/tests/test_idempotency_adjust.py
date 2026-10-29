"""Kiểm thử tính đúng đắn của cơ chế Idempotency Key cho API Điều chỉnh tồn kho (Stock Adjustment).

Kiểm tra:
1. Gửi 2 request tuần tự cùng Idempotency Key -> Chỉ ghi 1 dòng vào Thẻ kho, trả về cùng dữ liệu.
2. Gửi 5 request đồng thời cùng Idempotency Key -> Chỉ duy nhất 1 request thực hiện ghi DB, các request còn lại nhận bản ghi đã tồn tại.
3. Gửi request KHÔNG có Idempotency Key -> Hoạt động bình thường, ghi sổ cái như cũ.
4. Gửi request vi phạm logic nghiệp vụ (tồn âm, sản phẩm không tồn tại) -> Bị từ chối ngay lập tức, không retry oan.
"""

import os
import sys
import time
import uuid
import requests
import concurrent.futures

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def get_admin_token():
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]

def count_ledger_entries(token, product_id):
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/api/v1/stock-ledger/?product_id={product_id}", headers=headers)
    assert res.status_code == 200
    return len(res.json())

def test_idempotency():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Lay product id = 1 de test
    p_res = requests.get(f"{BASE_URL}/api/v1/products/1", headers=headers)
    assert p_res.status_code == 200, f"Cannot get product 1: {p_res.text}"
    p_data = p_res.json()
    curr_stock = p_data["current_stock"]
    target_stock_1 = curr_stock + 10
    
    print(f"Product 1 current stock: {curr_stock}")
    n_before = count_ledger_entries(token, 1)
    
    # --- TEST 1: Gửi cùng key 2 lần liên tiếp ---
    key1 = f"IDEM-TEST-SEQ-{time.time()}-{uuid.uuid4().hex[:6]}"
    h1 = {**headers, "X-Idempotency-Key": key1}
    payload1 = {
        "product_id": 1,
        "actual_stock": target_stock_1,
        "reason": "Test Idempotency Lan 1"
    }
    
    r1 = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload1, headers=h1)
    assert r1.status_code == 200, f"Request 1 failed: {r1.text}"
    res1 = r1.json()
    print("Test 1 - Lan 1:", res1["message"], "ref:", res1["reference_code"])
    
    # Request 2 với cùng key1
    r2 = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload1, headers=h1)
    assert r2.status_code == 200, f"Request 2 failed: {r2.text}"
    res2 = r2.json()
    print("Test 1 - Lan 2 (cùng key):", res2["message"], "ref:", res2["reference_code"])
    
    # Kiểm tra ref_code và idempotency_key giống hệt nhau
    assert res1["reference_code"] == res2["reference_code"], "Reference codes do not match!"
    assert res2.get("idempotency_key") == key1, "Idempotency key missing in response"
    
    n_after_seq = count_ledger_entries(token, 1)
    assert n_after_seq == n_before + 1, f"Expected exactly 1 new ledger entry, got {n_after_seq - n_before}"
    print("=> PASS TEST 1: Gửi cùng key 2 lần liên tiếp chỉ ghi đúng 1 lần vào ledger!")
    
    # --- TEST 2: Gửi cùng key song song từ 5 luồng đồng thời ---
    key2 = f"IDEM-TEST-CONCUR-{time.time()}-{uuid.uuid4().hex[:6]}"
    h2 = {**headers, "X-Idempotency-Key": key2}
    payload2 = {
        "product_id": 1,
        "actual_stock": target_stock_1 + 5,
        "reason": "Test Idempotency Song Song"
    }
    
    def send_adj(worker_idx):
        return requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload2, headers=h2)
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_adj, i) for i in range(5)]
        results = [f.result() for f in futures]
        
    for idx, r in enumerate(results):
        assert r.status_code == 200, f"Concurrent request {idx} failed: {r.text}"
        
    refs = [r.json()["reference_code"] for r in results]
    # Toàn bộ 5 request phải nhận được cùng một reference code
    assert len(set(refs)) == 1, f"Expected identical reference codes across 5 threads, got {refs}"
    
    n_after_conc = count_ledger_entries(token, 1)
    assert n_after_conc == n_after_seq + 1, f"Expected exactly 1 new ledger entry for concurrent batch, got {n_after_conc - n_after_seq}"
    print("=> PASS TEST 2: Gửi cùng key song song từ 5 luồng chỉ ghi đúng 1 lần vào ledger!")
    
    # --- TEST 3: Gửi request không có Idempotency Key -> Bình thường ---
    payload3 = {
        "product_id": 1,
        "actual_stock": target_stock_1 + 2,
        "reason": "Test Non-Idempotent Request"
    }
    r3 = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload3, headers=headers)
    assert r3.status_code == 200
    n_after_non_idem = count_ledger_entries(token, 1)
    assert n_after_non_idem == n_after_conc + 1
    print("=> PASS TEST 3: Không key vẫn chạy bình thường và ghi ledger như cũ!")
    
    # --- TEST 4: Vi phạm ràng buộc nghiệp vụ (tồn âm) -> Từ chối ngay lập tức không retry oan ---
    payload4 = {
        "product_id": 1,
        "actual_stock": -50,
        "reason": "Test Invalid Negative Stock"
    }
    r4 = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload4, headers=h1)
    assert r4.status_code == 400 or r4.status_code == 422
    print("=> PASS TEST 4: Vi phạm ràng buộc dữ liệu bị từ chối ngay lập tức!")

    print("\n" + "="*55)
    print(" TẤT CẢ 4 KIỂM THỬ IDEMPOTENCY CHO ADJUST ĐỀU ĐẠT 100%!")
    print("="*55 + "\n")

if __name__ == "__main__":
    test_idempotency()
