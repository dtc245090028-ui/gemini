"""SQLAlchemy Model cho Thẻ kho / Sổ kiểm toán tồn kho (stock_ledger)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False)  # IMPORT, EXPORT, ADJUSTMENT
    reference_code = Column(String(50), nullable=False, index=True)  # PN-XXXX hoặc PX-XXXX
    quantity_change = Column(Integer, nullable=False)  # + khi nhập, - khi xuất
    balance_after = Column(Integer, nullable=False)  # Số dư tồn kho tức thời sau giao dịch
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    note = Column(String(255), nullable=True)

    __table_args__ = (
        CheckConstraint("balance_after >= 0", name="chk_balance_after_non_negative"),
    )

    # Relationships
    product = relationship("Product", back_populates="ledger_entries")
    creator = relationship("User", back_populates="ledger_entries")
