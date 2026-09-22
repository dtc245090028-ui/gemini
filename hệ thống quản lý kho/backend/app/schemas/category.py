"""Pydantic Schemas cho Nhóm hàng hóa (Category)."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, description="Mã định danh nhóm hàng")
    name: str = Field(..., min_length=1, max_length=100, description="Tên nhóm hàng")
    description: Optional[str] = Field(None, description="Mô tả chi tiết nhóm hàng")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=20, description="Mã định danh nhóm hàng")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Tên nhóm hàng")
    description: Optional[str] = Field(None, description="Mô tả chi tiết nhóm hàng")


class CategoryResponse(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
