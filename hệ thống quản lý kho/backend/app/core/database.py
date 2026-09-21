"""Quản lý kết nối Cơ sở dữ liệu và Database Session bằng SQLAlchemy."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# Cấu hình tham số kết nối engine
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency cung cấp session kết nối CSDL và tự động đóng sau khi hoàn thành request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
