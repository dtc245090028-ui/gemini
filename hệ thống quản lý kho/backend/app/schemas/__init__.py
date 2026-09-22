"""Schemas package tập trung các Pydantic models."""

from app.schemas.category import (
    CategoryBase,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.schemas.export_note import (
    ExportNoteBase,
    ExportNoteCreate,
    ExportNoteDetailBase,
    ExportNoteDetailCreate,
    ExportNoteDetailResponse,
    ExportNoteResponse,
)
from app.schemas.import_note import (
    ImportNoteBase,
    ImportNoteCreate,
    ImportNoteDetailBase,
    ImportNoteDetailCreate,
    ImportNoteDetailResponse,
    ImportNoteResponse,
)
from app.schemas.product import (
    ProductBase,
    ProductCreate,
    ProductPaginationResponse,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.report import (
    InventorySummaryItem,
    InventorySummaryReport,
)
from app.schemas.stock_ledger import (
    StockAdjustmentCreate,
    StockAdjustmentResponse,
    StockLedgerResponse,
)
from app.schemas.supplier import (
    SupplierBase,
    SupplierCreate,
    SupplierResponse,
    SupplierUpdate,
)
from app.schemas.user import (
    TokenResponse,
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
)

__all__ = [
    "UserRole",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductPaginationResponse",
    "SupplierBase",
    "SupplierCreate",
    "SupplierUpdate",
    "SupplierResponse",
    "ImportNoteBase",
    "ImportNoteCreate",
    "ImportNoteDetailBase",
    "ImportNoteDetailCreate",
    "ImportNoteDetailResponse",
    "ImportNoteResponse",
    "ExportNoteBase",
    "ExportNoteCreate",
    "ExportNoteDetailBase",
    "ExportNoteDetailCreate",
    "ExportNoteDetailResponse",
    "ExportNoteResponse",
    "StockLedgerResponse",
    "StockAdjustmentCreate",
    "StockAdjustmentResponse",
    "InventorySummaryItem",
    "InventorySummaryReport",
]
