"""Bộ kiểm thử Blackbox & Bảo mật mở rộng theo tiêu chuẩn AGENT-TESTING-GUIDE.

Bao gồm:
1. Happy path, Schema validation, Boundary values (số âm, chuỗi rỗng).
2. Phân quyền RBAC, Token giả mạo, Không có token.
3. Luồng tích hợp liên hoàn nghiệp vụ kho & Guard-check.
4. Kiểm thử an ninh giả định: SQL injection text query, Giả mạo token.
"""

import pytest
import jwt
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_default_users


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Khởi tạo cấu trúc bảng CSDL và nạp dữ liệu tài khoản."""
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


# ==============================================================================
# 1. AUTHENTICATION & TOKEN SECURITY BLACKBOX
# ==============================================================================

def test_auth_negative_wrong_password(client):
    """Đăng nhập sai mật khẩu phải trả về 401."""
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401
    assert "detail" in res.json()


def test_auth_negative_nonexistent_user(client):
    """Đăng nhập tài khoản không tồn tại phải trả về 401."""
    res = client.post("/api/v1/auth/login", json={"username": "ghost_user", "password": "anypassword"})
    assert res.status_code == 401


def test_auth_schema_missing_fields(client):
    """Thiếu username hoặc password phải trả về 422 Unprocessable Content."""
    res = client.post("/api/v1/auth/login", json={"username": "admin"})
    assert res.status_code == 422

    res2 = client.post("/api/v1/auth/login", json={})
    assert res2.status_code == 422


def test_security_tampered_jwt_signature(client):
    """Token bị ký bởi secret key giả mạo phải bị từ chối 401."""
    fake_token = jwt.encode(
        {"sub": "admin", "role": "ADMIN", "exp": 9999999999},
        "FAKE_SECRET_KEY_NOT_OURS",
        algorithm="HS256"
    )
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
    assert res.status_code == 401


def test_security_malformed_token(client):
    """Token rác / không đúng format JWT phải trả về 401."""
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not_a_valid_jwt_token_string"})
    assert res.status_code == 401


def test_security_unauthenticated_requests(client):
    """Gọi các endpoint yêu cầu quyền mà không có header Authorization phải trả về 401."""
    assert client.get("/api/v1/products/").status_code == 401
    assert client.get("/api/v1/import-notes/").status_code == 401
    assert client.get("/api/v1/export-notes/").status_code == 401
    assert client.get("/api/v1/stock-ledger/").status_code == 401
    assert client.get("/api/v1/ai/monthly-report").status_code == 401


# ==============================================================================
# 2. RBAC ACCESS CONTROL ENFORCEMENT
# ==============================================================================

def test_rbac_accountant_forbidden_from_creating_products(client, ketoan_headers):
    """Vai trò Kế toán (ACCOUNTANT) không có quyền tạo sản phẩm mới -> phải trả về 403."""
    payload = {
        "code": "PROD_KETOAN_DENIED",
        "name": "Sản phẩm kế toán thử tạo",
        "unit": "Hộp",
        "category_id": 1,
        "standard_price": 50000,
        "min_stock": 5
    }
    res = client.post("/api/v1/products/", json=payload, headers=ketoan_headers)
    assert res.status_code == 403


def test_rbac_accountant_forbidden_from_creating_import_note(client, ketoan_headers):
    """Vai trò Kế toán không có quyền tạo phiếu nhập kho -> phải trả về 403."""
    payload = {
        "supplier_id": 1,
        "details": [{"product_id": 1, "quantity": 10, "unit_price": 10000}]
    }
    res = client.post("/api/v1/import-notes/", json=payload, headers=ketoan_headers)
    assert res.status_code == 403


def test_rbac_warehouse_keeper_cannot_create_users(client, thukho_headers):
    """Vai trò Thủ kho không có quyền tạo user mới -> phải trả về 403."""
    payload = {
        "username": "new_staff",
        "password": "password123",
        "full_name": "Nhân viên mới",
        "role": "ACCOUNTANT"
    }
    res = client.post("/api/v1/auth/users", json=payload, headers=thukho_headers)
    assert res.status_code == 403


# ==============================================================================
# 3. SCHEMA & BOUNDARY VALIDATION (SỐ ÂM, CHUỖI RỖNG, ID KHÔNG TỒN TẠI)
# ==============================================================================

def test_boundary_product_negative_min_stock(client, admin_headers):
    """Tạo sản phẩm với min_stock < 0 phải bị từ chối 422."""
    payload = {
        "code": "SKU_NEG_MIN",
        "name": "Hàng tồn âm",
        "unit": "Cái",
        "category_id": 1,
        "standard_price": 10000,
        "min_stock": -5
    }
    res = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    assert res.status_code == 422


def test_boundary_product_negative_standard_price(client, admin_headers):
    """Tạo sản phẩm với standard_price < 0 phải bị từ chối 422."""
    payload = {
        "code": "SKU_NEG_PRICE",
        "name": "Hàng giá âm",
        "unit": "Cái",
        "category_id": 1,
        "standard_price": -50000,
        "min_stock": 10
    }
    res = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    assert res.status_code == 422


def test_boundary_product_nonexistent_category(client, admin_headers):
    """Tạo sản phẩm với category_id không tồn tại (ID=99999) phải trả về 400."""
    payload = {
        "code": "SKU_NO_CAT",
        "name": "Hàng không danh mục",
        "unit": "Cái",
        "category_id": 99999,
        "standard_price": 20000,
        "min_stock": 5
    }
    res = client.post("/api/v1/products/", json=payload, headers=admin_headers)
    assert res.status_code == 400


def test_boundary_product_not_found(client, admin_headers):
    """Truy vấn sản phẩm ID=999999 không tồn tại phải trả về 404."""
    res = client.get("/api/v1/products/999999", headers=admin_headers)
    assert res.status_code == 404


def test_boundary_import_note_empty_details(client, admin_headers):
    """Tạo phiếu nhập không có dòng hàng nào (details=[]) phải bị từ chối 400 hoặc 422."""
    payload = {
        "supplier_id": 1,
        "note": "Phiếu rỗng",
        "details": []
    }
    res = client.post("/api/v1/import-notes/", json=payload, headers=admin_headers)
    assert res.status_code in [400, 422]


def test_boundary_import_note_zero_or_negative_quantity(client, admin_headers):
    """Tạo phiếu nhập với quantity <= 0 phải bị từ chối 422."""
    payload = {
        "supplier_id": 1,
        "details": [{"product_id": 1, "quantity": 0, "unit_price": 10000}]
    }
    res = client.post("/api/v1/import-notes/", json=payload, headers=admin_headers)
    assert res.status_code == 422

    payload_neg = {
        "supplier_id": 1,
        "details": [{"product_id": 1, "quantity": -10, "unit_price": 10000}]
    }
    res_neg = client.post("/api/v1/import-notes/", json=payload_neg, headers=admin_headers)
    assert res_neg.status_code == 422


def test_boundary_export_note_empty_details(client, admin_headers):
    """Tạo phiếu xuất không có sản phẩm (details=[]) phải bị từ chối 400 hoặc 422."""
    payload = {
        "recipient_name": "Người nhận A",
        "details": []
    }
    res = client.post("/api/v1/export-notes/", json=payload, headers=admin_headers)
    assert res.status_code in [400, 422]


def test_boundary_export_note_missing_recipient(client, admin_headers):
    """Tạo phiếu xuất thiếu recipient_name phải trả về 422."""
    payload = {
        "recipient_name": "",
        "details": [{"product_id": 1, "quantity": 1}]
    }
    res = client.post("/api/v1/export-notes/", json=payload, headers=admin_headers)
    assert res.status_code == 422


def test_boundary_ai_invalid_month_or_lookback(client, admin_headers):
    """Tham số tháng sai (month=13) hoặc lookback âm (lookback_days=-10) phải bị từ chối 422."""
    res_month = client.get("/api/v1/ai/monthly-report?month=13&year=2026", headers=admin_headers)
    assert res_month.status_code == 422

    res_lookback = client.get("/api/v1/ai/restock-suggestions?lookback_days=-10", headers=admin_headers)
    assert res_lookback.status_code == 422


# ==============================================================================
# 4. SECURITY & ROBUSTNESS TESTING (SQL INJECTION ATTEMPTS)
# ==============================================================================

def test_security_sql_injection_in_search_queries(client, admin_headers):
    """Thử nghiệm chuỗi tấn công SQL Injection vào ô tìm kiếm sản phẩm, nhà cung cấp, nhóm hàng.
    Hệ thống sử dụng ORM SQLAlchemy parameterized query nên phải trả về 200 an toàn, không bị lỗi 500."""
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "1 UNION SELECT 1, 'admin', 'pass', 1, 1 --",
        "' OR 1=1 --"
    ]
    for p in sql_payloads:
        # 1. Products search
        res_p = client.get(f"/api/v1/products/?search={p}", headers=admin_headers)
        assert res_p.status_code == 200

        # 2. Categories search
        res_c = client.get(f"/api/v1/categories/?search={p}", headers=admin_headers)
        assert res_c.status_code == 200

        # 3. Suppliers search
        res_s = client.get(f"/api/v1/suppliers/?search={p}", headers=admin_headers)
        assert res_s.status_code == 200


# ==============================================================================
# 5. INTEGRATED BUSINESS FLOW & GUARD-CHECK VALIDATION
# ==============================================================================

def test_integrated_full_warehouse_cycle_and_guard_check(client, admin_headers, thukho_headers):
    """Kiểm thử chu trình kinh doanh hoàn chỉnh:
    1. Tạo nhóm hàng & nhà cung cấp
    2. Tạo sản phẩm mới (tồn ban đầu = 0)
    3. Nhập kho 50 cái -> tồn = 50, thẻ kho ghi nhận
    4. Thử xuất kho 60 cái -> Bị chặn 400 (Chống tồn âm)
    5. Xuất kho 50 cái -> tồn = 0, thẻ kho ghi nhận
    6. Thử hủy phiếu nhập ban đầu -> Bị chặn 400 (Guard-check vì đã xuất hết hàng)
    """
    ts = datetime.now(timezone.utc).strftime("%H%M%S%f")

    # 1. Tạo Category
    cat_res = client.post("/api/v1/categories/", json={
        "code": f"CAT_E2E_{ts}",
        "name": f"Nhóm E2E {ts}"
    }, headers=admin_headers)
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    # 2. Tạo Supplier
    sup_res = client.post("/api/v1/suppliers/", json={
        "code": f"SUP_E2E_{ts}",
        "name": f"NCC E2E {ts}",
        "phone": "0988776655"
    }, headers=admin_headers)
    assert sup_res.status_code == 201
    sup_id = sup_res.json()["id"]

    # 3. Tạo Product với tồn ban đầu 0
    prod_res = client.post("/api/v1/products/", json={
        "code": f"SKU_E2E_{ts}",
        "name": f"Mặt hàng E2E {ts}",
        "unit": "Bộ",
        "category_id": cat_id,
        "standard_price": 250000,
        "min_stock": 10
    }, headers=admin_headers)
    assert prod_res.status_code == 201
    prod = prod_res.json()
    prod_id = prod["id"]
    assert prod["current_stock"] == 0

    # 4. Nhập kho 50 cái
    import_res = client.post("/api/v1/import-notes/", json={
        "supplier_id": sup_id,
        "note": "Nhập đợt 1 E2E",
        "details": [{"product_id": prod_id, "quantity": 50, "unit_price": 200000}]
    }, headers=thukho_headers)
    assert import_res.status_code == 201
    import_note = import_res.json()
    import_note_id = import_note["id"]

    # Kiểm tra tồn sau nhập
    prod_after_imp = client.get(f"/api/v1/products/{prod_id}", headers=admin_headers).json()
    assert prod_after_imp["current_stock"] == 50

    # 5. Thử xuất 60 cái (vượt quá 50) -> Bị chặn 400
    export_fail = client.post("/api/v1/export-notes/", json={
        "recipient_name": "Khách hàng mua lố",
        "details": [{"product_id": prod_id, "quantity": 60}]
    }, headers=thukho_headers)
    assert export_fail.status_code == 400
    assert "tồn kho không đủ" in export_fail.json()["detail"].lower()

    # Tồn vẫn nguyên 50
    prod_verify = client.get(f"/api/v1/products/{prod_id}", headers=admin_headers).json()
    assert prod_verify["current_stock"] == 50

    # 6. Xuất đúng 50 cái -> Thành công
    export_ok = client.post("/api/v1/export-notes/", json={
        "recipient_name": "Khách hàng hợp lệ",
        "details": [{"product_id": prod_id, "quantity": 50}]
    }, headers=thukho_headers)
    assert export_ok.status_code == 201

    # Tồn về 0
    prod_empty = client.get(f"/api/v1/products/{prod_id}", headers=admin_headers).json()
    assert prod_empty["current_stock"] == 0

    # 7. Thử hủy phiếu nhập (cố gắng trừ ngược lại 50 cái khi tồn đang là 0)
    # Guard-check phải chặn đứng và trả 400 để bảo vệ ACID
    cancel_imp = client.post(f"/api/v1/import-notes/{import_note_id}/cancel", headers=thukho_headers)
    assert cancel_imp.status_code == 400
    assert "không thể hoàn trả" in cancel_imp.json()["detail"].lower()
