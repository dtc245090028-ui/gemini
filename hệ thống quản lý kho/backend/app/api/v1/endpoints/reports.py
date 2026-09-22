"""API Endpoints cho Báo cáo Nhập - Xuất - Tồn và Cảnh báo Tồn kho."""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductResponse
from app.schemas.report import InventorySummaryReport
from app.services.inventory_service import get_inventory_summary_report

router = APIRouter(prefix="/reports", tags=["Báo cáo & Thống kê Kho (Reports)"])


@router.get(
    "/inventory-summary",
    response_model=InventorySummaryReport,
    summary="Báo cáo Nhập - Xuất - Tồn theo kỳ (Công thức chuẩn kế toán)",
)
def get_inventory_summary(
    from_date: Optional[datetime] = Query(
        None,
        description="Ngày bắt đầu kỳ báo cáo (Mặc định: 30 ngày trước)",
    ),
    to_date: Optional[datetime] = Query(
        None,
        description="Ngày kết thúc kỳ báo cáo (Mặc định: Hiện tại)",
    ),
    category_id: Optional[int] = Query(None, description="Lọc theo nhóm hàng"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tính toán báo cáo Nhập - Xuất - Tồn chính xác từ Thẻ kho (StockLedger).

    Luôn thỏa mãn công thức: Tồn đầu kỳ + Nhập trong kỳ - Xuất trong kỳ = Tồn cuối kỳ.
    """
    now = datetime.now(timezone.utc)
    if to_date is None:
        to_date = now
    if from_date is None:
        from_date = to_date - timedelta(days=30)

    report = get_inventory_summary_report(
        db=db,
        from_date=from_date,
        to_date=to_date,
        category_id=category_id,
    )
    return report


@router.get(
    "/low-stock",
    response_model=List[ProductResponse],
    summary="Danh sách các mặt hàng dưới định mức tồn tối thiểu",
)
def get_low_stock_alerts(
    category_id: Optional[int] = Query(None, description="Lọc theo nhóm hàng"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách các mặt hàng cần nhập thêm (current_stock <= min_stock)."""
    query = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(
            Product.current_stock <= Product.min_stock,
            Product.status == "ACTIVE",
        )
    )
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    products = query.order_by(Product.current_stock.asc()).all()
    return products
