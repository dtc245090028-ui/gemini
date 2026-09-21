"""Gói khởi tạo các Models SQLAlchemy.
Import toàn bộ models tại đây để Base.metadata nhận diện được tất cả các bảng.
"""

from app.core.database import Base
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.import_note import ImportNote, ImportNoteDetail
from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.stock_ledger import StockLedger

__all__ = [
    "Base",
    "User",
    "Category",
    "Product",
    "Supplier",
    "ImportNote",
    "ImportNoteDetail",
    "ExportNote",
    "ExportNoteDetail",
    "StockLedger",
]
