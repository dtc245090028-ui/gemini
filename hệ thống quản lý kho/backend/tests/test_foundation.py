"""Kiểm thử nền tảng kỹ thuật và cấu trúc cơ sở dữ liệu (Giai đoạn 0 & 1)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.core.database import engine, SessionLocal, Base
from app.models import Category, Product, Supplier, User, StockLedger


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """Kiểm tra endpoint /health trả về mã HTTP 200 và trạng thái healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_database_all_nine_tables_created():
    """Kiểm tra đầy đủ 9 bảng CSDL cốt lõi theo thiết kế ERD đã được tạo."""
    expected_tables = {
        "users",
        "categories",
        "products",
        "suppliers",
        "import_notes",
        "import_note_details",
        "export_notes",
        "export_note_details",
        "stock_ledger",
    }
    inspector = inspect(engine)
    created_tables = set(inspector.get_table_names())
    assert expected_tables.issubset(created_tables), f"Thiếu bảng: {expected_tables - created_tables}"


def test_prevent_negative_current_stock():
    """Kiểm tra ràng buộc CHECK (current_stock >= 0) ngăn chặn triệt để tồn kho âm."""
    db = SessionLocal()
    try:
        category = Category(code="TEST-CAT-01", name="Nhóm thử nghiệm")
        db.add(category)
        db.commit()

        # Thử thêm sản phẩm có số tồn âm (-10)
        invalid_product = Product(
            code="SP-NEG-TEST",
            name="Sản phẩm tồn âm lỗi",
            category_id=category.id,
            current_stock=-10,
        )
        db.add(invalid_product)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.query(Product).filter_by(code="SP-NEG-TEST").delete()
        db.query(Category).filter_by(code="TEST-CAT-01").delete()
        db.commit()
        db.close()
