"""Bộ kiểm thử cho Module Hàng hóa, Nhóm hàng & Nhà cung cấp (Bước 06 - Master Data)."""

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_default_users
from app.main import app
from app.models import Category, Product, Supplier, User


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Khởi tạo cấu trúc bảng CSDL và nạp dữ liệu ban đầu cho phiên kiểm thử."""
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
    """Header Authorization với JWT Token của tài khoản ADMIN."""
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def thukho_headers(client):
    """Header Authorization với JWT Token của tài khoản WAREHOUSE_KEEPER."""
    login_res = client.post("/api/v1/auth/login", json={"username": "thukho", "password": "thukho123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def ketoan_headers(client):
    """Header Authorization với JWT Token của tài khoản ACCOUNTANT."""
    login_res = client.post("/api/v1/auth/login", json={"username": "ketoan", "password": "ketoan123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==================== TESTS FOR CATEGORIES ====================

def test_crud_category_lifecycle(client, admin_headers, thukho_headers):
    """Kiểm thử vòng đời CRUD của Nhóm hàng hóa."""
    # 1. Thêm mới nhóm hàng
    cat_data = {
        "code": "DIEN-TU-TEST",
        "name": "Thiết bị điện tử",
        "description": "Các mặt hàng linh kiện điện tử",
    }
    create_res = client.post("/api/v1/categories/", json=cat_data, headers=thukho_headers)
    assert create_res.status_code == 201
    created_cat = create_res.json()
    cat_id = created_cat["id"]
    assert created_cat["code"] == "DIEN-TU-TEST"

    # 2. Thử tạo trùng mã code -> Phải trả về HTTP 400
    dup_res = client.post("/api/v1/categories/", json=cat_data, headers=thukho_headers)
    assert dup_res.status_code == 400
    assert "đã tồn tại" in dup_res.json()["detail"]

    # 3. Xem danh sách và tìm kiếm
    list_res = client.get("/api/v1/categories/?search=điện tử", headers=thukho_headers)
    assert list_res.status_code == 200
    assert any(c["id"] == cat_id for c in list_res.json())

    # 4. Cập nhật nhóm hàng
    update_res = client.put(
        f"/api/v1/categories/{cat_id}",
        json={"name": "Thiết bị điện tử cao cấp"},
        headers=thukho_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Thiết bị điện tử cao cấp"

    # 5. Xóa nhóm hàng khi chưa có sản phẩm liên kết (Admin)
    del_res = client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_category_delete_blocked_when_has_products(client, admin_headers):
    """Kiểm tra không thể xóa nhóm hàng khi đang có sản phẩm liên kết."""
    # Tạo category
    cat_res = client.post(
        "/api/v1/categories/",
        json={"code": "CAT-WITH-PROD", "name": "Nhóm có hàng"},
        headers=admin_headers,
    )
    cat_id = cat_res.json()["id"]

    # Tạo sản phẩm thuộc category này
    prod_res = client.post(
        "/api/v1/products/",
        json={
            "code": "SP-LINKED-01",
            "name": "Sản phẩm liên kết",
            "category_id": cat_id,
            "unit": "Hộp",
            "min_stock": 5,
            "current_stock": 10,
            "standard_price": 50000.0,
        },
        headers=admin_headers,
    )
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]

    # Thử xóa category -> Bị chặn 400
    del_res = client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)
    assert del_res.status_code == 400
    assert "không thể xóa" in del_res.json()["detail"].lower()

    # Dọn dẹp
    client.delete(f"/api/v1/products/{prod_id}", headers=admin_headers)
    client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)


# ==================== TESTS FOR PRODUCTS ====================

def test_crud_product_lifecycle_and_filters(client, admin_headers, thukho_headers, ketoan_headers):
    """Kiểm thử vòng đời Hàng hóa, kiểm tra trùng SKU, bộ lọc cảnh báo tồn và phân quyền."""
    # Chuẩn bị 1 nhóm hàng
    cat_res = client.post(
        "/api/v1/categories/",
        json={"code": "CAT-PROD-TEST", "name": "Nhóm thử nghiệm sản phẩm"},
        headers=admin_headers,
    )
    cat_id = cat_res.json()["id"]

    # 1. Thêm mới sản phẩm A (Tồn = 2, Min = 10 -> is_low_stock = True)
    prod_a_data = {
        "code": "SKU-A-LOW",
        "name": "Chuột Gaming Logitech",
        "category_id": cat_id,
        "unit": "Cái",
        "min_stock": 10,
        "current_stock": 2,
        "standard_price": 450000.0,
    }
    res_a = client.post("/api/v1/products/", json=prod_a_data, headers=thukho_headers)
    assert res_a.status_code == 201
    prod_a = res_a.json()
    assert prod_a["is_low_stock"] is True
    assert prod_a["category_name"] == "Nhóm thử nghiệm sản phẩm"

    # 2. Thêm mới sản phẩm B (Tồn = 50, Min = 10 -> is_low_stock = False)
    prod_b_data = {
        "code": "SKU-B-HIGH",
        "name": "Bàn phím cơ DareU",
        "category_id": cat_id,
        "unit": "Chiếc",
        "min_stock": 10,
        "current_stock": 50,
        "standard_price": 850000.0,
    }
    res_b = client.post("/api/v1/products/", json=prod_b_data, headers=thukho_headers)
    assert res_b.status_code == 201
    prod_b = res_b.json()
    assert prod_b["is_low_stock"] is False

    # 3. Kiểm tra chặn trùng SKU -> 400 Bad Request
    dup_res = client.post("/api/v1/products/", json=prod_a_data, headers=thukho_headers)
    assert dup_res.status_code == 400
    assert "đã tồn tại" in dup_res.json()["detail"]

    # 4. Kiểm tra nhóm hàng không tồn tại -> 400 Bad Request
    invalid_cat_data = prod_a_data.copy()
    invalid_cat_data["code"] = "SKU-INVALID-CAT"
    invalid_cat_data["category_id"] = 99999
    cat_err_res = client.post("/api/v1/products/", json=invalid_cat_data, headers=thukho_headers)
    assert cat_err_res.status_code == 400

    # 5. Kiểm tra Pydantic chặn giá âm / số tồn âm -> 422
    neg_data = prod_a_data.copy()
    neg_data["code"] = "SKU-NEG"
    neg_data["standard_price"] = -500.0
    neg_res = client.post("/api/v1/products/", json=neg_data, headers=thukho_headers)
    assert neg_res.status_code == 422

    # 6. Kiểm tra bộ lọc is_low_stock=true
    low_res = client.get(f"/api/v1/products/?category_id={cat_id}&is_low_stock=true", headers=ketoan_headers)
    assert low_res.status_code == 200
    low_items = low_res.json()
    assert any(p["code"] == "SKU-A-LOW" for p in low_items)
    assert not any(p["code"] == "SKU-B-HIGH" for p in low_items)

    # 7. Kiểm tra phân quyền RBAC: Kế toán chỉ được xem, không được thêm sản phẩm -> 403
    ketoan_add_res = client.post(
        "/api/v1/products/",
        json={"code": "SKU-KETOAN-FAIL", "name": "Lỗi quyền", "category_id": cat_id},
        headers=ketoan_headers,
    )
    assert ketoan_add_res.status_code == 403

    # 8. Thủ kho không được phép xóa sản phẩm -> 403 Forbidden
    thukho_del_res = client.delete(f"/api/v1/products/{prod_a['id']}", headers=thukho_headers)
    assert thukho_del_res.status_code == 403

    # 9. Admin xóa sản phẩm -> 200 OK
    admin_del_res = client.delete(f"/api/v1/products/{prod_a['id']}", headers=admin_headers)
    assert admin_del_res.status_code == 200
    client.delete(f"/api/v1/products/{prod_b['id']}", headers=admin_headers)
    client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)


# ==================== TESTS FOR SUPPLIERS ====================

def test_crud_supplier_lifecycle(client, admin_headers, thukho_headers):
    """Kiểm thử vòng đời CRUD của Nhà cung cấp."""
    # 1. Thêm mới NCC
    sup_data = {
        "code": "NCC-SAMSUNG-TEST",
        "name": "Samsung Vina Electronics",
        "phone": "02838221234",
        "email": "contact@samsung.vn",
        "address": "Khu công nghệ cao TP.HCM",
    }
    res = client.post("/api/v1/suppliers/", json=sup_data, headers=thukho_headers)
    assert res.status_code == 201
    sup = res.json()
    sup_id = sup["id"]
    assert sup["code"] == "NCC-SAMSUNG-TEST"

    # 2. Kiểm tra trùng mã NCC -> 400
    dup_res = client.post("/api/v1/suppliers/", json=sup_data, headers=thukho_headers)
    assert dup_res.status_code == 400

    # 3. Cập nhật thông tin NCC
    up_res = client.put(
        f"/api/v1/suppliers/{sup_id}",
        json={"phone": "0988776655", "address": "Quận 9, TP. Thủ Đức"},
        headers=thukho_headers,
    )
    assert up_res.status_code == 200
    assert up_res.json()["phone"] == "0988776655"

    # 4. Tìm kiếm nhà cung cấp
    search_res = client.get("/api/v1/suppliers/?search=Samsung", headers=thukho_headers)
    assert search_res.status_code == 200
    assert any(s["id"] == sup_id for s in search_res.json())

    # 5. Xóa nhà cung cấp (Admin)
    del_res = client.delete(f"/api/v1/suppliers/{sup_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_product_creation_with_initial_import_note(client, admin_headers):
    """Kiểm tra tính năng tự động tạo phiếu nhập kho và ghi thẻ kho khi thêm mới sản phẩm."""
    import uuid

    suffix = uuid.uuid4().hex[:6].upper()
    cat_code = f"CAT-INIT-{suffix}"
    sup_code = f"SUP-INIT-{suffix}"
    prod_code = f"SP-INIT-{suffix}"

    # 1. Tạo Category và Supplier phục vụ kiểm thử
    cat_res = client.post(
        "/api/v1/categories/",
        json={"code": cat_code, "name": "Nhóm thử nghiệm phiếu nhập đầu kỳ"},
        headers=admin_headers,
    )
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    sup_res = client.post(
        "/api/v1/suppliers/",
        json={"code": sup_code, "name": "NCC Thử nghiệm đầu kỳ"},
        headers=admin_headers,
    )
    assert sup_res.status_code == 201
    sup_id = sup_res.json()["id"]

    prod_id = None
    try:
        # 2. Thử tạo sản phẩm với NCC không tồn tại -> Báo lỗi 400
        bad_res = client.post(
            "/api/v1/products/",
            json={
                "code": f"SP-FAIL-{suffix}",
                "name": "Sản phẩm lỗi NCC",
                "category_id": cat_id,
                "unit": "Hộp",
                "standard_price": 50000.0,
                "initial_supplier_id": 999999,
                "initial_quantity": 10,
            },
            headers=admin_headers,
        )
        assert bad_res.status_code == 400
        assert "không tồn tại" in bad_res.json()["detail"]

        # 3. Tạo sản phẩm hợp lệ kèm tự động tạo phiếu nhập ban đầu
        create_res = client.post(
            "/api/v1/products/",
            json={
                "code": prod_code,
                "name": "Sản phẩm khởi tạo tồn kho",
                "category_id": cat_id,
                "unit": "Chiếc",
                "min_stock": 5,
                "standard_price": 100000.0,
                "initial_supplier_id": sup_id,
                "initial_quantity": 20,
                "initial_unit_price": 70000.0,
                "initial_note": "Nhập kho ban đầu khi thiết lập danh mục",
            },
            headers=admin_headers,
        )
        assert create_res.status_code == 201
        created_prod = create_res.json()
        prod_id = created_prod["id"]

        # Kiểm tra tồn kho đã được tăng lên 20 và có mã phiếu nhập trả về
        assert created_prod["current_stock"] == 20
        assert created_prod["initial_import_note_code"] is not None
        note_code = created_prod["initial_import_note_code"]
        assert note_code.startswith("PN-")

        # 4. Kiểm tra phiếu nhập kho trong CSDL
        note_res = client.get("/api/v1/import-notes/", headers=admin_headers)
        assert note_res.status_code == 200
        matched_notes = [n for n in note_res.json() if n["code"] == note_code]
        assert len(matched_notes) == 1
        note_data = matched_notes[0]
        assert note_data["supplier_id"] == sup_id
        assert note_data["status"] == "COMPLETED"
        assert note_data["total_amount"] == 20 * 70000.0

        # 5. Kiểm tra Thẻ kho (StockLedger) có ghi nhận giao dịch IMPORT
        ledger_res = client.get(f"/api/v1/stock-ledger/?product_id={prod_id}", headers=admin_headers)
        assert ledger_res.status_code == 200
        ledger_items = ledger_res.json()
        assert len(ledger_items) == 1
        assert ledger_items[0]["transaction_type"] == "IMPORT"
        assert ledger_items[0]["reference_code"] == note_code
        assert ledger_items[0]["quantity_change"] == 20
        assert ledger_items[0]["balance_after"] == 20
    finally:
        # Dọn dẹp an toàn
        if prod_id:
            client.delete(f"/api/v1/products/{prod_id}", headers=admin_headers)
        client.delete(f"/api/v1/suppliers/{sup_id}", headers=admin_headers)
        client.delete(f"/api/v1/categories/{cat_id}", headers=admin_headers)
