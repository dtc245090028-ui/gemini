"""API Endpoints cho quản lý Nhóm hàng hóa (Categories)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Nhóm hàng hóa (Categories)"])


@router.get(
    "/",
    response_model=List[CategoryResponse],
    summary="Lấy danh sách nhóm hàng hóa",
)
def get_categories(
    search: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo tên hoặc mã"),
    skip: int = Query(0, ge=0, description="Số lượng bỏ qua"),
    limit: int = Query(100, ge=1, le=500, description="Số lượng lấy tối đa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Truy vấn danh sách nhóm hàng có hỗ trợ tìm kiếm và phân trang."""
    query = db.query(Category)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (Category.name.ilike(search_pattern)) | (Category.code.ilike(search_pattern))
        )
    categories = query.offset(skip).limit(limit).all()
    return categories


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Lấy chi tiết một nhóm hàng hóa",
)
def get_category_by_id(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một nhóm hàng theo ID."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy nhóm hàng với ID: {category_id}.",
        )
    return category


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm mới nhóm hàng hóa",
)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Tạo nhóm hàng mới (Chỉ dành cho ADMIN hoặc WAREHOUSE_KEEPER)."""
    # Kiểm tra trùng mã code
    existing = db.query(Category).filter(Category.code == category_in.code.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã nhóm hàng '{category_in.code}' đã tồn tại trong hệ thống.",
        )

    category = Category(
        code=category_in.code.strip().upper(),
        name=category_in.name.strip(),
        description=category_in.description.strip() if category_in.description else None,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Cập nhật thông tin nhóm hàng hóa",
)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Cập nhật thông tin nhóm hàng theo ID."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy nhóm hàng với ID: {category_id}.",
        )

    # Nếu cập nhật code, kiểm tra không bị trùng với nhóm khác
    if category_in.code:
        new_code = category_in.code.strip().upper()
        if new_code != category.code:
            duplicate = db.query(Category).filter(Category.code == new_code).first()
            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mã nhóm hàng '{new_code}' đã được sử dụng bởi nhóm khác.",
                )
            category.code = new_code

    if category_in.name is not None:
        category.name = category_in.name.strip()
    if category_in.description is not None:
        category.description = category_in.description.strip()

    db.commit()
    db.refresh(category)
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa nhóm hàng hóa (Chỉ dành cho ADMIN)",
)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"])),
):
    """Xóa nhóm hàng khỏi hệ thống (Chỉ ADMIN, và nhóm hàng chưa chứa sản phẩm nào)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy nhóm hàng với ID: {category_id}.",
        )

    # Kiểm tra ràng buộc cha-con: Không cho phép xóa nhóm hàng đang có sản phẩm
    if category.products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể xóa nhóm hàng '{category.name}' vì đang có {len(category.products)} sản phẩm liên kết.",
        )

    db.delete(category)
    db.commit()
    return {"success": True, "message": f"Đã xóa thành công nhóm hàng: {category.name}"}
