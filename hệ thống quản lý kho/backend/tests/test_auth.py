"""Bộ kiểm thử cho Xác thực (Auth JWT), Phân quyền (RBAC) và SQLite Foreign Keys (Bước 05)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_default_users
from app.main import app
from app.models import Category, Product, User


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Khởi tạo cấu trúc bảng và nạp dữ liệu ban đầu cho phiên kiểm thử."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    """TestClient gọi API thông qua FastAPI app."""
    return TestClient(app)


def test_idempotent_seed():
    """Kiểm tra tính Idempotent của hàm seed: Gọi nhiều lần không sinh lỗi trùng lặp dữ liệu."""
    db = SessionLocal()
    try:
        # Gọi lại seed_default_users 2 lần liên tiếp
        seed_default_users(db)
        seed_default_users(db)

        # Đảm bảo 3 tài khoản mặc định tồn tại duy nhất
        admins = db.query(User).filter_by(username="admin").all()
        thukhos = db.query(User).filter_by(username="thukho").all()
        ketoans = db.query(User).filter_by(username="ketoan").all()

        assert len(admins) == 1, "Tài khoản admin phải là duy nhất"
        assert len(thukhos) == 1, "Tài khoản thukho phải là duy nhất"
        assert len(ketoans) == 1, "Tài khoản ketoan phải là duy nhất"
        assert admins[0].role == "ADMIN"
        assert thukhos[0].role == "WAREHOUSE_KEEPER"
        assert ketoans[0].role == "ACCOUNTANT"
    finally:
        db.close()


def test_login_json_success(client):
    """Kiểm tra đăng nhập thành công qua JSON body trả về JWT token và thông tin người dùng."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "ADMIN"


def test_login_json_wrong_password(client):
    """Kiểm tra đăng nhập sai mật khẩu trả về HTTP 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "sai_mat_khau"},
    )
    assert response.status_code == 401
    assert "detail" in response.json()


def test_login_json_nonexistent_user(client):
    """Kiểm tra đăng nhập với tài khoản không tồn tại trả về HTTP 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "khong_ton_tai", "password": "password123"},
    )
    assert response.status_code == 401


def test_login_oauth2_form_success(client):
    """Kiểm tra đăng nhập chuẩn OAuth2 Password Request Form (dùng cho Swagger UI Authorize)."""
    response = client.post(
        "/api/v1/auth/login-form",
        data={"username": "thukho", "password": "thukho123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_get_me_with_valid_token(client):
    """Kiểm tra endpoint /auth/me lấy thông tin tài khoản hiện tại bằng Bearer token."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "thukho", "password": "thukho123"},
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "thukho"
    assert user_data["role"] == "WAREHOUSE_KEEPER"


def test_get_me_without_token(client):
    """Kiểm tra gọi endpoint /auth/me không có token bị từ chối HTTP 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token(client):
    """Kiểm tra gọi endpoint /auth/me với token sai định dạng bị từ chối HTTP 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer token_khong_hop_le_123456"},
    )
    assert response.status_code == 401


def test_rbac_admin_create_user(client):
    """Kiểm tra phân quyền RBAC: Chỉ tài khoản ADMIN mới có quyền tạo người dùng mới."""
    # Đăng nhập bằng tài khoản ADMIN
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    admin_token = admin_login.json()["access_token"]

    new_user_data = {
        "username": "nhanvien_kho_moi",
        "password": "password123",
        "full_name": "Nhân viên mới",
        "role": "WAREHOUSE_KEEPER",
    }
    create_res = client.post(
        "/api/v1/auth/users",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["username"] == "nhanvien_kho_moi"

    # Dọn dẹp user vừa tạo
    db = SessionLocal()
    try:
        db.query(User).filter_by(username="nhanvien_kho_moi").delete()
        db.commit()
    finally:
        db.close()


def test_rbac_warehouse_keeper_forbidden_to_create_user(client):
    """Kiểm tra phân quyền RBAC: Tài khoản WAREHOUSE_KEEPER bị từ chối HTTP 403 khi gọi API tạo người dùng."""
    thukho_login = client.post(
        "/api/v1/auth/login",
        json={"username": "thukho", "password": "thukho123"},
    )
    thukho_token = thukho_login.json()["access_token"]

    create_res = client.post(
        "/api/v1/auth/users",
        json={
            "username": "user_khong_the_tao",
            "password": "password123",
            "full_name": "Tài khoản test",
            "role": "ACCOUNTANT",
        },
        headers={"Authorization": f"Bearer {thukho_token}"},
    )
    assert create_res.status_code == 403
    assert "từ chối" in create_res.json()["detail"].lower() or "quyền" in create_res.json()["detail"].lower()


def test_sqlite_foreign_key_enforcement():
    """Kiểm tra SQLite PRAGMA foreign_keys = ON đã hoạt động: Chặn chèn khóa ngoại không tồn tại."""
    db = SessionLocal()
    try:
        # Thử thêm sản phẩm với category_id không tồn tại (id = 999999)
        orphan_product = Product(
            code="SP-ORPHAN-FK-TEST",
            name="Sản phẩm sai khóa ngoại",
            category_id=999999,
            current_stock=10,
        )
        db.add(orphan_product)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()
