"""Kịch bản kiểm thử Nhóm A: Race Condition / TOCTOU khi tồn kho gần cạn.

Mục tiêu:
1. Thiết lập SKU-PERF-BULK-03 có tồn kho ban đầu = 10 đơn vị.
2. Tạo trước 30 phiếu xuất ở trạng thái CONFIRMED (mỗi phiếu 1 cái, tổng cầu = 30 > 10).
3. Bắn đồng thời 30 request POST /export-notes/{id}/ship bằng threading.Barrier (cùng một thời điểm microsecond).
4. Kiểm tra nghiệm thu:
   - Tồn kho có bị âm không?
   - Số lượng ship thành công có vượt quá 10 không?
   - Số lượng request bị từ chối đúng (HTTP 400) vs được chấp nhận sai?
   - Tính toàn vẹn của Thẻ kho (StockLedger).
"""

import sys
import os
import subprocess
import time
import threading
import requests
from datetime import datetime, timezone

# Đảm bảo in UTF-8 trên Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

if os.name == "nt" and not os.environ.get("INSIDE_DOCKER"):
    chk = subprocess.run(
        ["docker", "ps", "--filter", "name=warehouse_backend", "--filter", "status=running", "-q"],
        capture_output=True, text=True, check=False
    )
    if chk.returncode == 0 and chk.stdout.strip():
        res = subprocess.run(
            ["docker", "exec", "-e", "INSIDE_DOCKER=1", "warehouse_backend", "python", "/app/tests/performance/verify_group_a_race_condition.py"],
            check=False
        )
        sys.exit(res.returncode)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import models
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.core.database import SessionLocal, engine
from app.models.product import Product
from app.models.category import Category
from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.stock_ledger import StockLedger
from app.models.user import User

BASE_URL = "http://127.0.0.1:8000"
SKU_CODE = "SKU-PERF-BULK-03"
INITIAL_STOCK = 10
CONCURRENT_REQUESTS = 30


def setup_test_data():
    """Chuẩn bị dữ liệu kiểm thử sạch cho Nhóm A."""
    print("----------------------------------------------------------------------")
    print("1. KHỞI TẠO DỮ LIỆU KIỂM THỬ NHÓM A")
    print("----------------------------------------------------------------------")
    db = SessionLocal()
    try:
        # 1. Tìm hoặc tạo danh mục
        cat = db.query(Category).filter(Category.code == "CAT-PERF").first()
        if not cat:
            cat = Category(code="CAT-PERF", name="Danh mục Kiểm thử Hiệu năng")
            db.add(cat)
            db.flush()

        # 2. Tìm hoặc tạo SKU-PERF-BULK-03 với tồn kho ban đầu = 10
        prod = db.query(Product).filter(Product.code == SKU_CODE).first()
        now = datetime.now(timezone.utc)
        if not prod:
            prod = Product(
                code=SKU_CODE,
                name="Sản phẩm Kiểm thử Cạn tồn kho BULK-03",
                category_id=cat.id,
                unit="Cái",
                min_stock=5,
                current_stock=INITIAL_STOCK,
                standard_price=100000.0,
                status="ACTIVE",
            )
            db.add(prod)
            db.flush()

            # Thêm dòng thẻ kho khởi tạo
            init_ledger = StockLedger(
                product_id=prod.id,
                transaction_type="IMPORT",
                reference_code=f"INIT-{SKU_CODE}",
                quantity_change=INITIAL_STOCK,
                balance_after=INITIAL_STOCK,
                created_by=1,
                transaction_date=now,
                note="Khởi tạo số dư ban đầu cho kịch bản Nhóm A",
            )
            db.add(init_ledger)
            db.commit()
            print(f"  + Đã tạo mới {SKU_CODE} (ID {prod.id}) với current_stock = {INITIAL_STOCK}")
        else:
            # Dọn dẹp thẻ kho cũ của SKU này nếu có và reset về đúng 10
            db.query(StockLedger).filter(StockLedger.product_id == prod.id).delete()
            prod.current_stock = INITIAL_STOCK
            prod.status = "ACTIVE"
            init_ledger = StockLedger(
                product_id=prod.id,
                transaction_type="IMPORT",
                reference_code=f"INIT-{SKU_CODE}",
                quantity_change=INITIAL_STOCK,
                balance_after=INITIAL_STOCK,
                created_by=1,
                transaction_date=now,
                note="Reset số dư ban đầu cho kịch bản Nhóm A",
            )
            db.add(init_ledger)
            db.commit()
            print(f"  + Đã reset {SKU_CODE} (ID {prod.id}) về current_stock = {INITIAL_STOCK}")

        prod_id = prod.id

        # 3. Tạo trước 30 phiếu xuất ở trạng thái CONFIRMED (mỗi phiếu xuất 1 cái)
        # Tìm user kho để gán created_by
        user = db.query(User).filter(User.role.in_(["ADMIN", "WAREHOUSE_KEEPER"])).first()
        user_id = user.id if user else 1

        created_notes = []
        today_str = now.strftime("%Y%m%d")
        for i in range(CONCURRENT_REQUESTS):
            code = f"PX-GROUPA-{today_str}-{i+1:04d}"
            # Xóa phiếu cũ nếu trùng mã
            old_n = db.query(ExportNote).filter(ExportNote.code == code).first()
            if old_n:
                db.query(ExportNoteDetail).filter(ExportNoteDetail.export_note_id == old_n.id).delete()
                db.delete(old_n)
                db.flush()

            note = ExportNote(
                code=code,
                recipient_name=f"Khách hàng Test Race Condition {i+1}",
                created_by=user_id,
                note_date=now,
                total_amount=100000.0,
                status="CONFIRMED",
                note="Kịch bản kiểm thử Nhóm A race condition",
            )
            db.add(note)
            db.flush()

            detail = ExportNoteDetail(
                export_note_id=note.id,
                product_id=prod_id,
                quantity=1,
                unit_price=100000.0,
                subtotal=100000.0,
            )
            db.add(detail)
            created_notes.append(note.id)

        db.commit()
        print(f"  + Đã tạo sẵn {len(created_notes)} phiếu xuất CONFIRMED (mỗi phiếu 1 cái, tổng yêu cầu: {len(created_notes)} đơn vị).")
        return prod_id, created_notes

    finally:
        db.close()


def get_auth_token():
    """Đăng nhập lấy JWT Bearer token."""
    res = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": "perf_admin_01", "password": "Perf@123"},
        timeout=5,
    )
    if res.status_code == 200:
        token = res.json().get("access_token")
        return token
    raise RuntimeError(f"Không thể đăng nhập tài khoản test: {res.status_code} {res.text}")


def execute_concurrent_race_test(note_ids, token):
    """Bắn đồng thời 30 request POST /export-notes/{id}/ship bằng Barrier."""
    print("\n----------------------------------------------------------------------")
    print(f"2. BẮN ĐỒNG THỜI {len(note_ids)} REQUEST SHIP VÀO SKU-PERF-BULK-03 (TỒN KHO = {INITIAL_STOCK})")
    print("----------------------------------------------------------------------")

    barrier = threading.Barrier(len(note_ids))
    responses = []
    resp_lock = threading.Lock()

    def worker(note_id, idx):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        url = f"{BASE_URL}/api/v1/export-notes/{note_id}/ship"

        # Đợi tất cả 30 thread tập kết sẵn sàng
        barrier.wait()
        t0 = time.time()
        try:
            r = requests.post(url, headers=headers, timeout=10)
            latency = (time.time() - t0) * 1000
            with resp_lock:
                responses.append({
                    "note_id": note_id,
                    "index": idx,
                    "status_code": r.status_code,
                    "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
                    "latency_ms": latency,
                })
        except Exception as e:
            latency = (time.time() - t0) * 1000
            with resp_lock:
                responses.append({
                    "note_id": note_id,
                    "index": idx,
                    "status_code": 0,
                    "body": str(e),
                    "latency_ms": latency,
                })

    threads = [
        threading.Thread(target=worker, args=(note_id, i))
        for i, note_id in enumerate(note_ids)
    ]

    start_all = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total_time = time.time() - start_all

    print(f"  • Hoàn tất 30 request trong: {total_time:.3f} giây")
    return responses


def audit_results(prod_id, responses):
    """Kiểm toán dữ liệu và đánh giá các bất biến Nhóm A."""
    print("\n----------------------------------------------------------------------")
    print("3. PHÂN TÍCH KẾT QUẢ HTTP & KIỂM TOÁN CƠ SỞ DỮ LIỆU")
    print("----------------------------------------------------------------------")

    success_200 = [r for r in responses if r["status_code"] == 200]
    rejected_400 = [r for r in responses if r["status_code"] == 400]
    locked_500 = [r for r in responses if r["status_code"] == 500]
    other_errors = [r for r in responses if r["status_code"] not in (200, 400, 500)]

    print("• Thống kê phản hồi HTTP:")
    print(f"  - Thành công (200 OK)                   : {len(success_200)} / {len(responses)}")
    print(f"  - Từ chối đúng do hết hàng (400 Bad Req): {len(rejected_400)} / {len(responses)}")
    print(f"  - Lỗi khóa/quá tải (500 Server Error)   : {len(locked_500)} / {len(responses)}")
    print(f"  - Lỗi khác                              : {len(other_errors)} / {len(responses)}")

    if rejected_400:
        sample_err = rejected_400[0]["body"]
        print(f"  - Mẫu thông điệp từ chối (400)          : {sample_err.get('detail') if isinstance(sample_err, dict) else sample_err}")

    # Truy vấn trực tiếp CSDL
    db = SessionLocal()
    try:
        prod = db.query(Product).filter(Product.id == prod_id).first()
        final_stock = prod.current_stock

        # Lấy lịch sử thẻ kho sau khởi tạo
        ledger_entries = (
            db.query(StockLedger)
            .filter(StockLedger.product_id == prod_id)
            .order_by(StockLedger.id.asc())
            .all()
        )

        export_ledgers = [l for l in ledger_entries if l.transaction_type == "EXPORT"]
        total_quantity_shipped = sum(abs(l.quantity_change) for l in export_ledgers)

        # Kiểm tra tính lũy kế của Thẻ kho
        continuity_errors = 0
        duplicate_balances = set()
        seen_balances = set()

        for i in range(1, len(ledger_entries)):
            prev_l = ledger_entries[i - 1]
            curr_l = ledger_entries[i]
            expected = prev_l.balance_after + curr_l.quantity_change
            if curr_l.balance_after != expected:
                continuity_errors += 1
            if curr_l.balance_after in seen_balances:
                duplicate_balances.add(curr_l.balance_after)
            seen_balances.add(curr_l.balance_after)

        print("\n• Kiểm toán Cơ sở dữ liệu:")
        print(f"  - Tồn kho ban đầu                    : {INITIAL_STOCK} đơn vị")
        print(f"  - Tồn kho cuối cùng (current_stock)  : {final_stock} đơn vị")
        print(f"  - Tổng số lượng thực tế đã trừ kho   : {total_quantity_shipped} đơn vị")
        print(f"  - Số dòng Thẻ kho xuất hàng (EXPORT) : {len(export_ledgers)} dòng")
        print(f"  - Thẻ kho balance_after dòng cuối    : {ledger_entries[-1].balance_after if ledger_entries else 'N/A'}")
        print(f"  - Số lỗi đứt gãy lũy kế thẻ kho      : {continuity_errors} lỗi")
        print(f"  - Số giá trị balance_after bị lặp    : {len(duplicate_balances)} giá trị")

        # Đánh giá các tiêu chí Nhóm A
        is_negative = final_stock < 0
        is_oversold = total_quantity_shipped > INITIAL_STOCK or len(success_200) > INITIAL_STOCK
        is_exact = final_stock == 0 and total_quantity_shipped == INITIAL_STOCK and len(success_200) == INITIAL_STOCK

        print("\n----------------------------------------------------------------------")
        print("4. KẾT LUẬN ĐÁNH GIÁ AN TOÀN NHÓM A (RACE CONDITION / TOCTOU)")
        print("----------------------------------------------------------------------")
        print(f"• Bán vượt tồn kho (Oversold)    : {'[NGHIÊM TRỌNG] CÓ XẢY RA!' if is_oversold else '[AN TOÀN] KHÔNG BỊ VƯỢT'}")
        print(f"• Tồn kho bị âm (Negative Stock) : {'[NGHIÊM TRỌNG] TỒN KHO BỊ ÂM!' if is_negative else '[AN TOÀN] KHÔNG BỊ ÂM'}")
        print(f"• Tính toàn vẹn Thẻ kho          : {'[VI PHẠM]' if continuity_errors > 0 or len(duplicate_balances) > 0 else '[ĐẠT 100%]'}")
        print(f"• Khớp toán học kế toán (10 - 10): {'[ĐẠT CHÍNH XÁC]' if is_exact else '[SAI LỆCH]'}")

        severity = "Không phát hiện vấn đề" if (not is_negative and not is_oversold and is_exact and continuity_errors == 0) else "Nghiêm trọng"
        print(f"• Mức độ rủi ro xếp loại        : {severity.upper()}")
        print("----------------------------------------------------------------------")

        return {
            "initial_stock": INITIAL_STOCK,
            "final_stock": final_stock,
            "total_shipped": total_quantity_shipped,
            "success_200": len(success_200),
            "rejected_400": len(rejected_400),
            "locked_500": len(locked_500),
            "continuity_errors": continuity_errors,
            "duplicate_balances": len(duplicate_balances),
            "severity": severity,
            "raw_responses": responses,
        }

    finally:
        db.close()


if __name__ == "__main__":
    prod_id, note_ids = setup_test_data()
    token = get_auth_token()
    responses = execute_concurrent_race_test(note_ids, token)
    result = audit_results(prod_id, responses)
