"""API Endpoints cho quản lý Phiếu xuất kho (Export Notes)."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.export_note import ExportNote
from app.models.user import User
from app.schemas.export_note import (
    ExportNoteCreate,
    ExportNoteDetailResponse,
    ExportNoteResponse,
)
from app.services.inventory_service import cancel_export_note, create_export_note

router = APIRouter(prefix="/export-notes", tags=["Phiếu xuất kho (Export Notes)"])


def _serialize_export_note(note: ExportNote) -> ExportNoteResponse:
    """Helper chuyển đổi model ExportNote sang ExportNoteResponse đầy đủ quan hệ."""
    details = []
    for d in note.details:
        details.append(
            ExportNoteDetailResponse(
                id=d.id,
                export_note_id=d.export_note_id,
                product_id=d.product_id,
                quantity=d.quantity,
                unit_price=d.unit_price,
                subtotal=d.subtotal,
                product_name=d.product.name if d.product else None,
                product_code=d.product.code if d.product else None,
            )
        )
    return ExportNoteResponse(
        id=note.id,
        code=note.code,
        recipient_name=note.recipient_name,
        created_by=note.created_by,
        creator_name=note.creator.full_name if note.creator else None,
        note_date=note.note_date,
        total_amount=note.total_amount,
        note=note.note,
        status=note.status,
        details=details,
    )


@router.get(
    "/",
    response_model=List[ExportNoteResponse],
    summary="Lấy danh sách phiếu xuất kho",
)
def get_export_notes(
    search: Optional[str] = Query(None, description="Tìm theo mã phiếu xuất hoặc tên người nhận"),
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc theo trạng thái (COMPLETED, CANCELLED)"),
    skip: int = Query(0, ge=0, description="Số lượng bỏ qua"),
    limit: int = Query(50, ge=1, le=200, description="Số lượng lấy tối đa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Truy vấn danh sách phiếu xuất kho kèm phân trang và tìm kiếm."""
    query = (
        db.query(ExportNote)
        .options(
            joinedload(ExportNote.creator),
            joinedload(ExportNote.details),
        )
    )

    if search:
        query = query.filter(
            (ExportNote.code.ilike(f"%{search.strip()}%"))
            | (ExportNote.recipient_name.ilike(f"%{search.strip()}%"))
        )
    if status_filter:
        query = query.filter(ExportNote.status == status_filter.strip().upper())

    notes = query.order_by(ExportNote.id.desc()).offset(skip).limit(limit).all()
    return [_serialize_export_note(n) for n in notes]


@router.get(
    "/{export_note_id}",
    response_model=ExportNoteResponse,
    summary="Lấy chi tiết một phiếu xuất kho",
)
def get_export_note_by_id(
    export_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một phiếu xuất kèm danh sách mặt hàng và số lượng xuất."""
    note = (
        db.query(ExportNote)
        .options(
            joinedload(ExportNote.creator),
            joinedload(ExportNote.details),
        )
        .filter(ExportNote.id == export_note_id)
        .first()
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu xuất với ID {export_note_id}.",
        )
    return _serialize_export_note(note)


@router.post(
    "/",
    response_model=ExportNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lập phiếu xuất kho (ACID Transaction Chống tồn âm)",
)
def create_new_export_note(
    note_in: ExportNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Lập phiếu xuất kho: Kiểm tra số tồn tức thời, chặn đứng tồn âm, giảm tồn và ghi Thẻ kho."""
    note = create_export_note(db=db, note_in=note_in, current_user_id=current_user.id)
    return _serialize_export_note(note)


@router.post(
    "/{export_note_id}/cancel",
    response_model=ExportNoteResponse,
    summary="Hủy phiếu xuất kho",
)
def cancel_existing_export_note(
    export_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Hủy phiếu xuất kho: Hoàn trả số lượng vào kho và ghi bản ghi Thẻ kho ADJUSTMENT."""
    note = cancel_export_note(db=db, export_note_id=export_note_id, current_user_id=current_user.id)
    return _serialize_export_note(note)
