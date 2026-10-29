import json
import os
import sys
import time
import requests
import urllib.request
import threading

BASE_URL = "http://127.0.0.1:8000"
NGINX_URL = "http://127.0.0.1:5173"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def get_admin_token():
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]

def test_sse():
    token = get_admin_token()
    print("[1] Da lay token thanh cong.")
    
    received_messages = []
    connected_flag = threading.Event()
    stop_flag = threading.Event()

    def stream_listener(url):
        req = urllib.request.Request(
            f"{url}/api/v1/events/stream",
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
                        # comment / keepalive
                        received_messages.append({"type": "comment", "raw": line_str})
                    elif line_str.startswith("event:"):
                        current_event = line_str.split(":", 1)[1].strip()
                    elif line_str.startswith("data:"):
                        data_str = line_str.split(":", 1)[1].strip()
                        received_messages.append({"type": "event", "event": current_event, "data": json.loads(data_str)})
                        current_event = None
        except Exception as e:
            if not stop_flag.is_set():
                print(f"[SSE Client Error]: {e}")

    # Chạy listener qua Nginx (port 5173) để kiểm tra cấu hình proxy_buffering off
    t_listener = threading.Thread(target=stream_listener, args=(NGINX_URL,), daemon=True)
    t_listener.start()

    assert connected_flag.wait(timeout=5.0), "Timeout connecting to SSE stream through Nginx!"
    print("[2] Ket noi SSE qua Nginx thanh cong!")

    # Bắn liên tiếp 15 mutations điều chỉnh tồn kho trong vòng 100ms
    print("[3] Ban 15 mutation lien tiep de kiem chung co che Gom Su Kien (Debounce)...")
    headers = {"Authorization": f"Bearer {token}", "X-Client-Id": "test_client_sse_1"}
    
    t0_burst = time.perf_counter()
    for i in range(15):
        payload = {
            "product_id": 1,
            "actual_stock": 4 + (i % 2),
            "reason": f"SSE Test Burst {i}"
        }
        res = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload, headers=headers)
        assert res.status_code == 200, f"Adjust {i} failed: {res.text}"

    # Chờ 500ms để debounce flush (cửa sổ 200ms)
    time.sleep(0.6)
    stop_flag.set()

    # Thống kê tin nhắn nhận được
    events_only = [m for m in received_messages if m["type"] == "event"]
    comments_only = [m for m in received_messages if m["type"] == "comment"]

    print(f"[4] Ket qua nhan duoc:")
    print(f"  • Tong comments/keepalive: {len(comments_only)}")
    print(f"  • Tong su kien da nhan   : {len(events_only)}")
    for ev in events_only:
        d = ev["data"]
        print(f"    - Event: {ev['event']} | Resource: {d['resource']} | Mutations gộp: {d['mutation_count']} | Client IDs: {d['client_ids']}")

    # Kiểm tra thống kê backend
    stats_res = requests.get(f"{BASE_URL}/api/v1/events/stats", headers=headers)
    stats = stats_res.json()
    print(f"[5] Thong ke Backend Broadcaster:")
    print(f"  • Total mutations recorded: {stats['total_mutations_recorded']}")
    print(f"  • Total events emitted    : {stats['total_events_emitted']}")
    print(f"  • Ti le gop su kien       : {stats['batching_efficiency_ratio']}x (Dot bien du lieu duoc gop gon gang)")

    assert len(events_only) >= 1, "No data_changed events received!"
    assert len(events_only) < 15, f"Debounce failed: got {len(events_only)} events for 15 mutations (should be << 15)!"
    print("\n=> CHỨNG MINH THÀNH CÔNG: SỐ SỰ KIỆN PHÁT RA (", len(events_only), ") << SỐ THAY ĐỔI (15)!")

if __name__ == "__main__":
    test_sse()
