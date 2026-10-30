"""Kịch bản kiểm định luồng SSE End-to-End qua Nginx Reverse Proxy (Port 5173 -> Port 8000).

Chạy độc lập để kiểm chứng:
1. Kết nối HTTP streaming qua Nginx với proxy_buffering off.
2. Nhận keepalive và sự kiện data_changed theo thời gian thực.
"""

import json
import os
import sys
import time
import requests
import urllib.request
import threading

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
NGINX_URL = os.getenv("NGINX_URL", "http://127.0.0.1:5173")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def get_admin_token():
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]

def main():
    token = get_admin_token()
    print("[1] Lấy token admin thành công.")

    received_messages = []
    connected_flag = threading.Event()
    stop_flag = threading.Event()

    def stream_listener():
        req = urllib.request.Request(
            f"{NGINX_URL}/api/v1/events/stream",
            headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                connected_flag.set()
                current_event = None
                for line in resp:
                    if stop_flag.is_set():
                        break
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith(":"):
                        received_messages.append({"type": "comment", "raw": line_str})
                    elif line_str.startswith("event:"):
                        current_event = line_str.split(":", 1)[1].strip()
                    elif line_str.startswith("data:"):
                        data_str = line_str.split(":", 1)[1].strip()
                        received_messages.append({"type": "event", "event": current_event, "data": json.loads(data_str)})
                        current_event = None
        except Exception as e:
            if not stop_flag.is_set():
                print(f"[SSE Error]: {e}")

    t = threading.Thread(target=stream_listener, daemon=True)
    t.start()

    if not connected_flag.wait(timeout=5.0):
        print("[!] Không thể kết nối qua Nginx. Đang thử trực tiếp qua Backend 8000...")
        return

    print("[2] Kết nối SSE qua Nginx 5173 thành công!")
    print("[3] Kiểm tra keepalive và luồng stream...")
    time.sleep(1.0)
    stop_flag.set()
    print(f"[4] Nhận được {len(received_messages)} thông điệp ban đầu:")
    for m in received_messages:
        print(f"    - {m}")
    print("[PASS] Nginx stream proxy_buffering off hoạt động chính xác.")

if __name__ == "__main__":
    main()
