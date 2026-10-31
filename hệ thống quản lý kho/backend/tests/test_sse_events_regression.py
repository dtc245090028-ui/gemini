"""Kiểm thử hồi quy sự kiện SSE: Phát hiện lỗi bỏ sót sự kiện khi xóa/hủy phiếu xuất CONFIRMED (L3)."""

import asyncio
import json
import pytest
from app.core.database import Base, engine, SessionLocal
from app.core.events import broadcaster
from app.core.seed import seed_default_users
from app.models.export_note import ExportNote
from app.services.inventory_service import delete_export_note, cancel_export_note


@pytest.fixture(autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()


@pytest.mark.asyncio
async def test_delete_confirmed_export_note_must_publish_sse():
    """L3 Reproduction: Xóa phiếu xuất CONFIRMED bắt buộc phải phát sự kiện SSE."""
    broadcaster.set_loop(asyncio.get_running_loop())
    q = await broadcaster.subscribe()

    db = SessionLocal()
    try:
        # Tạo phiếu xuất CONFIRMED tạm
        test_code = "PX-TEST-REPRODUCE-L3-DEL"
        existing = db.query(ExportNote).filter_by(code=test_code).first()
        if existing:
            db.delete(existing)
            db.commit()

        note = ExportNote(
            code=test_code,
            recipient_name="Tester",
            created_by=1,
            total_amount=10000.0,
            status="CONFIRMED",
            note="Test L3 Delete",
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        note_id = note.id

        # Hút sạch các sự kiện cũ trong queue nếu có
        while not q.empty():
            q.get_nowait()

        # Gọi hàm delete_export_note
        delete_export_note(db=db, export_note_id=note_id, current_user_id=1)

        # Chờ nhận event (debounce window 200ms -> chờ tối đa 0.8s)
        try:
            msg = await asyncio.wait_for(q.get(), timeout=0.8)
            lines = msg.strip().split("\n")
            data = json.loads(lines[1].replace("data: ", ""))
            assert data["resource"] == "export_notes"
            assert data["action"] in ["DELETE", "CANCEL"]
        except asyncio.TimeoutError:
            pytest.fail("FAIL (L3): Không nhận được sự kiện SSE sau khi xóa phiếu xuất CONFIRMED!")
    finally:
        await broadcaster.unsubscribe(q)
        db.close()


@pytest.mark.asyncio
async def test_cancel_confirmed_export_note_must_publish_sse():
    """L3 Reproduction: Hủy phiếu xuất CONFIRMED bắt buộc phải phát sự kiện SSE."""
    broadcaster.set_loop(asyncio.get_running_loop())
    q = await broadcaster.subscribe()

    db = SessionLocal()
    try:
        # Tạo phiếu xuất CONFIRMED tạm
        test_code = "PX-TEST-REPRODUCE-L3-CAN"
        existing = db.query(ExportNote).filter_by(code=test_code).first()
        if existing:
            db.delete(existing)
            db.commit()

        note = ExportNote(
            code=test_code,
            recipient_name="Tester",
            created_by=1,
            total_amount=10000.0,
            status="CONFIRMED",
            note="Test L3 Cancel",
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        note_id = note.id

        # Hút sạch các sự kiện cũ trong queue
        while not q.empty():
            q.get_nowait()

        # Gọi hàm cancel_export_note
        cancel_export_note(db=db, export_note_id=note_id, current_user_id=1, reason="Test L3")

        # Chờ nhận event (debounce window 200ms -> chờ tối đa 0.8s)
        try:
            msg = await asyncio.wait_for(q.get(), timeout=0.8)
            lines = msg.strip().split("\n")
            data = json.loads(lines[1].replace("data: ", ""))
            assert data["resource"] == "export_notes"
            assert data["action"] in ["CANCEL", "DELETE"]
        except asyncio.TimeoutError:
            pytest.fail("FAIL (L3): Không nhận được sự kiện SSE sau khi hủy phiếu xuất CONFIRMED!")
    finally:
        await broadcaster.unsubscribe(q)
        db.close()
