"""API Endpoints cho tra cứu Thẻ kho (Stock Ledger) và Điều chỉnh kiểm kê tồn kho (Stock Adjustment)."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.stock_ledger import StockLedger
from app.models.user import User
from app.schemas.stock_ledger import (
    StockAdjustmentCreate,
    StockAdjustmentResponse,
    StockLedgerResponse,
)
from app.services.inventory_service import adjust_stock

router = APIRouter(prefix="/stock-ledger", tags=["Thẻ kho & Điều chỉnh (Stock Ledger)"])


@router.get("", response_model=List[StockLedgerResponse], include_in_schema=False)
@router.get(
    "/",
    response_model=List[StockLedgerResponse],
    summary="Tra cứu lịch sử Thẻ kho (Audit Trail)",
)
def get_stock_ledger_entries(
    product_id: Optional[int] = Query(None, description="Lọc theo ID mặt hàng"),
    transaction_type: Optional[str] = Query(None, description="Lọc theo loại giao dịch: IMPORT, EXPORT, ADJUSTMENT"),
    from_date: Optional[datetime] = Query(None, description="Từ ngày"),
    to_date: Optional[datetime] = Query(None, description="Đến ngày"),
    skip: int = Query(0, ge=0, description="Số lượng bỏ qua"),
    limit: int = Query(100, ge=1, le=500, description="Số lượng lấy tối đa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Truy vấn sổ kiểm toán Thẻ kho phục vụ truy vết lịch sử biến động từng giây."""
    query = (
        db.query(StockLedger)
        .options(
            joinedload(StockLedger.product),
            joinedload(StockLedger.creator),
        )
    )

    if product_id is not None:
        query = query.filter(StockLedger.product_id == product_id)
    if transaction_type:
        query = query.filter(StockLedger.transaction_type == transaction_type.strip().upper())
    if from_date:
        query = query.filter(StockLedger.transaction_date >= from_date)
    if to_date:
        query = query.filter(StockLedger.transaction_date <= to_date)

    entries = (
        query.order_by(StockLedger.transaction_date.desc(), StockLedger.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for e in entries:
        results.append(
            StockLedgerResponse(
                id=e.id,
                product_id=e.product_id,
                transaction_type=e.transaction_type,
                reference_code=e.reference_code,
                quantity_change=e.quantity_change,
                balance_after=e.balance_after,
                created_by=e.created_by,
                transaction_date=e.transaction_date,
                note=e.note,
                product_name=e.product.name if e.product else None,
                product_code=e.product.code if e.product else None,
                creator_name=e.creator.full_name if e.creator else None,
            )
        )
    return results


@router.post(
    "/adjust",
    response_model=StockAdjustmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Lập phiếu điều chỉnh kiểm kê tồn kho (Lối thoát khi hủy phiếu bị chặn hoặc kiểm kê thực tế)",
)
def create_stock_adjustment(
    adj_in: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Điều chỉnh số lượng tồn kho theo số lượng thực tế sau kiểm kê.

    - Cập nhật current_stock của sản phẩm bằng actual_stock.
    - Tự động ghi bản ghi Thẻ kho ADJUSTMENT với chênh lệch và lý do.
    """
    return adjust_stock(db=db, adj_in=adj_in, current_user_id=current_user.id)
