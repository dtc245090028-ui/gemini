from app.core.metrics import write_metrics
from app.core.events import broadcaster
"""Dịch vụ nghiệp vụ Quản lý Kho: Nhập kho, Xuất kho, Thẻ kho và Giao dịch ACID."""

import random
import time
from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func, text
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
    idempotency_key: Optional[str] = None,
    stage_timing: Optional[Any] = None,
    client_id: Optional[str] = None,
) -> ImportNote:
    """Lập phiếu nhập kho trong một Transaction ACID duy nhất.

    - Tăng current_stock của từng mặt hàng.
    - Tự động ghi nhận bản ghi Thẻ kho (StockLedger).
    - Áp dụng Retry Pattern xử lý đụng độ mã tự sinh.
    - Idempotency Key bảo đảm chống ghi trùng lặp dữ liệu.
    """
    if idempotency_key:
        idempotency_key = idempotency_key.strip() or None

    # Kiểm tra Idempotency Key trước khi thực hiện logic tạo phiếu
    if idempotency_key:
        existing_note = db.query(ImportNote).filter(ImportNote.idempotency_key == idempotency_key).first()
        if existing_note:
            return existing_note

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
        if product.current_stock + item.quantity > 1_000_000_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Tồn kho sau khi nhập của mặt hàng '{product.name}' ({product.code}) vượt quá giới hạn tối đa cho phép (1.000.000.000). "
                    f"Tồn hiện tại: {product.current_stock}, Yêu cầu nhập: {item.quantity}."
                ),
            )
        product_map[item.product_id] = product

    # 3. Tính toán tổng tiền
    total_amount = sum(item.quantity * item.unit_price for item in note_in.details)
    now = datetime.now(timezone.utc)

    # 4. Thực thi Transaction với Retry Pattern (Optimistic Concurrency)
    max_retries = 7
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

            t_tx_start = time.perf_counter()
            if stage_timing:
                stage_timing.t_tx_start = t_tx_start
            write_metrics.enter_transaction()
            import_note = ImportNote(
                code=note_code,
                supplier_id=note_in.supplier_id,
                created_by=current_user_id,
                note_date=now,
                total_amount=total_amount,
                note=note_in.note.strip() if note_in.note else None,
                status="COMPLETED",
                idempotency_key=idempotency_key,
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

                # Cập nhật tồn kho nguyên tử ở tầng SQL
                product = product_map[item.product_id]
                row = db.execute(
                    text("""
                        UPDATE products
                        SET current_stock = current_stock + :qty
                        WHERE id = :prod_id AND current_stock + :qty <= 1000000000
                        RETURNING current_stock
                    """),
                    {"qty": item.quantity, "prod_id": item.product_id},
                ).fetchone()
                if row is None:
                    db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Tồn kho sau khi nhập của mặt hàng '{product.name}' vượt quá giới hạn tối đa (1.000.000.000).",
                    )
                new_balance = row[0]
                db.expire(product, ["current_stock"])

                # Ghi Thẻ kho (StockLedger)
                ledger_entry = StockLedger(
                    product_id=product.id,
                    transaction_type="IMPORT",
                    reference_code=import_note.code,
                    quantity_change=item.quantity,
                    balance_after=new_balance,
                    created_by=current_user_id,
                    transaction_date=now,
                    note=f"Nhập kho theo phiếu {import_note.code}",
                )
                db.add(ledger_entry)

            t_com_start = time.perf_counter()
            if stage_timing:
                stage_timing.t_commit_start = t_com_start
            db.commit()
            t_now = time.perf_counter()
            if stage_timing:
                stage_timing.t_commit_end = t_now
            write_metrics.exit_transaction(
                tx_time_ms=(t_now - t_tx_start) * 1000,
                commit_time_ms=(t_now - t_com_start) * 1000
            )
            db.refresh(import_note)
            broadcaster.publish_after_commit(
                resource="import_notes",
                action="CREATE",
                client_id=client_id,
                metadata={"code": import_note.code}
            )
            return import_note

        except IntegrityError as exc:
            db.rollback()
            # Xử lý trường hợp 2 request đồng thời gửi cùng một idempotency_key
            if idempotency_key:
                existing_note = db.query(ImportNote).filter(ImportNote.idempotency_key == idempotency_key).first()
                if existing_note:
                    return existing_note
            if note_in.code:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Mã phiếu nhập '{note_in.code.strip().upper()}' đã tồn tại trong hệ thống.",
                )
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Xung đột mã phiếu do nhiều giao dịch đồng thời. Vui lòng thử lại.",
                )
            # Giãn cách ngẫu nhiên (Exponential Backoff + Jitter) để tránh đụng độ liên tiếp
            write_metrics.exit_transaction(0, 0)
            delay = 0.025 * (2 ** attempt) + random.uniform(0.015, 0.045)
            write_metrics.record_retry(delay * 1000)
            time.sleep(delay)


def create_export_note(
    db: Session,
    note_in: ExportNoteCreate,
    current_user_id: int,
    idempotency_key: Optional[str] = None,
    stage_timing: Optional[Any] = None,
    client_id: Optional[str] = None,
) -> ExportNote:
    """Lập phiếu xuất kho trong một Transaction ACID duy nhất.

    - Kiểm tra nghiêm ngặt chống tồn kho âm (Rollback 100% nếu thiếu hàng).
    - Giảm current_stock của từng mặt hàng khi chuyển trạng thái sang SHIPPING.
    - Idempotency Key bảo đảm chống ghi trùng lặp dữ liệu.
    """
    if idempotency_key:
        idempotency_key = idempotency_key.strip() or None

    # Kiểm tra Idempotency Key trước khi thực hiện logic tạo phiếu
    if idempotency_key:
        existing_note = db.query(ExportNote).filter(ExportNote.idempotency_key == idempotency_key).first()
        if existing_note:
            return existing_note

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
    max_retries = 7
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

            t_tx_start = time.perf_counter()
            if stage_timing:
                stage_timing.t_tx_start = t_tx_start
            export_note = ExportNote(
                code=note_code,
                recipient_name=note_in.recipient_name.strip(),
                created_by=current_user_id,
                note_date=now,
                total_amount=total_amount,
                note=note_in.note.strip() if note_in.note else None,
                status="CONFIRMED",
                idempotency_key=idempotency_key,
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
            t_com_start = time.perf_counter()
            if stage_timing:
                stage_timing.t_commit_start = t_com_start
            db.commit()
            t_now = time.perf_counter()
            if stage_timing:
                stage_timing.t_commit_end = t_now
            db.refresh(export_note)
            broadcaster.publish_after_commit(
                resource="export_notes",
                action="CREATE",
                client_id=client_id,
                metadata={"code": export_note.code}
            )
            return export_note

        except IntegrityError as exc:
            db.rollback()
            # Xử lý trường hợp 2 request đồng thời gửi cùng một idempotency_key
            if idempotency_key:
                existing_note = db.query(ExportNote).filter(ExportNote.idempotency_key == idempotency_key).first()
                if existing_note:
                    return existing_note
            if note_in.code:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Mã phiếu xuất '{note_in.code.strip().upper()}' đã tồn tại trong hệ thống.",
                )
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Xung đột mã phiếu do nhiều giao dịch đồng thời. Vui lòng thử lại.",
                )
            # Giãn cách ngẫu nhiên (Exponential Backoff + Jitter) để tránh đụng độ liên tiếp
            write_metrics.exit_transaction(0, 0)
            delay = 0.025 * (2 ** attempt) + random.uniform(0.015, 0.045)
            write_metrics.record_retry(delay * 1000)
            time.sleep(delay)


def cancel_import_note(
    db: Session,
    import_note_id: int,
    current_user_id: int,
    reason: Optional[str] = None,
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

    # Chốt ở tầng DB bằng UPDATE có điều kiện (Phương án C)
    res_upd = db.execute(
        text("UPDATE import_notes SET status = 'CANCELLED' WHERE id = :id AND status = 'COMPLETED'"),
        {"id": import_note_id}
    )
    if res_upd.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiếu nhập '{import_note.code}' đã bị hủy hoặc trạng thái đã thay đổi bởi giao dịch khác.",
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
    if reason and reason.strip():
        r_text = reason.strip()
        import_note.note = f"{import_note.note or ''} [Lý do hủy: {r_text}]".strip()
        ledger_note = f"Hoàn tác do hủy phiếu nhập {import_note.code}: {r_text}"
    else:
        ledger_note = f"Hoàn tác do hủy phiếu nhập {import_note.code}"

    for detail in import_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        row = db.execute(
            text("""
                UPDATE products
                SET current_stock = current_stock - :qty
                WHERE id = :prod_id AND current_stock >= :qty
                RETURNING current_stock
            """),
            {"qty": detail.quantity, "prod_id": detail.product_id},
        ).fetchone()

        if row is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể hủy phiếu nhập: tồn kho hiện tại không đủ để hoàn tác cho sản phẩm '{product.name}'.",
            )

        new_balance = row[0]
        db.expire(product, ["current_stock"])

        ledger_entry = StockLedger(
            product_id=product.id,
            transaction_type="ADJUSTMENT",
            reference_code=f"CANCEL-{import_note.code}",
            quantity_change=-detail.quantity,
            balance_after=new_balance,
            created_by=current_user_id,
            transaction_date=now,
            note=ledger_note,
        )
        db.add(ledger_entry)

    db.commit()
    db.refresh(import_note)
    broadcaster.publish_after_commit(
        resource="import_notes",
        action="CANCEL",
        metadata={"code": import_note.code}
    )
    return import_note


def ship_export_note(
    db: Session,
    export_note_id: int,
    current_user_id: int,
    stage_timing: Optional[Any] = None,
    client_id: Optional[str] = None,
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
    t_tx_start = time.perf_counter()
    if stage_timing:
        stage_timing.t_tx_start = t_tx_start
    write_metrics.enter_transaction()
    now = datetime.now(timezone.utc)
    export_note.status = "SHIPPING"

    for detail in export_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        row = db.execute(
            text("""
                UPDATE products 
                SET current_stock = current_stock - :qty 
                WHERE id = :prod_id AND current_stock >= :qty 
                RETURNING current_stock
            """),
            {"qty": detail.quantity, "prod_id": detail.product_id},
        ).fetchone()

        if row is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Không đủ hàng tồn kho cho sản phẩm '{product.name}' (Mã SKU: {product.code}) để giao hàng. "
                    f"Số lượng tồn hiện có: {product.current_stock}, Yêu cầu xuất: {detail.quantity}. Không thể xuất kho."
                ),
            )

        new_balance = row[0]
        db.expire(product, ["current_stock"])

        ledger_entry = StockLedger(
            product_id=product.id,
            transaction_type="EXPORT",
            reference_code=export_note.code,
            quantity_change=-detail.quantity,
            balance_after=new_balance,
            created_by=current_user_id,
            transaction_date=now,
            note=f"Xuất kho giao cho {export_note.recipient_name} theo phiếu {export_note.code}",
        )
        db.add(ledger_entry)

    t_com_start = time.perf_counter()
    if stage_timing:
        stage_timing.t_commit_start = t_com_start
    db.commit()
    t_now = time.perf_counter()
    if stage_timing:
        stage_timing.t_commit_end = t_now
    write_metrics.exit_transaction(
        tx_time_ms=(t_now - t_tx_start) * 1000,
        commit_time_ms=(t_now - t_com_start) * 1000
    )
    db.refresh(export_note)
    broadcaster.publish_after_commit(
        resource="export_notes",
        action="SHIP",
        client_id=client_id,
        metadata={"code": export_note.code}
    )
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

    # Chốt ở tầng DB bằng UPDATE có điều kiện (Phương án C)
    res_upd = db.execute(
        text("UPDATE export_notes SET status = 'COMPLETED' WHERE id = :id AND status = 'SHIPPING'"),
        {"id": export_note_id}
    )
    if res_upd.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiếu xuất '{export_note.code}' đã hoàn thành hoặc trạng thái không còn là SHIPPING.",
        )

    t_tx_start = time.perf_counter()
    export_note.status = "COMPLETED"
    t_com_start = time.perf_counter()
    db.commit()
    t_now = time.perf_counter()
    write_metrics.exit_transaction(
        tx_time_ms=(t_now - t_tx_start) * 1000,
        commit_time_ms=(t_now - t_com_start) * 1000
    )
    db.refresh(export_note)
    broadcaster.publish_after_commit(
        resource="export_notes",
        action="COMPLETE",
        metadata={"code": export_note.code}
    )
    return export_note


def cancel_export_note(
    db: Session,
    export_note_id: int,
    current_user_id: int,
    reason: Optional[str] = None,
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
        # Chốt ở tầng DB bằng DELETE có điều kiện
        res_del = db.execute(
            text("DELETE FROM export_notes WHERE id = :id AND status = 'CONFIRMED'"),
            {"id": export_note_id}
        )
        if res_del.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trạng thái phiếu xuất '{export_note.code}' đã thay đổi hoặc đang được xử lý đồng thời.",
            )
        deleted_code = export_note.code
        db.commit()
        broadcaster.publish_after_commit(
            resource="export_notes",
            action="CANCEL",
            metadata={"code": deleted_code}
        )
        return None, True

    # Trạng thái SHIPPING hoặc COMPLETED: Chốt ở tầng DB bằng UPDATE có điều kiện (Phương án C)
    res_upd = db.execute(
        text("""
            UPDATE export_notes 
            SET status = 'CANCELLED' 
            WHERE id = :id AND status IN ('SHIPPING', 'COMPLETED')
        """),
        {"id": export_note_id}
    )
    if res_upd.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Phiếu xuất '{export_note.code}' đã bị hủy hoặc trạng thái đã thay đổi bởi giao dịch khác.",
        )

    t_tx_start = time.perf_counter()
    now = datetime.now(timezone.utc)
    export_note.status = "CANCELLED"
    if reason and reason.strip():
        r_text = reason.strip()
        export_note.note = f"{export_note.note or ''} [Lý do hủy: {r_text}]".strip()
        ledger_note = f"Hoàn tác do hủy phiếu xuất {export_note.code}: {r_text}"
    else:
        ledger_note = f"Hoàn tác do hủy phiếu xuất {export_note.code}"

    for detail in export_note.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        if product.current_stock + detail.quantity > 1_000_000_000:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể hủy phiếu xuất: tồn kho sau khi hoàn trả vượt quá giới hạn tối đa (1.000.000.000).",
            )
        row = db.execute(
            text("""
                UPDATE products 
                SET current_stock = current_stock + :qty 
                WHERE id = :prod_id AND current_stock + :qty <= 1000000000
                RETURNING current_stock
            """),
            {"qty": detail.quantity, "prod_id": detail.product_id},
        ).fetchone()

        if row is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể hủy phiếu xuất: tồn kho sau khi hoàn trả vượt quá giới hạn tối đa (1.000.000.000).",
            )

        new_balance = row[0]
        db.expire(product, ["current_stock"])

        ledger_entry = StockLedger(
            product_id=product.id,
            transaction_type="ADJUSTMENT",
            reference_code=f"CANCEL-{export_note.code}",
            quantity_change=detail.quantity,
            balance_after=new_balance,
            created_by=current_user_id,
            transaction_date=now,
            note=ledger_note,
        )
        db.add(ledger_entry)

    t_com_start = time.perf_counter()
    db.commit()
    t_now = time.perf_counter()
    write_metrics.exit_transaction(
        tx_time_ms=(t_now - t_tx_start) * 1000,
        commit_time_ms=(t_now - t_com_start) * 1000
    )
    db.refresh(export_note)
    broadcaster.publish_after_commit(
        resource="export_notes",
        action="CANCEL",
        metadata={"code": export_note.code}
    )
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

    # Chốt ở tầng DB bằng DELETE có điều kiện (Phương án C)
    res_del = db.execute(
        text("DELETE FROM export_notes WHERE id = :id AND status = 'CONFIRMED'"),
        {"id": export_note_id}
    )
    if res_del.rowcount == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa phiếu xuất '{export_note.code}' vì trạng thái đã thay đổi hoặc không phải CONFIRMED.",
        )

    deleted_code = export_note.code
    db.commit()
    broadcaster.publish_after_commit(
        resource="export_notes",
        action="DELETE",
        metadata={"code": deleted_code}
    )


def adjust_stock(
    db: Session,
    adj_in: StockAdjustmentCreate,
    current_user_id: int,
    idempotency_key: Optional[str] = None,
    stage_timing: Optional[Any] = None,
    client_id: Optional[str] = None,
) -> StockAdjustmentResponse:
    """Lối thoát kiểm kê / Điều chỉnh tồn kho thủ công (Hỗ trợ Idempotency Key & Safe Retry)."""
    clean_key = idempotency_key.strip() if idempotency_key and idempotency_key.strip() else None

    # 1. Kiểm tra Idempotency trước khi thực thi
    if clean_key:
        existing = db.query(StockLedger).filter(StockLedger.idempotency_key == clean_key).first()
        if existing:
            prod = db.query(Product).filter(Product.id == existing.product_id).first()
            return StockAdjustmentResponse(
                success=True,
                product_id=existing.product_id,
                product_code=prod.code if prod else "",
                product_name=prod.name if prod else "",
                old_stock=existing.balance_after - existing.quantity_change,
                actual_stock=existing.balance_after,
                difference=existing.quantity_change,
                reference_code=existing.reference_code,
                message="Giao dịch điều chỉnh kiểm kê đã được ghi nhận trước đó (Idempotent response).",
                idempotency_key=existing.idempotency_key,
            )

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

    # Thực thi với retry pattern chỉ dành riêng cho lỗi tranh chấp khóa tạm thời (locked/busy)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            t_tx_start = time.perf_counter()
            if stage_timing:
                stage_timing.t_tx_start = t_tx_start
            write_metrics.enter_transaction()

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
                idempotency_key=clean_key,
            )
            db.add(ledger_entry)

            t_com_start = time.perf_counter()
            if stage_timing:
                stage_timing.t_commit_start = t_com_start
            db.commit()
            t_now = time.perf_counter()
            if stage_timing:
                stage_timing.t_commit_end = t_now
            write_metrics.exit_transaction(
                tx_time_ms=(t_now - t_tx_start) * 1000,
                commit_time_ms=(t_now - t_com_start) * 1000,
            )
            broadcaster.publish_after_commit(
                resource="stock_ledger",
                action="ADJUST",
                client_id=client_id,
                metadata={"product_id": product.id}
            )

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
                idempotency_key=clean_key,
            )

        except IntegrityError as exc:
            db.rollback()
            write_metrics.exit_transaction(0, 0)
            if clean_key:
                existing = db.query(StockLedger).filter(StockLedger.idempotency_key == clean_key).first()
                if existing:
                    return StockAdjustmentResponse(
                        success=True,
                        product_id=existing.product_id,
                        product_code=product.code,
                        product_name=product.name,
                        old_stock=existing.balance_after - existing.quantity_change,
                        actual_stock=existing.balance_after,
                        difference=existing.quantity_change,
                        reference_code=existing.reference_code,
                        message="Giao dịch điều chỉnh kiểm kê đã được ghi nhận trước đó (Idempotent response).",
                        idempotency_key=existing.idempotency_key,
                    )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dữ liệu điều chỉnh kiểm kê vi phạm ràng buộc toàn vẹn cơ sở dữ liệu.",
            )

        except Exception as exc:
            db.rollback()
            write_metrics.exit_transaction(0, 0)
            err_msg = str(exc).lower()
            if ("locked" in err_msg or "busy" in err_msg) and attempt < max_retries - 1:
                delay = 0.05 * (2 ** attempt) + random.uniform(0.02, 0.05)
                write_metrics.record_retry(delay * 1000)
                time.sleep(delay)
                continue
            raise


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
    total_adjustment = 0
    total_closing = 0
    total_inventory_value = 0.0

    for product in products:
        # 1. Tồn đầu kỳ: Tổng đại số quantity_change của mọi giao dịch TRƯỚC from_date
        opening_stock = (
            db.query(func.coalesce(func.sum(StockLedger.quantity_change), 0))
            .filter(
                StockLedger.product_id == product.id,
                StockLedger.transaction_date < from_date,
            )
            .scalar()
        )

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

        # Nhập thương mại từ NCC (IMPORT)
        period_import = sum(e.quantity_change for e in period_entries if e.transaction_type == "IMPORT")

        # Hoàn trừ xuất kho do hủy phiếu (CANCEL-PX-)
        cancel_export_qty = sum(
            e.quantity_change
            for e in period_entries
            if e.transaction_type == "ADJUSTMENT"
            and e.reference_code
            and e.reference_code.startswith("CANCEL-PX")
        )

        # Xuất kho thương mại thuần túy (EXPORT) sau khi đã trừ lượng hủy hoàn trả
        period_export = sum(abs(e.quantity_change) for e in period_entries if e.transaction_type == "EXPORT") - cancel_export_qty

        # Các khoản điều chỉnh khác (ví dụ: kiểm kê kho hoặc hủy nhập)
        period_adjustment = sum(
            e.quantity_change
            for e in period_entries
            if e.transaction_type == "ADJUSTMENT"
            and (not e.reference_code or not e.reference_code.startswith("CANCEL-PX"))
        )

        # 3. Tồn cuối kỳ = Tồn đầu + Nhập - Xuất + Điều chỉnh
        closing_stock = opening_stock + period_import - period_export + period_adjustment
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
                adjustment=period_adjustment,
                closing_stock=closing_stock,
                standard_price=product.standard_price,
                total_value=total_val,
                is_low_stock=closing_stock <= product.min_stock,
            )
        )

        total_opening += opening_stock
        total_import += period_import
        total_export += period_export
        total_adjustment += period_adjustment
        total_closing += closing_stock
        total_inventory_value += total_val

    return InventorySummaryReport(
        from_date=from_date,
        to_date=to_date,
        total_products=len(products),
        total_opening=total_opening,
        total_import=total_import,
        total_export=total_export,
        total_adjustment=total_adjustment,
        total_closing=total_closing,
        total_inventory_value=total_inventory_value,
        items=items,
    )
