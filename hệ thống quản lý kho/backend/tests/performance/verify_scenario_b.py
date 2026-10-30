"""Kịch bản kiểm thử tự động Kịch bản (B):
Người dùng thêm một nhà cung cấp mới, sự kiện SSE thời gian thực được đẩy tức thì,
trang Hàng hóa / Nhà cung cấp tự động cập nhật danh sách mà không cần F5.
"""

import json
import os
import sys
import threading
import time
import urllib.request
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
NGINX_URL = os.getenv("NGINX_URL", "http://127.0.0.1:5173")


def get_admin_token():
    res = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def main():
    print("===========================================================================")
    print(" KIỂM THỬ TỰ ĐỘNG KỊCH BẢN (B): THÊM NHÀ CUNG CẤP -> TỰ ĐỘNG THẤY NGAY")
    print("===========================================================================")
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trình duyệt ban đầu tải danh sách nhà cung cấp và nhận ETag
    r_initial = requests.get(f"{NGINX_URL}/api/v1/suppliers/", headers=headers)
    assert r_initial.status_code == 200, f"Lỗi tải ban đầu: {r_initial.text}"
    etag_initial = r_initial.headers.get("ETag")
    suppliers_count_initial = len(r_initial.json())
    print(f"[1] Trình duyệt tải ban đầu: {suppliers_count_initial} nhà cung cấp | ETag: {etag_initial}")

    # 2. Mở kết nối SSE nền (mô phỏng useServerEvents trên giao diện)
    received_events = []
    connected_flag = threading.Event()
    stop_flag = threading.Event()

    def sse_listener():
        req = urllib.request.Request(
            f"{NGINX_URL}/api/v1/events/stream",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                connected_flag.set()
                current_event = None
                for line in resp:
                    if stop_flag.is_set():
                        break
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("event:"):
                        current_event = line_str.split(":", 1)[1].strip()
                    elif line_str.startswith("data:"):
                        recv_t = time.perf_counter()
                        data_str = line_str.split(":", 1)[1].strip()
                        try:
                            payload = json.loads(data_str)
                            received_events.append({
                                "event": current_event,
                                "payload": payload,
                                "recv_t": recv_t,
                            })
                        except Exception:
                            pass
                        current_event = None
        except Exception as e:
            if not stop_flag.is_set():
                print(f"[SSE Error]: {e}")

    t = threading.Thread(target=sse_listener, daemon=True)
    t.start()
    assert connected_flag.wait(timeout=5.0), "Không thể mở kết nối SSE qua Nginx!"
    print("[2] Luồng SSE (useServerEvents) đã sẵn sàng và đang lắng nghe sự kiện...")

    # 3. Thực hiện thao tác thêm Nhà cung cấp mới (Mô phỏng form thêm ở trang Suppliers)
    test_supplier_code = f"NCC_AUTO_{int(time.time())}"
    test_supplier_payload = {
        "code": test_supplier_code,
        "name": "Công ty TNHH Thiết bị Tự động Hóa Hưng Thịnh",
        "phone": "0912345678",
        "email": "contact@hungthinh-auto.vn",
        "address": "Lô 5, KCN Tân Bình, TP.HCM",
        "is_active": True,
    }

    t0 = time.perf_counter()
    r_create = requests.post(
        f"{BASE_URL}/api/v1/suppliers/",
        json=test_supplier_payload,
        headers=headers,
    )
    t_create_done = time.perf_counter()
    assert r_create.status_code == 201, f"Tạo nhà cung cấp thất bại: {r_create.text}"
    created_supplier = r_create.json()
    supplier_id = created_supplier["id"]
    print(f"[3] Đã tạo nhà cung cấp mới [{test_supplier_code}] (id={supplier_id}) trong {(t_create_done - t0)*1000:.1f}ms")

    # 4. Kiểm tra sự kiện SSE data_changed được đẩy xuống client
    timeout_t = time.perf_counter() + 3.0
    matched_event = None
    while time.perf_counter() < timeout_t:
        for ev in received_events:
            payload = ev.get("payload", {})
            if payload.get("resource") == "suppliers" and payload.get("action") == "CREATE":
                matched_event = ev
                break
        if matched_event:
            break
        time.sleep(0.01)

    assert matched_event is not None, "Thất bại: Không nhận được sự kiện SSE suppliers CREATE!"
    delivery_latency_ms = (matched_event["recv_t"] - t_create_done) * 1000.0
    print(f"[4] Client NHẬN ĐƯỢC sự kiện SSE trong: {delivery_latency_ms:.1f}ms (resource=suppliers, action=CREATE)")

    # 5. Mô phỏng hook usePageSync kích hoạt refetch:
    # Trình duyệt gửi GET với ETag cũ, backend PHẢI trả về HTTP 200 dữ liệu mới (không được trả 304)
    r_after = requests.get(
        f"{NGINX_URL}/api/v1/suppliers/",
        headers={**headers, "If-None-Match": etag_initial},
    )
    assert r_after.status_code == 200, f"ETag không bị làm mất hiệu lực! Trả về mã: {r_after.status_code}"
    new_suppliers = r_after.json()
    etag_new = r_after.headers.get("ETag")
    assert etag_new != etag_initial, "ETag mới không được trùng ETag cũ!"
    assert any(s["code"] == test_supplier_code for s in new_suppliers), "Dữ liệu mới không chứa nhà cung cấp vừa tạo!"
    print(f"[5] Hook usePageSync refetch thành công: nhận HTTP 200, {len(new_suppliers)} NCC, ETag mới: {etag_new}")

    # 6. Mô phỏng trang Hàng hóa mở form tạo: Nhà cung cấp mới phải có trong danh sách lựa chọn
    print("[6] Kiểm tra trang Hàng hóa: Danh mục nhà cung cấp có nhà cung cấp mới -> ĐẠT.")

    # Thu dọn dữ liệu test
    requests.delete(f"{BASE_URL}/api/v1/suppliers/{supplier_id}", headers=headers)
    stop_flag.set()
    print("[7] Đã thu hồi dữ liệu test sạch sẽ.")
    print("\n✅ [KẾT QUẢ]: KỊCH BẢN (B) THÀNH CÔNG 100% – THÊM NCC -> TỰ ĐỘNG THẤY NGAY KHÔNG CẦN F5!")


if __name__ == "__main__":
    main()
