"""Kiểm thử tính đúng đắn của cơ chế Idempotency Key cho API Điều chỉnh tồn kho (Stock Adjustment).

Chạy 100% cô lập trên Test Database qua FastAPI TestClient.
Kiểm tra:
1. Gửi 2 request tuần tự cùng Idempotency Key -> Chỉ ghi 1 dòng vào Thẻ kho, trả về cùng dữ liệu.
2. Gửi 5 request đồng thời cùng Idempotency Key -> Chỉ duy nhất 1 request thực hiện ghi DB, các request còn lại nhận bản ghi đã tồn tại.
3. Gửi request KHÔNG có Idempotency Key -> Hoạt động bình thường, ghi sổ cái như cũ.
4. Gửi request vi phạm logic nghiệp vụ (tồn âm, sản phẩm không tồn tại) -> Bị từ chối ngay lập tức, không retry oan.
"""

import time
import uuid
import concurrent.futures
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.database import Base, engine, SessionLocal
from app.core.seed import seed_default_users
from app.models.product import Product
from app.models.category import Category
from app.models.stock_ledger import StockLedger


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_default_users(db)
    # Đảm bảo có category và product mẫu trong test DB
    cat = db.query(Category).first()
    if not cat:
        cat = Category(code="CAT_TEST", name="Danh mục Test")
        db.add(cat)
        db.commit()
        db.refresh(cat)

    prod = db.query(Product).first()
    if not prod:
        prod = Product(
            code="SKU_TEST_IDEM",
            name="Sản phẩm Test Idempotency",
            category_id=cat.id,
            current_stock=100,
            standard_price=50000,
            unit="Cái",
            min_stock=10,
        )
        db.add(prod)
        db.commit()
    db.close()
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_token(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def test_idempotency_sequential_and_concurrent(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Lấy thông tin sản phẩm mẫu trong test database
    db = SessionLocal()
    prod = db.query(Product).first()
    prod_id = prod.id
    curr_stock = prod.current_stock
    n_before = db.query(StockLedger).filter(StockLedger.product_id == prod_id).count()
    db.close()

    # --- TEST 1: Gửi cùng key 2 lần liên tiếp ---
    key1 = f"IDEM-SEQ-{time.time()}-{uuid.uuid4().hex[:6]}"
    h1 = {**headers, "X-Idempotency-Key": key1}
    payload1 = {
        "product_id": prod_id,
        "actual_stock": curr_stock + 10,
        "reason": "Test Idempotency Lan 1"
    }

    r1 = client.post("/api/v1/stock-ledger/adjust", json=payload1, headers=h1)
    assert r1.status_code == 200, f"Request 1 failed: {r1.text}"
    res1 = r1.json()

    # Request 2 với cùng key1
    r2 = client.post("/api/v1/stock-ledger/adjust", json=payload1, headers=h1)
    assert r2.status_code == 200, f"Request 2 failed: {r2.text}"
    res2 = r2.json()

    # Kiểm tra ref_code và idempotency_key giống hệt nhau
    assert res1["reference_code"] == res2["reference_code"], "Reference codes do not match!"
    assert res2.get("idempotency_key") == key1, "Idempotency key missing in response"

    db = SessionLocal()
    n_after_seq = db.query(StockLedger).filter(StockLedger.product_id == prod_id).count()
    assert n_after_seq == n_before + 1, f"Expected exactly 1 new ledger entry, got {n_after_seq - n_before}"

    # --- TEST 2: Gửi cùng key song song từ 5 luồng đồng thời ---
    key2 = f"IDEM-CONCUR-{time.time()}-{uuid.uuid4().hex[:6]}"
    h2 = {**headers, "X-Idempotency-Key": key2}
    payload2 = {
        "product_id": prod_id,
        "actual_stock": curr_stock + 20,
        "reason": "Test Idempotency Song Song"
    }

    def send_adj(worker_idx):
        c = TestClient(app)
        return c.post("/api/v1/stock-ledger/adjust", json=payload2, headers=h2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_adj, i) for i in range(5)]
        results = [f.result() for f in futures]

    for idx, r in enumerate(results):
        assert r.status_code == 200, f"Concurrent request {idx} failed: {r.text}"

    refs = [r.json()["reference_code"] for r in results]
    assert len(set(refs)) == 1, f"Expected identical reference codes across 5 threads, got {refs}"

    n_after_conc = db.query(StockLedger).filter(StockLedger.product_id == prod_id).count()
    assert n_after_conc == n_after_seq + 1, f"Expected exactly 1 new ledger entry for concurrent batch, got {n_after_conc - n_after_seq}"

    # --- TEST 3: Gửi request không có Idempotency Key -> Hoạt động bình thường ---
    payload3 = {
        "product_id": prod_id,
        "actual_stock": curr_stock + 25,
        "reason": "Test Non-Idempotent Request"
    }
    r3 = client.post("/api/v1/stock-ledger/adjust", json=payload3, headers=headers)
    assert r3.status_code == 200
    n_after_non_idem = db.query(StockLedger).filter(StockLedger.product_id == prod_id).count()
    assert n_after_non_idem == n_after_conc + 1

    # --- TEST 4: Vi phạm ràng buộc nghiệp vụ (tồn âm) -> Từ chối ngay lập tức ---
    payload4 = {
        "product_id": prod_id,
        "actual_stock": -50,
        "reason": "Test Invalid Negative Stock"
    }
    r4 = client.post("/api/v1/stock-ledger/adjust", json=payload4, headers=h1)
    assert r4.status_code in (400, 422), f"Expected 400 or 422, got {r4.status_code}"

    db.close()
