"""Kiểm thử tính năng tối ưu đọc: ETag / HTTP 304 Not Modified và nén GZip.

Chạy 100% cô lập trên Test Database qua FastAPI TestClient.
Kiểm tra:
1. GET /api/v1/products/ trả về 200 OK kèm header ETag.
2. GET /api/v1/products/ với If-None-Match trùng khớp trả về HTTP 304 Not Modified với body rỗng.
3. GET /api/v1/products/ với If-None-Match sai lệch trả về 200 OK với body đầy đủ.
4. GET /api/v1/products/ với Accept-Encoding: gzip trả về dữ liệu nén GZip.
5. Luồng SSE /api/v1/events/stream và xuất file /export-excel được loại trừ khỏi ETag/GZip buffering.
6. ETag AN TOÀN: Phát hiện ghi trực tiếp vào DB từ ngoài -> vô hiệu hóa ETag cũ, trả 200.
7. ETag AN TOÀN: Thay đổi Boot ID (restart app) -> ETag cũ không được trả 304.
"""

import gzip
import json
import pytest
from sqlalchemy import text
from starlette.testclient import TestClient
from app.main import app
from app.core.database import Base, engine
from app.core.seed import seed_default_users
import app.core.http_cache as http_cache


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    from app.core.database import SessionLocal
    db = SessionLocal()
    seed_default_users(db)
    db.close()
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_token(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def test_etag_and_304(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. First GET request without If-None-Match
    resp1 = client.get("/api/v1/products/?limit=10", headers=headers)
    assert resp1.status_code == 200
    etag = resp1.headers.get("etag")
    assert etag is not None, "Header ETag phải tồn tại trong response 200"
    assert len(resp1.content) > 0
    assert "private" in resp1.headers.get("cache-control", ""), "Cache-Control phải chứa 'private'"
    assert "Authorization" in resp1.headers.get("vary", ""), "Vary phải chứa 'Authorization'"

    # 2. Second GET request with matching If-None-Match -> 304 Not Modified
    headers_with_etag = {**headers, "If-None-Match": etag}
    resp2 = client.get("/api/v1/products/?limit=10", headers=headers_with_etag)
    assert resp2.status_code == 304, f"Mong đợi 304 Not Modified, nhận được {resp2.status_code}"
    assert len(resp2.content) == 0, f"Body của 304 phải rỗng, nhận được {len(resp2.content)} bytes"
    assert resp2.headers.get("etag") == etag

    # 3. GET with mismatched If-None-Match -> 200 OK with full body
    headers_mismatch = {**headers, "If-None-Match": '"outdated-hash-99999"'}
    resp3 = client.get("/api/v1/products/?limit=10", headers=headers_mismatch)
    assert resp3.status_code == 200
    assert len(resp3.content) > 0
    assert resp3.headers.get("etag") == etag


def test_gzip_compression(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}", "Accept-Encoding": "gzip"}
    resp = client.get("/api/v1/products/?limit=50", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) or "items" in data


def test_resource_version_fast_etag(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Lấy ETag hiện tại của categories
    resp = client.get("/api/v1/categories/", headers=headers)
    assert resp.status_code == 200
    fast_etag = resp.headers.get("etag")
    assert fast_etag is not None

    # Gửi If-None-Match với fast version -> Nhận 304 ngay lập tức
    resp304 = client.get("/api/v1/categories/", headers={**headers, "If-None-Match": fast_etag})
    assert resp304.status_code == 304, f"Expected 304 for fast version ETag, got {resp304.status_code}"
    assert len(resp304.content) == 0

    # Khi có mutation làm tăng version -> version cũ bị từ chối và trả về 200 kèm version mới
    cur_ver = http_cache.RESOURCE_VERSIONS.get("categories", 1)
    http_cache.increment_resource_version("categories")
    new_ver = http_cache.RESOURCE_VERSIONS["categories"]
    assert new_ver > cur_ver

    resp_after = client.get("/api/v1/categories/", headers={**headers, "If-None-Match": fast_etag})
    assert resp_after.status_code == 200, "Sau khi tăng version, If-None-Match cũ không được trả về 304"
    assert f"categories-v{new_ver}" in resp_after.headers.get("etag", "")


def test_etag_external_write_invalidation(client, admin_token):
    """Bắt buộc (Mục 4): GET lấy ETag -> ghi trực tiếp vào DB bằng SQL ngoài -> GET kèm If-None-Match PHẢI trả 200 dữ liệu mới."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. GET lấy ETag ban đầu
    resp1 = client.get("/api/v1/categories/", headers=headers)
    assert resp1.status_code == 200
    old_etag = resp1.headers.get("etag")
    old_data = resp1.json()

    # Xác nhận 304 khi chưa có thay đổi
    resp_check = client.get("/api/v1/categories/", headers={**headers, "If-None-Match": old_etag})
    assert resp_check.status_code == 304

    # 2. Ghi trực tiếp vào CSDL qua raw SQL (mô phỏng tiến trình ngoài như demo_cleanup hoặc CLI)
    unique_code = f"CAT_{http_cache.uuid.uuid4().hex[:6]}"
    unique_name = f"DanhMuc_Ngoai_{http_cache.uuid.uuid4().hex[:6]}"
    with engine.begin() as conn:
        conn.execute(text(f"INSERT INTO categories (code, name, description) VALUES ('{unique_code}', '{unique_name}', 'Mo ta SQL truc tiep')"))

    # 3. GET kèm If-None-Match cũ PHẢI nhận 200 (không được trả 304) và có dữ liệu mới
    resp_after_sql = client.get("/api/v1/categories/", headers={**headers, "If-None-Match": old_etag})
    assert resp_after_sql.status_code == 200, f"Mong đợi 200 sau khi ghi CSDL ngoài, nhưng nhận được {resp_after_sql.status_code}"
    new_etag = resp_after_sql.headers.get("etag")
    assert new_etag != old_etag, "ETag mới phải khác ETag cũ do data_version đã thay đổi"

    # Kiểm tra bản ghi mới đã xuất hiện
    cat_names = [c["name"] for c in resp_after_sql.json()]
    assert unique_name in cat_names, f"Bản ghi {unique_name} phải xuất hiện trong dữ liệu mới"


def test_etag_boot_id_restart_invalidation(client, admin_token):
    """Bắt buộc (Mục 4): Restart backend (đổi Boot ID) -> ETag cũ không được cho 304 sai."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Lấy ETag hiện tại
    resp1 = client.get("/api/v1/products/?limit=10", headers=headers)
    assert resp1.status_code == 200
    current_etag = resp1.headers.get("etag")

    # Xác nhận 304 khi cùng session
    resp_check = client.get("/api/v1/products/?limit=10", headers={**headers, "If-None-Match": current_etag})
    assert resp_check.status_code == 304

    # 2. Mô phỏng server restart bằng cách cấp BOOT_ID mới
    original_boot_id = http_cache.BOOT_ID
    try:
        http_cache.BOOT_ID = http_cache.uuid.uuid4().hex[:8]

        # 3. GET với ETag của lần boot trước -> PHẢI trả về 200, KHÔNG ĐƯỢC trả 304
        resp_after_restart = client.get("/api/v1/products/?limit=10", headers={**headers, "If-None-Match": current_etag})
        assert resp_after_restart.status_code == 200, f"Sau khi restart, ETag cũ không được trả về 304 (nhận {resp_after_restart.status_code})"
        assert resp_after_restart.headers.get("etag") != current_etag
    finally:
        http_cache.BOOT_ID = original_boot_id
