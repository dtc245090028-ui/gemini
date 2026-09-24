"""Bộ kiểm thử cho Giao dịch ACID Nhập/Xuất kho, Chống tồn âm, Thẻ kho và Báo cáo (Bước 07)."""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_default_users
from app.main import app
from app.models import (
    Category,
    ExportNote,
    ExportNoteDetail,
    ImportNote,
    ImportNoteDetail,
    Product,
    StockLedger,
    Supplier,
)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Khởi tạo CSDL và nạp người dùng mặc định."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_users(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def thukho_headers(client):
    login_res = client.post("/api/v1/auth/login", json={"username": "thukho", "password": "thukho123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def sample_master_data():
    """Tạo hoặc lấy nhà cung cấp, nhóm hàng và sản phẩm phục vụ kiểm thử kho (Idempotent)."""
    db = SessionLocal()
    try:
        cat = db.query(Category).filter_by(code="CAT-ACID-TEST").first()
        if not cat:
            cat = Category(code="CAT-ACID-TEST", name="Nhóm thử nghiệm ACID")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        sup = db.query(Supplier).filter_by(code="SUP-ACID-TEST").first()
        if not sup:
            sup = Supplier(code="SUP-ACID-TEST", name="Nhà cung cấp ACID Test", phone="0911223344")
            db.add(sup)
            db.commit()
            db.refresh(sup)

        prod = db.query(Product).filter_by(code="SKU-ACID-01").first()
        if not prod:
            prod = Product(
                code="SKU-ACID-01",
                name="Ổ cứng SSD NVMe 1TB",
                category_id=cat.id,
                unit="Chiếc",
                min_stock=5,
                current_stock=0,
                standard_price=1500000.0,
            )
            db.add(prod)
            db.commit()
            db.refresh(prod)

        return {"cat_id": cat.id, "sup_id": sup.id, "prod_id": prod.id}
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def init_test_data(sample_master_data):
    """Làm sạch dữ liệu giao dịch cũ và thiết lập tồn kho = 0 trước khi chạy chuỗi bài test."""
    db = SessionLocal()
    try:
        prod_id = sample_master_data["prod_id"]
        prod = db.get(Product, prod_id)
        if prod:
            db.query(StockLedger).filter_by(product_id=prod_id).delete()
            # Dọn dẹp import details & export details liên quan
            import_details = db.query(ImportNoteDetail).filter_by(product_id=prod_id).all()
            for d in import_details:
                db.delete(d)
            export_details = db.query(ExportNoteDetail).filter_by(product_id=prod_id).all()
            for d in export_details:
                db.delete(d)
            prod.current_stock = 0
            db.commit()
    finally:
        db.close()
    yield


def test_create_import_note_and_stock_ledger(client, thukho_headers, sample_master_data):
    """Kiểm tra lập phiếu nhập kho: Tăng tồn kho và tự động ghi Thẻ kho."""
    sup_id = sample_master_data["sup_id"]
    prod_id = sample_master_data["prod_id"]

    import_data = {
        "supplier_id": sup_id,
        "note": "Nhập lô SSD đầu tiên",
        "details": [
            {"product_id": prod_id, "quantity": 50, "unit_price": 1400000.0}
        ],
    }

    res = client.post("/api/v1/import-notes/", json=import_data, headers=thukho_headers)
    assert res.status_code == 201
    note = res.json()
    assert note["code"].startswith("PN-")
    assert note["total_amount"] == 50 * 1400000.0
    assert note["status"] == "COMPLETED"

    # Kiểm tra tồn kho sản phẩm tăng lên 50
    prod_res = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers)
    assert prod_res.json()["current_stock"] == 50

    # Kiểm tra Thẻ kho được ghi nhận
    ledger_res = client.get(f"/api/v1/stock-ledger/?product_id={prod_id}", headers=thukho_headers)
    assert ledger_res.status_code == 200
    entries = ledger_res.json()
    assert len(entries) >= 1
    assert entries[0]["transaction_type"] == "IMPORT"
    assert entries[0]["quantity_change"] == 50
    assert entries[0]["balance_after"] == 50


def test_atomic_export_negative_stock_prevention(client, thukho_headers, sample_master_data):
    """Kiểm tra CHẶN ĐỨNG TỒN ÂM: Xuất quá số lượng tồn bị từ chối 400 và Rollback 100%."""
    prod_id = sample_master_data["prod_id"]

    # Kiểm tra số tồn hiện tại
    prod_res = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers)
    current_stock_before = prod_res.json()["current_stock"]

    # Thử xuất số lượng vượt quá tồn kho (hiện có 50, đòi xuất 999)
    excess_export = {
        "recipient_name": "Khách hàng mua sỉ",
        "note": "Yêu cầu xuất quá số tồn",
        "details": [
            {"product_id": prod_id, "quantity": 999, "unit_price": 1800000.0}
        ],
    }

    res = client.post("/api/v1/export-notes/", json=excess_export, headers=thukho_headers)
    assert res.status_code == 400
    assert "không đủ hàng tồn kho" in res.json()["detail"].lower()

    # Xác nhận số tồn kho hoàn toàn KHÔNG THAY ĐỔI
    prod_after = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()
    assert prod_after["current_stock"] == current_stock_before


def test_create_export_note_success(client, thukho_headers, sample_master_data):
    """Kiểm tra xuất kho thành công khi số lượng tồn đáp ứng đủ."""
    prod_id = sample_master_data["prod_id"]

    valid_export = {
        "recipient_name": "Công ty Tin học ABC",
        "note": "Xuất 20 ổ SSD",
        "details": [
            {"product_id": prod_id, "quantity": 20, "unit_price": 1700000.0}
        ],
    }

    res = client.post("/api/v1/export-notes/", json=valid_export, headers=thukho_headers)
    assert res.status_code == 201
    export_note = res.json()
    assert export_note["code"].startswith("PX-")
    assert export_note["status"] == "CONFIRMED"

    # Tại bước CONFIRMED: Chưa trừ tồn kho (tồn vẫn là 50)
    prod_mid = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()
    assert prod_mid["current_stock"] == 50

    # Chuyển sang SHIPPING (Giao hàng) -> Trừ kho từ 50 xuống 30
    ship_res = client.post(f"/api/v1/export-notes/{export_note['id']}/ship", headers=thukho_headers)
    assert ship_res.status_code == 200
    assert ship_res.json()["status"] == "SHIPPING"

    # Tồn kho giảm từ 50 xuống 30
    prod_after = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()
    assert prod_after["current_stock"] == 30

    # Thẻ kho ghi nhận dòng EXPORT
    ledger_res = client.get(f"/api/v1/stock-ledger/?product_id={prod_id}", headers=thukho_headers)
    entries = ledger_res.json()
    assert entries[0]["transaction_type"] == "EXPORT"
    assert entries[0]["quantity_change"] == -20
    assert entries[0]["balance_after"] == 30

    # Hoàn thành phiếu xuất
    comp_res = client.post(f"/api/v1/export-notes/{export_note['id']}/complete", headers=thukho_headers)
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"


def test_cancel_import_note_guard_check_rejection(client, thukho_headers, sample_master_data):
    """Kiểm tra Guard-Check chống tồn âm khi hủy phiếu nhập cũ mà hàng đã bị xuất đi."""
    sup_id = sample_master_data["sup_id"]
    prod_id = sample_master_data["prod_id"]

    # Nhập 100 sản phẩm mới
    import_res = client.post(
        "/api/v1/import-notes/",
        json={
            "supplier_id": sup_id,
            "details": [{"product_id": prod_id, "quantity": 100, "unit_price": 1000000.0}],
        },
        headers=thukho_headers,
    )
    import_note_id = import_res.json()["id"]
    # Hiện tại tồn kho = 30 + 100 = 130

    # Xuất đi 110 sản phẩm -> Lập phiếu & Giao hàng -> Tồn kho còn 20
    exp_res = client.post(
        "/api/v1/export-notes/",
        json={
            "recipient_name": "Đại lý X",
            "details": [{"product_id": prod_id, "quantity": 110, "unit_price": 1200000.0}],
        },
        headers=thukho_headers,
    )
    assert exp_res.status_code == 201
    exp_id = exp_res.json()["id"]
    client.post(f"/api/v1/export-notes/{exp_id}/ship", headers=thukho_headers)
    # Tồn kho hiện tại = 20

    # Thử hủy phiếu nhập 100 ban đầu -> Cần trừ 100 nhưng kho chỉ còn 20 -> Guard-check chặn 400!
    cancel_res = client.post(f"/api/v1/import-notes/{import_note_id}/cancel", headers=thukho_headers)
    assert cancel_res.status_code == 400
    detail_msg = cancel_res.json()["detail"].lower()
    assert "không thể hủy" in detail_msg
    assert "điều chỉnh tồn kho" in detail_msg

    # Tồn kho vẫn an toàn ở mức 20
    prod_check = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()
    assert prod_check["current_stock"] == 20


def test_stock_adjustment_exit_route(client, thukho_headers, sample_master_data):
    """Kiểm tra endpoint Điều chỉnh kiểm kê tồn kho (Lối thoát khi hủy phiếu bị chặn hoặc kiểm kê)."""
    prod_id = sample_master_data["prod_id"]

    adj_data = {
        "product_id": prod_id,
        "actual_stock": 25,  # Tồn kho đang là 20, kiểm kê thực tế có 25
        "reason": "Kiểm kê định kỳ tháng 9 phát hiện thừa 5 cái",
    }
    adj_res = client.post("/api/v1/stock-ledger/adjust", json=adj_data, headers=thukho_headers)
    assert adj_res.status_code == 200
    adj_info = adj_res.json()
    assert adj_info["actual_stock"] == 25
    assert adj_info["difference"] == 5
    assert adj_info["reference_code"].startswith("ADJ-")

    # Kiểm tra tồn kho sản phẩm đã thành 25
    prod_check = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()
    assert prod_check["current_stock"] == 25


def test_inventory_summary_report_accounting_formula(client, thukho_headers):
    """Kiểm tra Báo cáo Nhập - Xuất - Tồn: Luôn khớp công thức Tồn đầu + Nhập - Xuất = Tồn cuối."""
    now = datetime.now(timezone.utc)
    from_date = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    to_date = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    report_res = client.get(
        f"/api/v1/reports/inventory-summary?from_date={from_date}&to_date={to_date}",
        headers=thukho_headers,
    )
    assert report_res.status_code == 200
    report = report_res.json()

    for item in report["items"]:
        # Công thức kế toán bất biến
        expected_closing = item["opening_stock"] + item["total_import"] - item["total_export"]
        assert item["closing_stock"] == expected_closing, (
            f"Lỗi công thức tại sản phẩm {item['product_code']}: "
            f"{item['opening_stock']} + {item['total_import']} - {item['total_export']} != {item['closing_stock']}"
        )


def test_cancel_confirmed_export_note_hard_deletes(client, thukho_headers, sample_master_data):
    """Kiểm tra: Hủy phiếu xuất ở bước Xác nhận (CONFIRMED) -> Xóa hẳn khỏi CSDL, không để lại phiếu rác."""
    prod_id = sample_master_data["prod_id"]

    # 1. Tạo phiếu xuất ở bước Xác nhận
    create_res = client.post(
        "/api/v1/export-notes/",
        json={
            "recipient_name": "Khách hàng hủy sớm",
            "details": [{"product_id": prod_id, "quantity": 5, "unit_price": 1500000.0}],
        },
        headers=thukho_headers,
    )
    assert create_res.status_code == 201
    note_id = create_res.json()["id"]

    # 2. Hủy phiếu khi đang CONFIRMED
    cancel_res = client.post(f"/api/v1/export-notes/{note_id}/cancel", headers=thukho_headers)
    assert cancel_res.status_code == 200

    # 3. Kiểm tra phiếu đã bị xóa hoàn toàn khỏi DB (GET trả về 404)
    get_res = client.get(f"/api/v1/export-notes/{note_id}", headers=thukho_headers)
    assert get_res.status_code == 404


def test_cancel_shipping_export_note_restores_stock_and_keeps_record(client, thukho_headers, sample_master_data):
    """Kiểm tra: Hủy phiếu xuất ở bước Đang giao (SHIPPING) -> Trừ kho trước đó, khi hủy hoàn trả tồn kho và lưu vết CANCELLED."""
    prod_id = sample_master_data["prod_id"]

    # Lấy tồn kho ban đầu
    stock_before = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()["current_stock"]

    # 1. Tạo phiếu xuất
    create_res = client.post(
        "/api/v1/export-notes/",
        json={
            "recipient_name": "Khách hàng boom hàng khi đang giao",
            "details": [{"product_id": prod_id, "quantity": 5, "unit_price": 1500000.0}],
        },
        headers=thukho_headers,
    )
    assert create_res.status_code == 201
    note_id = create_res.json()["id"]

    # 2. Bắt đầu giao hàng -> Tồn kho giảm 5
    ship_res = client.post(f"/api/v1/export-notes/{note_id}/ship", headers=thukho_headers)
    assert ship_res.status_code == 200
    assert ship_res.json()["status"] == "SHIPPING"
    stock_shipping = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()["current_stock"]
    assert stock_shipping == stock_before - 5

    # 3. Hủy đơn khi đang giao
    cancel_res = client.post(f"/api/v1/export-notes/{note_id}/cancel", headers=thukho_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # 4. Tồn kho được hoàn trả lại như ban đầu
    stock_after = client.get(f"/api/v1/products/{prod_id}", headers=thukho_headers).json()["current_stock"]
    assert stock_after == stock_before

    # 5. Phiếu VẪN TỒN TẠI trong CSDL với trạng thái CANCELLED
    get_res = client.get(f"/api/v1/export-notes/{note_id}", headers=thukho_headers)
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "CANCELLED"

    # 6. Thẻ kho ghi nhận dòng ADJUSTMENT (+5)
    ledger_res = client.get(f"/api/v1/stock-ledger/?product_id={prod_id}", headers=thukho_headers)
    last_entry = ledger_res.json()[0]
    assert last_entry["transaction_type"] == "ADJUSTMENT"
    assert last_entry["quantity_change"] == 5
