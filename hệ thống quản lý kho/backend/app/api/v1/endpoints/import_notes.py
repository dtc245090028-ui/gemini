"""API Endpoints cho quản lý Phiếu nhập kho (Import Notes)."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.import_note import ImportNote
from app.models.user import User
from app.schemas.import_note import (
    ImportNoteCreate,
    ImportNoteDetailResponse,
    ImportNoteResponse,
)
from app.services.inventory_service import cancel_import_note, create_import_note

router = APIRouter(prefix="/import-notes", tags=["Phiếu nhập kho (Import Notes)"])


def _serialize_import_note(note: ImportNote) -> ImportNoteResponse:
    """Helper chuyển đổi model ImportNote sang ImportNoteResponse đầy đủ quan hệ."""
    details = []
    for d in note.details:
        details.append(
            ImportNoteDetailResponse(
                id=d.id,
                import_note_id=d.import_note_id,
                product_id=d.product_id,
                quantity=d.quantity,
                unit_price=d.unit_price,
                subtotal=d.subtotal,
                product_name=d.product.name if d.product else None,
                product_code=d.product.code if d.product else None,
            )
        )
    return ImportNoteResponse(
        id=note.id,
        code=note.code,
        supplier_id=note.supplier_id,
        supplier_name=note.supplier.name if note.supplier else None,
        created_by=note.created_by,
        creator_name=note.creator.full_name if note.creator else None,
        note_date=note.note_date,
        total_amount=note.total_amount,
        note=note.note,
        status=note.status,
        details=details,
    )


@router.get("", response_model=List[ImportNoteResponse], include_in_schema=False)
@router.get(
    "/",
    response_model=List[ImportNoteResponse],
    summary="Lấy danh sách phiếu nhập kho",
)
def get_import_notes(
    search: Optional[str] = Query(None, description="Tìm theo mã phiếu nhập"),
    supplier_id: Optional[int] = Query(None, description="Lọc theo ID nhà cung cấp"),
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc theo trạng thái (COMPLETED, CANCELLED)"),
    skip: int = Query(0, ge=0, description="Số lượng bỏ qua"),
    limit: int = Query(50, ge=1, le=200, description="Số lượng lấy tối đa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Truy vấn danh sách phiếu nhập kèm phân trang và tìm kiếm."""
    query = (
        db.query(ImportNote)
        .options(
            joinedload(ImportNote.supplier),
            joinedload(ImportNote.creator),
            joinedload(ImportNote.details),
        )
    )

    if search:
        query = query.filter(ImportNote.code.ilike(f"%{search.strip()}%"))
    if supplier_id is not None:
        query = query.filter(ImportNote.supplier_id == supplier_id)
    if status_filter:
        query = query.filter(ImportNote.status == status_filter.strip().upper())

    notes = query.order_by(ImportNote.id.desc()).offset(skip).limit(limit).all()
    return [_serialize_import_note(n) for n in notes]


@router.get(
    "/{import_note_id}",
    response_model=ImportNoteResponse,
    summary="Lấy chi tiết một phiếu nhập kho",
)
def get_import_note_by_id(
    import_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một phiếu nhập kèm toàn bộ danh sách hàng hóa và đơn giá."""
    note = (
        db.query(ImportNote)
        .options(
            joinedload(ImportNote.supplier),
            joinedload(ImportNote.creator),
            joinedload(ImportNote.details),
        )
        .filter(ImportNote.id == import_note_id)
        .first()
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu nhập với ID {import_note_id}.",
        )
    return _serialize_import_note(note)


@router.post("", response_model=ImportNoteResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post(
    "/",
    response_model=ImportNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lập phiếu nhập kho (ACID Transaction)",
)
def create_new_import_note(
    note_in: ImportNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Lập phiếu nhập kho: Tăng tồn kho và tự động ghi Thẻ kho (StockLedger)."""
    note = create_import_note(db=db, note_in=note_in, current_user_id=current_user.id)
    return _serialize_import_note(note)


@router.post(
    "/{import_note_id}/cancel",
    response_model=ImportNoteResponse,
    summary="Hủy phiếu nhập kho (Kèm Guard-check chống tồn âm)",
)
def cancel_existing_import_note(
    import_note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Hủy phiếu nhập kho.

    Nếu hàng đã bị xuất đi dẫn đến tồn kho hiện tại không đủ để hoàn trả,
    hệ thống sẽ từ chối và hướng dẫn tạo phiếu Điều chỉnh tồn kho (Stock Adjustment).
    """
    note = cancel_import_note(db=db, import_note_id=import_note_id, current_user_id=current_user.id)
    return _serialize_import_note(note)
