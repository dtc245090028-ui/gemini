"""Kiểm thử tập trung cho hệ thống sự kiện thời gian thực (Server-Sent Events Broadcaster).

Kiểm tra:
1. Sự kiện phát từ một điểm tập trung sau commit (hook publish_after_commit).
2. Khi giao dịch bị ROLLBACK hoặc lỗi, tuyệt đối KHÔNG phát sự kiện.
3. Cơ chế gom sự kiện (Debounce 200ms): 15 mutations liên tiếp gom thành 1 event duy nhất.
4. Đo độ trễ từ commit đến lúc phát sự kiện (commit -> event delivery latency).
5. Định danh phiên client_id (X-Client-Id) được truyền tải chính xác trong payload.
"""

import asyncio
import json
import time
import pytest
from app.core.events import EventBroadcaster
from app.core.database import Base, engine, SessionLocal
from app.core.seed import seed_default_users
from app.models.product import Product
from app.models.category import Category
from app.services.inventory_service import create_import_note


@pytest.mark.asyncio
async def test_sse_debounce_and_batching():
    """Kiểm thử gom sự kiện (Debounce): 15 mutations dồn dập chỉ phát 1 sự kiện gộp."""
    broadcaster = EventBroadcaster(debounce_window_s=0.15, heartbeat_interval_s=10.0)
    broadcaster.set_loop(asyncio.get_running_loop())

    q = await broadcaster.subscribe()
    assert broadcaster.get_stats()["active_subscribers"] == 1

    # Phát 15 mutation liên tiếp
    t_start = time.perf_counter()
    for i in range(15):
        broadcaster.publish_after_commit(
            resource="stock_ledger",
            action="ADJUST",
            client_id="client_test_1",
            metadata={"product_id": 1, "idx": i},
        )

    # Chờ debounce window (150ms) xả sự kiện
    raw_msg = await asyncio.wait_for(q.get(), timeout=1.0)
    t_delivered = time.perf_counter()

    assert raw_msg.startswith("event: data_changed\ndata: ")
    lines = raw_msg.strip().split("\n")
    data = json.loads(lines[1].replace("data: ", ""))

    assert data["event"] == "data_changed"
    assert data["resource"] == "stock_ledger"
    assert data["action"] == "ADJUST"
    assert data["mutation_count"] == 15
    assert "client_test_1" in data["client_ids"]

    # Đo độ trễ từ lúc mutation đầu tiên đến lúc nhận được event
    delivery_latency_ms = (t_delivered - t_start) * 1000.0
    print(f"\n[SSE Benchmark] Delivery Latency: {delivery_latency_ms:.2f} ms | Debounce window: 150 ms")
    assert delivery_latency_ms < 350.0, f"Độ trễ quá cao: {delivery_latency_ms} ms"

    # Đảm bảo hàng đợi không có thêm sự kiện rác
    assert q.empty(), "Hàng đợi phải rỗng sau khi đã gom toàn bộ 15 mutations!"

    stats = broadcaster.get_stats()
    assert stats["total_mutations_recorded"] == 15
    assert stats["total_events_emitted"] == 1
    assert stats["batching_efficiency_ratio"] == 15.0

    await broadcaster.unsubscribe(q)
    assert broadcaster.get_stats()["active_subscribers"] == 0


@pytest.mark.asyncio
async def test_rollback_does_not_emit_sse():
    """Kiểm thử: Khi giao dịch Database gặp lỗi / Rollback, tuyệt đối KHÔNG phát SSE."""
    from app.core.events import broadcaster as global_broadcaster
    global_broadcaster.set_loop(asyncio.get_running_loop())

    q = await global_broadcaster.subscribe()
    initial_emitted = global_broadcaster.total_events_emitted

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_default_users(db)

    # Cố tình thực hiện giao dịch nhập kho không hợp lệ (nhà cung cấp không tồn tại -> Rollback)
    from fastapi import HTTPException
    try:
        from app.schemas.import_note import ImportNoteCreate, ImportNoteDetailCreate
        invalid_data = ImportNoteCreate(
            supplier_id=999999,  # Không tồn tại
            details=[ImportNoteDetailCreate(product_id=1, quantity=10, unit_price=10000)],
        )
        create_import_note(db=db, note_in=invalid_data, current_user_id=1)
    except HTTPException:
        pass  # Đã bị rollback như kỳ vọng

    db.close()

    # Chờ 300ms để chắc chắn không có debounce flush nào được kích hoạt
    await asyncio.sleep(0.3)

    assert q.empty(), "Hàng đợi SSE KHÔNG ĐƯỢC có thông điệp nào khi giao dịch bị Rollback!"
    assert global_broadcaster.total_events_emitted == initial_emitted

    await global_broadcaster.unsubscribe(q)
