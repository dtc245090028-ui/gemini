"""API Endpoints cho Báo cáo Nhập - Xuất - Tồn và Cảnh báo Tồn kho."""

import io
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.models.import_note import ImportNote
from app.models.export_note import ExportNote

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
    "/inventory-summary/export-excel",
    summary="Xuất Báo cáo Nhập - Xuất - Tồn ra file Excel (.xlsx)",
)
def export_inventory_summary_excel(
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
    """Xuất bảng tổng hợp Nhập - Xuất - Tồn của tất cả mặt hàng theo kỳ ra tệp Excel."""
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

    wb = Workbook()
    ws = wb.active
    ws.title = "Nhap_Xuat_Ton"
    ws.views.sheetView[0].showGridLines = True

    # Định nghĩa styles
    title_font = Font(name="Arial", size=14, bold=True, color="1E293B")
    subtitle_font = Font(name="Arial", size=10, italic=True, color="64748B")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    total_font = Font(name="Arial", size=10, bold=True, color="0F172A")
    total_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    data_font = Font(name="Arial", size=10, color="000000")

    thin_border_side = Side(style="thin", color="CBD5E1")
    cell_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=thin_border_side,
    )
    total_border = Border(
        left=thin_border_side,
        right=thin_border_side,
        top=thin_border_side,
        bottom=Side(style="double", color="0F172A"),
    )

    # Tiêu đề báo cáo
    ws.merge_cells("A1:K1")
    t_cell = ws["A1"]
    t_cell.value = "BÁO CÁO NHẬP - XUẤT - TỒN KHO"
    t_cell.font = title_font
    t_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 25

    # Phụ đề ngày
    ws.merge_cells("A2:K2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Kỳ báo cáo: Từ {from_date.strftime('%d/%m/%Y')} đến {to_date.strftime('%d/%m/%Y')}"
    sub_cell.font = subtitle_font
    sub_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 18

    # Tiêu đề cột
    headers = [
        "STT",
        "Mã hàng",
        "Tên hàng hóa",
        "ĐVT",
        "Tồn đầu",
        "Nhập",
        "Xuất",
        "Điều chỉnh",
        "Tồn cuối",
        "Đơn giá (VNĐ)",
        "Thành tiền (VNĐ)",
    ]
    ws.row_dimensions[4].height = 24
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=4, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.border = cell_border
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Nạp dữ liệu sản phẩm
    current_row = 5
    for idx, it in enumerate(report.items, start=1):
        ws.row_dimensions[current_row].height = 20
        row_vals = [
            idx,
            it.product_code,
            it.product_name,
            it.unit,
            it.opening_stock,
            it.total_import,
            it.total_export,
            it.adjustment,
            it.closing_stock,
            it.standard_price,
            it.total_value,
        ]
        for col_idx, val in enumerate(row_vals, start=1):
            c = ws.cell(row=current_row, column=col_idx, value=val)
            c.font = data_font
            c.border = cell_border
            if col_idx in (1, 4):
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in (2, 3):
                c.alignment = Alignment(horizontal="left", vertical="center")
            else:
                c.alignment = Alignment(horizontal="right", vertical="center")
                c.number_format = "#,##0"
        current_row += 1

    # Dòng tổng cộng cuối bảng
    ws.row_dimensions[current_row].height = 22
    summary_vals = [
        "TỔNG CỘNG",
        "",
        f"({report.total_products} sản phẩm)",
        "",
        report.total_opening,
        report.total_import,
        report.total_export,
        report.total_adjustment,
        report.total_closing,
        "",
        report.total_inventory_value,
    ]
    for col_idx, val in enumerate(summary_vals, start=1):
        c = ws.cell(row=current_row, column=col_idx, value=val)
        c.font = total_font
        c.fill = total_fill
        c.border = total_border
        if col_idx in (1, 3):
            c.alignment = Alignment(horizontal="center", vertical="center")
        elif col_idx in (5, 6, 7, 8, 9, 11):
            c.alignment = Alignment(horizontal="right", vertical="center")
            c.number_format = "#,##0"
        else:
            c.alignment = Alignment(horizontal="center", vertical="center")

    # Độ rộng cột
    col_widths = [6, 12, 36, 10, 12, 12, 12, 12, 12, 16, 20]
    for idx, width in enumerate(col_widths, start=1):
        col_letter = ws.cell(row=4, column=idx).column_letter
        ws.column_dimensions[col_letter].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"bao_cao_nhap_xuat_ton_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


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


@router.get(
    "/kpi-summary",
    summary="Thống kê tổng quan KPI kho hàng cho Dashboard",
)
def get_kpi_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy số liệu tổng hợp chính xác theo thời gian thực cho Bảng điều khiển (Dashboard)."""
    total_products = db.query(Product).count()
    total_stock = db.query(func.coalesce(func.sum(Product.current_stock), 0)).scalar()
    low_stock_count = (
        db.query(Product)
        .filter(
            Product.current_stock <= Product.min_stock,
            Product.status == "ACTIVE",
        )
        .count()
    )
    total_import_notes = db.query(ImportNote).count()
    total_export_notes = db.query(ExportNote).count()

    return {
        "total_products": total_products,
        "total_stock": int(total_stock or 0),
        "low_stock_count": low_stock_count,
        "total_import_notes": total_import_notes,
        "total_export_notes": total_export_notes,
    }
