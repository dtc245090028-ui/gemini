"""SQLAlchemy Model cho Người dùng (users)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="WAREHOUSE_KEEPER")  # ADMIN, WAREHOUSE_KEEPER, ACCOUNTANT
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    import_notes = relationship("ImportNote", back_populates="creator")
    export_notes = relationship("ExportNote", back_populates="creator")
    ledger_entries = relationship("StockLedger", back_populates="creator")
