"""API Endpoints cho tra cứu Thẻ kho (Stock Ledger), Xuất Excel và Điều chỉnh kiểm kê tồn kho (Stock Adjustment)."""

import calendar
from datetime import date, datetime, timedelta, timezone
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
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


@router.get(
    "/export-excel",
    summary="Xuất sổ cái Thẻ kho ra file Excel (.xlsx) gồm 2 sheet Nhập kho và Xuất kho",
)
def export_stock_ledger_excel(
    period: str = Query(
        "day",
        description="Phạm vi thời gian: day (Theo ngày), week (Theo tuần), month (Theo tháng)",
    ),
    target_date: Optional[date] = Query(
        None,
        description="Ngày mốc định dạng YYYY-MM-DD (Mặc định: ngày hôm nay theo giờ Việt Nam)",
    ),
    product_id: Optional[int] = Query(None, description="Lọc theo ID mặt hàng (nếu có)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xuất dữ liệu Thẻ kho trong phạm vi Ngày / Tuần / Tháng ra file .xlsx gồm 2 sheet: Nhập kho và Xuất kho."""
    vn_tz = timezone(timedelta(hours=7))
    now_vn = datetime.now(vn_tz)
    chosen_date = target_date or now_vn.date()
    mode = (period or "day").strip().lower()

    if mode == "day":
        start_day = chosen_date
        end_day = chosen_date
        period_label = f"Ngày {chosen_date.strftime('%d/%m/%Y')}"
        file_suffix = f"ngay_{chosen_date.strftime('%Y%m%d')}"
    elif mode == "week":
        start_day = chosen_date - timedelta(days=chosen_date.weekday())
        end_day = start_day + timedelta(days=6)
        period_label = f"Tuần {start_day.strftime('%d/%m/%Y')} - {end_day.strftime('%d/%m/%Y')}"
        file_suffix = f"tuan_{start_day.strftime('%Y%m%d')}_{end_day.strftime('%Y%m%d')}"
    elif mode == "month":
        start_day = date(chosen_date.year, chosen_date.month, 1)
        last_day_num = calendar.monthrange(chosen_date.year, chosen_date.month)[1]
        end_day = date(chosen_date.year, chosen_date.month, last_day_num)
        period_label = f"Tháng {chosen_date.month:02d}/{chosen_date.year}"
        file_suffix = f"thang_{chosen_date.year}{chosen_date.month:02d}"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tham số 'period' không hợp lệ. Chỉ chấp nhận: day, week, month.",
        )

    start_dt = datetime(start_day.year, start_day.month, start_day.day, 0, 0, 0)
    end_dt = datetime(end_day.year, end_day.month, end_day.day, 23, 59, 59, 999999)

    query = (
        db.query(StockLedger)
        .options(
            joinedload(StockLedger.product),
            joinedload(StockLedger.creator),
        )
        .filter(
            StockLedger.transaction_date >= start_dt,
            StockLedger.transaction_date <= end_dt,
        )
    )
    if product_id is not None:
        query = query.filter(StockLedger.product_id == product_id)

    entries = query.order_by(StockLedger.transaction_date.desc(), StockLedger.id.desc()).all()

    import_entries = [
        e for e in entries
        if e.transaction_type == "IMPORT" or (e.transaction_type == "ADJUSTMENT" and e.quantity_change > 0)
    ]
    export_entries = [
        e for e in entries
        if e.transaction_type == "EXPORT" or (e.transaction_type == "ADJUSTMENT" and e.quantity_change < 0)
    ]

    wb = Workbook()
    ws_import = wb.active
    ws_import.title = "Nhập kho"
    ws_export = wb.create_sheet(title="Xuất kho")

    # Định dạng chung cho bảng Excel
    title_font = Font(name="Arial", size=13, bold=True, color="1E293B")
    subtitle_font = Font(name="Arial", size=10, italic=True, color="475569")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    cell_font = Font(name="Arial", size=10, color="0F172A")
    bold_cell_font = Font(name="Arial", size=10, bold=True, color="0F172A")

    thin_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    headers = [
        "Thời gian",
        "Tên hàng hóa",
        "Mã chứng từ",
        "Số lượng",
        "Tồn sau giao dịch",
        "Người thực hiện",
        "Ghi chú",
    ]
    col_widths = [22, 38, 22, 15, 18, 24, 42]

    def populate_sheet(ws, sheet_title: str, rows: List[StockLedger], header_hex: str):
        ws.merge_cells("A1:G1")
        ws["A1"] = f"SỔ CÁI THẺ KHO - {sheet_title.upper()} ({period_label.upper()})"
        ws["A1"].font = title_font
        ws["A1"].alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[1].height = 24

        ws.merge_cells("A2:G2")
        ws["A2"] = (
            f"Người xuất báo cáo: {current_user.full_name} ({current_user.username}) | "
            f"Thời điểm xuất: {now_vn.strftime('%d/%m/%Y %H:%M:%S')}"
        )
        ws["A2"].font = subtitle_font
        ws["A2"].alignment = Alignment(horizontal="left", vertical="center")
        ws.row_dimensions[2].height = 18

        header_fill = PatternFill(start_color=header_hex, end_color=header_hex, fill_type="solid")
        ws.row_dimensions[4].height = 24
        for col_idx, h_text in enumerate(headers, start=1):
            cell = ws.cell(row=4, column=col_idx, value=h_text)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = cell_border
            cell.alignment = Alignment(
                horizontal="center" if col_idx in (1, 3, 4, 5) else "left",
                vertical="center",
            )

        for row_idx, item in enumerate(rows, start=5):
            ws.row_dimensions[row_idx].height = 20
            time_str = item.transaction_date.strftime("%d/%m/%Y %H:%M:%S") if item.transaction_date else "-"
            prod_name = item.product.name if item.product else f"Mặt hàng #{item.product_id}"
            creator_name = item.creator.full_name if item.creator else "Hệ thống"
            qty = abs(int(item.quantity_change))
            note_text = item.note or "-"

            row_values = [
                time_str,
                prod_name,
                item.reference_code,
                qty,
                int(item.balance_after),
                creator_name,
                note_text,
            ]
            for col_idx, val in enumerate(row_values, start=1):
                c = ws.cell(row=row_idx, column=col_idx, value=val)
                c.font = bold_cell_font if col_idx in (4, 5) else cell_font
                c.border = cell_border
                if col_idx in (1, 3):
                    c.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx in (4, 5):
                    c.alignment = Alignment(horizontal="right", vertical="center")
                    c.number_format = "#,##0"
                else:
                    c.alignment = Alignment(horizontal="left", vertical="center")

        for idx, width in enumerate(col_widths, start=1):
            col_letter = ws.cell(row=4, column=idx).column_letter
            ws.column_dimensions[col_letter].width = width

    populate_sheet(ws_import, "Bảng Nhập Kho", import_entries, "166534")
    populate_sheet(ws_export, "Bảng Xuất Kho", export_entries, "1E40AF")

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"the_kho_{file_suffix}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


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
