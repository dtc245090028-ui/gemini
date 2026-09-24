"""Pydantic Schemas cho Hàng hóa (Product) và Cảnh báo Tồn kho."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field


class ProductBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Mã SKU hàng hóa")
    name: str = Field(..., min_length=1, max_length=200, description="Tên mặt hàng")
    category_id: int = Field(..., ge=1, description="ID nhóm hàng hóa")
    unit: str = Field(default="Cái", min_length=1, max_length=20, description="Đơn vị tính")
    min_stock: int = Field(default=10, ge=0, description="Định mức tồn tối thiểu để cảnh báo")
    standard_price: float = Field(default=0.0, ge=0.0, description="Đơn giá tiêu chuẩn (VNĐ)")
    image_url: Optional[str] = Field(None, max_length=500, description="Đường dẫn hoặc URL ảnh sản phẩm")
    status: str = Field(default="ACTIVE", description="Trạng thái hàng: ACTIVE, DISCONTINUED")


class ProductCreate(ProductBase):
    current_stock: int = Field(default=0, ge=0, description="Số lượng tồn ban đầu (>= 0)")


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Tên mặt hàng")
    category_id: Optional[int] = Field(None, ge=1, description="ID nhóm hàng hóa")
    unit: Optional[str] = Field(None, min_length=1, max_length=20, description="Đơn vị tính")
    min_stock: Optional[int] = Field(None, ge=0, description="Định mức tồn tối thiểu")
    standard_price: Optional[float] = Field(None, ge=0.0, description="Đơn giá tiêu chuẩn")
    image_url: Optional[str] = Field(None, max_length=500, description="Đường dẫn hoặc URL ảnh sản phẩm")
    status: Optional[str] = Field(None, description="Trạng thái hàng: ACTIVE, DISCONTINUED")


class ProductResponse(ProductBase):
    id: int
    current_stock: int
    created_at: datetime
    category_name: Optional[str] = None

    @computed_field
    def is_low_stock(self) -> bool:
        """Thuộc tính tự động tính toán: True khi tồn kho hiện tại <= mức tồn tối thiểu."""
        return self.current_stock <= self.min_stock

    model_config = ConfigDict(from_attributes=True)


class ProductPaginationResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    skip: int
    limit: int
