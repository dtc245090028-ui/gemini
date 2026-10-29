"""HTTP Caching & Compression Middlewares for SmartKho (Step E2: Read Optimization).

Features:
1. ETag / If-None-Match Middleware (HTTP 304 Not Modified):
   - Computes SHA1 hash of response body for GET requests.
   - Compares with client's `If-None-Match` header.
   - Returns 304 Not Modified when content is unchanged (empty body, saves bandwidth & parsing).
   - Skips SSE stream (/api/v1/events/stream) and binary file downloads (/export-excel).

2. Selective GZip Compression Middleware:
   - Compresses HTTP responses >= 1000 bytes.
   - Strictly excludes SSE stream (/api/v1/events/stream) to prevent buffering/broken streams.
"""

import hashlib
from typing import List
from starlette.types import ASGIApp, Scope, Receive, Send, Message
from starlette.middleware.gzip import GZipMiddleware


class ETagMiddleware:
    """ETag / If-None-Match Middleware for GET endpoints."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "GET":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Skip SSE streaming and large file exports
        if path.startswith("/api/v1/events/stream") or "/export-excel" in path:
            await self.app(scope, receive, send)
            return

        # Extract client If-None-Match header
        headers = dict(scope.get("headers", []))
        raw_if_none_match = headers.get(b"if-none-match", b"").decode("latin-1").strip()
        client_etag = raw_if_none_match.strip('"').lstrip("W/").strip('"') if raw_if_none_match else ""

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

        # Only generate ETag for 200 OK responses
        if status_code == 200 and full_body:
            etag_hash = hashlib.sha1(full_body).hexdigest()
            etag_header_value = f'"{etag_hash}"'

            if client_etag and client_etag == etag_hash:
                # 304 Not Modified
                resp_headers = [
                    (k, v) for k, v in response_start.get("headers", [])
                    if k.lower() not in (b"content-length", b"content-type")
                ]
                resp_headers.append((b"etag", etag_header_value.encode("latin-1")))
                resp_headers.append((b"cache-control", b"no-cache"))
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

            # Normal 200 OK: append ETag header and update Content-Length if present
            resp_headers = [
                (k, v) for k, v in response_start.get("headers", [])
                if k.lower() != b"etag"
            ]
            resp_headers.append((b"etag", etag_header_value.encode("latin-1")))
            resp_headers.append((b"cache-control", b"no-cache"))
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
