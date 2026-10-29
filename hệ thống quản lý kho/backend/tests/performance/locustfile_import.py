"""Locust Performance Test Scenario cho Nhóm C: POST /import-notes/ Concurrency Spike.
Tương tự Bậc 5 (20 users, constant(0), 60 giây) nhưng nhắm vào Module Nhập kho:
- 80% spike_import_hammer: tạo phiếu nhập mới không kèm idempotency_key (kiểm tra xung đột sinh mã và cập nhật tồn kho).
- 20% spike_import_replay: tạo phiếu kèm X-Idempotency-Key trùng lặp (kiểm tra cơ chế chống ghi lặp).
"""

import os
import random
import time
import queue
import threading
from locust import HttpUser, task, constant

# Danh sách 20 tài khoản test có quyền kho (ADMIN & WAREHOUSE_KEEPER)
USERS_TARGETED = [
    ("perf_admin_01", "Perf@123", "ADMIN"),
    ("perf_admin_02", "Perf@123", "ADMIN"),
    ("perf_admin_03", "Perf@123", "ADMIN"),
    ("perf_admin_04", "Perf@123", "ADMIN"),
    ("perf_wh_01", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_02", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_03", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_04", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_05", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_06", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_07", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_08", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_09", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_10", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_11", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_12", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_acct_01", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_acct_02", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_acct_03", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_acct_04", "Perf@123", "WAREHOUSE_KEEPER"),
]

queue_targeted = queue.Queue()
for u in USERS_TARGETED:
    queue_targeted.put(u)

PERF_SKU_MAP = {}
_sku_map_lock = threading.Lock()
_sku_map_loaded = False


class BaseWarehouseUser(HttpUser):
    abstract = True

    def _ensure_perf_sku_map(self):
        global _sku_map_loaded
        if _sku_map_loaded:
            return
        with _sku_map_lock:
            if _sku_map_loaded:
                return
            res = self.client.get(
                "/api/v1/products/?search=SKU-PERF-&limit=50",
                name="[Init] Lookup SKU-PERF-* IDs",
            )
            if res.status_code == 200:
                for p in res.json():
                    code = p.get("code")
                    pid = p.get("id")
                    if code and pid:
                        PERF_SKU_MAP[code] = pid
                if PERF_SKU_MAP:
                    _sku_map_loaded = True
                    print(f"[INIT] Đã nạp động PERF_SKU_MAP: {PERF_SKU_MAP}")
                else:
                    raise RuntimeError(
                        "[LỖI] Không tìm thấy sản phẩm SKU-PERF-* trong CSDL! "
                        "Hãy chạy setup_perf_data.py trước khi chạy Locust."
                    )

    def login_once(self, user_queue, fallback_list):
        try:
            self.user_info = user_queue.get_nowait()
        except queue.Empty:
            self.user_info = random.choice(fallback_list)

        username, password, role = self.user_info
        self.username = username
        self.role = role

        ip_suffix = abs(hash(username)) % 250 + 1
        client_ip = f"10.0.1.{ip_suffix}"

        for attempt in range(5):
            res = self.client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
                headers={"X-Forwarded-For": client_ip},
                name="[Auth] Login (One-time on_start)",
            )
            if res.status_code == 200:
                token = res.json().get("access_token")
                self.client.headers.update({"Authorization": f"Bearer {token}"})
                self._ensure_perf_sku_map()
                return
            time.sleep(0.1 * (attempt + 1))

        print(f"[AUTH ERROR] Cannot login {username} after retries: {res.status_code}")


class ImportSpikeUser(BaseWarehouseUser):
    """Spike cực đại trên module Nhập kho - 20 user dồn dập nhập kho không nghỉ."""
    wait_time = constant(0)

    def on_start(self):
        self.login_once(queue_targeted, USERS_TARGETED)

    @task(8)
    def spike_import_hammer(self):
        target_prod_id = random.choice([
            PERF_SKU_MAP["SKU-PERF-BULK-01"],
            PERF_SKU_MAP["SKU-PERF-BULK-02"],
        ])
        payload = {
            "supplier_id": 1,
            "note": f"Spike import {self.username}",
            "details": [
                {
                    "product_id": target_prod_id,
                    "quantity": 1,
                    "unit_price": 50000.0,
                }
            ],
        }
        self.client.post(
            "/api/v1/import-notes/",
            json=payload,
            name="[Spike] POST /import-notes/",
        )

    @task(2)
    def spike_import_idempotency_replay(self):
        target_prod_id = PERF_SKU_MAP["SKU-PERF-BULK-01"]
        duplicate_key = f"SPIKE-IMPORT-REPLAY-{self.username}-{random.randint(1, 3)}"
        payload = {
            "supplier_id": 1,
            "note": f"Spike import replay {self.username}",
            "details": [
                {
                    "product_id": target_prod_id,
                    "quantity": 1,
                    "unit_price": 50000.0,
                }
            ],
        }
        with self.client.post(
            "/api/v1/import-notes/",
            json=payload,
            headers={"X-Idempotency-Key": duplicate_key},
            catch_response=True,
            name="[Spike Replay] POST /import-notes/",
        ) as res:
            if res.status_code in (200, 201):
                res.success()
            else:
                res.failure(f"Spike Import Idempotency error: {res.status_code}")
