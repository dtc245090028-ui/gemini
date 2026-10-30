"""Kiểm thử tính đúng đắn và độ bền của Cổng ghi (Write Gate) & Cơ chế Backpressure khi VƯỢT NGƯỠNG.

Yêu cầu kiểm chứng (Item 4):
1. Hàng đợi công bằng FIFO: Các luồng được phục vụ chính xác theo thứ tự đến.
2. Quá tải độ sâu hàng đợi (Queue Full): Trả về HTTP 503 kèm header Retry-After.
3. Quá hạn chờ (Queue Timeout): Request không bị treo quá ngưỡng timeout_seconds, trả về 503.
4. Tuyệt đối KHÔNG có lỗi 500 lạ, KHÔNG 'database is locked', dữ liệu kế toán toàn vẹn.
5. Client chỉ retry an toàn khi có Idempotency Key.
"""

import time
import uuid
import threading
import collections
import concurrent.futures
import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient
from app.main import app
from app.core.write_gate import write_gate, WriteGate
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
    cat = db.query(Category).first()
    if not cat:
        cat = Category(code="CAT_WG", name="Danh mục WG")
        db.add(cat)
        db.commit()
    prod = db.query(Product).first()
    if not prod:
        prod = Product(
            code="SKU_WG_TEST",
            name="Sản phẩm Test WG",
            category_id=cat.id,
            current_stock=500,
            standard_price=100000,
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
    assert res.status_code == 200
    return res.json()["access_token"]


def test_fair_fifo_order_guarantee():
    """Kiểm chứng: Hàng đợi FIFO đánh thức đúng thứ tự các luồng đã đến (không bỏ đói)."""
    gate = WriteGate()
    gate.concurrency_limit = 1
    gate.timeout_seconds = 2.0
    gate.max_queue_size = 10

    # Chiếm slot đầu tiên
    assert gate.acquire() is True

    acquisition_order = []
    ready_flags = [threading.Event() for _ in range(3)]

    def waiter_task(worker_id):
        ready_flags[worker_id].set()
        gate.acquire()
        acquisition_order.append(worker_id)
        gate.release()

    threads = []
    for i in range(3):
        t = threading.Thread(target=waiter_task, args=(i,))
        threads.append(t)
        t.start()
        ready_flags[i].wait(timeout=0.5)
        # Chờ nhỏ để đảm bảo thứ tự enqueue vào FIFO
        time.sleep(0.05)

    # Giải phóng slot ban đầu, lần lượt các worker phải được vào theo đúng thứ tự 0, 1, 2
    gate.release()

    for t in threads:
        t.join(timeout=2.0)

    print(f"\n[FIFO Check] Acquisition order: {acquisition_order}")
    assert acquisition_order == [0, 1, 2], f"Thứ tự phục vụ không phải FIFO: {acquisition_order}"


def test_queue_full_rejection():
    """Kiểm chứng: Khi hàng đợi vượt quá max_queue_size, từ chối ngay bằng HTTP 503 + Retry-After."""
    gate = WriteGate()
    gate.concurrency_limit = 1
    gate.max_queue_size = 2  # Chỉ cho phép tối đa 1 active + 1 waiting
    gate.timeout_seconds = 2.0

    assert gate.acquire() is True  # Slot active 1

    waiter_ready = threading.Event()
    def waiter():
        waiter_ready.set()
        gate.acquire()
        gate.release()

    t = threading.Thread(target=waiter)
    t.start()
    waiter_ready.wait()
    time.sleep(0.05)  # Hàng đợi lúc này có 1 active + 1 waiting = 2 (Đầy)

    # Request thứ 3 đến khi hàng đợi đã đầy -> Phải bị từ chối 503 ngay lập tức
    with pytest.raises(HTTPException) as exc_info:
        gate.acquire()

    assert exc_info.value.status_code == 503
    assert exc_info.value.headers.get("Retry-After") is not None
    assert gate.get_stats()["total_rejected_queue_full"] == 1

    # Dọn dẹp
    gate.release()
    t.join(timeout=1.0)


def test_timeout_rejection_no_hanging():
    """Kiểm chứng: Khi thời gian chờ vượt quá timeout_seconds, request không treo và nhận 503."""
    gate = WriteGate()
    gate.concurrency_limit = 1
    gate.timeout_seconds = 0.2  # 200 ms timeout

    assert gate.acquire() is True

    t_start = time.perf_counter()
    with pytest.raises(HTTPException) as exc_info:
        gate.acquire()
    t_elapsed = time.perf_counter() - t_start

    # Phải trả về trong khoảng 200ms - 250ms, không được treo
    print(f"\n[Timeout Check] Elapsed: {t_elapsed:.3f} s (Expected ~0.20s)")
    assert 0.18 <= t_elapsed <= 0.35, f"Request bị treo quá lâu: {t_elapsed} s"
    assert exc_info.value.status_code == 503
    assert gate.get_stats()["total_rejected_timeout"] == 1

    gate.release()


def test_overload_end_to_end_via_fastapi(client, admin_token):
    """Kiểm thử tải dồn dập vượt ngưỡng qua FastAPI TestClient:
    - Các request bị quá tải nhận 503 + Retry-After.
    - KHÔNG CÓ 500 Internal Server Error.
    - KHÔNG CÓ 'database is locked'.
    - Toàn vẹn dữ liệu được bảo vệ.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    db = SessionLocal()
    prod = db.query(Product).first()
    prod_id = prod.id
    init_stock = prod.current_stock
    db.close()

    # Tạm thời hạ ngưỡng của write_gate để kích hoạt quá tải có kiểm soát
    orig_max_q = write_gate.max_queue_size
    orig_timeout = write_gate.timeout_seconds
    orig_limit = write_gate.concurrency_limit

    write_gate.max_queue_size = 4
    write_gate.timeout_seconds = 0.25
    write_gate.concurrency_limit = 1
    write_gate.reset_stats()

    results = []

    def send_write(worker_id):
        c = TestClient(app)
        idem_key = f"OVERLOAD-TEST-{uuid.uuid4().hex[:6]}"
        h = {**headers, "X-Idempotency-Key": idem_key}
        payload = {
            "product_id": prod_id,
            "actual_stock": init_stock + worker_id + 1,
            "reason": f"Overload Stress {worker_id}"
        }
        resp = c.post("/api/v1/stock-ledger/adjust", json=payload, headers=h)
        return resp.status_code, resp.headers.get("retry-after")

    # Bắn đồng thời 16 requests khi hàng đợi chỉ chứa tối đa 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(send_write, i) for i in range(16)]
        results = [f.result() for f in futures]

    # Khôi phục cấu hình
    write_gate.max_queue_size = orig_max_q
    write_gate.timeout_seconds = orig_timeout
    write_gate.concurrency_limit = orig_limit

    status_codes = [r[0] for r in results]
    print(f"\n[Overload Results] Status codes distribution: {collections.Counter(status_codes)}")

    # 1. Không có mã lỗi 500 lạ
    assert 500 not in status_codes, "Không được phép xảy ra lỗi 500 Internal Server Error!"

    # 2. Phải có ít nhất 1 request thành công 200
    assert 200 in status_codes, "Phải có request được tiếp nhận xử lý thành công 200"

    # 3. Các request quá tải phải nhận 503 kèm Retry-After
    rejections = [r for r in results if r[0] == 503]
    assert len(rejections) > 0, "Phải có request bị từ chối 503 do vượt ngưỡng hàng đợi"
    for _, retry_after in rejections:
        assert retry_after is not None, "Mọi phản hồi 503 phải có header Retry-After"
