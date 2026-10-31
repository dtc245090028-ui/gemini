"""Kịch bản kiểm định luồng SSE End-to-End qua Nginx Reverse Proxy (Port 5173 -> Port 8000).

Đo đạc thực tế:
1. Độ trễ từ lúc Commit thành công -> Sự kiện NHẬN ĐƯỢC ở client SSE thật (p50/p95).
2. Tỷ lệ gom sự kiện (Debounce ratio) khi có đợt ghi dồn dập (Burst).
"""

import json
import os
import sys
import time
import requests
import urllib.request
import threading
from typing import List

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
NGINX_URL = os.getenv("NGINX_URL", "http://127.0.0.1:5173")

def percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c < len(sorted_vals):
        return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])
    return sorted_vals[f]

def get_admin_token():
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]

def main():
    token = get_admin_token()
    print("===========================================================================")
    print(" KIỂM ĐỊNH LUỒNG SSE END-TO-END QUA NGINX REVERSE PROXY (PORT 5173)")
    print("===========================================================================")
    print(f"[1] Đã xác thực admin token thành công.")

    received_events = []
    connected_flag = threading.Event()
    stop_flag = threading.Event()

    def sse_listener():
        req = urllib.request.Request(
            f"{NGINX_URL}/api/v1/events/stream",
            headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
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
                                "recv_t": recv_t
                            })
                        except Exception:
                            pass
                        current_event = None
        except Exception as e:
            if not stop_flag.is_set():
                print(f"[SSE Error]: {e}")

    t = threading.Thread(target=sse_listener, daemon=True)
    t.start()

    if not connected_flag.wait(timeout=5.0):
        print("[!] Không thể kết nối SSE qua Nginx.")
        return

    print("[2] Kết nối SSE qua Nginx 5173 thành công (proxy_buffering off sẵn sàng).")
    time.sleep(0.5)

    headers = {"Authorization": f"Bearer {token}"}

    # =========================================================================
    # PHẦN A: ĐO ĐỘ TRỄ COMMIT -> CLIENT NHẬN ĐƯỢC (10 LƯỢT TUẦN TỰ)
    # =========================================================================
    print("\n--- PHẦN A: ĐO ĐỘ TRỄ COMMIT -> CLIENT NHẬN SỰ KIỆN (10 LƯỢT) ---")
    latencies_ms = []

    for i in range(1, 11):
        prev_count = len(received_events)
        t_commit_start = time.perf_counter()

        # Thao tác ghi đơn lẻ (nhập kho nhỏ)
        p_res = requests.post(
            f"{BASE_URL}/api/v1/import-notes/",
            json={
                "supplier_id": 1,
                "note": "Test SSE Delivery",
                "details": [{"product_id": 1, "quantity": 1, "unit_price": 50000.0}]
            },
            headers=headers
        )
        t_commit_end = time.perf_counter()
        assert p_res.status_code in (200, 201), f"Tạo phiếu nhập lỗi: {p_res.text}"

        # Chờ nhận event tương ứng ở client SSE (cửa sổ gom mặc định 200ms)
        timeout_t = time.perf_counter() + 2.0
        while len(received_events) == prev_count and time.perf_counter() < timeout_t:
            time.sleep(0.005)

        if len(received_events) > prev_count:
            last_ev = received_events[-1]
            delivery_delay_ms = (last_ev["recv_t"] - t_commit_end) * 1000.0
            latencies_ms.append(delivery_delay_ms)
            print(f"  Lượt {i:02d}: Commit = {(t_commit_end - t_commit_start)*1000:.1f}ms | Commit -> SSE Nhận = {delivery_delay_ms:.1f}ms")
        else:
            print(f"  Lượt {i:02d}: Timeout không nhận được sự kiện!")

        time.sleep(0.3)

    sorted_lats = sorted(latencies_ms)
    p50 = percentile(sorted_lats, 50)
    p95 = percentile(sorted_lats, 95)
    mean_lat = sum(sorted_lats) / len(sorted_lats) if sorted_lats else 0.0

    print(f"\n  >> KẾT QUẢ ĐỘ TRỄ COMMIT -> CLIENT NHẬN (ms):")
    print(f"     Min={min(sorted_lats):.1f} | Mean={mean_lat:.1f} | p50={p50:.1f} | p95={p95:.1f} | Max={max(sorted_lats):.1f}")

    # =========================================================================
    # PHẦN B: ĐO TỶ LỆ GOM SỰ KIỆN (DEBOUNCE RATIO) DƯỚI TẢI DỒN DẬP (BURST)
    # =========================================================================
    print("\n--- PHẦN B: ĐO TỶ LỆ GOM SỰ KIỆN (DEBOUNCE) KHI GHI LIÊN TỤC 15 MUTATIONS ---")
    prev_count_b = len(received_events)
    t_burst_start = time.perf_counter()

    # Bắn liên tục 15 mutations trong thời gian rất ngắn (<100ms)
    burst_mutations = 15
    for b in range(burst_mutations):
        requests.post(
            f"{BASE_URL}/api/v1/import-notes/",
            json={
                "supplier_id": 1,
                "note": "Test Debounce",
                "details": [{"product_id": 1, "quantity": 1, "unit_price": 50000.0}]
            },
            headers=headers
        )

    t_burst_end = time.perf_counter()
    burst_duration_ms = (t_burst_end - t_burst_start) * 1000.0

    # Chờ 1 giây để cửa sổ gom sự kiện (200ms) hoàn tất broadcast
    time.sleep(1.0)
    events_received_in_burst = len(received_events) - prev_count_b

    debounce_ratio = burst_mutations / max(1, events_received_in_burst)
    print(f"  • Số mutation ghi liên tiếp   : {burst_mutations} thao tác (trong {burst_duration_ms:.1f}ms)")
    print(f"  • Số sự kiện client nhận được : {events_received_in_burst} sự kiện")
    print(f"  • Tỷ lệ gom (Debounce Ratio)  : {debounce_ratio:.1f}x")

    stop_flag.set()

    # Thu dọn các phiếu test vừa tạo
    print("\n[3] Đang thu dọn CSDL sạch sẽ...")
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from app.core.database import SessionLocal
    from app.models.import_note import ImportNote, ImportNoteDetail
    from app.models.stock_ledger import StockLedger
    from app.models.product import Product

    db = SessionLocal()
    try:
        notes = db.query(ImportNote).filter(ImportNote.note.in_(["Test SSE Delivery", "Test Debounce"])).all()
        for n in notes:
            db.query(StockLedger).filter(StockLedger.reference_code == n.code).delete()
            db.query(ImportNoteDetail).filter(ImportNoteDetail.import_note_id == n.id).delete()
            db.delete(n)
        prod = db.query(Product).filter(Product.id == 1).first()
        if prod:
            prod.current_stock = 4
        db.commit()
        print("  ✅ Đã thu hồi sạch dữ liệu test.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
