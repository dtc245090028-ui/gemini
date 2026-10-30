"""Kiểm thử tự động tái hiện các lỗi L1, L2, L4, L5 (Trước và sau khi sửa).

L1: StockLedger.jsx không cập nhật khi tạo phiếu nhập (backend phát import_notes)
L2: Products.jsx không cập nhật khi điều chỉnh kiểm kê (backend phát stock_ledger)
L4: Suppliers.jsx không cập nhật khi tạo sản phẩm mới liên kết (backend phát products)
L5: useServerEvents.js sau khi reconnect không đồng bộ lại dữ liệu
"""

import os
import re
import sys
import time
import requests
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")


def get_token(username="admin", password="admin123"):
    res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def login_ui(page, token):
    page.goto(f"{FRONTEND_URL}/login")
    page.evaluate(f"localStorage.setItem('token', '{token}');")
    page.goto(FRONTEND_URL)
    page.wait_for_timeout(1000)


def cleanup(created_pids=None, created_imp_ids=None):
    import subprocess
    script = f"""
import sqlite3
conn = sqlite3.connect('/var/lib/warehouse/warehouse.db')
cur = conn.cursor()
pids = {created_pids or []}
for pid in pids:
    cur.execute("DELETE FROM products WHERE id = ?", (pid,))

imp_ids = {created_imp_ids or []}
for nid in imp_ids:
    cur.execute("DELETE FROM stock_ledger WHERE reference_code IN (SELECT code FROM import_notes WHERE id = ?)", (nid,))
    cur.execute("DELETE FROM import_note_details WHERE import_note_id = ?", (nid,))
    cur.execute("DELETE FROM import_notes WHERE id = ?", (nid,))

cur.execute("DELETE FROM stock_ledger WHERE note LIKE '%L1_TEST%' OR note LIKE '%L2_TEST%' OR reference_code LIKE '%L2_TEST%'")
cur.execute("UPDATE products SET current_stock = 79 WHERE id = 1")
cur.execute("UPDATE products SET current_stock = 30 WHERE id = 109")
conn.commit()
"""
    subprocess.run(["docker", "exec", "warehouse_backend", "python", "-c", script], capture_output=True, text=True)


def test_l1(playwright):
    """L1: StockLedger.jsx chỉ nghe 'stock_ledger' nên không tự cập nhật khi tạo phiếu nhập."""
    print("\n--- [L1 REPRODUCTION] Thẻ kho khi tạo phiếu nhập kho (import_notes) ---")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()
    created_imp_ids = []

    try:
        login_ui(page, token)
        page.locator('button:has-text("Thẻ kho & Kiểm kê")').first.click()
        page.wait_for_timeout(1500)

        imp_payload = {
            "supplier_id": 1,
            "note": "L1_TEST_IMPORT",
            "details": [{"product_id": 1, "quantity": 1, "unit_price": 50000.0}]
        }
        res = requests.post(f"{BASE_URL}/api/v1/import-notes", json=imp_payload, headers=headers)
        assert res.status_code == 201, f"Tạo phiếu nhập lỗi: {res.text}"
        imp_data = res.json()
        imp_code = imp_data["code"]
        created_imp_ids.append(imp_data["id"])
        print(f"  • Đã tạo phiếu nhập {imp_code} qua API.")

        t0 = time.perf_counter()
        updated = False
        while time.perf_counter() - t0 < 4.0:
            if page.locator(f'td:has-text("{imp_code}")').count() > 0:
                updated = True
                break
            page.wait_for_timeout(100)

        dt = (time.perf_counter() - t0) * 1000
        if updated:
            print(f"  >> L1 PASS: Bảng Thẻ kho đã tự cập nhật hiển thị {imp_code} trong {dt:.2f} ms")
            return True, dt
        else:
            print(f"  >> L1 FAIL: Hết timeout 4.0s, Bảng Thẻ kho KHÔNG tự cập nhật chứng từ {imp_code}!")
            return False, dt
    finally:
        browser.close()
        cleanup(created_imp_ids=created_imp_ids)


def test_l2(playwright):
    """L2: Products.jsx thiếu 'stock_ledger' nên điều chỉnh kiểm kê không cập nhật tồn."""
    print("\n--- [L2 REPRODUCTION] Trang Hàng hóa khi Điều chỉnh kiểm kê tồn kho ---")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()

    try:
        login_ui(page, token)
        page.locator('button:has-text("Hàng hóa")').first.click()
        page.wait_for_timeout(1500)

        adj_payload = {
            "product_id": 109,
            "actual_stock": 35,
            "reason": "L2_TEST_ADJUST"
        }
        res = requests.post(f"{BASE_URL}/api/v1/stock-ledger/adjust", json=adj_payload, headers=headers)
        assert res.status_code == 200, f"Điều chỉnh tồn kho lỗi: {res.text}"
        print(f"  • Đã điều chỉnh tồn SP109 thành 35 qua API.")

        t0 = time.perf_counter()
        updated = False
        while time.perf_counter() - t0 < 4.0:
            row = page.locator('tr:has-text("SP109")')
            if row.count() > 0 and "35" in row.inner_text():
                updated = True
                break
            page.wait_for_timeout(100)

        dt = (time.perf_counter() - t0) * 1000
        if updated:
            print(f"  >> L2 PASS: Bảng Hàng hóa đã tự cập nhật tồn kho SP109 sang 35 trong {dt:.2f} ms")
            return True, dt
        else:
            print(f"  >> L2 FAIL: Hết timeout 4.0s, Bảng Hàng hóa KHÔNG cập nhật tồn kho SP109 sang 35!")
            return False, dt
    finally:
        browser.close()
        cleanup()


def test_l4(playwright):
    """L4: Suppliers.jsx chỉ nghe 'suppliers' nên số sản phẩm liên kết không đổi khi thêm sản phẩm."""
    print("\n--- [L4 REPRODUCTION] Nhà cung cấp khi thêm sản phẩm mới trực thuộc ---")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()
    created_pids = []

    try:
        login_ui(page, token)
        page.locator('button:has-text("Nhà cung cấp")').first.click()
        page.wait_for_timeout(1500)

        card = page.locator('div.card-wood:has-text("NCC_VIENDONG")').first
        init_match = re.search(r"Hàng hóa cung ứng \((\d+)\)", card.inner_text())
        init_count = int(init_match.group(1)) if init_match else 0
        expected_count = init_count + 1
        print(f"  • Số hàng hóa cung ứng của NCC_VIENDONG ban đầu: {init_count} (Kỳ vọng: {expected_count})")

        sku_code = f"SKU-L4-{int(time.time())}"
        prod_payload = {
            "code": sku_code,
            "name": f"Product L4 {sku_code}",
            "category_id": 1,
            "supplier_id": 1,
            "standard_price": 100000.0,
            "unit": "Cái",
            "min_stock": 5
        }
        res = requests.post(f"{BASE_URL}/api/v1/products", json=prod_payload, headers=headers)
        assert res.status_code == 201, f"Tạo sản phẩm lỗi: {res.text}"
        pid = res.json()["id"]
        created_pids.append(pid)
        print(f"  • Đã tạo sản phẩm {sku_code} thuộc NCC 1 qua API.")

        t0 = time.perf_counter()
        updated = False
        while time.perf_counter() - t0 < 4.0:
            curr_match = re.search(r"Hàng hóa cung ứng \((\d+)\)", card.inner_text())
            if curr_match and int(curr_match.group(1)) == expected_count:
                updated = True
                break
            page.wait_for_timeout(100)

        dt = (time.perf_counter() - t0) * 1000
        if updated:
            print(f"  >> L4 PASS: Bảng Nhà cung cấp đã tự cập nhật số sản phẩm lên {expected_count} trong {dt:.2f} ms")
            return True, dt
        else:
            print(f"  >> L4 FAIL: Hết timeout 4.0s, Bảng Nhà cung cấp KHÔNG tự cập nhật số sản phẩm ({init_count} vẫn giữ nguyên)!")
            return False, dt
    finally:
        browser.close()
        cleanup(created_pids=created_pids)


def test_l5(playwright):
    """L5: Sau khi SSE reconnect thành công, frontend không đồng bộ lại dữ liệu."""
    print("\n--- [L5 REPRODUCTION] Tự đồng bộ sau khi SSE Reconnect ---")
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()
    created_imp_ids = []

    try:
        login_ui(page, token)
        page.locator('button:has-text("Tổng quan")').first.click()
        page.wait_for_timeout(1500)

        kpi_before = page.locator('p:has-text("Phiếu nhập kho")').locator('..').locator('h3').inner_text()
        print(f"  • Số phiếu nhập trước khi ngắt SSE: {kpi_before}")
        expected_count = str(int(kpi_before) + 1)

        # Mô phỏng rớt kết nối SSE: Chặn luồng SSE bằng cách ngắt kết nối mạng tạm thời
        page.route("**/api/v1/events/stream", lambda route: route.abort())
        page.wait_for_timeout(1000)
        print("  • Đã chặn đường SSE (mô phỏng mất mạng/restart backend).")

        # Tạo phiếu nhập trong lúc mạng SSE bị đứt
        imp_payload = {
            "supplier_id": 1,
            "note": "L5_TEST_RECONNECT",
            "details": [{"product_id": 1, "quantity": 1, "unit_price": 50000.0}]
        }
        res = requests.post(f"{BASE_URL}/api/v1/import-notes", json=imp_payload, headers=headers)
        assert res.status_code == 201
        created_imp_ids.append(res.json()["id"])
        print(f"  • Đã tạo phiếu nhập mới trong lúc mất mạng, kỳ vọng hiển thị: {expected_count}")

        # Khôi phục đường SSE (hết mất mạng, reconnect thành công)
        page.unroute("**/api/v1/events/stream")
        print("  • Đã khôi phục mạng SSE, trình duyệt tự động kết nối lại...")

        t0 = time.perf_counter()
        updated = False
        while time.perf_counter() - t0 < 4.0:
            val = page.locator('p:has-text("Phiếu nhập kho")').locator('..').locator('h3').inner_text()
            if val == expected_count:
                updated = True
                break
            page.wait_for_timeout(100)

        dt = (time.perf_counter() - t0) * 1000
        if updated:
            print(f"  >> L5 PASS: Sau khi reconnect, giao diện tự động đồng bộ trong {dt:.2f} ms")
            return True, dt
        else:
            print(f"  >> L5 FAIL: Sau khi reconnect, giao diện KHÔNG tự đồng bộ lại (vẫn giữ {kpi_before}, phải chờ 60s polling)!")
            return False, dt
    finally:
        browser.close()
        cleanup(created_imp_ids=created_imp_ids)


def main():
    print("==========================================================================")
    print(" CHẠY BỘ KIỂM THỬ TÁI HIỆN LỖI L1 - L5 (BƯỚC 0 - CHƯA SỬA MÃ NGUỒN)")
    print("==========================================================================")
    with sync_playwright() as playwright:
        r1, _ = test_l1(playwright)
        r2, _ = test_l2(playwright)
        r4, _ = test_l4(playwright)
        r5, _ = test_l5(playwright)

    print("\n==========================================================================")
    print(f" KẾT QUẢ TÁI HIỆN BƯỚC 0:")
    print(f" - L1 (StockLedger missing import_notes): {'PASS' if r1 else 'FAIL (Đã tái hiện đúng)'}")
    print(f" - L2 (Products missing stock_ledger):   {'PASS' if r2 else 'FAIL (Đã tái hiện đúng)'}")
    print(f" - L4 (Suppliers missing products):       {'PASS' if r4 else 'FAIL (Đã tái hiện đúng)'}")
    print(f" - L5 (useServerEvents no sync on recon): {'PASS' if r5 else 'FAIL (Đã tái hiện đúng)'}")
    print("==========================================================================")


if __name__ == "__main__":
    main()
