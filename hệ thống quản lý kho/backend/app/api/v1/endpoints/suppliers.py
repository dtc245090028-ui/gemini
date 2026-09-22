"""API Endpoints cho quản lý Nhà cung cấp (Suppliers)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["Nhà cung cấp (Suppliers)"])


@router.get(
    "/",
    response_model=List[SupplierResponse],
    summary="Lấy danh sách nhà cung cấp",
)
def get_suppliers(
    search: Optional[str] = Query(None, description="Tìm kiếm theo mã, tên, số điện thoại hoặc email"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái hoạt động"),
    skip: int = Query(0, ge=0, description="Số lượng bỏ qua"),
    limit: int = Query(100, ge=1, le=500, description="Số lượng lấy tối đa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Truy vấn danh sách nhà cung cấp kèm tìm kiếm và phân trang."""
    query = db.query(Supplier)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (Supplier.name.ilike(pattern))
            | (Supplier.code.ilike(pattern))
            | (Supplier.phone.ilike(pattern))
            | (Supplier.email.ilike(pattern))
        )

    if is_active is not None:
        query = query.filter(Supplier.is_active == is_active)

    suppliers = query.order_by(Supplier.id.desc()).offset(skip).limit(limit).all()
    return suppliers


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Lấy chi tiết một nhà cung cấp",
)
def get_supplier_by_id(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một nhà cung cấp theo ID."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy nhà cung cấp với ID: {supplier_id}.",
        )
    return supplier


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm mới nhà cung cấp (Chỉ dành cho ADMIN hoặc WAREHOUSE_KEEPER)",
)
def create_supplier(
    supplier_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Tạo mới một nhà cung cấp vào hệ thống."""
    sup_code = supplier_in.code.strip().upper()
    existing = db.query(Supplier).filter(Supplier.code == sup_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã nhà cung cấp '{sup_code}' đã tồn tại trong hệ thống.",
        )

    supplier = Supplier(
        code=sup_code,
        name=supplier_in.name.strip(),
        phone=supplier_in.phone.strip() if supplier_in.phone else None,
        email=supplier_in.email.strip() if supplier_in.email else None,
        address=supplier_in.address.strip() if supplier_in.address else None,
        is_active=supplier_in.is_active,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    summary="Cập nhật nhà cung cấp (Chỉ dành cho ADMIN hoặc WAREHOUSE_KEEPER)",
)
def update_supplier(
    supplier_id: int,
    supplier_in: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Cập nhật thông tin nhà cung cấp theo ID."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy nhà cung cấp với ID: {supplier_id}.",
        )

    if supplier_in.code:
        new_code = supplier_in.code.strip().upper()
        if new_code != supplier.code:
            duplicate = db.query(Supplier).filter(Supplier.code == new_code).first()
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã nhà cung cấp '{new_code}' đã được sử dụng bởi đơn vị khác.",
                )
            supplier.code = new_code

    if supplier_in.name is not None:
        supplier.name = supplier_in.name.strip()
    if supplier_in.phone is not None:
        supplier.phone = supplier_in.phone.strip()
    if supplier_in.email is not None:
        supplier.email = supplier_in.email.strip()
    if supplier_in.address is not None:
        supplier.address = supplier_in.address.strip()
    if supplier_in.is_active is not None:
        supplier.is_active = supplier_in.is_active

    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete(
    "/{supplier_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa hoặc ngừng hợp tác nhà cung cấp (Chỉ dành cho ADMIN)",
)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"])),
):
    """Xóa nhà cung cấp. Nếu đã phát sinh phiếu nhập thì chuyển trạng thái is_active=False."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy nhà cung cấp với ID: {supplier_id}.",
        )

    if supplier.import_notes:
        supplier.is_active = False
        db.commit()
        return {
            "success": True,
            "action": "DEACTIVATED",
            "message": f"Nhà cung cấp '{supplier.name}' đã phát sinh {len(supplier.import_notes)} phiếu nhập kho nên được chuyển sang trạng thái ngừng hoạt động (is_active=False) để bảo toàn chứng từ.",
        }

    db.delete(supplier)
    db.commit()
    return {
        "success": True,
        "action": "DELETED",
        "message": f"Đã xóa thành công nhà cung cấp: {supplier.name}",
    }
