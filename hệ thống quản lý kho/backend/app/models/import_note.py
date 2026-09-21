"""SQLAlchemy Models cho Phiếu nhập kho (import_notes) và Chi tiết phiếu nhập (import_note_details)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class ImportNote(Base):
    __tablename__ = "import_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # PN-YYYYMMDD-XXX
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    note_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_amount = Column(Float, nullable=False, default=0.0)
    note = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="COMPLETED")  # DRAFT, COMPLETED, CANCELLED

    # Relationships
    supplier = relationship("Supplier", back_populates="import_notes")
    creator = relationship("User", back_populates="import_notes")
    details = relationship("ImportNoteDetail", back_populates="import_note", cascade="all, delete-orphan")


class ImportNoteDetail(Base):
    __tablename__ = "import_note_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    import_note_id = Column(Integer, ForeignKey("import_notes.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_import_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="chk_import_unit_price_non_negative"),
    )

    # Relationships
    import_note = relationship("ImportNote", back_populates="details")
    product = relationship("Product", back_populates="import_details")
