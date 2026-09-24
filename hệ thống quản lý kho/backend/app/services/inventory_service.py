"""Dịch vụ nghiệp vụ Quản lý Kho: Nhập kho, Xuất kho, Thẻ kho và Giao dịch ACID."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.import_note import ImportNote, ImportNoteDetail
from app.models.product import Product
from app.models.stock_ledger import StockLedger
from app.models.supplier import Supplier
from app.schemas.export_note import ExportNoteCreate
from app.schemas.import_note import ImportNoteCreate
from app.schemas.report import InventorySummaryItem, InventorySummaryReport
from app.schemas.stock_ledger import StockAdjustmentCreate, StockAdjustmentResponse


def generate_note_code(db: Session, prefix: str, model_class, code_column) -> str:
    """Sinh mã chứng từ tự động dạng {PREFIX}-YYYYMMDD-XXXX (ví dụ: PN-20260922-0001)."""
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    code_pattern = f"{prefix}-{today_str}-%"

    # Tìm mã lớn nhất trong ngày hiện tại
    last_code = (
        db.query(func.max(code_column))
        .filter(code_column.like(code_pattern))
        .scalar()
    )

    if last_code:
        try:
            seq_part = last_code.split("-")[-1]
            next_seq = int(seq_part) + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}-{today_str}-{next_seq:04d}"


def create_import_note(
    db: Session,
    note_in: ImportNoteCreate,
    current_user_id: int,
) -> ImportNote:
    """Lập phiếu nhập kho trong một Transaction ACID duy nhất.

    - Tăng current_stock của từng mặt hàng.
    - Tự động ghi nhận bản ghi Thẻ kho (StockLedger).
    - Áp dụng Retry Pattern xử lý đụng độ mã tự sinh.
    """
    # 1. Kiểm tra nhà cung cấp
    supplier = db.query(Supplier).filter(Supplier.id == note_in.supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nhà cung cấp với ID {note_in.supplier_id} không tồn tại trong hệ thống.",
        )

    # 2. Kiểm tra các mặt hàng nhập
    product_map = {}
    for item in note_in.details:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mặt hàng với ID {item.product_id} không tồn tại.",
            )
        if product.status == "DISCONTINUED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mặt hàng '{product.name}' ({product.code}) đã ngừng kinh doanh, không thể nhập kho.",
            )
        product_map[item.product_id] = product

    # 3. Tính toán tổng tiền
    total_amount = sum(item.quantity * item.unit_price for item in note_in.details)
    now = datetime.now(timezone.utc)

    # 4. Thực thi Transaction với Retry Pattern (Optimistic Concurrency)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if note_in.code:
                note_code = note_in.code.strip().upper()
                existing = db.query(ImportNote).filter(ImportNote.code == note_code).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Mã phiếu nhập '{note_code}' đã tồn tại.",
                    )
            else:
                note_code = generate_note_code(db, "PN", ImportNote, ImportNote.code)

            import_note = ImportNote(
                code=note_code,
                supplier_id=note_in.supplier_id,
                created_by=current_user_id,
                note_date=now,
                total_amount=total_amount,
                note=note_in.note.strip() if note_in.note else None,
                status="COMPLETED",
            )
            db.add(import_note)
            db.flush()  # Sinh import_note.id

            for item in note_in.details:
                subtotal = item.quantity * item.unit_price
                detail = ImportNoteDetail(
                    import_note_id=import_note.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=subtotal,
                )
                db.add(detail)

                # Cập nhật tồn kho
                product = product_map[item.product_id]
                product.current_stock += item.quantity

                # Ghi Thẻ kho (StockLedger)
                ledger_entry = StockLedger(
                    product_id=product.id,
                    transaction_type="IMPORT",
                    reference_code=import_note.code,
                    quantity_change=item.quantity,
                    balance_after=product.current_stock,
                    created_by=current_user_id,
                    transaction_date=now,
                    note=f"Nhập kho theo phiếu {import_note.code}",
                )
                db.add(ledger_entry)

            db.commit()
            db.refresh(import_note)
            return import_note

        except IntegrityError as exc:
            db.rollback()
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Xung đột mã phiếu do nhiều giao dịch đồng thời. Vui lòng thử lại.",
                )


def create_export_note(
    db: Session,
    note_in: ExportNoteCreate,
    current_user_id: int,
) -> ExportNote:
    """Lập phiếu xuất kho trong một Transaction ACID duy nhất.

    - Kiểm tra nghiêm ngặt chống tồn kho âm (Rollback 100% nếu thiếu hàng).
    - Giảm current_stock của từng mặt hàng.
    - Tự động ghi nhận bản ghi Thẻ kho (StockLedger).
    """
    # 1. Kiểm tra tồn kho cho tất cả sản phẩm TRƯỚC KHI thực hiện bất kỳ thay đổi nào
    product_map = {}
    for item in note_in.details:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mặt hàng với ID {item.product_id} không tồn tại.",
            )
        if product.status == "DISCONTINUED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mặt hàng '{product.name}' ({product.code}) đã ngừng kinh doanh.",
            )

        # CHỐNG TỒN ÂM: Kiểm tra tồn kho tức thời
        if product.current_stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Không đủ hàng tồn kho cho sản phẩm '{product.name}' (Mã SKU: {product.code}). "
                    f"Số lượng tồn hiện có: {product.current_stock}, Yêu cầu xuất: {item.quantity}. "
                    f"Thiếu hụt: {item.quantity - product.current_stock}. Giao dịch xuất kho đã bị hủy bỏ."
                ),
            )
        product_map[item.product_id] = product

    # 2. Tính tổng tiền
    total_amount = sum(item.quantity * item.unit_price for item in note_in.details)
    now = datetime.now(timezone.utc)

    # 3. Thực thi Transaction với Retry Pattern
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if note_in.code:
                note_code = note_in.code.strip().upper()
                existing = db.query(ExportNote).filter(ExportNote.code == note_code).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Mã phiếu xuất '{note_code}' đã tồn tại.",
                    )
            else:
                note_code = generate_note_code(db, "PX", ExportNote, ExportNote.code)

            export_note = ExportNote(
                code=note_code,
                recipient_name=note_in.recipient_name.strip(),
                created_by=current_user_id,
                note_date=now,
                total_amount=total_amount,
                note=note_in.note.strip() if note_in.note else None,
                status="CONFIRMED",
            )
            db.add(export_note)
            db.flush()

            for item in note_in.details:
                subtotal = item.quantity * item.unit_price
                detail = ExportNoteDetail(
                    export_note_id=export_note.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=subtotal,
                )
                db.add(detail)

            # Ở trạng thái CONFIRMED: Chưa trừ tồn kho thực tế và chưa ghi nhận Thẻ kho.
            # Tồn kho và Thẻ kho sẽ chỉ được xử lý khi chuyển sang bước SHIPPING (Giao hàng).
            db.commit()
            db.refresh(export_note)
            return export_note

        except IntegrityError as exc:
            db.rollback()
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Xung đột mã phiếu do nhiều giao dịch đồng thời. Vui lòng thử lại.",
                )


def cancel_import_note(
    db: Session,
    import_note_id: int,
    current_user_id: int,
) -> ImportNote:
    """Hủy phiếu nhập kho an toàn (Phương án B kèm Guard-check chống tồn âm).

    - Kiểm tra nếu hàng đã xuất bớt dẫn đến tồn kho hiện tại < số lượng cần hoàn trả -> Từ chối.
    - Nếu đủ hàng: Đổi trạng thái sang CANCELLED, trừ lại tồn kho và ghi Thẻ kho ADJUSTMENT.
    """
    import_note = (
        db.query(ImportNote)
        .options(joinedload(ImportNote.details))
        .filter(ImportNote.id == import_note_id)
        .first()
    )
    if not import_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu nhập với ID {import_note_id}.",
        )

    if import_note.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiếu nhập '{import_note.code}' đã bị hủy trước đó.",
        )

    # GUARD-CHECK CHỐNG TỒN ÂM:
    # Nếu hàng từ phiếu nhập này đã bị xuất đi, việc hủy sẽ làm tồn kho bị âm!
    for detail in import_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        if product.current_stock < detail.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Không thể hủy phiếu nhập '{import_note.code}' vì mặt hàng '{product.name}' "
                    f"chỉ còn tồn {product.current_stock} cái trong kho (nhỏ hơn {detail.quantity} cái cần hoàn tác) "
                    f"do đã phát sinh các phiếu xuất hàng tiếp sau. "
                    f"Vui lòng sử dụng tính năng 'Điều chỉnh tồn kho (Stock Adjustment)' để cân bằng số lượng thực tế."
                ),
            )

    # Thực hiện hủy an toàn
    now = datetime.now(timezone.utc)
    import_note.status = "CANCELLED"

    for detail in import_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        product.current_stock -= detail.quantity

        ledger_entry = StockLedger(
            product_id=product.id,
            transaction_type="ADJUSTMENT",
            reference_code=f"CANCEL-{import_note.code}",
            quantity_change=-detail.quantity,
            balance_after=product.current_stock,
            created_by=current_user_id,
            transaction_date=now,
            note=f"Hoàn tác do hủy phiếu nhập {import_note.code}",
        )
        db.add(ledger_entry)

    db.commit()
    db.refresh(import_note)
    return import_note


def ship_export_note(
    db: Session,
    export_note_id: int,
    current_user_id: int,
) -> ExportNote:
    """Chuyển trạng thái phiếu xuất sang Đang Giao Hàng (SHIPPING).

    - Kiểm tra nghiêm ngặt chống tồn âm (Guard-check tại thời điểm xuất kho thực tế).
    - Giảm current_stock của từng mặt hàng.
    - Ghi nhận bản ghi Thẻ kho (StockLedger) loại EXPORT.
    """
    export_note = (
        db.query(ExportNote)
        .options(joinedload(ExportNote.details).joinedload(ExportNoteDetail.product))
        .filter(ExportNote.id == export_note_id)
        .first()
    )
    if not export_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu xuất với ID {export_note_id}.",
        )

    if export_note.status != "CONFIRMED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiếu xuất '{export_note.code}' đang ở trạng thái '{export_note.status}'. Chỉ có thể chuyển sang giao hàng từ trạng thái 'CONFIRMED' (Đã xác nhận).",
        )

    # 1. Kiểm tra tồn kho tức thời cho toàn bộ sản phẩm TRƯỚC KHI trừ
    for detail in export_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mặt hàng với ID {detail.product_id} không tồn tại.",
            )
        if product.current_stock < detail.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Không đủ hàng tồn kho cho sản phẩm '{product.name}' (Mã SKU: {product.code}) để giao hàng. "
                    f"Số lượng tồn hiện có: {product.current_stock}, Yêu cầu xuất: {detail.quantity}. "
                    f"Thiếu hụt: {detail.quantity - product.current_stock}. Không thể xuất kho."
                ),
            )

    # 2. Trừ tồn kho và ghi Thẻ kho
    now = datetime.now(timezone.utc)
    export_note.status = "SHIPPING"

    for detail in export_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        product.current_stock -= detail.quantity

        ledger_entry = StockLedger(
            product_id=product.id,
            transaction_type="EXPORT",
            reference_code=export_note.code,
            quantity_change=-detail.quantity,
            balance_after=product.current_stock,
            created_by=current_user_id,
            transaction_date=now,
            note=f"Xuất kho giao cho {export_note.recipient_name} theo phiếu {export_note.code}",
        )
        db.add(ledger_entry)

    db.commit()
    db.refresh(export_note)
    return export_note


def complete_export_note(
    db: Session,
    export_note_id: int,
    current_user_id: int,
) -> ExportNote:
    """Xác nhận hoàn thành giao hàng (COMPLETED).

    - Chuyển trạng thái từ SHIPPING -> COMPLETED.
    - Hàng đã được trừ tồn kho từ bước SHIPPING.
    """
    export_note = (
        db.query(ExportNote)
        .options(joinedload(ExportNote.details))
        .filter(ExportNote.id == export_note_id)
        .first()
    )
    if not export_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu xuất với ID {export_note_id}.",
        )

    if export_note.status != "SHIPPING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiếu xuất '{export_note.code}' đang ở trạng thái '{export_note.status}'. Chỉ có thể hoàn thành từ trạng thái 'SHIPPING' (Đang giao).",
        )

    export_note.status = "COMPLETED"
    db.commit()
    db.refresh(export_note)
    return export_note


def cancel_export_note(
    db: Session,
    export_note_id: int,
    current_user_id: int,
) -> tuple[Optional[ExportNote], bool]:
    """Hủy phiếu xuất kho an toàn theo nghiệp vụ:
    - Nếu trạng thái là CONFIRMED (Chưa trừ kho): Xóa hoàn toàn bản ghi khỏi CSDL (không lưu vết phiếu rác).
    - Nếu trạng thái là SHIPPING hoặc COMPLETED: Đổi sang CANCELLED, hoàn trả số lượng vào kho và ghi Thẻ kho ADJUSTMENT.
    Trả về: (export_note, was_deleted)
    """
    export_note = (
        db.query(ExportNote)
        .options(joinedload(ExportNote.details))
        .filter(ExportNote.id == export_note_id)
        .first()
    )
    if not export_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu xuất với ID {export_note_id}.",
        )

    if export_note.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiếu xuất '{export_note.code}' đã bị hủy trước đó.",
        )

    if export_note.status == "CONFIRMED":
        # Hàng chưa xuất, chưa trừ tồn kho, chưa có thẻ kho -> Xóa hẳn khỏi CSDL
        db.delete(export_note)
        db.commit()
        return None, True

    # Trạng thái SHIPPING hoặc COMPLETED: Đã trừ kho -> Cần hoàn kho và lưu vết phiếu CANCELLED
    now = datetime.now(timezone.utc)
    export_note.status = "CANCELLED"

    for detail in export_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        product.current_stock += detail.quantity

        ledger_entry = StockLedger(
            product_id=product.id,
            transaction_type="ADJUSTMENT",
            reference_code=f"CANCEL-{export_note.code}",
            quantity_change=detail.quantity,
            balance_after=product.current_stock,
            created_by=current_user_id,
            transaction_date=now,
            note=f"Hoàn tác do hủy phiếu xuất {export_note.code}",
        )
        db.add(ledger_entry)

    db.commit()
    db.refresh(export_note)
    return export_note, False


def delete_export_note(
    db: Session,
    export_note_id: int,
    current_user_id: int,
) -> None:
    """Xóa vĩnh viễn phiếu xuất kho (Chỉ cho phép khi ở trạng thái CONFIRMED)."""
    export_note = db.query(ExportNote).filter(ExportNote.id == export_note_id).first()
    if not export_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiếu xuất với ID {export_note_id}.",
        )

    if export_note.status != "CONFIRMED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chỉ có thể xóa trực tiếp phiếu xuất ở trạng thái 'CONFIRMED' (Chưa xuất kho). Phiếu '{export_note.code}' đang ở trạng thái '{export_note.status}', vui lòng sử dụng chức năng Hủy đơn.",
        )

    db.delete(export_note)
    db.commit()


def adjust_stock(
    db: Session,
    adj_in: StockAdjustmentCreate,
    current_user_id: int,
) -> StockAdjustmentResponse:
    """Lối thoát kiểm kê / Điều chỉnh tồn kho thủ công (Phương án A lối thoát khi guard check từ chối)."""
    product = db.query(Product).filter(Product.id == adj_in.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm với ID {adj_in.product_id}.",
        )

    old_stock = product.current_stock
    difference = adj_in.actual_stock - old_stock
    now = datetime.now(timezone.utc)
    ref_code = f"ADJ-{now.strftime('%Y%m%d%H%M%S')}-{product.id}"

    product.current_stock = adj_in.actual_stock

    ledger_entry = StockLedger(
        product_id=product.id,
        transaction_type="ADJUSTMENT",
        reference_code=ref_code,
        quantity_change=difference,
        balance_after=adj_in.actual_stock,
        created_by=current_user_id,
        transaction_date=now,
        note=f"Điều chỉnh kiểm kê: {adj_in.reason.strip()}",
    )
    db.add(ledger_entry)
    db.commit()

    return StockAdjustmentResponse(
        success=True,
        product_id=product.id,
        product_code=product.code,
        product_name=product.name,
        old_stock=old_stock,
        actual_stock=adj_in.actual_stock,
        difference=difference,
        reference_code=ref_code,
        message=f"Đã điều chỉnh tồn kho sản phẩm '{product.name}' từ {old_stock} sang {adj_in.actual_stock} (Chênh lệch: {difference:+d}).",
    )


def get_inventory_summary_report(
    db: Session,
    from_date: datetime,
    to_date: datetime,
    category_id: Optional[int] = None,
) -> InventorySummaryReport:
    """Tính toán Báo cáo Nhập - Xuất - Tồn chính xác từ Thẻ kho (StockLedger).

    Công thức kế toán bất biến:
    Tồn đầu kỳ + Nhập trong kỳ - Xuất trong kỳ = Tồn cuối kỳ
    """
    # Chuẩn hóa về naive UTC datetime để so sánh chính xác với SQLite DateTime
    if from_date.tzinfo is not None:
        from_date = from_date.astimezone(timezone.utc).replace(tzinfo=None)
    if to_date.tzinfo is not None:
        to_date = to_date.astimezone(timezone.utc).replace(tzinfo=None)

    prod_query = db.query(Product).options(joinedload(Product.category))
    if category_id is not None:
        prod_query = prod_query.filter(Product.category_id == category_id)
    products = prod_query.all()

    items: List[InventorySummaryItem] = []
    total_opening = 0
    total_import = 0
    total_export = 0
    total_closing = 0
    total_inventory_value = 0.0

    for product in products:
        # 1. Tồn đầu kỳ: Số dư balance_after của giao dịch gần nhất TRƯỚC from_date
        last_entry_before = (
            db.query(StockLedger)
            .filter(
                StockLedger.product_id == product.id,
                StockLedger.transaction_date < from_date,
            )
            .order_by(StockLedger.transaction_date.desc(), StockLedger.id.desc())
            .first()
        )
        opening_stock = last_entry_before.balance_after if last_entry_before else 0

        # 2. Biến động trong kỳ [from_date, to_date]
        period_entries = (
            db.query(StockLedger)
            .filter(
                StockLedger.product_id == product.id,
                StockLedger.transaction_date >= from_date,
                StockLedger.transaction_date <= to_date,
            )
            .all()
        )

        period_import = sum(e.quantity_change for e in period_entries if e.quantity_change > 0)
        period_export = sum(abs(e.quantity_change) for e in period_entries if e.quantity_change < 0)

        # 3. Tồn cuối kỳ = Tồn đầu + Nhập - Xuất
        closing_stock = opening_stock + period_import - period_export
        total_val = closing_stock * product.standard_price

        items.append(
            InventorySummaryItem(
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                category_name=product.category.name if product.category else None,
                unit=product.unit,
                opening_stock=opening_stock,
                total_import=period_import,
                total_export=period_export,
                closing_stock=closing_stock,
                standard_price=product.standard_price,
                total_value=total_val,
                is_low_stock=closing_stock <= product.min_stock,
            )
        )

        total_opening += opening_stock
        total_import += period_import
        total_export += period_export
        total_closing += closing_stock
        total_inventory_value += total_val

    return InventorySummaryReport(
        from_date=from_date,
        to_date=to_date,
        total_products=len(products),
        total_opening=total_opening,
        total_import=total_import,
        total_export=total_export,
        total_closing=total_closing,
        total_inventory_value=total_inventory_value,
        items=items,
    )
