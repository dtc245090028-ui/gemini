import os
from pathlib import Path
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db, require_roles
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Hàng hóa & Tồn kho (Products)"])


@router.get("", response_model=List[ProductResponse], include_in_schema=False)
@router.get(
    "/",
    response_model=List[ProductResponse],
    summary="Lấy danh sách hàng hóa",
)
def get_products(
    search: Optional[str] = Query(None, description="Tìm theo tên sản phẩm hoặc mã SKU"),
    category_id: Optional[int] = Query(None, description="Lọc theo ID nhóm hàng"),
    is_low_stock: Optional[bool] = Query(None, description="Lọc hàng sắp hết (current_stock <= min_stock)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc theo trạng thái: ACTIVE, DISCONTINUED"),
    skip: int = Query(0, ge=0, description="Số bản ghi bỏ qua"),
    limit: int = Query(50, ge=1, le=500, description="Số bản ghi lấy tối đa"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Truy vấn danh sách hàng hóa kèm các bộ lọc tìm kiếm, nhóm hàng, cảnh báo tồn và phân trang."""
    query = db.query(Product).options(joinedload(Product.category))

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter((Product.name.ilike(pattern)) | (Product.code.ilike(pattern)))

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if status_filter:
        query = query.filter(Product.status == status_filter.strip().upper())

    if is_low_stock is not None:
        if is_low_stock:
            query = query.filter(Product.current_stock <= Product.min_stock)
        else:
            query = query.filter(Product.current_stock > Product.min_stock)

    products = query.order_by(Product.id.desc()).offset(skip).limit(limit).all()
    return products


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Lấy chi tiết một mặt hàng",
)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy thông tin chi tiết một mặt hàng theo ID."""
    product = (
        db.query(Product)
        .options(joinedload(Product.category))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm với ID: {product_id}.",
        )
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm mới hàng hóa (Chỉ dành cho ADMIN hoặc WAREHOUSE_KEEPER)",
)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Thêm mới một mặt hàng vào kho. Kiểm tra trùng SKU và nhóm hàng hợp lệ."""
    # 1. Kiểm tra nhóm hàng có tồn tại không
    category = db.query(Category).filter(Category.id == product_in.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nhóm hàng với ID {product_in.category_id} không tồn tại trong hệ thống.",
        )

    # 2. Kiểm tra trùng mã SKU
    sku_code = product_in.code.strip().upper()
    existing = db.query(Product).filter(Product.code == sku_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã SKU '{sku_code}' đã tồn tại trong hệ thống.",
        )

    # 3. Tạo sản phẩm mới
    product = Product(
        code=sku_code,
        name=product_in.name.strip(),
        category_id=product_in.category_id,
        unit=product_in.unit.strip(),
        min_stock=product_in.min_stock,
        current_stock=product_in.current_stock,
        standard_price=product_in.standard_price,
        image_url=product_in.image_url.strip() if product_in.image_url else None,
        status=product_in.status.upper(),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Cập nhật thông tin hàng hóa (Chỉ dành cho ADMIN hoặc WAREHOUSE_KEEPER)",
)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Cập nhật thông tin hàng hóa theo ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm với ID: {product_id}.",
        )

    # Nếu cập nhật category_id, kiểm tra xem có tồn tại không
    if product_in.category_id is not None:
        category = db.query(Category).filter(Category.id == product_in.category_id).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nhóm hàng với ID {product_in.category_id} không tồn tại.",
            )
        product.category_id = product_in.category_id

    if product_in.name is not None:
        product.name = product_in.name.strip()
    if product_in.unit is not None:
        product.unit = product_in.unit.strip()
    if product_in.min_stock is not None:
        product.min_stock = product_in.min_stock
    if product_in.standard_price is not None:
        product.standard_price = product_in.standard_price
    if product_in.image_url is not None:
        product.image_url = product_in.image_url.strip() if product_in.image_url.strip() else None
    if product_in.status is not None:
        product.status = product_in.status.strip().upper()

    db.commit()
    db.refresh(product)
    return product


@router.post(
    "/{product_id}/image",
    response_model=ProductResponse,
    summary="Tải lên hình ảnh sản phẩm (Chỉ dành cho ADMIN hoặc WAREHOUSE_KEEPER)",
)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "WAREHOUSE_KEEPER"])),
):
    """Tải lên tệp ảnh cho sản phẩm và lưu vào thư mục static."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm với ID: {product_id}.",
        )

    # Kiểm tra định dạng hợp lệ
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng ảnh '{file.content_type}' không được hỗ trợ. Vui lòng chọn ảnh JPEG, PNG, WEBP hoặc GIF.",
        )

    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"]:
        ext = ".jpg"

    filename = f"{product.code}{ext}"
    upload_dir = Path(__file__).resolve().parent.parent.parent.parent / "static" / "products"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    product.image_url = f"/static/products/{filename}"
    db.commit()
    db.refresh(product)
    return product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa hoặc ngừng kinh doanh hàng hóa (Chỉ dành cho ADMIN)",
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"])),
):
    """Xóa hàng hóa. Nếu đã có giao dịch liên quan thì tự động chuyển sang DISCONTINUED."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm với ID: {product_id}.",
        )

    # Kiểm tra xem sản phẩm đã phát sinh giao dịch nhập/xuất/thẻ kho chưa
    has_history = (
        bool(product.import_details)
        or bool(product.export_details)
        or bool(product.ledger_entries)
    )

    if has_history:
        product.status = "DISCONTINUED"
        db.commit()
        return {
            "success": True,
            "action": "DISCONTINUED",
            "message": f"Sản phẩm '{product.name}' đã phát sinh giao dịch kho nên được chuyển sang trạng thái DISCONTINUED (ngừng kinh doanh) để bảo toàn dữ liệu lịch sử.",
        }

    # Nếu chưa có lịch sử giao dịch thì cho phép xóa hoàn toàn
    db.delete(product)
    db.commit()
    return {
        "success": True,
        "action": "DELETED",
        "message": f"Đã xóa thành công sản phẩm: {product.name}",
    }
