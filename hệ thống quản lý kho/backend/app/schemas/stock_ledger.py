"""Pydantic Schemas cho Thẻ kho (StockLedger) và Phiếu điều chỉnh kiểm kê (StockAdjustment)."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class StockLedgerResponse(BaseModel):
    id: int
    product_id: int
    transaction_type: str
    reference_code: str
    quantity_change: int
    balance_after: int
    created_by: int
    transaction_date: datetime
    note: Optional[str] = None
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    creator_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StockAdjustmentCreate(BaseModel):
    product_id: int = Field(..., ge=1, description="ID mặt hàng cần kiểm kê / điều chỉnh")
    actual_stock: int = Field(..., ge=0, description="Số lượng tồn kho thực tế sau kiểm kê (>= 0)")
    reason: str = Field(..., min_length=3, max_length=255, description="Lý do điều chỉnh (kiểm kê thực tế, bù trừ sai sót, hư hao...)")


class StockAdjustmentResponse(BaseModel):
    success: bool = True
    product_id: int
    product_code: str
    product_name: str
    old_stock: int
    actual_stock: int
    difference: int
    reference_code: str
    message: str
