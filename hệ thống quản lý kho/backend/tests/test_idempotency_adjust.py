import concurrent.futures
import os
import sys
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_URL = "http://127.0.0.1:8000"

def get_admin_token():
    res = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    if res.status_code != 200:
        raise RuntimeError(f"Login failed: {res.text}")
    return res.json()["access_token"]

def count_ledger_entries(token, product_id):
    res = requests.get(
        f"{BASE_URL}/api/v1/stock-ledger/?product_id={product_id}&limit=1000",
        headers={"Authorization": f"Bearer {token}"}
    )
    data = res.json()
    items = data["items"] if isinstance(data, dict) and "items" in data else data
    return len(items)

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
    key1 = f"IDEM-TEST-SEQ-{os.getpid()}-1"
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
    key2 = f"IDEM-TEST-CONCUR-{os.getpid()}-2"
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
        assert r.status_code == 200, f"Concurrent worker {idx} failed: {r.status_code} {r.text}"
        
    ref_codes = set(r.json()["reference_code"] for r in results)
    assert len(ref_codes) == 1, f"Expected 1 unique reference code, got: {ref_codes}"
    
    n_after_concur = count_ledger_entries(token, 1)
    assert n_after_concur == n_after_seq + 1, f"Expected exactly 1 new ledger entry for concurrent calls, got {n_after_concur - n_after_seq}"
    print("=> PASS TEST 2: Gửi cùng key song song từ 5 luồng chỉ ghi đúng 1 lần vào ledger!")
    
    # --- TEST 3: Không key (chạy bình thường) ---
    payload3 = {
        "product_id": 1,
        "actual_stock": curr_stock,
        "reason": "Test Không Key Khôi Phục Tồn Cũ"
    }
    r3 = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload3, headers=headers)
    assert r3.status_code == 200, f"Request 3 failed: {r3.text}"
    n_after_no_key = count_ledger_entries(token, 1)
    assert n_after_no_key == n_after_concur + 1, "Expected 1 new entry when no key provided"
    print("=> PASS TEST 3: Không key vẫn chạy bình thường và ghi ledger như cũ!")
    
    # --- TEST 4: Dữ liệu vi phạm ràng buộc (tồn âm < 0) ---
    payload4 = {
        "product_id": 1,
        "actual_stock": -50,
        "reason": "Test Vi Pham Rang Buoc"
    }
    r4 = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload4, headers=headers)
    assert r4.status_code in (400, 422), f"Expected 400 or 422, got {r4.status_code}"
    print("=> PASS TEST 4: Vi phạm ràng buộc dữ liệu bị từ chối ngay lập tức!")

    print("\n=======================================================")
    print(" TẤT CẢ 4 KIỂM THỬ IDEMPOTENCY CHO ADJUST ĐỀU ĐẠT 100%!")
    print("=======================================================")

if __name__ == "__main__":
    test_idempotency()
