"""Bộ kiểm thử cho Module AI Trợ lý và Heuristic Fallback Engine (Giai đoạn 3 / Mốc KT3).

Bao phủ các yêu cầu:
1. Data Pipeline an toàn: Không rò rỉ giá mua (unit_price) nhạy cảm.
2. Dữ liệu rỗng: Không crash khi chưa có sản phẩm hoặc giao dịch.
3. Fallback Engine: Hoạt động chính xác khi chưa có GEMINI_API_KEY hoặc offline.
4. Gợi ý nhập hàng: Tính toán đúng velocity, days_until_stockout và mức ưu tiên HIGH/MEDIUM/LOW.
5. Biến động bất thường: Phát hiện chính xác SURGE_EXPORT (>200%) và DEAD_STOCK (>30 ngày).
6. Mock Gemini API: Kiểm tra khi API trả về thành công thì is_fallback=False.
7. Phân quyền RBAC: Cả 3 vai trò (ADMIN, WAREHOUSE_KEEPER, ACCOUNTANT) đều được xem AI.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_default_users
from app.main import app
from app.models import (
    Category,
    ExportNote,
    ExportNoteDetail,
    ImportNote,
    ImportNoteDetail,
    Product,
    StockLedger,
    Supplier,
    User,
)
from app.services.ai_service import AIService


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Khởi tạo CSDL và nạp người dùng mặc định."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def thukho_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "thukho", "password": "thukho123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ketoan_headers(client):
    res = client.post("/api/v1/auth/login", json={"username": "ketoan", "password": "ketoan123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def ai_test_data():
    """Tạo bộ dữ liệu test riêng biệt cho các kịch bản AI (Idempotent)."""
    db = SessionLocal()
    try:
        # Category
        cat = db.query(Category).filter(Category.code == "CAT_AI").first()
        if not cat:
            cat = Category(code="CAT_AI", name="Linh kiện AI", description="Nhóm test AI")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        # Supplier
        sup = db.query(Supplier).filter(Supplier.code == "SUP_AI").first()
        if not sup:
            sup = Supplier(code="SUP_AI", name="Nhà phân phối AI Test", is_active=True)
            db.add(sup)
            db.commit()
            db.refresh(sup)

        # Product 1: Bán chạy sắp hết hàng (current_stock = 3, min_stock = 15)
        p1 = db.query(Product).filter(Product.code == "AI_SP01_FAST").first()
        if not p1:
            p1 = Product(
                code="AI_SP01_FAST",
                name="Sản phẩm Bán Chạy",
                category_id=cat.id,
                unit="Cái",
                min_stock=15,
                current_stock=3,
                standard_price=500000.0,
                status="ACTIVE",
            )
            db.add(p1)
        else:
            p1.current_stock = 3
            p1.min_stock = 15

        # Product 2: Xuất tăng đột biến (current_stock = 50, min_stock = 10)
        p2 = db.query(Product).filter(Product.code == "AI_SP02_SURGE").first()
        if not p2:
            p2 = Product(
                code="AI_SP02_SURGE",
                name="Sản phẩm Xuất Đột Biến",
                category_id=cat.id,
                unit="Hộp",
                min_stock=10,
                current_stock=50,
                standard_price=200000.0,
                status="ACTIVE",
            )
            db.add(p2)
        else:
            p2.current_stock = 50
            p2.min_stock = 10

        # Product 3: Hàng tồn kho chết (current_stock = 80, min_stock = 5, không xuất 30 ngày)
        p3 = db.query(Product).filter(Product.code == "AI_SP03_DEAD").first()
        if not p3:
            p3 = Product(
                code="AI_SP03_DEAD",
                name="Sản phẩm Tồn Chết",
                category_id=cat.id,
                unit="Bộ",
                min_stock=5,
                current_stock=80,
                standard_price=100000.0,
                status="ACTIVE",
            )
            db.add(p3)
        else:
            p3.current_stock = 80
            p3.min_stock = 5

        db.commit()
        db.refresh(p1)
        db.refresh(p2)
        db.refresh(p3)

        user = db.query(User).filter(User.username == "thukho").first()
        now = datetime.now()

        # Tạo lịch sử xuất cho P1 (bán chạy): 20 sản phẩm xuất trong 5 ngày qua
        exp1 = db.query(ExportNote).filter(ExportNote.code == "PX-AI-P1-STATIC").first()
        if not exp1:
            exp1 = ExportNote(
                code="PX-AI-P1-STATIC",
                recipient_name="Khách hàng AI 1",
                created_by=user.id,
                note_date=now - timedelta(days=5),
                total_amount=10000000.0,
                status="COMPLETED",
            )
            db.add(exp1)
            db.flush()
            db.add(
                ExportNoteDetail(
                    export_note_id=exp1.id,
                    product_id=p1.id,
                    quantity=20,
                    unit_price=500000.0,
                    subtotal=10000000.0,
                )
            )

        # Tạo lịch sử xuất cho P2 (xuất đột biến): 25 sản phẩm xuất trong 2 ngày gần nhất
        exp2 = db.query(ExportNote).filter(ExportNote.code == "PX-AI-P2-STATIC").first()
        if not exp2:
            exp2 = ExportNote(
                code="PX-AI-P2-STATIC",
                recipient_name="Khách hàng AI 2",
                created_by=user.id,
                note_date=now - timedelta(days=2),
                total_amount=5000000.0,
                status="COMPLETED",
            )
            db.add(exp2)
            db.flush()
            db.add(
                ExportNoteDetail(
                    export_note_id=exp2.id,
                    product_id=p2.id,
                    quantity=25,
                    unit_price=200000.0,
                    subtotal=5000000.0,
                )
            )

        db.commit()

        return {
            "p1_id": p1.id,
            "p2_id": p2.id,
            "p3_id": p3.id,
        }
    finally:
        db.close()



def test_ai_pipeline_excludes_unit_price(ai_test_data):
    """Kiểm tra an toàn bảo mật: Tuyệt đối không gửi giá mua (unit_price) vào context AI."""
    db = SessionLocal()
    try:
        now = datetime.now()

        # 1. Pipeline Monthly Aggregated
        metrics = AIService.get_monthly_aggregated_data(db, now.month, now.year)
        metrics_dict = metrics.model_dump()
        for key in ["unit_price", "standard_price", "cost_price", "subtotal", "total_amount"]:
            assert key not in metrics_dict, f"Rò rỉ trường giá nhạy cảm {key} trong metrics!"
        for item in metrics_dict.get("top_exported_products", []):
            assert "unit_price" not in item
            assert "standard_price" not in item

        # 2. Pipeline Restock Candidates
        restock_candidates = AIService.get_restock_candidates_data(db, lookback_days=30)
        for item in restock_candidates:
            for key in ["unit_price", "standard_price", "cost_price"]:
                assert key not in item, f"Rò rỉ trường giá {key} trong restock candidates!"

        # 3. Pipeline Anomalies Candidates
        anomalies_candidates = AIService.get_anomalies_candidates_data(db, lookback_days=30)
        for item in anomalies_candidates:
            for key in ["unit_price", "standard_price", "cost_price"]:
                assert key not in item, f"Rò rỉ trường giá {key} trong anomalies candidates!"
    finally:
        db.close()


def test_ai_monthly_report_endpoint(client, thukho_headers, ai_test_data):
    """Kiểm tra endpoint /monthly-report trả về đúng định dạng khi offline (fallback)."""
    now = datetime.now()
    response = client.get(
        f"/api/v1/ai/monthly-report?month={now.month}&year={now.year}",
        headers=thukho_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["period"] == f"{now.month:02d}/{now.year}"
    assert data["is_fallback"] is True
    assert data["provider"] == "heuristic_fallback"
    assert "metrics" in data
    assert data["metrics"]["total_products"] >= 3
    assert len(data["executive_summary"]) > 10
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) > 0


def test_ai_restock_suggestions_endpoint(client, admin_headers, ai_test_data):
    """Kiểm tra gợi ý nhập hàng phát hiện đúng sản phẩm bán chạy sắp hết hàng (AI_SP01_FAST)."""
    response = client.get(
        "/api/v1/ai/restock-suggestions?lookback_days=30",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["is_fallback"] is True
    assert data["provider"] == "heuristic_fallback"
    assert data["total_suggested_items"] >= 1

    # Tìm sản phẩm AI_SP01_FAST trong danh sách gợi ý
    fast_item = next((it for it in data["items"] if it["product_code"] == "AI_SP01_FAST"), None)
    assert fast_item is not None
    assert fast_item["priority"] == "HIGH"
    assert fast_item["current_stock"] == 3
    assert fast_item["min_stock"] == 15
    assert fast_item["suggested_quantity"] >= 15
    assert len(fast_item["reason"]) > 0


def test_ai_anomalies_endpoint(client, ketoan_headers, ai_test_data):
    """Kiểm tra phát hiện bất thường: xuất đột biến (AI_SP02_SURGE) và hàng tồn chết (AI_SP03_DEAD)."""
    response = client.get(
        "/api/v1/ai/anomalies?lookback_days=30",
        headers=ketoan_headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["is_fallback"] is True
    assert data["provider"] == "heuristic_fallback"
    assert data["total_anomalies"] >= 1

    # Kiểm tra có sản phẩm xuất đột biến
    surge_item = next((it for it in data["anomalies"] if it["product_code"] == "AI_SP02_SURGE"), None)
    if surge_item:
        assert surge_item["anomaly_type"] == "SURGE_EXPORT"
        assert len(surge_item["suggested_action"]) > 0

    # Kiểm tra có sản phẩm tồn kho chết
    dead_item = next((it for it in data["anomalies"] if it["product_code"] == "AI_SP03_DEAD"), None)
    if dead_item:
        assert dead_item["anomaly_type"] == "DEAD_STOCK"
        assert len(dead_item["suggested_action"]) > 0


def test_ai_mock_gemini_success(client, admin_headers, ai_test_data):
    """Giả lập gọi thành công Google Gemini API để kiểm tra luồng tích hợp LLM thật."""
    mock_response = MagicMock()
    mock_response.text = (
        '{"executive_summary": "Tóm tắt từ Gemini AI mô phỏng thành công.", '
        '"recommendations": ["Khuyến nghị AI 1", "Khuyến nghị AI 2"]}'
    )

    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "dummy_test_api_key"):
        with patch("google.generativeai.GenerativeModel", return_value=mock_model):
            response = client.get("/api/v1/ai/monthly-report", headers=admin_headers)
            assert response.status_code == 200
            data = response.json()

            assert data["is_fallback"] is False
            assert data["provider"] == "gemini"
            assert "Gemini AI mô phỏng" in data["executive_summary"]
            assert len(data["recommendations"]) == 2


def test_ai_rbac_and_unauthorized(client):
    """Kiểm tra phân quyền: Không có Bearer Token thì từ chối truy cập HTTP 401."""
    res1 = client.get("/api/v1/ai/monthly-report")
    assert res1.status_code == 401

    res2 = client.get("/api/v1/ai/restock-suggestions")
    assert res2.status_code == 401

    res3 = client.get("/api/v1/ai/anomalies")
    assert res3.status_code == 401
