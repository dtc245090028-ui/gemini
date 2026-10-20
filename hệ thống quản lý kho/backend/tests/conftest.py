"""Cấu hình Pytest và cô lập CSDL kiểm thử (Isolated Test Database).

Đảm bảo mọi lệnh chạy kiểm thử pytest tuyệt đối không tác động hay ghi dữ liệu rác
vào cơ sở dữ liệu làm việc chính warehouse.db.
"""

import os
import sys

# Thiết lập DATABASE_URL trỏ sang test_warehouse.db TRƯỚC KHI bất kỳ module app nào được nạp
TEST_DB_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "test_warehouse.db")
)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"

import pytest
from app.api.deps import rate_limiter
from app.core.database import Base, engine


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Đặt lại bộ đếm Rate Limiter trước mỗi test case để các test không ảnh hưởng lẫn nhau."""
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture(scope="session", autouse=True)
def isolate_test_database():
    """Tự động dọn dẹp file test_warehouse.db (kèm -wal, -shm) sau khi hoàn tất phiên kiểm thử."""
    yield
    # Đóng kết nối engine và xóa file test database
    engine.dispose()
    for suffix in ("", "-wal", "-shm"):
        path = f"{TEST_DB_FILE}{suffix}"
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
