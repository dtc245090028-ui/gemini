"""Pydantic Schemas cho Nhà cung cấp (Supplier)."""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SupplierBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=30, description="Mã nhà cung cấp")
    name: str = Field(..., min_length=1, max_length=150, description="Tên nhà cung cấp")
    phone: Optional[str] = Field(None, max_length=20, description="Số điện thoại liên hệ")
    email: Optional[str] = Field(None, max_length=100, description="Email liên hệ")
    address: Optional[str] = Field(None, max_length=255, description="Địa chỉ trụ sở")
    is_active: bool = Field(default=True, description="Trạng thái hoạt động")


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=30, description="Mã nhà cung cấp")
    name: Optional[str] = Field(None, min_length=1, max_length=150, description="Tên nhà cung cấp")
    phone: Optional[str] = Field(None, max_length=20, description="Số điện thoại")
    email: Optional[str] = Field(None, max_length=100, description="Email")
    address: Optional[str] = Field(None, max_length=255, description="Địa chỉ")
    is_active: Optional[bool] = Field(None, description="Trạng thái hoạt động")


class SupplierResponse(SupplierBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
