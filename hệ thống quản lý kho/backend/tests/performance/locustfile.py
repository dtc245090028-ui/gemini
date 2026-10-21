"""Locust Performance Test Scenario cho Hệ thống Quản lý Kho.
Mô phỏng 20 Virtual Users theo 4 nhóm hành vi:
- Nhóm 1: Bình thường (10 users)
- Nhóm 2: Hoạt động mạnh (5 users)
- Nhóm 3: Gây áp lực dồn điểm (3 users)
- Nhóm 4: Dữ liệu xấu & Replay (2 users)
"""

import os
import random
import time
import uuid
import queue
from locust import HttpUser, task, between, constant, events

# Danh sách 20 tài khoản test tương ứng từng nhóm
USERS_NORMAL = [
    ("perf_admin_01", "Perf@123", "ADMIN"),
    ("perf_admin_02", "Perf@123", "ADMIN"),
    ("perf_acct_01", "Perf@123", "ACCOUNTANT"),
    ("perf_acct_02", "Perf@123", "ACCOUNTANT"),
    ("perf_acct_03", "Perf@123", "ACCOUNTANT"),
    ("perf_wh_01", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_02", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_03", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_04", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_05", "Perf@123", "WAREHOUSE_KEEPER"),
]

USERS_ACTIVE = [
    ("perf_wh_06", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_07", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_08", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_acct_04", "Perf@123", "ACCOUNTANT"),
    ("perf_admin_03", "Perf@123", "ADMIN"),
]

USERS_PRESSURE = [
    ("perf_wh_09", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_10", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_admin_04", "Perf@123", "ADMIN"),
]

USERS_BAD = [
    ("perf_wh_11", "Perf@123", "WAREHOUSE_KEEPER"),
    ("perf_wh_12", "Perf@123", "WAREHOUSE_KEEPER"),
]

# Thread-safe queues để cấp phát tài khoản
queue_normal = queue.Queue()
queue_active = queue.Queue()
queue_pressure = queue.Queue()
queue_bad = queue.Queue()
queue_targeted = queue.Queue()

# Danh sách tất cả tài khoản có quyền kho (ADMIN & WAREHOUSE_KEEPER)
USERS_TARGETED = [
    u for u in (USERS_NORMAL + USERS_ACTIVE + USERS_PRESSURE + USERS_BAD)
    if u[2] in ("ADMIN", "WAREHOUSE_KEEPER")
]

for u in USERS_NORMAL:
    queue_normal.put(u)
for u in USERS_ACTIVE:
    queue_active.put(u)
for u in USERS_PRESSURE:
    queue_pressure.put(u)
for u in USERS_BAD:
    queue_bad.put(u)
for u in USERS_TARGETED:
    queue_targeted.put(u)

# Cache ID của các SKU-PERF-* để dùng trong test
# Sẽ được cập nhật động trong init
PERF_SKU_MAP = {
    "SKU-PERF-RACE": 86,
    "SKU-PERF-BULK-01": 87,
    "SKU-PERF-BULK-02": 88,
    "SKU-PERF-FLOW": 89,
    "SKU-PERF-BAD": 90,
}


class BaseWarehouseUser(HttpUser):
    abstract = True

    def login_once(self, user_queue, fallback_list):
        """Đăng nhập một lần duy nhất trong on_start và lưu token dùng lại cho mọi task."""
        try:
            self.user_info = user_queue.get_nowait()
        except queue.Empty:
            self.user_info = random.choice(fallback_list)

        username, password, role = self.user_info
        self.username = username
        self.role = role

        # Giả lập IP riêng biệt cho từng người dùng văn phòng
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
                return
            time.sleep(0.1 * (attempt + 1))

        print(f"[AUTH ERROR] Cannot login {username} after retries: {res.status_code}")


class NormalUser(BaseWarehouseUser):
    """Nhóm 1: Người dùng bình thường (10 users, thao tác đều, có nghỉ giữa các bước)."""
    weight = 10
    wait_time = between(2, 4)

    def on_start(self):
        self.login_once(queue_normal, USERS_NORMAL)

    @task(3)
    def view_dashboard(self):
        self.client.get("/api/v1/reports/inventory-summary", name="[Read] GET /reports/inventory-summary")

    @task(3)
    def list_products(self):
        self.client.get("/api/v1/products/?limit=50", name="[Read] GET /products/?limit=50")

    @task(2)
    def list_export_notes(self):
        self.client.get("/api/v1/export-notes/?limit=20", name="[Read] GET /export-notes/?limit=20")

    @task(2)
    def view_stock_ledgers(self):
        self.client.get("/api/v1/stock-ledger/?limit=20", name="[Read] GET /stock-ledger/?limit=20")


class ActiveUser(BaseWarehouseUser):
    """Nhóm 2: Người dùng hoạt động mạnh (5 users, thao tác liên tục)."""
    weight = 5
    wait_time = between(0.5, 1.0)

    def on_start(self):
        self.login_once(queue_active, USERS_ACTIVE)

    @task(4)
    def create_and_ship_export_note(self):
        """Tạo phiếu xuất kho và thực hiện xuất kho (/ship) trên SKU-PERF-BULK-01."""
        target_prod_id = PERF_SKU_MAP["SKU-PERF-BULK-01"]
        idem_key = f"PERF-IDEM-{uuid.uuid4()}"
        payload = {
            "recipient_name": f"Khách hàng {self.username}",
            "note": "Xuất kho kiểm thử tải thường xuyên",
            "details": [
                {
                    "product_id": target_prod_id,
                    "quantity": 1,
                    "unit_price": 100000.0,
                }
            ],
        }
        res_create = self.client.post(
            "/api/v1/export-notes/",
            json=payload,
            headers={"X-Idempotency-Key": idem_key},
            name="[Write Active] POST /export-notes/ (BULK-01)",
        )
        if res_create.status_code == 201:
            note_id = res_create.json().get("id")
            if note_id:
                self.client.post(
                    f"/api/v1/export-notes/{note_id}/ship",
                    name="[Write Active] POST /export-notes/{id}/ship",
                )

    @task(2)
    def read_low_stock(self):
        self.client.get("/api/v1/reports/low-stock", name="[Read Active] GET /reports/low-stock")


class PressureUser(BaseWarehouseUser):
    """Nhóm 3: Người dùng gây áp lực (3 users, lặp nhanh không nghỉ)."""
    weight = 3
    wait_time = constant(0)

    def on_start(self):
        self.login_once(queue_pressure, USERS_PRESSURE)

    @task(5)
    def hammer_export_flow(self):
        """Dồn dập gọi API tạo và chuyển sang SHIPPING trên SKU-PERF-BULK-02."""
        target_prod_id = PERF_SKU_MAP["SKU-PERF-BULK-02"]
        payload = {
            "recipient_name": f"Khách Dồn Tải {self.username}",
            "note": "Test dồn tải không nghỉ",
            "details": [
                {
                    "product_id": target_prod_id,
                    "quantity": 1,
                    "unit_price": 150000.0,
                }
            ],
        }
        res_create = self.client.post(
            "/api/v1/export-notes/",
            json=payload,
            name="[Hammer Pressure] POST /export-notes/ (BULK-02)",
        )
        if res_create.status_code == 201:
            note_id = res_create.json().get("id")
            if note_id:
                self.client.post(
                    f"/api/v1/export-notes/{note_id}/ship",
                    name="[Hammer Pressure] POST /export-notes/{id}/ship",
                )

    @task(1)
    def check_flow_product(self):
        target_prod_id = PERF_SKU_MAP["SKU-PERF-FLOW"]
        self.client.get(f"/api/v1/products/{target_prod_id}", name="[Hammer Pressure] GET /products/{flow_id}")


class BadDataUser(BaseWarehouseUser):
    """Nhóm 4: Người dùng nhập dữ liệu xấu / gửi trùng lặp (2 users)."""
    weight = 2
    wait_time = between(1, 2)

    def on_start(self):
        self.login_once(queue_bad, USERS_BAD)

    @task(2)
    def send_malformed_payload(self):
        """Gửi các payload lỗi có chủ đích để kiểm tra độ bền của Pydantic & FastAPI validator."""
        target_prod_id = PERF_SKU_MAP["SKU-PERF-BAD"]
        choice = random.randint(1, 3)

        if choice == 1:
            # Số lượng âm (-10)
            payload = {
                "recipient_name": "Test Lỗi Số Lượng Âm",
                "details": [{"product_id": target_prod_id, "quantity": -10, "unit_price": 50000.0}],
            }
        elif choice == 2:
            # Danh sách mặt hàng rỗng
            payload = {
                "recipient_name": "Test Lỗi Items Rỗng",
                "details": [],
            }
        else:
            # Chuỗi ghi chú quá dài (5000 ký tự)
            payload = {
                "recipient_name": "Test Chuỗi Dài",
                "note": "A" * 5000,
                "details": [{"product_id": target_prod_id, "quantity": 1, "unit_price": 50000.0}],
            }

        # Kỳ vọng trả về 400 hoặc 422: được tính là kiểm tra thành công
        with self.client.post(
            "/api/v1/export-notes/",
            json=payload,
            catch_response=True,
            name="[Bad Data Expected 4xx] POST /export-notes/ (Malformed)",
        ) as response:
            if response.status_code in (400, 422):
                response.success()
            else:
                response.failure(f"Kỳ vọng 400/422 nhưng nhận {response.status_code}")

    @task(2)
    def send_duplicate_idempotency(self):
        """Gửi trùng lặp cùng một X-Idempotency-Key liên tiếp."""
        target_prod_id = PERF_SKU_MAP["SKU-PERF-BULK-01"]
        duplicate_key = f"PERF-REPLAY-{random.randint(1, 5)}"
        payload = {
            "recipient_name": "Test Trùng Lặp Idempotency",
            "details": [{"product_id": target_prod_id, "quantity": 1, "unit_price": 100000.0}],
        }
        with self.client.post(
            "/api/v1/export-notes/",
            json=payload,
            headers={"X-Idempotency-Key": duplicate_key},
            catch_response=True,
            name="[Idempotency Replay] POST /export-notes/ (Duplicate Key)",
        ) as res:
            if res.status_code in (200, 201):
                res.success()
            else:
                res.failure(f"Idempotency trả mã lỗi bất thường: {res.status_code}")


class TargetedPressureUser(BaseWarehouseUser):
    """Bậc 4: 20 user cùng dồn một điểm vào luồng Tạo phiếu & Xuất kho (không nghỉ)."""
    wait_time = constant(0)

    def on_start(self):
        self.login_once(queue_targeted, USERS_TARGETED)

    @task
    def hammer_export_flow(self):
        target_prod_id = random.choice([
            PERF_SKU_MAP["SKU-PERF-BULK-01"],
            PERF_SKU_MAP["SKU-PERF-BULK-02"],
        ])
        payload = {
            "recipient_name": f"Khách Dồn Điểm {self.username}",
            "note": "Test dồn 1 điểm Bậc 4",
            "details": [
                {
                    "product_id": target_prod_id,
                    "quantity": 1,
                    "unit_price": 100000.0,
                }
            ],
        }
        res_create = self.client.post(
            "/api/v1/export-notes/",
            json=payload,
            name="[Targeted Pressure] POST /export-notes/",
        )
        if res_create.status_code == 201:
            note_id = res_create.json().get("id")
            if note_id:
                self.client.post(
                    f"/api/v1/export-notes/{note_id}/ship",
                    name="[Targeted Pressure] POST /export-notes/{id}/ship",
                )


class SpikeUser(BaseWarehouseUser):
    """Bậc 5: Spike cực đại - 20 user dồn dập xuất kho không nghỉ kèm kiểm thử replay idempotency."""
    wait_time = constant(0)

    def on_start(self):
        self.login_once(queue_targeted, USERS_TARGETED)

    @task(8)
    def spike_export_hammer(self):
        target_prod_id = random.choice([
            PERF_SKU_MAP["SKU-PERF-BULK-01"],
            PERF_SKU_MAP["SKU-PERF-BULK-02"],
        ])
        payload = {
            "recipient_name": f"Spike Customer {self.username}",
            "note": "Spike test Bậc 5",
            "details": [
                {
                    "product_id": target_prod_id,
                    "quantity": 1,
                    "unit_price": 100000.0,
                }
            ],
        }
        res_create = self.client.post(
            "/api/v1/export-notes/",
            json=payload,
            name="[Spike] POST /export-notes/",
        )
        if res_create.status_code == 201:
            note_id = res_create.json().get("id")
            if note_id:
                self.client.post(
                    f"/api/v1/export-notes/{note_id}/ship",
                    name="[Spike] POST /export-notes/{id}/ship",
                )

    @task(2)
    def spike_idempotency_replay(self):
        target_prod_id = PERF_SKU_MAP["SKU-PERF-BULK-01"]
        duplicate_key = f"SPIKE-REPLAY-{self.username}-{random.randint(1, 3)}"
        payload = {
            "recipient_name": f"Spike Replay {self.username}",
            "note": "Spike replay idempotency",
            "details": [{"product_id": target_prod_id, "quantity": 1, "unit_price": 100000.0}],
        }
        with self.client.post(
            "/api/v1/export-notes/",
            json=payload,
            headers={"X-Idempotency-Key": duplicate_key},
            catch_response=True,
            name="[Spike Replay] POST /export-notes/",
        ) as res:
            if res.status_code in (200, 201):
                res.success()
            else:
                res.failure(f"Spike Idempotency error: {res.status_code}")

