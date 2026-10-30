"""SQLAlchemy Model cho Hàng hóa (products) kèm ràng buộc chống tồn âm."""

from datetime import datetime
from app.core.config import get_now_vn
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # Mã SKU
    name = Column(String(200), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    unit = Column(String(20), nullable=False, default="Cái")
    min_stock = Column(Integer, nullable=False, default=10)
    current_stock = Column(Integer, nullable=False, default=0)
    standard_price = Column(Float, nullable=False, default=0.0)
    image_url = Column(String(500), nullable=True)  # Đường dẫn hoặc URL ảnh sản phẩm
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, DISCONTINUED
    created_at = Column(DateTime, nullable=False, default=get_now_vn)

    # Ràng buộc toàn vẹn: Chặn đứng nguy cơ tồn kho âm ở mức CSDL
    __table_args__ = (
        CheckConstraint("current_stock >= 0", name="chk_stock_non_negative"),
    )

    # Relationships
    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    import_details = relationship("ImportNoteDetail", back_populates="product")
    export_details = relationship("ExportNoteDetail", back_populates="product")
    ledger_entries = relationship("StockLedger", back_populates="product")

    @property
    def category_name(self):
        return self.category.name if self.category else None

    @property
    def supplier_name(self):
        return self.supplier.name if self.supplier else None
