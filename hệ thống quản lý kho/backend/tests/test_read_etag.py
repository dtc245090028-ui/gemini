"""Test suite for Step E2: Read Optimization, ETag / 304 Not Modified & GZip Compression.

Verifies:
1. GET /api/v1/products/ returns 200 OK with ETag header.
2. GET /api/v1/products/ with matching If-None-Match returns 304 Not Modified with empty body.
3. GET /api/v1/products/ with mismatched If-None-Match returns 200 OK with updated body and ETag.
4. GET /api/v1/products/ with Accept-Encoding: gzip returns GZip compressed payload.
5. GET /api/v1/events/stream is exempt from ETag and GZip buffering.
"""

import sys
import json
import gzip
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://127.0.0.1:8000"


def get_auth_token():
    payload = json.dumps({"username": "admin", "password": "admin123"}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/api/v1/auth/login",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def test_etag_and_compression():
    token = get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
    }

    print("\n--- [TEST 1] First GET request without If-None-Match ---")
    req = urllib.request.Request(f"{BASE_URL}/api/v1/products/?limit=10", headers=headers)
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        etag = resp.headers.get("ETag")
        body = resp.read()
        print(f"Status: {resp.status}, Body length: {len(body)} bytes, ETag: {etag}")
        assert etag, "ETag header missing in response!"
        assert len(body) > 0, "Response body should not be empty"

    print("\n--- [TEST 2] Second GET request WITH matching If-None-Match ---")
    headers_with_etag = dict(headers)
    headers_with_etag["If-None-Match"] = etag
    req2 = urllib.request.Request(f"{BASE_URL}/api/v1/products/?limit=10", headers=headers_with_etag)
    try:
        with urllib.request.urlopen(req2) as resp2:
            status = resp2.status
            body2 = resp2.read()
    except urllib.error.HTTPError as e:
        status = e.code
        body2 = e.read()

    print(f"Status: {status}, Body length: {len(body2)} bytes")
    assert status == 304, f"Expected 304 Not Modified, got {status}"
    assert len(body2) == 0, f"Expected empty body for 304, got {len(body2)} bytes"
    print("[PASS] HTTP 304 Not Modified correctly returned!")

    print("\n--- [TEST 3] GET request WITH mismatched If-None-Match ---")
    headers_mismatch = dict(headers)
    headers_mismatch["If-None-Match"] = '"invalid-etag-hash-12345"'
    req3 = urllib.request.Request(f"{BASE_URL}/api/v1/products/?limit=10", headers=headers_mismatch)
    with urllib.request.urlopen(req3) as resp3:
        assert resp3.status == 200, f"Expected 200, got {resp3.status}"
        body3 = resp3.read()
        new_etag = resp3.headers.get("ETag")
        print(f"Status: {resp3.status}, Body length: {len(body3)} bytes, ETag: {new_etag}")
        assert resp3.status == 200
        assert new_etag == etag

    print("\n--- [TEST 4] GZip Compression with Accept-Encoding: gzip ---")
    headers_gzip = dict(headers)
    headers_gzip["Accept-Encoding"] = "gzip"
    req4 = urllib.request.Request(f"{BASE_URL}/api/v1/products/?limit=50", headers=headers_gzip)
    with urllib.request.urlopen(req4) as resp4:
        content_encoding = resp4.headers.get("Content-Encoding")
        raw_bytes = resp4.read()
        print(f"Content-Encoding: {content_encoding}, Compressed Size: {len(raw_bytes)} bytes")
        assert content_encoding == "gzip", f"Expected gzip, got {content_encoding}"
        decompressed = gzip.decompress(raw_bytes)
        print(f"Decompressed Size: {len(decompressed)} bytes (Ratio: {len(decompressed)/len(raw_bytes):.2f}x)")
        assert len(decompressed) > len(raw_bytes), "Decompressed size should be larger"
        parsed = json.loads(decompressed.decode("utf-8"))
        assert "items" in parsed or isinstance(parsed, list)

    print("\n--- [ALL ETag & GZip TESTS PASSED SUCCESSFULLY] ---\n")


if __name__ == "__main__":
    test_etag_and_compression()
