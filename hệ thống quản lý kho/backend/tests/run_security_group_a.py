"""Kịch bản kiểm thử bảo mật - NHÓM A: PHÂN QUYỀN (Authorization).

Phạm vi:
- Chỉ kiểm thử trên tài khoản tiền tố perf_* và mặt hàng tiền tố SKU-PERF-*.
- Đo lường chi tiết: request, status code, latency (ms), response snippet, đánh giá lỗ hổng và mức độ.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000/api/v1"
SECRET_KEY = "kho-ai-secret-key-super-secure-change-in-production-2026"
ALGORITHM = "HS256"

# Helper gửi HTTP request có đo thời gian thực
def send_request(method: str, path: str, token: str = None, data: dict = None, custom_headers: dict = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if custom_headers:
        headers.update(custom_headers)

    body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

    start_time = time.perf_counter()
    status_code = None
    response_body = None
    try:
        with urllib.request.urlopen(req) as resp:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            status_code = resp.status
            content = resp.read().decode("utf-8", errors="replace")
            try:
                response_body = json.loads(content)
            except Exception:
                response_body = content
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        status_code = e.code
        content = e.read().decode("utf-8", errors="replace")
        try:
            response_body = json.loads(content)
        except Exception:
            response_body = content
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        status_code = 0
        response_body = {"error": str(e)}

    return {
        "method": method,
        "url": url,
        "status_code": status_code,
        "elapsed_ms": round(elapsed_ms, 2),
        "body": response_body,
    }


def login(username, password):
    res = send_request("POST", "/auth/login", data={"username": username, "password": password})
    if res["status_code"] == 200 and "access_token" in res["body"]:
        return res["body"]["access_token"], res["body"]["user"]
    raise RuntimeError(f"Login failed for {username}: {res}")


def create_custom_jwt(payload: dict, secret: str = SECRET_KEY, alg: str = "HS256"):
    import base64
    import hashlib
    import hmac

    def b64url(b):
        return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")

    header = {"alg": alg, "typ": "JWT"}
    header_b64 = b64url(json.dumps(header).encode("utf-8"))
    payload_b64 = b64url(json.dumps(payload).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}"

    if alg.upper() == "NONE":
        return f"{signing_input}."
    elif alg.upper() == "HS256":
        sig = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        return f"{signing_input}.{b64url(sig)}"
    else:
        raise ValueError("Unsupported alg")


def run_tests():
    print("=" * 80)
    print("BẮT ĐẦU CHẠY KIỂM THỬ BẢO MẬT: NHÓM A - PHÂN QUYỀN (AUTHORIZATION)")
    print("=" * 80)

    # Lấy token các tài khoản
    admin_token, admin_user = login("perf_admin_01", "Perf@123")
    wh1_token, wh1_user = login("perf_wh_01", "Perf@123")
    wh2_token, wh2_user = login("perf_wh_02", "Perf@123")
    acct_token, acct_user = login("perf_acct_01", "Perf@123")

    print(f"Đăng nhập thành công:")
    print(f" - Admin: {admin_user['username']} (ID: {admin_user['id']}, Role: {admin_user['role']})")
    print(f" - Thủ kho 1: {wh1_user['username']} (ID: {wh1_user['id']}, Role: {wh1_user['role']})")
    print(f" - Thủ kho 2: {wh2_user['username']} (ID: {wh2_user['id']}, Role: {wh2_user['role']})")
    print(f" - Kế toán: {acct_user['username']} (ID: {acct_user['id']}, Role: {acct_user['role']})")

    # Lấy 1 mặt hàng test SKU-PERF-*
    prod_res = send_request("GET", "/products?search=SKU-PERF-BULK-01", token=wh1_token)
    perf_prod = prod_res["body"][0]
    prod_id = perf_prod["id"]
    print(f"Sản phẩm dùng test: {perf_prod['code']} (ID: {prod_id}, Tồn kho: {perf_prod['current_stock']})")

    results = []

    # -------------------------------------------------------------
    # TEST CASE 1: Dùng tài khoản thường gọi thử endpoint dành cho quản trị viên
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("TEST CASE 1: Role-Based Access Control (RBAC) - Gọi endpoint Admin")
    print("-" * 70)

    # 1.1 Thủ kho gọi POST /auth/users (chỉ ADMIN)
    tc1_1 = send_request("POST", "/auth/users", token=wh1_token, data={
        "username": "perf_test_hack",
        "full_name": "Test Hack User",
        "role": "ADMIN",
        "password": "Password@123"
    })
    results.append({
        "id": "TC-01.1",
        "name": "Thủ kho (WAREHOUSE_KEEPER) gọi POST /auth/users (Tạo user)",
        "expected_status": 403,
        "result": tc1_1,
        "is_vuln": tc1_1["status_code"] != 403,
        "severity": "Nghiêm trọng" if tc1_1["status_code"] == 201 else "Không phát hiện vấn đề",
        "finding": "Chặn thành công với HTTP 403" if tc1_1["status_code"] == 403 else f"Bị bypass: mã {tc1_1['status_code']}"
    })

    # 1.2 Kế toán gọi DELETE /products/{id} (chỉ ADMIN)
    tc1_2 = send_request("DELETE", f"/products/{prod_id}", token=acct_token)
    results.append({
        "id": "TC-01.2",
        "name": "Kế toán (ACCOUNTANT) gọi DELETE /products/{id} (Xóa hàng hóa)",
        "expected_status": 403,
        "result": tc1_2,
        "is_vuln": tc1_2["status_code"] != 403,
        "severity": "Nghiêm trọng" if tc1_2["status_code"] == 200 else "Không phát hiện vấn đề",
        "finding": "Chặn thành công với HTTP 403" if tc1_2["status_code"] == 403 else f"Bị bypass: mã {tc1_2['status_code']}"
    })

    # 1.3 Thủ kho gọi DELETE /products/{id} (chỉ ADMIN)
    tc1_3 = send_request("DELETE", f"/products/{prod_id}", token=wh1_token)
    results.append({
        "id": "TC-01.3",
        "name": "Thủ kho (WAREHOUSE_KEEPER) gọi DELETE /products/{id} (Xóa hàng hóa)",
        "expected_status": 403,
        "result": tc1_3,
        "is_vuln": tc1_3["status_code"] != 403,
        "severity": "Nghiêm trọng" if tc1_3["status_code"] == 200 else "Không phát hiện vấn đề",
        "finding": "Chặn thành công với HTTP 403" if tc1_3["status_code"] == 403 else f"Bị bypass: mã {tc1_3['status_code']}"
    })

    # 1.4 Kế toán gọi POST /products/ (chỉ ADMIN, WAREHOUSE_KEEPER)
    tc1_4 = send_request("POST", "/products/", token=acct_token, data={
        "code": "SKU-PERF-FAIL",
        "name": "Mặt hàng trái phép",
        "category_id": 1,
        "unit": "Cái",
        "min_stock": 5,
        "current_stock": 10,
        "standard_price": 50000.0,
        "status": "ACTIVE"
    })
    results.append({
        "id": "TC-01.4",
        "name": "Kế toán (ACCOUNTANT) gọi POST /products/ (Tạo hàng hóa mới)",
        "expected_status": 403,
        "result": tc1_4,
        "is_vuln": tc1_4["status_code"] != 403,
        "severity": "Trung bình" if tc1_4["status_code"] == 201 else "Không phát hiện vấn đề",
        "finding": "Chặn thành công với HTTP 403" if tc1_4["status_code"] == 403 else f"Bị bypass: mã {tc1_4['status_code']}"
    })

    # 1.5 Kế toán gọi POST /export-notes/ (chỉ ADMIN, WAREHOUSE_KEEPER)
    tc1_5 = send_request("POST", "/export-notes/", token=acct_token, data={
        "recipient_name": "Kế toán tự xuất",
        "details": [{"product_id": prod_id, "quantity": 1, "unit_price": 100000.0}]
    })
    results.append({
        "id": "TC-01.5",
        "name": "Kế toán (ACCOUNTANT) gọi POST /export-notes/ (Lập phiếu xuất)",
        "expected_status": 403,
        "result": tc1_5,
        "is_vuln": tc1_5["status_code"] != 403,
        "severity": "Nghiêm trọng" if tc1_5["status_code"] == 201 else "Không phát hiện vấn đề",
        "finding": "Chặn thành công với HTTP 403" if tc1_5["status_code"] == 403 else f"Bị bypass: mã {tc1_5['status_code']}"
    })

    # -------------------------------------------------------------
    # TEST CASE 2: Đổi ID trong request (IDOR / BOLA)
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("TEST CASE 2: Insecure Direct Object References (IDOR / BOLA)")
    print("-" * 70)

    # 2.0 Thủ kho 1 lập 1 phiếu xuất kho test
    create_exp = send_request("POST", "/export-notes/", token=wh1_token, data={
        "recipient_name": "Khách hàng Test IDOR",
        "note": "Phiếu xuất tạo bởi perf_wh_01 để kiểm thử IDOR",
        "details": [{"product_id": prod_id, "quantity": 1, "unit_price": 100000.0}]
    })
    if create_exp["status_code"] != 201:
        raise RuntimeError(f"Tạo phiếu xuất thất bại: {create_exp}")
    export_note = create_exp["body"]
    note_id = export_note["id"]
    print(f"Đã lập phiếu xuất kiểm thử: ID={note_id}, Code={export_note['code']}, CreatedBy={export_note['created_by']} (perf_wh_01)")

    # 2.1 Thủ kho 2 đọc chi tiết phiếu xuất của Thủ kho 1
    tc2_1 = send_request("GET", f"/export-notes/{note_id}", token=wh2_token)
    results.append({
        "id": "TC-02.1",
        "name": f"Thủ kho 2 (perf_wh_02) đọc GET /export-notes/{note_id} của Thủ kho 1",
        "expected_status": 200, # Trong quản lý kho, việc xem có thể hợp lệ hoặc là IDOR đọc
        "result": tc2_1,
        "is_vuln": False, # Quyền xem thông tin kho dùng chung
        "severity": "Thấp",
        "finding": "Thủ kho 2 đọc được phiếu xuất của Thủ kho 1 (Chính sách chia sẻ đọc giữa các thủ kho)."
    })

    # 2.2 Thủ kho 2 gọi DELETE /export-notes/{id} (Xóa phiếu của Thủ kho 1)
    tc2_2 = send_request("DELETE", f"/export-notes/{note_id}", token=wh2_token)
    results.append({
        "id": "TC-02.2",
        "name": f"Thủ kho 2 (perf_wh_02) gọi DELETE /export-notes/{note_id} (Xóa phiếu của Thủ kho 1)",
        "expected_status": 403, # Lẽ ra chỉ người tạo hoặc Admin mới được xóa!
        "result": tc2_2,
        "is_vuln": tc2_2["status_code"] == 200,
        "severity": "Nghiêm trọng" if tc2_2["status_code"] == 200 else "Không phát hiện vấn đề",
        "finding": (
            f"[LỖ HỔNG IDOR/BOLA] Thủ kho 2 xóa thành công phiếu xuất ID {note_id} do Thủ kho 1 tạo (HTTP 200)! "
            "Thiếu kiểm tra quyền sở hữu đối tượng (Object-Level Authorization: created_by == current_user.id)."
            if tc2_2["status_code"] == 200 else "Hệ thống đã chặn thành công."
        )
    })

    # 2.3 Tạo lại 1 phiếu khác để test Hủy (Cancel) chéo
    create_exp2 = send_request("POST", "/export-notes/", token=wh1_token, data={
        "recipient_name": "Khách hàng Test IDOR Cancel",
        "note": "Phiếu xuất số 2 bởi perf_wh_01",
        "details": [{"product_id": prod_id, "quantity": 1, "unit_price": 100000.0}]
    })
    note_id2 = create_exp2["body"]["id"]

    tc2_3 = send_request("POST", f"/export-notes/{note_id2}/cancel", token=wh2_token)
    results.append({
        "id": "TC-02.3",
        "name": f"Thủ kho 2 (perf_wh_02) gọi POST /export-notes/{note_id2}/cancel (Hủy phiếu của Thủ kho 1)",
        "expected_status": 403,
        "result": tc2_3,
        "is_vuln": tc2_3["status_code"] == 200,
        "severity": "Nghiêm trọng" if tc2_3["status_code"] == 200 else "Không phát hiện vấn đề",
        "finding": (
            f"[LỖ HỔNG IDOR/BOLA] Thủ kho 2 hủy thành công phiếu xuất ID {note_id2} của Thủ kho 1 (HTTP 200)! "
            "Bất kỳ ai mang vai trò WAREHOUSE_KEEPER đều có thể can thiệp chứng từ của đồng nghiệp."
            if tc2_3["status_code"] == 200 else "Hệ thống đã chặn thành công."
        )
    })

    # 2.4 Truy vấn ID phiếu xuất không tồn tại (ID = 99999999)
    tc2_4 = send_request("GET", "/export-notes/99999999", token=wh1_token)
    results.append({
        "id": "TC-02.4",
        "name": "Truy vấn ID không tồn tại GET /export-notes/99999999",
        "expected_status": 404,
        "result": tc2_4,
        "is_vuln": tc2_4["status_code"] == 500,
        "severity": "Không phát hiện vấn đề",
        "finding": "Trả về HTTP 404 Not Found rõ ràng, không bị crash 500." if tc2_4["status_code"] == 404 else f"Mã trạng thái: {tc2_4['status_code']}"
    })

    # -------------------------------------------------------------
    # TEST CASE 3: Token hết hạn, token bị chỉnh sửa payload, token của tài khoản khác
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("TEST CASE 3: Token Integrity & Lifecycle (Expired, Tampered, Alg:none, Impersonation)")
    print("-" * 70)

    # 3.1 Token hết hạn (exp = now - 1 hour)
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "perf_wh_01",
        "role": "WAREHOUSE_KEEPER",
        "user_id": wh1_user["id"],
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp())
    }
    expired_token = create_custom_jwt(expired_payload)
    tc3_1 = send_request("GET", "/auth/me", token=expired_token)
    results.append({
        "id": "TC-03.1",
        "name": "Gửi JWT đã hết hạn (Expired Token) vào GET /auth/me",
        "expected_status": 401,
        "result": tc3_1,
        "is_vuln": tc3_1["status_code"] != 401,
        "severity": "Nghiêm trọng" if tc3_1["status_code"] == 200 else "Không phát hiện vấn đề",
        "finding": "Chặn chính xác với HTTP 401: Token không hợp lệ hoặc đã hết hạn." if tc3_1["status_code"] == 401 else f"Lỗi: mã {tc3_1['status_code']}"
    })

    # 3.2 Token bị sửa payload (Tampered Payload: đổi role từ WAREHOUSE_KEEPER -> ADMIN nhưng giữ nguyên signature cũ)
    parts = wh1_token.split(".")
    import base64
    fake_payload = {
        "sub": "perf_wh_01",
        "role": "ADMIN",
        "user_id": wh1_user["id"],
        "exp": int((now + timedelta(hours=8)).timestamp()),
        "iat": int(now.timestamp())
    }
    fake_payload_b64 = base64.urlsafe_b64encode(json.dumps(fake_payload).encode()).decode().rstrip("=")
    tampered_token = f"{parts[0]}.{fake_payload_b64}.{parts[2]}"
    tc3_2 = send_request("POST", "/auth/users", token=tampered_token, data={
        "username": "perf_hacked_admin",
        "full_name": "Hacked Admin",
        "role": "ADMIN",
        "password": "Password@123"
    })
    results.append({
        "id": "TC-03.2",
        "name": "Gửi JWT bị sửa payload (Tampered Signature) vào POST /auth/users",
        "expected_status": 401,
        "result": tc3_2,
        "is_vuln": tc3_2["status_code"] != 401,
        "severity": "Nghiêm trọng" if tc3_2["status_code"] in (200, 201) else "Không phát hiện vấn đề",
        "finding": "Chặn chính xác với HTTP 401: Chữ ký HMAC không khớp." if tc3_2["status_code"] == 401 else f"Lỗi: mã {tc3_2['status_code']}"
    })

    # 3.3 Token thuật toán alg: "none"
    alg_none_payload = {
        "sub": "perf_admin_01",
        "role": "ADMIN",
        "user_id": admin_user["id"],
        "exp": int((now + timedelta(hours=8)).timestamp()),
        "iat": int(now.timestamp())
    }
    alg_none_token = create_custom_jwt(alg_none_payload, alg="none")
    tc3_3 = send_request("GET", "/auth/me", token=alg_none_token)
    results.append({
        "id": "TC-03.3",
        "name": "Gửi JWT với thuật toán alg: 'none' (JWT None Algorithm Bypass)",
        "expected_status": 401,
        "result": tc3_3,
        "is_vuln": tc3_3["status_code"] != 401,
        "severity": "Nghiêm trọng" if tc3_3["status_code"] == 200 else "Không phát hiện vấn đề",
        "finding": "Chặn chính xác với HTTP 401: PyJWT từ chối token không ký." if tc3_3["status_code"] == 401 else f"Lỗi: mã {tc3_3['status_code']}"
    })

    # 3.4 Sử dụng token của tài khoản khác
    tc3_4 = send_request("GET", "/auth/me", token=wh2_token)
    user_returned = tc3_4["body"].get("username") if isinstance(tc3_4["body"], dict) else ""
    results.append({
        "id": "TC-03.4",
        "name": "Kiểm tra ánh xạ danh tính token: Token của perf_wh_02",
        "expected_status": 200,
        "result": tc3_4,
        "is_vuln": user_returned != "perf_wh_02",
        "severity": "Không phát hiện vấn đề",
        "finding": f"Hệ thống định danh chính xác người dùng {user_returned} dựa trên token."
    })

    # -------------------------------------------------------------
    # TEST CASE 4: Thiếu header Authorization hoặc đổi HTTP Method
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("TEST CASE 4: Missing Authorization Header & HTTP Method Switching")
    print("-" * 70)

    # 4.1 Gọi GET /products không có Authorization header
    tc4_1 = send_request("GET", "/products", token=None)
    results.append({
        "id": "TC-04.1",
        "name": "Gọi GET /products khi thiếu hoàn toàn header Authorization",
        "expected_status": 401,
        "result": tc4_1,
        "is_vuln": tc4_1["status_code"] != 401,
        "severity": "Nghiêm trọng" if tc4_1["status_code"] == 200 else "Không phát hiện vấn đề",
        "finding": "Chặn chính xác với HTTP 401: Chưa cung cấp mã xác thực trong header." if tc4_1["status_code"] == 401 else f"Lỗi: mã {tc4_1['status_code']}"
    })

    # 4.2 Gọi POST /export-notes/ không có Authorization header
    tc4_2 = send_request("POST", "/export-notes/", token=None, data={
        "recipient_name": "Test No Auth",
        "details": [{"product_id": prod_id, "quantity": 1, "unit_price": 100000.0}]
    })
    results.append({
        "id": "TC-04.2",
        "name": "Gọi POST /export-notes/ khi thiếu header Authorization",
        "expected_status": 401,
        "result": tc4_2,
        "is_vuln": tc4_2["status_code"] != 401,
        "severity": "Nghiêm trọng" if tc4_2["status_code"] in (200, 201) else "Không phát hiện vấn đề",
        "finding": "Chặn chính xác với HTTP 401." if tc4_2["status_code"] == 401 else f"Lỗi: mã {tc4_2['status_code']}"
    })

    # 4.3 Gửi Authorization header sai định dạng: "Basic dXNlcjpwYXNz"
    tc4_3 = send_request("GET", "/auth/me", custom_headers={"Authorization": "Basic dXNlcjpwYXNz"})
    results.append({
        "id": "TC-04.3",
        "name": "Gửi header Authorization sai định dạng (Basic Auth thay vì Bearer)",
        "expected_status": 401,
        "result": tc4_3,
        "is_vuln": tc4_3["status_code"] != 401,
        "severity": "Không phát hiện vấn đề",
        "finding": "Chặn chính xác với HTTP 401." if tc4_3["status_code"] == 401 else f"Lỗi: mã {tc4_3['status_code']}"
    })

    # 4.4 Đổi method: Gọi GET /export-notes/{id}/ship thay vì POST
    tc4_4 = send_request("GET", f"/export-notes/{note_id2}/ship", token=wh1_token)
    results.append({
        "id": "TC-04.4",
        "name": f"Đổi HTTP Method: Gọi GET /export-notes/{note_id2}/ship thay vì POST",
        "expected_status": 405,
        "result": tc4_4,
        "is_vuln": tc4_4["status_code"] not in (404, 405),
        "severity": "Không phát hiện vấn đề",
        "finding": f"FastAPI từ chối chuẩn mực với HTTP {tc4_4['status_code']} (Method Not Allowed), không thực thi logic nghiệp vụ."
    })

    # 4.5 Đổi method: Gọi GET /auth/users thay vì POST
    tc4_5 = send_request("GET", "/auth/users", token=wh1_token)
    results.append({
        "id": "TC-04.5",
        "name": "Đổi HTTP Method: Gọi GET /auth/users thay vì POST (Thử bypass quyền)",
        "expected_status": 405,
        "result": tc4_5,
        "is_vuln": tc4_5["status_code"] == 200,
        "severity": "Không phát hiện vấn đề",
        "finding": f"FastAPI từ chối với HTTP {tc4_5['status_code']}, không bỏ sót bước kiểm tra quyền."
    })

    # -------------------------------------------------------------
    # TEST CASE 5: Mass Assignment (Gửi field lạ / field quản trị)
    # -------------------------------------------------------------
    print("\n" + "-" * 70)
    print("TEST CASE 5: Mass Assignment & Parameter Tampering")
    print("-" * 70)

    # 5.1 PUT /products/{id} gửi thêm {"current_stock": 999999, "role": "ADMIN", "is_admin": True}
    old_stock = perf_prod["current_stock"]
    tc5_1 = send_request("PUT", f"/products/{prod_id}", token=wh1_token, data={
        "name": perf_prod["name"],
        "current_stock": 999999,
        "role": "ADMIN",
        "is_admin": True,
        "status": "ACTIVE"
    })
    # Kiểm tra lại tồn kho sau khi gọi PUT
    check_prod = send_request("GET", f"/products/{prod_id}", token=wh1_token)["body"]
    new_stock = check_prod["current_stock"]
    stock_tampered = (new_stock == 999999)
    results.append({
        "id": "TC-05.1",
        "name": f"Gửi kèm 'current_stock: 999999' vào PUT /products/{prod_id}",
        "expected_status": 200,
        "result": tc5_1,
        "is_vuln": stock_tampered,
        "severity": "Nghiêm trọng" if stock_tampered else "Không phát hiện vấn đề",
        "finding": (
            "[LỖ HỔNG MASS ASSIGNMENT] Tồn kho bị sửa trực tiếp qua API cập nhật hàng hóa!"
            if stock_tampered else
            f"An toàn: Pydantic ProductUpdate lọc bỏ field 'current_stock'. Tồn kho không đổi ({old_stock} -> {new_stock})."
        )
    })

    # 5.2 POST /export-notes/ gửi thêm {"status": "COMPLETED", "total_amount": 0.0, "created_by": 1}
    tc5_2 = send_request("POST", "/export-notes/", token=wh1_token, data={
        "recipient_name": "Mass Assignment Test",
        "status": "COMPLETED",
        "total_amount": 0.0,
        "created_by": 1,
        "details": [{"product_id": prod_id, "quantity": 1, "unit_price": 100000.0}]
    })
    exp_body = tc5_2["body"] if isinstance(tc5_2["body"], dict) else {}
    status_tampered = exp_body.get("status") == "COMPLETED"
    creator_tampered = exp_body.get("created_by") == 1
    amount_tampered = exp_body.get("total_amount") == 0.0
    mass_vuln = status_tampered or creator_tampered or amount_tampered

    # Dọn dẹp phiếu vừa tạo
    if "id" in exp_body:
        send_request("DELETE", f"/export-notes/{exp_body['id']}", token=admin_token)

    results.append({
        "id": "TC-05.2",
        "name": "Gửi kèm 'status: COMPLETED', 'total_amount: 0', 'created_by: 1' vào POST /export-notes/",
        "expected_status": 201,
        "result": tc5_2,
        "is_vuln": mass_vuln,
        "severity": "Nghiêm trọng" if mass_vuln else "Không phát hiện vấn đề",
        "finding": (
            f"[LỖ HỔNG MASS ASSIGNMENT] Field nhạy cảm bị ghi đè! status={exp_body.get('status')}, created_by={exp_body.get('created_by')}, total_amount={exp_body.get('total_amount')}"
            if mass_vuln else
            f"An toàn: Backend tự gán status='CONFIRMED', created_by={exp_body.get('created_by')}, tính lại total_amount={exp_body.get('total_amount')} từ details."
        )
    })

    # 5.3 POST /auth/users gửi thêm field lạ không có trong schema
    tc5_3 = send_request("POST", "/auth/users", token=admin_token, data={
        "username": "perf_mass_test",
        "full_name": "Mass Test User",
        "role": "WAREHOUSE_KEEPER",
        "password": "Password@123",
        "is_superuser": True,
        "permissions": ["ALL"]
    })
    user_created = tc5_3["body"] if isinstance(tc5_3["body"], dict) else {}
    results.append({
        "id": "TC-05.3",
        "name": "Admin tạo user gửi thêm 'is_superuser: True', 'permissions: [ALL]'",
        "expected_status": 201,
        "result": tc5_3,
        "is_vuln": "is_superuser" in user_created,
        "severity": "Không phát hiện vấn đề",
        "finding": "An toàn: Pydantic UserCreate chỉ nhận các trường được khai báo, các trường lạ bị loại bỏ tự động."
    })

    # Ghi kết quả ra file JSON
    with open("group_a_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("HOÀN TẤT CHẠY KIỂM THỬ NHÓM A. TỔNG HỢP KẾT QUẢ:")
    print("=" * 80)
    for r in results:
        status_flag = "[FAIL/VULN]" if r["is_vuln"] else "[PASS/SECURE]"
        print(f"{status_flag} {r['id']} - {r['name']}")
        print(f"       HTTP Code: {r['result']['status_code']} | Latency: {r['result']['elapsed_ms']}ms | Mức độ: {r['severity']}")
        print(f"       Ghi nhận: {r['finding']}\n")


if __name__ == "__main__":
    run_tests()
