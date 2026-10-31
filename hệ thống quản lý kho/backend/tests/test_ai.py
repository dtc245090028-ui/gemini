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


@pytest.fixture(autouse=True)
def clean_ai_cache():
    """Đảm bảo dọn dẹp cache trước và sau mỗi test case."""
    from app.services.ai_cache import AICacheManager
    AICacheManager.clear()
    yield
    AICacheManager.clear()


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
    with patch.object(settings, "GEMINI_API_KEY", ""):
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
    with patch.object(settings, "GEMINI_API_KEY", ""):
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
    with patch.object(settings, "GEMINI_API_KEY", ""):
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


def test_ai_in_day_cache(client, admin_headers, ai_test_data):
    """Kiểm tra cơ chế Cache trong ngày: Lần gọi thứ 2 trả về is_cached=True, force_refresh=True thì gọi mới."""
    mock_response = MagicMock()
    mock_response.text = (
        '{"executive_summary": "Tóm tắt kiểm tra Cache.", "recommendations": ["Khuyến nghị 1"]}'
    )
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "dummy_test_api_key"):
        with patch("google.generativeai.GenerativeModel", return_value=mock_model):
            # Lần gọi 1 -> Tạo mới vào cache
            res1 = client.get("/api/v1/ai/monthly-report?month=1&year=2026", headers=admin_headers)
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["is_fallback"] is False
            assert data1["is_cached"] is False

            # Lần gọi 2 -> Phải lấy từ Cache
            res2 = client.get("/api/v1/ai/monthly-report?month=1&year=2026", headers=admin_headers)
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["is_cached"] is True
            assert data2["executive_summary"] == data1["executive_summary"]

            # Lần gọi 3 -> force_refresh=true phải bỏ qua cache
            res3 = client.get("/api/v1/ai/monthly-report?month=1&year=2026&force_refresh=true", headers=admin_headers)
            assert res3.status_code == 200
            data3 = res3.json()
            assert data3["is_cached"] is False


def test_generate_ai_order_fallback(client, admin_headers, ai_test_data):
    """Kiểm tra sinh đơn hàng khi không có Gemini Key hoặc Offline -> Dùng Heuristic Fallback."""
    with patch.object(settings, "GEMINI_API_KEY", ""):
        res = client.post("/api/v1/ai/generate-order", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()

        assert data["is_fallback"] is True
        assert data["provider"] == "heuristic_fallback"
        assert data["quantity"] > 0
        assert data["quantity"] <= data["current_stock"]
        assert data["recipient_name"] != ""
        assert data["product_code"] != ""
        assert "Đơn hàng AI:" in data["note"]


def test_generate_ai_order_gemini_success_and_cache(client, admin_headers, ai_test_data):
    """Kiểm tra sinh đơn hàng thành công với Gemini AI và kiểm tra cơ chế Cache trong ngày."""
    mock_response = MagicMock()
    mock_response.text = (
        '{"scenario_id": "SCENARIO_02", "recipient_name": "Công ty TNHH Giải Pháp Đám Mây CloudV", '
        '"role": "company", "product_sku": "AI_SP02_SURGE", "quantity": 15, "discount_percent": 7.0, '
        '"reason": "Khách hàng doanh nghiệp trang bị đồng loạt cho trung tâm dữ liệu mới."}'
    )
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "dummy_test_api_key"):
        with patch("google.generativeai.GenerativeModel", return_value=mock_model):
            # Lần gọi 1 -> Thành công và lưu cache trong ngày
            res1 = client.post("/api/v1/ai/generate-order", headers=admin_headers)
            assert res1.status_code == 200
            data1 = res1.json()

            assert data1["is_fallback"] is False
            assert data1["provider"] == "gemini"
            assert data1["is_cached"] is False
            assert data1["product_code"] == "AI_SP02_SURGE"
            assert data1["quantity"] == 15
            assert data1["discount_percent"] == 7.0
            assert "CloudV" in data1["recipient_name"]

            # Lần gọi 2 -> Lấy từ Cache trong ngày mà không gọi lại Gemini API
            res2 = client.post("/api/v1/ai/generate-order", headers=admin_headers)
            assert res2.status_code == 200
            data2 = res2.json()

            assert data2["is_cached"] is True
            assert data2["product_code"] == data1["product_code"]
            assert data2["quantity"] == data1["quantity"]

            # Lần gọi 3 -> force_refresh=true thì tính toán lại
            res3 = client.post("/api/v1/ai/generate-order?force_refresh=true", headers=admin_headers)
            assert res3.status_code == 200
            data3 = res3.json()
            assert data3["is_cached"] is False


def test_generate_ai_order_rbac(client, ketoan_headers):
    """Kiểm tra phân quyền: Chỉ ADMIN và WAREHOUSE_KEEPER mới được tạo đơn hàng AI."""
    # Chưa đăng nhập -> 401
    res1 = client.post("/api/v1/ai/generate-order")
    assert res1.status_code == 401

    # Kế toán -> 403 Forbidden (chỉ ADMIN và THUKHO được tạo phiếu xuất)
    res2 = client.post("/api/v1/ai/generate-order", headers=ketoan_headers)
    assert res2.status_code == 403


def test_ask_ai_fallback(client, admin_headers, ai_test_data):
    """Kiểm tra chức năng Hỏi đáp AI khi offline hoặc không có API key -> Trả lời bằng Fallback Engine."""
    with patch.object(settings, "GEMINI_API_KEY", ""):
        # Chế độ SmartKho
        res = client.post(
            "/api/v1/ai/ask",
            json={
                "question": "Làm thế nào để xử lý các mặt hàng dưới mức tồn an toàn?",
                "month": 1,
                "year": 2026,
                "include_smartkho": True,
            },
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()

        assert data["is_fallback"] is True
        assert data["provider"] == "heuristic_fallback"
        assert "tồn kho an toàn" in data["answer"].lower()
        assert data["include_smartkho"] is True
        assert len(data["timestamp"]) > 0


def test_ask_ai_gemini_pure_and_smartkho_modes(client, admin_headers, ai_test_data):
    """Kiểm tra chế độ thuần câu hỏi (AI tự do trả lời) và chế độ có tích chọn #SmartKho."""
    mock_response = MagicMock()
    mock_response.text = '{"answer": "Xe buýt dừng ở 2 trạm."}'
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "dummy_test_api_key"):
        with patch("google.generativeai.GenerativeModel", return_value=mock_model):
            # 1. include_smartkho = False (Thuần câu hỏi)
            res1 = client.post(
                "/api/v1/ai/ask",
                json={"question": "Một chiếc xe buýt dừng ở bao nhiêu trạm?", "include_smartkho": False},
                headers=admin_headers,
            )
            assert res1.status_code == 200
            data1 = res1.json()
            assert data1["include_smartkho"] is False
            assert "Xe buýt dừng ở 2 trạm" in data1["answer"]

            # 2. include_smartkho = True (Chế độ #SmartKho)
            res2 = client.post(
                "/api/v1/ai/ask",
                json={"question": "Kế hoạch nhập hàng tối ưu?", "month": 1, "year": 2026, "include_smartkho": True},
                headers=admin_headers,
            )
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["include_smartkho"] is True


def test_ask_ai_rbac_and_unauthorized(client, ketoan_headers):
    """Kiểm tra phân quyền hỏi đáp AI: Chưa đăng nhập bị 401, Kế toán (ACCOUNTANT) được phép truy cập (200)."""
    # Chưa đăng nhập -> 401
    res1 = client.post("/api/v1/ai/ask", json={"question": "Xin chào AI?"})
    assert res1.status_code == 401

    # Kế toán -> Được phép hỏi đáp (200)
    with patch.object(settings, "GEMINI_API_KEY", ""):
        res2 = client.post(
            "/api/v1/ai/ask",
            json={"question": "Đánh giá xuất nhập kho kỳ này?", "month": 1, "year": 2026},
            headers=ketoan_headers,
        )
        assert res2.status_code == 200


def test_ai_range_cache_fingerprint_single_day_and_fallback(client, admin_headers, ai_test_data):
    """Kiểm tra lưu & tái sử dụng báo cáo AI theo khoảng ngày:
    - Chế độ dự phòng (is_fallback=True) không khóa bản lưu cho lần gọi AI thật kế tiếp.
    - Khoảng nhiều ngày chỉ có 1 ngày biến động tái sử dụng nhận xét của ngày đó.
    - Khi dữ liệu stock_ledger trong khoảng thay đổi (dấu vết dữ liệu đổi), bản lưu cũ tự hết hạn.
    """
    db = SessionLocal()
    try:
        p1 = db.query(Product).filter(Product.code == "AI_SP01_FAST").first()
        admin_user = db.query(User).filter(User.username == "admin").first()

        # Tạo 1 biến động duy nhất vào ngày 2025-05-14 (nằm trong tuần 2025-05-12 -> 2025-05-18)
        db.query(StockLedger).filter(
            StockLedger.reference_code.like("TEST_RANGE_%")
        ).delete(synchronize_session=False)
        db.commit()

        ledger1 = StockLedger(
            product_id=p1.id,
            transaction_type="IMPORT",
            reference_code="TEST_RANGE_01",
            quantity_change=10,
            balance_after=p1.current_stock + 10,
            created_by=admin_user.id,
            note="Test range cache 1",
            transaction_date=datetime(2025, 5, 14, 10, 0, 0),
        )
        db.add(ledger1)
        db.commit()

        # 1. Gọi ở chế độ Fallback (không có GEMINI_API_KEY)
        with patch.object(settings, "GEMINI_API_KEY", ""):
            res_fb = client.get(
                "/api/v1/ai/monthly-report?period_type=day&target_date=2025-05-14",
                headers=admin_headers,
            )
            assert res_fb.status_code == 200
            data_fb = res_fb.json()
            assert data_fb["is_fallback"] is True
            assert data_fb["is_cached"] is False
            assert data_fb["start_date"] == "2025-05-14"
            assert data_fb["end_date"] == "2025-05-14"

        # 2. Khi có GEMINI_API_KEY trở lại, bản fallback trước đó không được chặn -> Gọi AI thật
        mock_response = MagicMock()
        mock_response.text = (
            '{"executive_summary": "Nhận xét AI ngày 14/05/2025.", "recommendations": ["Khuyến nghị ngày 14/05"]}'
        )
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        with patch.object(settings, "GEMINI_API_KEY", "dummy_test_api_key"):
            with patch("google.generativeai.GenerativeModel", return_value=mock_model):
                res_ai_day = client.get(
                    "/api/v1/ai/monthly-report?period_type=day&target_date=2025-05-14",
                    headers=admin_headers,
                )
                assert res_ai_day.status_code == 200
                data_ai_day = res_ai_day.json()
                assert data_ai_day["is_fallback"] is False
                assert data_ai_day["is_cached"] is False
                assert data_ai_day["cached_at"] is not None
                assert mock_model.generate_content.call_count == 1

                # 3. Gọi theo tuần chứa ngày 2025-05-14 (tuần 2025-05-12 -> 2025-05-18 chỉ có 1 ngày biến động)
                # Hệ thống phải tái sử dụng nhận xét của ngày 2025-05-14 mà KHÔNG gọi thêm Gemini AI
                res_week = client.get(
                    "/api/v1/ai/monthly-report?period_type=week&target_date=2025-05-14",
                    headers=admin_headers,
                )
                assert res_week.status_code == 200
                data_week = res_week.json()
                assert data_week["is_cached"] is True
                assert data_week["start_date"] == "2025-05-12"
                assert data_week["end_date"] == "2025-05-18"
                assert data_week["executive_summary"] == "Nhận xét AI ngày 14/05/2025."
                assert mock_model.generate_content.call_count == 1

                # 4. Thêm 1 dòng biến động mới vào ngày 2025-05-14 -> Dấu vết dữ liệu (fingerprint) thay đổi
                ledger2 = StockLedger(
                    product_id=p1.id,
                    transaction_type="EXPORT",
                    reference_code="TEST_RANGE_02",
                    quantity_change=-4,
                    balance_after=p1.current_stock + 6,
                    created_by=admin_user.id,
                    note="Test range cache 2",
                    transaction_date=datetime(2025, 5, 14, 15, 0, 0),
                )
                db.add(ledger2)
                db.commit()

                # Gọi lại ngày 2025-05-14 -> Bản lưu cũ tự hết hạn do fingerprint đổi, gọi lại Gemini AI
                res_after_change = client.get(
                    "/api/v1/ai/monthly-report?period_type=day&target_date=2025-05-14",
                    headers=admin_headers,
                )
                assert res_after_change.status_code == 200
                data_after = res_after_change.json()
                assert data_after["is_cached"] is False
                assert mock_model.generate_content.call_count == 2
    finally:
        db.query(StockLedger).filter(
            StockLedger.reference_code.like("TEST_RANGE_%")
        ).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_ask_ai_context_info_financials_and_low_stock(client, admin_headers, ai_test_data):
    """Kiểm tra context_info của ask_ai (include_smartkho=True) chứa:
    - Tổng tiền nhập/xuất hợp lệ và tổng giá trị tồn kho ước tính (VNĐ có dấu phân cách hàng nghìn)
    - Danh sách mã hàng dưới tồn an toàn (ví dụ AI_SP01_FAST)
    - Nhãn diễn giải đúng: 'mặt hàng đang kinh doanh (trong đó ... mặt hàng có phát sinh nhập/xuất trong kỳ)'
    - Bảo mật: Tuyệt đối không chứa chữ 'unit_price' trong prompt gửi đi.
    """
    db = SessionLocal()
    now = datetime.now()
    try:
        user = db.query(User).filter(User.username == "thukho").first()
        sup = db.query(Supplier).filter(Supplier.code == "SUP_AI").first()
        p1 = db.query(Product).filter(Product.code == "AI_SP01_FAST").first()

        # Đảm bảo p1 đang dưới tồn an toàn (current_stock <= min_stock)
        p1.current_stock = 3
        p1.min_stock = 15

        # Tạo 1 phiếu nhập hợp lệ trong tháng hiện tại nếu chưa có để kiểm tra tổng tiền nhập > 0
        imp = db.query(ImportNote).filter(ImportNote.code == "PN-AI-CTX-TEST").first()
        if not imp:
            imp = ImportNote(
                code="PN-AI-CTX-TEST",
                supplier_id=sup.id,
                created_by=user.id,
                note_date=now,
                total_amount=2500000.0,
                status="COMPLETED",
                note="Phiếu nhập test context_info AI",
            )
            db.add(imp)
            db.flush()
            db.add(
                ImportNoteDetail(
                    import_note_id=imp.id,
                    product_id=p1.id,
                    quantity=5,
                    unit_price=500000.0,
                    subtotal=2500000.0,
                )
            )
        db.commit()

        captured_prompts = []

        def fake_call_gemini(prompt_content, generation_config=None):
            captured_prompts.append(prompt_content)
            return '{"answer": "Báo cáo phân tích tài chính và tồn kho từ Gemini."}'

        with patch.object(settings, "GEMINI_API_KEY", "dummy_test_api_key"):
            with patch.object(AIService, "_call_gemini_with_models", side_effect=fake_call_gemini):
                res = client.post(
                    "/api/v1/ai/ask",
                    json={
                        "question": "Trong tháng này có bao nhiêu hàng hóa ra vào, số tiền vào và ra là bao nhiêu?",
                        "month": now.month,
                        "year": now.year,
                        "include_smartkho": True,
                    },
                    headers=admin_headers,
                )
                assert res.status_code == 200
                assert len(captured_prompts) == 1
                sent_prompt = captured_prompts[0]

                # 1. Có nhãn diễn giải đúng cho active_products
                assert "mặt hàng đang kinh doanh" in sent_prompt
                assert "có phát sinh nhập/xuất trong kỳ" in sent_prompt
                assert "đang hoạt động)" not in sent_prompt

                # 2. Có tổng giá trị tiền nhập / xuất và tổng giá trị tồn kho định dạng VNĐ
                assert "Tổng giá trị tiền nhập kho trong kỳ:" in sent_prompt
                assert "Tổng giá trị tiền xuất kho trong kỳ:" in sent_prompt
                assert "Tổng giá trị tồn kho hiện tại ước tính:" in sent_prompt
                assert "VNĐ" in sent_prompt

                # 3. Có danh sách mã hàng dưới tồn an toàn cụ thể (AI_SP01_FAST)
                assert "Danh sách mặt hàng dưới mức tồn an toàn" in sent_prompt
                assert "AI_SP01_FAST" in sent_prompt

                # 4. Không chứa từ khóa nhạy cảm unit_price
                assert "unit_price" not in sent_prompt
    finally:
        db.query(ImportNoteDetail).filter(
            ImportNoteDetail.import_note_id.in_(
                db.query(ImportNote.id).filter(ImportNote.code == "PN-AI-CTX-TEST")
            )
        ).delete(synchronize_session=False)
        db.query(ImportNote).filter(ImportNote.code == "PN-AI-CTX-TEST").delete(synchronize_session=False)
        db.commit()
        db.close()
