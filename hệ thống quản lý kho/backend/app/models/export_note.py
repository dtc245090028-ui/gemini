"""SQLAlchemy Models cho Phiếu xuất kho (export_notes) và Chi tiết phiếu xuất (export_note_details)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExportNote(Base):
    __tablename__ = "export_notes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # PX-YYYYMMDD-XXX
    recipient_name = Column(String(100), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    note_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_amount = Column(Float, nullable=False, default=0.0)
    note = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="COMPLETED")  # DRAFT, COMPLETED, CANCELLED

    # Relationships
    creator = relationship("User", back_populates="export_notes")
    details = relationship("ExportNoteDetail", back_populates="export_note", cascade="all, delete-orphan")


class ExportNoteDetail(Base):
    __tablename__ = "export_note_details"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    export_note_id = Column(Integer, ForeignKey("export_notes.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False, default=0.0)
    subtotal = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_export_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="chk_export_unit_price_non_negative"),
    )

    # Relationships
    export_note = relationship("ExportNote", back_populates="details")
    product = relationship("Product", back_populates="export_details")
