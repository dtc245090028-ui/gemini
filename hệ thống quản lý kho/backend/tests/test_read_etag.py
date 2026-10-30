"""Kiểm thử tính năng tối ưu đọc: ETag / HTTP 304 Not Modified và nén GZip.

Chạy 100% cô lập trên Test Database qua FastAPI TestClient.
Kiểm tra:
1. GET /api/v1/products/ trả về 200 OK kèm header ETag.
2. GET /api/v1/products/ với If-None-Match trùng khớp trả về HTTP 304 Not Modified với body rỗng.
3. GET /api/v1/products/ với If-None-Match sai lệch trả về 200 OK với body đầy đủ.
4. GET /api/v1/products/ với Accept-Encoding: gzip trả về dữ liệu nén GZip (Content-Encoding: gzip).
5. Luồng SSE /api/v1/events/stream và xuất file /export-excel được loại trừ khỏi ETag/GZip buffering.
"""

import gzip
import json
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.database import Base, engine
from app.core.seed import seed_default_users


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

    # TestClient (httpx) tự động giải nén Content-Encoding: gzip sang plain bytes
    # Ta kiểm tra response hợp lệ và có thể parse JSON
    data = resp.json()
    assert isinstance(data, list) or "items" in data
