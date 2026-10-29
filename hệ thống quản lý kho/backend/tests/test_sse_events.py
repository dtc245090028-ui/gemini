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

def get_target_stream_url():
    # If NGINX_URL is reachable (running on host machine), test through Nginx.
    # Otherwise (e.g. running inside docker container), test through BASE_URL.
    try:
        req = urllib.request.Request(f"{NGINX_URL}/")
        with urllib.request.urlopen(req, timeout=1.0):
            return NGINX_URL
    except Exception:
        return BASE_URL

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

    stream_target = get_target_stream_url()
    t_listener = threading.Thread(target=stream_listener, args=(stream_target,), daemon=True)
    t_listener.start()

    assert connected_flag.wait(timeout=5.0), f"Timeout connecting to SSE stream through {stream_target}!"
    print(f"[2] Ket noi SSE qua {stream_target} thanh cong!")

    # Bắn liên tiếp 15 mutations điều chỉnh tồn kho trong vòng 100ms
    print("[3] Ban 15 mutation lien tiep de kiem chung co che Gom Su Kien (Debounce)...")
    headers = {"Authorization": f"Bearer {token}", "X-Client-Id": "test_client_sse_1"}
    
    for i in range(15):
        payload = {
            "product_id": 1,
            "actual_stock": 10 + (i % 5),
            "reason": f"SSE Stress Test {i}",
            "idempotency_key": f"SSE-TEST-{time.time()}-{i}"
        }
        r = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=payload, headers=headers)
        assert r.status_code == 200, f"Mutation {i} failed: {r.text}"

    # Chờ 0.5s để debounce window (200ms) gom xong và flush
    time.sleep(0.6)
    stop_flag.set()

    print("[4] Ket qua nhan duoc:")
    data_events = [m for m in received_messages if m.get("type") == "event"]
    keepalives = [m for m in received_messages if m.get("type") == "comment"]
    
    print(f"  • Tong comments/keepalive: {len(keepalives)}")
    print(f"  • Tong su kien da nhan   : {len(data_events)}")
    for ev in data_events:
        d = ev["data"]
        print(f"    - Event: {ev['event']} | Resource: {d.get('resource')} | Mutations gộp: {d.get('mutation_count')} | Client IDs: {d.get('client_ids')}")

    # Đọc thống kê từ endpoint /api/v1/events/stats
    stats_res = requests.get(f"{BASE_URL}/api/v1/events/stats", headers=headers)
    stats = stats_res.json()
    print("[5] Thong ke Backend Broadcaster:")
    print(f"  • Total mutations recorded: {stats['total_mutations_recorded']}")
    print(f"  • Total events emitted    : {stats['total_events_emitted']}")
    print(f"  • Ti le gop su kien       : {stats['batching_efficiency_ratio']}x (Dot bien du lieu duoc gop gon gang)")

    assert len(data_events) >= 1, "Phải nhận được ít nhất 1 sự kiện data_changed!"
    # Chứng minh: Số sự kiện phát ra << 15 mutations
    assert len(data_events) <= 3, f"Số sự kiện phát ra ({len(data_events)}) quá nhiều, debounce chưa hoạt động tối ưu!"
    assert stats['batching_efficiency_ratio'] >= 3.0, "Hiệu suất gom sự kiện phải đạt ít nhất 3.0x!"
    print("\n=> CHỨNG MINH THÀNH CÔNG: SỐ SỰ KIỆN PHÁT RA (", len(data_events), ") << SỐ THAY ĐỔI (15)!\n")

if __name__ == "__main__":
    test_sse()
