"""Pydantic Schemas cho Phiếu xuất kho (ExportNote) và Chi tiết phiếu xuất."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExportNoteDetailBase(BaseModel):
    product_id: int = Field(..., ge=1, description="ID mặt hàng")
    quantity: int = Field(..., gt=0, description="Số lượng xuất (phải > 0)")
    unit_price: float = Field(default=0.0, ge=0.0, description="Đơn giá xuất (>= 0)")


class ExportNoteDetailCreate(ExportNoteDetailBase):
    pass


class ExportNoteDetailResponse(ExportNoteDetailBase):
    id: int
    export_note_id: int
    subtotal: float
    product_name: Optional[str] = None
    product_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExportNoteBase(BaseModel):
    recipient_name: str = Field(..., min_length=1, max_length=100, description="Tên người hoặc đơn vị nhận hàng")
    note: Optional[str] = Field(None, description="Ghi chú phiếu xuất")


class ExportNoteCreate(ExportNoteBase):
    code: Optional[str] = Field(None, max_length=50, description="Mã phiếu xuất (nếu để trống hệ thống tự sinh PX-YYYYMMDD-XXXX)")
    details: List[ExportNoteDetailCreate] = Field(..., min_length=1, description="Danh sách chi tiết hàng xuất (tối thiểu 1 mặt hàng)")


class ExportNoteResponse(ExportNoteBase):
    id: int
    code: str
    created_by: int
    note_date: datetime
    total_amount: float
    status: str
    creator_name: Optional[str] = None
    details: List[ExportNoteDetailResponse] = []

    model_config = ConfigDict(from_attributes=True)
