"""Quản lý kết nối Cơ sở dữ liệu và Database Session bằng SQLAlchemy."""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.core.config import settings

# Cấu hình tham số kết nối engine và Connection Pool tường minh
connect_args = {}
pool_kwargs = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    pool_kwargs["poolclass"] = QueuePool
    pool_kwargs["pool_size"] = 20
    pool_kwargs["max_overflow"] = 20
    pool_kwargs["pool_timeout"] = 30.0
    pool_kwargs["pool_recycle"] = 1800
    pool_kwargs["pool_pre_ping"] = True

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **pool_kwargs,
    echo=False,
)

# Kích hoạt kiểm tra khóa ngoại (Foreign Keys), chế độ WAL và busy_timeout cho SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_products_max_stock_ins
            BEFORE INSERT ON products
            FOR EACH ROW
            WHEN NEW.current_stock > 1000000000
            BEGIN
                SELECT RAISE(ABORT, 'Tồn kho vượt quá trần tối đa cho phép 1.000.000.000');
            END;
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_products_max_stock_upd
            BEFORE UPDATE OF current_stock ON products
            FOR EACH ROW
            WHEN NEW.current_stock > 1000000000
            BEGIN
                SELECT RAISE(ABORT, 'Tồn kho vượt quá trần tối đa cho phép 1.000.000.000');
            END;
        """)
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency cung cấp session kết nối CSDL và tự động đóng sau khi hoàn thành request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
