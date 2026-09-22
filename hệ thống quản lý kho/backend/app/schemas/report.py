"""Pydantic Schemas cho Báo cáo Nhập - Xuất - Tồn và Thống kê Kho."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class InventorySummaryItem(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    category_name: Optional[str] = None
    unit: str
    opening_stock: int = Field(..., description="Số lượng tồn đầu kỳ")
    total_import: int = Field(..., description="Tổng số lượng nhập trong kỳ")
    total_export: int = Field(..., description="Tổng số lượng xuất trong kỳ")
    closing_stock: int = Field(..., description="Số lượng tồn cuối kỳ (Tồn đầu + Nhập - Xuất)")
    standard_price: float = Field(..., description="Đơn giá chuẩn")
    total_value: float = Field(..., description="Giá trị tồn kho cuối kỳ (closing_stock * standard_price)")
    is_low_stock: bool = Field(..., description="Cờ cảnh báo hàng dưới mức tồn tối thiểu")


class InventorySummaryReport(BaseModel):
    from_date: datetime
    to_date: datetime
    total_products: int
    total_opening: int
    total_import: int
    total_export: int
    total_closing: int
    total_inventory_value: float
    items: List[InventorySummaryItem]
