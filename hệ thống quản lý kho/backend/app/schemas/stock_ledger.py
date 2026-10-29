"""Pydantic Schemas cho Thẻ kho (StockLedger) và Phiếu điều chỉnh kiểm kê (StockAdjustment)."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StockLedgerSummary(BaseModel):
    opening_balance: int = 0
    total_in: int = 0
    total_out: int = 0
    closing_balance: int = 0


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
    product_sku: Optional[str] = None
    creator_name: Optional[str] = None
    qty_in: int = 0
    qty_out: int = 0
    balance_before: int = 0
    min_stock: int = 0
    summary: Optional[StockLedgerSummary] = None

    model_config = ConfigDict(from_attributes=True)


class StockLedgerListResponse(BaseModel):
    items: List[StockLedgerResponse]
    total: int
    summary: Optional[StockLedgerSummary] = None


class ReferenceLedgerItemResponse(BaseModel):
    id: int
    product_id: int
    product_code: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    unit: Optional[str] = None
    transaction_type: str
    quantity_change: int
    qty_in: int
    qty_out: int
    balance_before: int
    balance_after: int
    min_stock: int = 0
    unit_price: Optional[float] = None
    subtotal: Optional[float] = None


class ReferenceDetailResponse(BaseModel):
    reference_code: str
    transaction_type: str
    transaction_date: datetime
    created_by: int
    creator_name: Optional[str] = None
    partner_name: Optional[str] = None
    note: Optional[str] = None
    note_status: Optional[str] = None
    total_amount: Optional[float] = None
    total_qty_in: int = 0
    total_qty_out: int = 0
    items: List[ReferenceLedgerItemResponse]


class StockAdjustmentCreate(BaseModel):
    product_id: int = Field(..., ge=1, description="ID mặt hàng cần kiểm kê / điều chỉnh")
    actual_stock: int = Field(..., ge=0, description="Số lượng tồn kho thực tế sau kiểm kê (>= 0)")
    reason: Optional[str] = Field(None, min_length=3, max_length=255, description="Lý do điều chỉnh (kiểm kê thực tế, bù trừ sai sót, hư hao...)")
    note: Optional[str] = Field(None, min_length=3, max_length=255, description="Ghi chú lý do điều chỉnh (tương thích ngược với UI)")

    def model_post_init(self, __context) -> None:
        if not self.reason and self.note:
            self.reason = self.note
        if not self.reason:
            raise ValueError("Vui lòng nhập lý do điều chỉnh kiểm kê (reason/note).")


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
