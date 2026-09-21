"""SQLAlchemy Model cho Nhà cung cấp (suppliers)."""

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(30), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    import_notes = relationship("ImportNote", back_populates="supplier")
