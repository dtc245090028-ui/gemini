"""Bộ kiểm thử cho Module AI khi Kho Rỗng (Empty Warehouse Data) hoặc Không phát sinh giao dịch.

Bao phủ các kịch bản:
1. CSDL hoàn toàn rỗng (0 mặt hàng, 0 giao dịch):
   - Endpoint /monthly-report trả về 200 OK, kích hoạt fallback báo kho rỗng, không crash 500.
   - Endpoint /restock-suggestions trả về 200 OK, items=[] và thông báo kho cân bằng an toàn.
   - Endpoint /anomalies trả về 200 OK, anomalies=[] và thông báo kho vận hành ổn định.
2. Có sản phẩm nhưng không có giao dịch trong kỳ (active_products = 0):
   - /monthly-report nhận diện trạng thái kho bất động và đưa ra khuyến nghị phù hợp.
3. Sử dụng CSDL SQLite in-memory độc lập (:memory:), tuyệt đối không can thiệp hay sửa đổi CSDL thật.
"""

from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.config import settings
from app.core.database import Base
from app.core.seed import seed_default_users
from app.main import app
from app.models import Category, Product
from app.services.ai_cache import AICacheManager


# Khởi tạo Engine SQLite in-memory hoàn toàn độc lập cho test case dữ liệu rỗng
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="module")
def setup_empty_db():
    """Tạo bảng và nạp người dùng mặc định trên DB in-memory, giữ kho hoàn toàn rỗng."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_cache():
    """Dọn sạch AI cache trước và sau mỗi test."""
    AICacheManager.clear()
    yield
    AICacheManager.clear()


@pytest.fixture
def client(setup_empty_db):
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ai_monthly_report_completely_empty_warehouse(client, auth_headers):
    """Kiểm tra báo cáo tháng khi kho hoàn toàn không có sản phẩm nào (total_products == 0)."""
    now = datetime.now()
    res = client.get(
        f"/api/v1/ai/monthly-report?month={now.month}&year={now.year}",
        headers=auth_headers,
    )
    assert res.status_code == 200, f"Lỗi endpoint trả về {res.status_code}: {res.text}"
    data = res.json()

    # Kiểm tra cờ Fallback & Metrics
    assert data["is_fallback"] is True
    assert data["provider"] == "heuristic_fallback"
    assert data["metrics"]["total_products"] == 0
    assert data["metrics"]["active_products"] == 0
    assert data["metrics"]["total_imports_qty"] == 0
    assert data["metrics"]["total_exports_qty"] == 0
    assert data["metrics"]["low_stock_count"] == 0
    assert data["metrics"]["top_exported_products"] == []

    # Nội dung thông báo thân thiện về kho rỗng
    summary_lower = data["executive_summary"].lower()
    assert "chưa ghi nhận mặt hàng nào" in summary_lower or "khởi tạo danh mục" in summary_lower
    assert len(data["recommendations"]) >= 1


def test_ai_restock_suggestions_completely_empty_warehouse(client, auth_headers):
    """Kiểm tra gợi ý nhập hàng khi kho không có sản phẩm nào."""
    res = client.get("/api/v1/ai/restock-suggestions?lookback_days=30", headers=auth_headers)
    assert res.status_code == 200, f"Lỗi endpoint trả về {res.status_code}: {res.text}"
    data = res.json()

    assert data["is_fallback"] is True
    assert data["provider"] == "heuristic_fallback"
    assert data["total_suggested_items"] == 0
    assert data["items"] == []
    assert len(data["executive_summary"]) > 0


def test_ai_anomalies_completely_empty_warehouse(client, auth_headers):
    """Kiểm tra phát hiện bất thường khi kho không có sản phẩm nào."""
    res = client.get("/api/v1/ai/anomalies?lookback_days=30", headers=auth_headers)
    assert res.status_code == 200, f"Lỗi endpoint trả về {res.status_code}: {res.text}"
    data = res.json()

    assert data["is_fallback"] is True
    assert data["provider"] == "heuristic_fallback"
    assert data["total_anomalies"] == 0
    assert data["anomalies"] == []
    assert len(data["executive_summary"]) > 0


def test_ai_monthly_report_products_exist_but_zero_transactions(client, auth_headers):
    """Kiểm tra báo cáo tháng khi kho có mặt hàng nhưng không phát sinh bất kỳ giao dịch nào (active_products == 0)."""
    # Thêm 1 sản phẩm vào CSDL in-memory nhưng không tạo phiếu nhập/xuất
    db = TestingSessionLocal()
    try:
        cat = Category(code="CAT_EMPTY_TEST", name="Danh mục thử nghiệm")
        db.add(cat)
        db.commit()
        db.refresh(cat)

        p = Product(
            code="SP_NO_TX",
            name="Sản phẩm chưa có giao dịch",
            category_id=cat.id,
            unit="Cái",
            min_stock=10,
            current_stock=50,
            standard_price=100000.0,
            status="ACTIVE",
        )
        db.add(p)
        db.commit()
    finally:
        db.close()

    now = datetime.now()
    from unittest.mock import patch
    with patch.object(settings, "GEMINI_API_KEY", ""):
        res = client.get(
            f"/api/v1/ai/monthly-report?month={now.month}&year={now.year}",
            headers=auth_headers,
        )
        assert res.status_code == 200
        data = res.json()

        assert data["is_fallback"] is True
        assert data["metrics"]["total_products"] >= 1
        assert data["metrics"]["active_products"] == 0
        assert data["metrics"]["total_imports_qty"] == 0
        assert data["metrics"]["total_exports_qty"] == 0

        summary_lower = data["executive_summary"].lower()
        assert "bất động" in summary_lower or "không phát sinh" in summary_lower or "chưa ghi nhận" in summary_lower
        assert len(data["recommendations"]) >= 1
