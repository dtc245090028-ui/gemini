"""HTTP Caching & Compression Middlewares for SmartKho (Step E2: Read Optimization).

Features:
1. Version-Per-Resource Fast ETag (Zero-Query 304 Not Modified):
   - Duy trì biến đếm phiên bản theo từng tài nguyên (products, categories, suppliers, ...).
   - Tăng version tự động trong hook publish_after_commit.
   - Nếu client gửi If-None-Match khớp với version hiện tại của danh mục, trả về ngay HTTP 304
     mà KHÔNG CẦN CHẠY QUERY HAY SERIALIZATION TRÊN DATABASE.

2. Content-Hash Fallback ETag (SHA1):
   - Với các request có query parameters hoặc tìm kiếm phức tạp, tính toán mã băm SHA1 trên body.
   - Trả về 304 Not Modified nếu If-None-Match trùng khớp.

3. Bảo mật bộ đệm & Chống rò rỉ dữ liệu người dùng:
   - Luôn trả về `Cache-Control: private, no-cache` để cấm các proxy/CDN dùng chung lưu đệm dữ liệu riêng tư.
   - Luôn bổ sung `Vary: Accept-Encoding, Authorization` để tách biệt bộ đệm giữa các tài khoản đăng nhập khác nhau.

4. Selective GZip Compression Middleware:
   - Nén HTTP response >= 1000 bytes.
   - Loại trừ nghiêm ngặt luồng SSE (/api/v1/events/stream) và file nhị phân (/export-excel).
"""

import hashlib
from typing import List, Dict, Optional
from starlette.types import ASGIApp, Scope, Receive, Send, Message
from starlette.middleware.gzip import GZipMiddleware

# Biến đếm phiên bản tài nguyên (được tăng tự động sau mỗi commit thành công)
RESOURCE_VERSIONS: Dict[str, int] = {
    "products": 1,
    "categories": 1,
    "suppliers": 1,
    "import_notes": 1,
    "export_notes": 1,
    "stock_ledger": 1,
    "reports": 1,
}

def increment_resource_version(resource: str):
    """Tăng phiên bản của tài nguyên (và các tài nguyên liên quan) khi có mutation commit."""
    if resource in RESOURCE_VERSIONS:
        RESOURCE_VERSIONS[resource] += 1
    # Biến động kho cũng làm thay đổi danh sách products và báo cáo
    if resource in ("import_notes", "export_notes", "stock_ledger"):
        RESOURCE_VERSIONS["products"] = RESOURCE_VERSIONS.get("products", 1) + 1
        RESOURCE_VERSIONS["reports"] = RESOURCE_VERSIONS.get("reports", 1) + 1


def get_resource_from_path(path: str) -> Optional[str]:
    parts = path.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        return parts[2]
    return None


class ETagMiddleware:
    """ETag / If-None-Match Middleware với Version-Per-Resource Fast Path & Content Hash Fallback."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "GET":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Bỏ qua SSE stream và xuất file
        if path.startswith("/api/v1/events/stream") or "/export-excel" in path:
            await self.app(scope, receive, send)
            return

        # Trích xuất header If-None-Match từ client
        headers = dict(scope.get("headers", []))
        raw_if_none_match = headers.get(b"if-none-match", b"").decode("latin-1").strip()
        client_etag = raw_if_none_match.strip('"').lstrip("W/").strip('"') if raw_if_none_match else ""

        resource = get_resource_from_path(path)
        query_string = scope.get("query_string", b"").decode("latin-1").strip()

        # FAST PATH: Nếu là request danh sách đơn giản không filter (hoặc limit cơ bản)
        # và client gửi ETag dạng version "resource-vX" trùng khớp với RESOURCE_VERSIONS:
        if resource and resource in RESOURCE_VERSIONS and not query_string:
            current_ver = RESOURCE_VERSIONS[resource]
            fast_etag_str = f"{resource}-v{current_ver}"
            if client_etag == fast_etag_str:
                # Trả về 304 ngay lập tức mà KHÔNG CẦN CHẠY ROUTE HAY QUERY DB!
                resp_headers = [
                    (b"etag", f'W/"{fast_etag_str}"'.encode("latin-1")),
                    (b"cache-control", b"private, no-cache"),
                    (b"vary", b"Accept-Encoding, Authorization"),
                ]
                await send({
                    "type": "http.response.start",
                    "status": 304,
                    "headers": resp_headers,
                })
                await send({
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                })
                return

        # FALLBACK PATH: Thực thi ứng dụng và tính hash trên body
        response_start: dict = {}
        body_chunks: List[bytes] = []

        async def capture_send(message: Message) -> None:
            nonlocal response_start
            if message["type"] == "http.response.start":
                response_start = message
            elif message["type"] == "http.response.body":
                body_chunks.append(message.get("body", b""))

        await self.app(scope, receive, capture_send)

        if not response_start:
            return

        full_body = b"".join(body_chunks)
        status_code = response_start.get("status", 200)

        # Chỉ áp dụng ETag cho response 200 OK
        if status_code == 200 and full_body:
            # Nếu là endpoint danh mục không query, dùng version ETag
            if resource and resource in RESOURCE_VERSIONS and not query_string:
                etag_header_value = f'W/"{resource}-v{RESOURCE_VERSIONS[resource]}"'
                etag_compare = f"{resource}-v{RESOURCE_VERSIONS[resource]}"
            else:
                etag_hash = hashlib.sha1(full_body).hexdigest()
                etag_header_value = f'"{etag_hash}"'
                etag_compare = etag_hash

            if client_etag and client_etag == etag_compare:
                # 304 Not Modified
                resp_headers = [
                    (k, v) for k, v in response_start.get("headers", [])
                    if k.lower() not in (b"content-length", b"content-type", b"cache-control", b"vary", b"etag")
                ]
                resp_headers.append((b"etag", etag_header_value.encode("latin-1")))
                resp_headers.append((b"cache-control", b"private, no-cache"))
                resp_headers.append((b"vary", b"Accept-Encoding, Authorization"))
                await send({
                    "type": "http.response.start",
                    "status": 304,
                    "headers": resp_headers,
                })
                await send({
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                })
                return

            # Normal 200 OK: gắn header ETag, Cache-Control, Vary
            resp_headers = [
                (k, v) for k, v in response_start.get("headers", [])
                if k.lower() not in (b"etag", b"cache-control", b"vary")
            ]
            resp_headers.append((b"etag", etag_header_value.encode("latin-1")))
            resp_headers.append((b"cache-control", b"private, no-cache"))
            resp_headers.append((b"vary", b"Accept-Encoding, Authorization"))
            response_start["headers"] = resp_headers

        await send(response_start)
        await send({
            "type": "http.response.body",
            "body": full_body,
            "more_body": False,
        })


class SelectiveGZipMiddleware(GZipMiddleware):
    """GZipMiddleware excluding SSE streaming and Excel downloads."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            if path.startswith("/api/v1/events/stream") or "/export-excel" in path:
                await self.app(scope, receive, send)
                return
        await super().__call__(scope, receive, send)
