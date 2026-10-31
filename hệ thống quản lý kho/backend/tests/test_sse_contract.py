"""Contract Test: Đảm bảo tính nhất quán 100% giữa tài nguyên sự kiện Backend phát và Frontend lắng nghe."""

import os
import re
import glob
import pytest
from app.core.events import EventResource

# Danh sách ngoại lệ tài nguyên backend phát mà không trang nào cần nghe (nếu có) kèm lý do
# Hiện tại: 100% tài nguyên backend phát đều có ít nhất 1 trang lắng nghe.
EXCEPTIONS_BACKEND_RESOURCES = {
    # Ví dụ: "auth": "Chỉ dùng cho đăng nhập/đăng xuất toàn hệ thống"
}


def find_frontend_dir():
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
        os.path.abspath("hệ thống quản lý kho/frontend"),
        os.path.abspath("frontend"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def get_backend_published_resources():
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app"))
    py_files = glob.glob(os.path.join(backend_root, "**", "*.py"), recursive=True)
    published = set()
    pattern = re.compile(r'publish_after_commit\(\s*resource=[\'"]([a-zA-Z0-9_]+)[\'"]')
    for f in py_files:
        with open(f, "r", encoding="utf-8") as fp:
            content = fp.read()
        for match in pattern.finditer(content):
            published.add(match.group(1))
    return published


def get_frontend_listened_resources():
    frontend_dir = find_frontend_dir()
    if not frontend_dir:
        return {}
    pages_dir = os.path.join(frontend_dir, "src", "pages")
    page_files = glob.glob(os.path.join(pages_dir, "*.jsx"))
    page_resources = {}
    pattern = re.compile(r'resource:\s*(\[[^\]]+\]|[\'"][a-zA-Z0-9_]+[\'"])')
    for pf in page_files:
        page_name = os.path.basename(pf)
        with open(pf, "r", encoding="utf-8") as fp:
            content = fp.read()
        match = pattern.search(content)
        if match:
            raw = match.group(1).strip()
            if raw.startswith("["):
                # Mảng: ['a', 'b']
                items = [it.strip(" '\"\n\r\t") for it in raw[1:-1].split(",") if it.strip(" '\"\n\r\t")]
                page_resources[page_name] = set(items)
            else:
                page_resources[page_name] = {raw.strip(" '\"")}
    return page_resources


def test_contract_all_backend_published_resources_in_event_resource():
    """Tất cả resource được backend phát phải nằm trong EventResource chuẩn."""
    published = get_backend_published_resources()
    declared = EventResource.all_resources()
    undeclared = published - declared
    assert not undeclared, f"Backend đang phát các resource chưa được định nghĩa trong EventResource: {undeclared}"


def test_contract_frontend_resources_match_backend():
    """Hợp đồng 2 chiều giữa Frontend và Backend:
    (a) Trang khai báo resource mà backend không bao giờ phát -> FAIL.
    (b) Backend phát resource mà không trang nào nghe (không nằm trong ngoại lệ) -> FAIL.
    """
    frontend_dir = find_frontend_dir()
    if not frontend_dir:
        pytest.skip("Thư mục frontend không tồn tại trong môi trường này (chạy trong isolated container).")

    page_resources = get_frontend_listened_resources()
    assert page_resources, "Không tìm thấy khai báo usePageSync nào ở frontend!"

    backend_all = EventResource.all_resources()
    all_frontend_listened = set()

    # (a) Kiểm tra mọi trang chỉ nghe resource hợp lệ mà backend có định nghĩa
    for page, resources in page_resources.items():
        invalid = resources - backend_all
        assert not invalid, f"Trang {page} đang nghe resource không tồn tại ở backend: {invalid}"
        all_frontend_listened.update(resources)

    # (b) Kiểm tra mọi resource backend phát phải có ít nhất 1 trang nghe
    published_backend = get_backend_published_resources()
    unheard = (published_backend - all_frontend_listened) - set(EXCEPTIONS_BACKEND_RESOURCES.keys())
    assert not unheard, f"Backend phát resource nhưng không trang nào nghe: {unheard}. Nếu cố ý, hãy thêm vào EXCEPTIONS_BACKEND_RESOURCES với giải thích."
