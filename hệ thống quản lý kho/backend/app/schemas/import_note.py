"""Pydantic Schemas cho Phiếu nhập kho (ImportNote) và Chi tiết phiếu nhập."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ImportNoteDetailBase(BaseModel):
    product_id: int = Field(..., ge=1, description="ID mặt hàng")
    quantity: int = Field(..., gt=0, description="Số lượng nhập (phải > 0)")
    unit_price: float = Field(..., ge=0.0, description="Đơn giá nhập (>= 0)")


class ImportNoteDetailCreate(ImportNoteDetailBase):
    pass


class ImportNoteDetailResponse(ImportNoteDetailBase):
    id: int
    import_note_id: int
    subtotal: float
    product_name: Optional[str] = None
    product_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ImportNoteBase(BaseModel):
    supplier_id: int = Field(..., ge=1, description="ID nhà cung cấp")
    note: Optional[str] = Field(None, description="Ghi chú phiếu nhập")


class ImportNoteCreate(ImportNoteBase):
    code: Optional[str] = Field(None, max_length=50, description="Mã phiếu nhập (nếu để trống hệ thống tự sinh PN-YYYYMMDD-XXXX)")
    details: List[ImportNoteDetailCreate] = Field(..., min_length=1, description="Danh sách chi tiết hàng nhập (tối thiểu 1 mặt hàng)")


class ImportNoteResponse(ImportNoteBase):
    id: int
    code: str
    created_by: int
    note_date: datetime
    total_amount: float
    status: str
    supplier_name: Optional[str] = None
    creator_name: Optional[str] = None
    details: List[ImportNoteDetailResponse] = []

    model_config = ConfigDict(from_attributes=True)
