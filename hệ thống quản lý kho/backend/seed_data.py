"""Script nạp dữ liệu mẫu thực tế 60 ngày (Storytelling Seed Data).

Bao gồm:
- 3 tài khoản người dùng theo 3 vai trò (admin, thukho, ketoan).
- 4 nhóm hàng (categories) và 3 nhà cung cấp (suppliers).
- 22 mặt hàng công nghệ thực tế (products).
- 3 kịch bản cốt lõi cho AI phân tích:
  + SP001 (Bàn phím cơ Akko): Bán chạy, tồn cạn kiệt (4/15) -> AI gợi ý nhập khẩn cấp (HIGH).
  + SP002 (Chuột Logitech G304): Xuất tăng đột biến tuần này (35 cái) -> AI báo động SURGE_EXPORT (>200%).
  + SP003 (Cáp VGA to HDMI): Tồn 60 cái suốt 60 ngày không xuất đơn nào -> AI cảnh báo DEAD_STOCK.
- Chuỗi giao dịch nhập/xuất và sổ cái Thẻ kho (StockLedger) bảo toàn số dư chuẩn ACID.
"""

from datetime import datetime, timedelta
import random
import sys
from sqlalchemy.orm import Session

# Đảm bảo in tiếng Việt mượt mà trên console Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models.category import Category
from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.import_note import ImportNote, ImportNoteDetail
from app.models.product import Product
from app.models.stock_ledger import StockLedger
from app.models.supplier import Supplier
from app.models.user import User


def seed_xlsx_transactions(db: Session, prod_map: dict, sup_map: dict, thukho_user: User, now: datetime):
    """Nạp phiếu nhập khởi tạo và một số phiếu xuất mẫu cho 54 mặt hàng từ Excel nếu chưa có."""
    existing_xlsx = db.query(ImportNote).filter(ImportNote.code == "PN-SEED-XLSX-01").first()
    if existing_xlsx:
        return

    print("[INFO] Sinh giao dich nhap/xuat kho cho 54 mat hang moi tu bang gia Excel...")
    xlsx_date = now - timedelta(days=25)

    # 1. Phiếu nhập từ các chuỗi bán lẻ / nhà phân phối lớn
    imp_fpt = ImportNote(
        code="PN-SEED-XLSX-01",
        supplier_id=sup_map["NCC_FPTSHOP"].id,
        created_by=thukho_user.id,
        note_date=xlsx_date,
        total_amount=0.0,
        status="COMPLETED",
        note="Nhập kho chính hãng thiết bị Apple, Laptop Dell & phụ kiện từ FPT Shop",
    )
    db.add(imp_fpt)
    db.flush()

    total_imp_amount = 0.0
    for i in range(23, 77):
        code = f"SP{i:03d}"
        if code in prod_map:
            p = prod_map[code]
            if p.standard_price >= 20000000:
                qty = random.randint(6, 12)
            elif p.standard_price >= 5000000:
                qty = random.randint(10, 20)
            elif p.standard_price >= 1000000:
                qty = random.randint(15, 30)
            else:
                qty = random.randint(30, 60)

            unit_price = round(p.standard_price * 0.78, -3)
            subtotal = unit_price * qty
            total_imp_amount += subtotal

            db.add(
                ImportNoteDetail(
                    import_note_id=imp_fpt.id,
                    product_id=p.id,
                    quantity=qty,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )
            p.current_stock += qty
            db.add(
                StockLedger(
                    product_id=p.id,
                    transaction_type="IMPORT",
                    reference_code=imp_fpt.code,
                    quantity_change=qty,
                    balance_after=p.current_stock,
                    created_by=thukho_user.id,
                    transaction_date=xlsx_date,
                    note="Nhập kho hàng công nghệ theo bảng giá tham khảo",
                )
            )

    imp_fpt.total_amount = total_imp_amount

    # 2. Phiếu xuất bán thương mại một số mặt hàng (Điện thoại, Laptop, Phụ kiện)
    exp_retail = ExportNote(
        code="PX-SEED-XLSX-01",
        recipient_name="Khách hàng Bán lẻ & Đối tác Doanh nghiệp",
        created_by=thukho_user.id,
        note_date=now - timedelta(days=8),
        total_amount=0.0,
        status="COMPLETED",
        note="Xuất kho cung ứng đơn hàng bán lẻ định kỳ",
    )
    db.add(exp_retail)
    db.flush()

    total_exp_amount = 0.0
    for i in range(23, 77, 2):  # Xuất xen kẽ các mã
        code = f"SP{i:03d}"
        if code in prod_map:
            p = prod_map[code]
            qty_out = min(p.current_stock // 3, 2 if p.standard_price > 15000000 else 6)
            if qty_out > 0:
                subtotal = p.standard_price * qty_out
                total_exp_amount += subtotal
                db.add(
                    ExportNoteDetail(
                        export_note_id=exp_retail.id,
                        product_id=p.id,
                        quantity=qty_out,
                        unit_price=p.standard_price,
                        subtotal=subtotal,
                    )
                )
                p.current_stock -= qty_out
                db.add(
                    StockLedger(
                        product_id=p.id,
                        transaction_type="EXPORT",
                        reference_code=exp_retail.code,
                        quantity_change=-qty_out,
                        balance_after=p.current_stock,
                        created_by=thukho_user.id,
                        transaction_date=now - timedelta(days=8),
                        note="Xuất hàng thương mại đơn lẻ",
                    )
                )
    exp_retail.total_amount = total_exp_amount
    db.commit()
    print("[SUCCESS] Da nap thanh cong giao dich kho cho 54 mat hang moi!")


def seed_database():
    print("[INFO] Bat dau qua trinh nap du lieu mau (Storytelling Seed Data)...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # =====================================================================
        # 1. TÀI KHOẢN NGƯỜI DÙNG (3 ROLES)
        # =====================================================================
        print("[INFO] 1. Khoi tao tai khoan nguoi dung...")

        users_data = [
            ("admin", "admin123", "Quản Trị Viên Hệ Thống", "ADMIN"),
            ("thukho", "thukho123", "Nguyễn Văn Kho (Thủ kho)", "WAREHOUSE_KEEPER"),
            ("ketoan", "ketoan123", "Trần Thị Toán (Kế toán)", "ACCOUNTANT"),
        ]
        user_map = {}
        for username, password, full_name, role in users_data:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    username=username,
                    password_hash=get_password_hash(password),
                    full_name=full_name,
                    role=role,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            user_map[username] = user

        admin_user = user_map["admin"]
        thukho_user = user_map["thukho"]

        # =====================================================================
        # 2. NHÓM HÀNG (CATEGORIES)
        # =====================================================================
        print("[INFO] 2. Khoi tao nhom hang hoa...")
        categories_data = [
            ("CAT_PK", "Phụ kiện máy tính & Di động", "Bàn phím, chuột, tai nghe, sạc cáp, túi chống sốc"),
            ("CAT_LK", "Linh kiện phần cứng", "Ổ cứng SSD, RAM, nguồn, tản nhiệt, USB, thẻ nhớ"),
            ("CAT_TB", "Thiết bị ngoại vi & Âm thanh", "Màn hình, webcam, máy in, loa"),
            ("CAT_NET", "Thiết bị mạng", "Router Wifi, switch chia mạng, cáp mạng"),
            ("CAT_DT", "Điện thoại & Thiết bị di động", "Điện thoại thông minh iPhone, Samsung, Xiaomi, Oppo, Vivo"),
            ("CAT_LT", "Máy tính xách tay & Laptop", "MacBook, Dell, Asus, HP, Lenovo, Acer"),
            ("CAT_PC", "Máy tính để bàn & PC", "PC Gaming, PC văn phòng, Mini PC Intel NUC, iMac"),
        ]
        cat_map = {}
        for code, name, desc in categories_data:
            cat = db.query(Category).filter(Category.code == code).first()
            if not cat:
                cat = Category(code=code, name=name, description=desc)
                db.add(cat)
                db.commit()
                db.refresh(cat)
            cat_map[code] = cat

        # =====================================================================
        # 3. NHÀ CUNG CẤP (SUPPLIERS)
        # =====================================================================
        print("[INFO] 3. Khoi tao nha cung cap...")
        suppliers_data = [
            ("NCC_VIENDONG", "Công ty TNHH Phân Phối Viễn Đông", "0243888999", "viendong@tech.vn", "Hà Nội"),
            ("NCC_SAIGON", "Tổng đại lý Tin học Sài Gòn", "0283999888", "saigon@distri.vn", "TP. Hồ Chí Minh"),
            ("NCC_ACHAU", "Công ty Cổ phần Công nghệ Á Châu", "0236777888", "achau@hardware.com", "Đà Nẵng"),
            ("NCC_FPTSHOP", "Công ty Cổ phần Bán lẻ Kỹ thuật số FPT (FPT Shop)", "18006601", "fptshop@fpt.com.vn", "Hà Nội"),
            ("NCC_TGDD", "Công ty Cổ phần Thế Giới Di Động", "18001060", "cskh@thegioididong.com", "TP. Hồ Chí Minh"),
            ("NCC_CELLPHONES", "Hệ thống Bán lẻ Di động CellphoneS", "18002097", "cskh@cellphones.com.vn", "TP. Hồ Chí Minh"),
            ("NCC_PHONGVU", "Công ty Cổ phần Thương mại Dịch vụ Phong Vũ", "18006867", "cskh@phongvu.vn", "TP. Hồ Chí Minh"),
            ("NCC_GEARVN", "Công ty TNHH Thương mại Gearvn", "18006975", "cskh@gearvn.com", "TP. Hồ Chí Minh"),
            ("NCC_ANPHAT", "Công ty Cổ phần Tin học An Phát", "19000323", "cskh@anphatpc.com.vn", "Hà Nội"),
            ("NCC_HOANGHA", "Hệ thống Bán lẻ Di động Hoàng Hà Mobile", "19002091", "cskh@hoanghamobile.com", "Hà Nội"),
        ]
        sup_map = {}
        for code, name, phone, email, addr in suppliers_data:
            sup = db.query(Supplier).filter(Supplier.code == code).first()
            if not sup:
                sup = Supplier(code=code, name=name, phone=phone, email=email, address=addr, is_active=True)
                db.add(sup)
                db.commit()
                db.refresh(sup)
            sup_map[code] = sup

        # =====================================================================
        # 4. DANH SÁCH 22 HÀNG HÓA (PRODUCTS)
        # =====================================================================
        print("[INFO] 4. Khoi tao 22 mat hang thuc te (kem 3 kich ban cot loi)...")

        # SKU, Name, Category, Unit, MinStock, StandardPrice
        products_meta = [
            # 3 kịch bản cốt lõi cho AI:
            ("SP001", "Bàn phím cơ Akko 3087", "CAT_PK", "Chiếc", 15, 950000.0),      # Sắp cạn kho
            ("SP002", "Chuột không dây Logitech G304", "CAT_PK", "Chiếc", 10, 750000.0), # Xuất đột biến tuần này
            ("SP003", "Cáp chuyển đổi VGA to HDMI", "CAT_PK", "Sợi", 5, 85000.0),        # Hàng chết (60 ngày 0 xuất)
            # 19 mặt hàng luân chuyển bình thường:
            ("SP004", "Màn hình Dell UltraSharp 24 inch", "CAT_TB", "Chiếc", 5, 5500000.0),
            ("SP005", "Ổ cứng SSD Samsung 980 1TB NVMe", "CAT_LK", "Chiếc", 8, 2200000.0),
            ("SP006", "RAM Corsair Vengeance 16GB DDR4", "CAT_LK", "Thanh", 10, 1150000.0),
            ("SP007", "Router Wifi 6 TP-Link Archer AX10", "CAT_NET", "Bộ", 6, 1250000.0),
            ("SP008", "Switch mạng 8 cổng Gigabit TP-Link", "CAT_NET", "Chiếc", 5, 450000.0),
            ("SP009", "Webcam Logitech C920 Pro Full HD", "CAT_TB", "Chiếc", 4, 1650000.0),
            ("SP010", "Tai nghe Gaming HyperX Cloud II", "CAT_PK", "Chiếc", 6, 1850000.0),
            ("SP011", "Nguồn máy tính Corsair CV650 650W", "CAT_LK", "Chiếc", 5, 1400000.0),
            ("SP012", "Bộ phát Wifi Mesh Mercusys Halo H50G", "CAT_NET", "Bộ", 4, 1350000.0),
            ("SP013", "Ổ cứng di động WD My Passport 2TB", "CAT_LK", "Chiếc", 5, 2100000.0),
            ("SP014", "Loa vi tính Microlab M-108 2.1", "CAT_TB", "Bộ", 4, 550000.0),
            ("SP015", "Tản nhiệt CPU Deepcool Gammaxx 400", "CAT_LK", "Bộ", 8, 380000.0),
            ("SP016", "Cáp mạng bấm sẵn Cat6 UTP 10 mét", "CAT_NET", "Sợi", 20, 65000.0),
            ("SP017", "Chuột văn phòng Logitech B100", "CAT_PK", "Chiếc", 15, 90000.0),
            ("SP018", "Bàn di chuột Gaming cỡ lớn 80x30cm", "CAT_PK", "Tấm", 12, 120000.0),
            ("SP019", "Giá treo tai nghe kim loại đa năng", "CAT_PK", "Chiếc", 8, 150000.0),
            ("SP020", "Bộ chia cổng USB 3.0 Orico 4 cổng", "CAT_PK", "Chiếc", 10, 160000.0),
            ("SP021", "Keo tản nhiệt Arctic MX-4 4g", "CAT_LK", "Tuýp", 15, 130000.0),
            ("SP022", "Màn hình LG 27 inch 4K IPS", "CAT_TB", "Chiếc", 3, 7900000.0),
            # 54 mặt hàng công nghệ thực tế từ bảng giá đối tác (danh_sach_san_pham_gia.xlsx):
            ("SP023", "iPhone 16 128GB", "CAT_DT", "Chiếc", 3, 20790000.0),
            ("SP024", "iPhone 15 128GB", "CAT_DT", "Chiếc", 3, 16990000.0),
            ("SP025", "iPhone 14 128GB", "CAT_DT", "Chiếc", 5, 13990000.0),
            ("SP026", "Samsung Galaxy S24", "CAT_DT", "Chiếc", 3, 18990000.0),
            ("SP027", "Samsung Galaxy A55 5G", "CAT_DT", "Chiếc", 5, 8990000.0),
            ("SP028", "Samsung Galaxy Z Fold6", "CAT_DT", "Chiếc", 3, 40990000.0),
            ("SP029", "Xiaomi 14", "CAT_DT", "Chiếc", 3, 15990000.0),
            ("SP030", "Xiaomi Redmi Note 13", "CAT_DT", "Chiếc", 5, 5490000.0),
            ("SP031", "Oppo Reno12", "CAT_DT", "Chiếc", 5, 9490000.0),
            ("SP032", "Oppo A79", "CAT_DT", "Chiếc", 5, 5990000.0),
            ("SP033", "Vivo V30", "CAT_DT", "Chiếc", 5, 10990000.0),
            ("SP034", "MacBook Air M3 13 inch", "CAT_LT", "Chiếc", 3, 27990000.0),
            ("SP035", "MacBook Pro M3 14 inch", "CAT_LT", "Chiếc", 3, 42990000.0),
            ("SP036", "Dell Inspiron 15 3520 i5", "CAT_LT", "Chiếc", 5, 14990000.0),
            ("SP037", "Dell XPS 13", "CAT_LT", "Chiếc", 3, 32990000.0),
            ("SP038", "Asus Vivobook 15 R5", "CAT_LT", "Chiếc", 5, 13990000.0),
            ("SP039", "Asus TUF Gaming F15", "CAT_LT", "Chiếc", 3, 19990000.0),
            ("SP040", "HP Pavilion 14", "CAT_LT", "Chiếc", 3, 15990000.0),
            ("SP041", "HP Envy x360", "CAT_LT", "Chiếc", 3, 22990000.0),
            ("SP042", "Lenovo ThinkPad E14", "CAT_LT", "Chiếc", 3, 16990000.0),
            ("SP043", "Lenovo Legion 5", "CAT_LT", "Chiếc", 3, 24990000.0),
            ("SP044", "Acer Aspire 5", "CAT_LT", "Chiếc", 5, 12990000.0),
            ("SP045", "Acer Nitro 5", "CAT_LT", "Chiếc", 3, 18990000.0),
            ("SP046", "PC Gaming Gigabyte i5 RTX4060", "CAT_PC", "Bộ", 3, 22990000.0),
            ("SP047", "PC Văn phòng Dell OptiPlex", "CAT_PC", "Bộ", 5, 10990000.0),
            ("SP048", "Mini PC Intel NUC", "CAT_PC", "Bộ", 5, 8990000.0),
            ("SP049", "iMac 24 inch M3", "CAT_PC", "Bộ", 3, 34990000.0),
            ("SP050", "Logitech M185", "CAT_PK", "Chiếc", 15, 250000.0),
            ("SP051", "Logitech G102", "CAT_PK", "Chiếc", 15, 350000.0),
            ("SP052", "Razer DeathAdder V2", "CAT_PK", "Chiếc", 8, 1290000.0),
            ("SP053", "Chuột không dây Rapoo M100", "CAT_PK", "Chiếc", 15, 180000.0),
            ("SP054", "Dell S2421H 24 inch", "CAT_TB", "Chiếc", 8, 2790000.0),
            ("SP055", "LG UltraGear 27GP850", "CAT_TB", "Chiếc", 5, 8990000.0),
            ("SP056", "Samsung Odyssey G5", "CAT_TB", "Chiếc", 5, 5990000.0),
            ("SP057", "ViewSonic VA2432", "CAT_TB", "Chiếc", 8, 2490000.0),
            ("SP058", "RAM Kingston 8GB DDR4", "CAT_LK", "Thanh", 15, 550000.0),
            ("SP059", "RAM Corsair Vengeance 16GB", "CAT_LK", "Thanh", 8, 1290000.0),
            ("SP060", "SSD Samsung 970 Evo 500GB", "CAT_LK", "Chiếc", 8, 1290000.0),
            ("SP061", "SSD WD Blue 1TB", "CAT_LK", "Chiếc", 8, 1490000.0),
            ("SP062", "Bàn phím cơ Akko 3068", "CAT_PK", "Chiếc", 15, 990000.0),
            ("SP063", "Bàn phím Newmen GM610", "CAT_PK", "Chiếc", 15, 450000.0),
            ("SP064", "Tai nghe Sony WH-1000XM5", "CAT_PK", "Chiếc", 5, 8490000.0),
            ("SP065", "Tai nghe JBL Tune 510BT", "CAT_PK", "Chiếc", 15, 990000.0),
            ("SP066", "Sạc dự phòng Anker 10000mAh", "CAT_PK", "Củ", 15, 590000.0),
            ("SP067", "Sạc dự phòng Xiaomi 20000mAh", "CAT_PK", "Củ", 15, 490000.0),
            ("SP068", "Cáp sạc USB-C to USB-C", "CAT_PK", "Sợi", 15, 190000.0),
            ("SP069", "Cáp sạc Lightning chính hãng Apple", "CAT_PK", "Sợi", 15, 490000.0),
            ("SP070", "Sạc nhanh 20W Apple", "CAT_PK", "Củ", 15, 590000.0),
            ("SP071", "Ốp lưng iPhone 16 silicon", "CAT_PK", "Cái", 15, 990000.0),
            ("SP072", "Túi chống sốc laptop 15.6 inch", "CAT_PK", "Cái", 15, 250000.0),
            ("SP073", "USB Kingston 64GB", "CAT_LK", "Chiếc", 15, 150000.0),
            ("SP074", "Thẻ nhớ SanDisk 128GB", "CAT_LK", "Thẻ", 15, 350000.0),
            ("SP075", "Webcam Logitech C270", "CAT_PK", "Chiếc", 15, 650000.0),
            ("SP076", "Loa Bluetooth JBL Go 3", "CAT_TB", "Chiếc", 15, 690000.0),
        ]

        prod_map = {}
        for code, name, cat_code, unit, min_stock, price in products_meta:
            p = db.query(Product).filter(Product.code == code).first()
            if not p:
                p = Product(
                    code=code,
                    name=name,
                    category_id=cat_map[cat_code].id,
                    unit=unit,
                    min_stock=min_stock,
                    current_stock=0,  # Sẽ được tính chính xác qua các giao dịch
                    standard_price=price,
                    image_url=f"/static/products/{code}.jpg",
                    status="ACTIVE",
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            else:
                p.name = name
                p.standard_price = price
                p.unit = unit
                p.min_stock = min_stock
                if not p.image_url:
                    p.image_url = f"/static/products/{code}.jpg"
                db.commit()
            prod_map[code] = p

        # =====================================================================
        # 5. SINH LỊCH SỬ GIAO DỊCH 60 NGÀY (NHẬP - XUẤT - THẺ KHO)
        # =====================================================================
        print("[INFO] 5. Sinh chuoi giao dich nhap xuat 60 ngay theo kich ban logic...")
        now = datetime.now()

        # Nạp giao dịch khởi tạo cho 54 mặt hàng mới từ Excel (nếu chưa có)
        seed_xlsx_transactions(db, prod_map, sup_map, thukho_user, now)

        # Kiểm tra nếu đã có phiếu nhập của SP001 thì bỏ qua bước sinh giao dịch để tránh nhân đôi
        existing_import = (
            db.query(ImportNote).filter(ImportNote.code == "PN-SEED-INIT-01").first()
        )
        if existing_import:
            print("[INFO] Du lieu giao dich 60 ngay ban dau da ton tai, hoan tat cap nhat!")
            return

        # -------------------------------------------------------------
        # Đợt 1: Nhập kho ban đầu (Cách đây 55 ngày)
        # -------------------------------------------------------------
        init_date = now - timedelta(days=55)
        imp1 = ImportNote(
            code="PN-SEED-INIT-01",
            supplier_id=sup_map["NCC_VIENDONG"].id,
            created_by=thukho_user.id,
            note_date=init_date,
            total_amount=0.0,
            status="COMPLETED",
            note="Nhập kho kiện hàng thiết bị và linh kiện đợt 1",
        )
        db.add(imp1)
        db.flush()

        import_quantities = {
            "SP001": 50,  # Nhập 50 bàn phím
            "SP002": 80,  # Nhập 80 chuột
            "SP003": 60,  # Nhập 60 cáp (Hàng chết: sẽ giữ nguyên 60 chiếc, 0 xuất)
            "SP004": 15,
            "SP005": 30,
            "SP006": 40,
            "SP007": 20,
            "SP008": 25,
            "SP009": 18,
            "SP010": 22,
            "SP011": 15,
            "SP012": 12,
            "SP013": 20,
            "SP014": 15,
            "SP015": 30,
            "SP016": 50,
            "SP017": 60,
            "SP018": 45,
            "SP019": 25,
            "SP020": 35,
            "SP021": 40,
            "SP022": 8,
        }

        total_imp1_amount = 0.0
        for code, qty in import_quantities.items():
            p = prod_map[code]
            unit_price = p.standard_price * 0.75  # Giá nhập khoảng 75% giá chuẩn
            subtotal = unit_price * qty
            total_imp1_amount += subtotal

            # Chi tiết phiếu nhập
            db.add(
                ImportNoteDetail(
                    import_note_id=imp1.id,
                    product_id=p.id,
                    quantity=qty,
                    unit_price=unit_price,
                    subtotal=subtotal,
                )
            )
            # Tăng tồn kho
            p.current_stock += qty

            # Ghi thẻ kho
            db.add(
                StockLedger(
                    product_id=p.id,
                    transaction_type="IMPORT",
                    reference_code=imp1.code,
                    quantity_change=qty,
                    balance_after=p.current_stock,
                    created_by=thukho_user.id,
                    transaction_date=init_date,
                    note="Nhập hàng khởi đầu đợt 1",
                )
            )

        imp1.total_amount = total_imp1_amount
        db.commit()

        # -------------------------------------------------------------
        # Đợt 2: Các giao dịch xuất hàng bình thường (Từ ngày 45 đến ngày 10 trước)
        # -------------------------------------------------------------
        customers = [
            "Công ty CP Truyền Thông Alpha",
            "Trường Đại học Công nghệ FPT",
            "Văn phòng Luật sư Nhân Đức",
            "Cửa hàng Tin học Nguyễn Kim",
            "Hệ thống Phòng Net CyberCore",
        ]

        # Kịch bản xuất cho SP001: Xuất 46 cái trong 30 ngày qua để tồn kho còn đúng 4 chiếc (4 < min_stock 15)
        # Xuất rải rác:
        p1 = prod_map["SP001"]
        export_dates_sp1 = [
            (now - timedelta(days=28), 10),
            (now - timedelta(days=20), 12),
            (now - timedelta(days=12), 14),
            (now - timedelta(days=4), 10),
        ]
        for idx, (exp_date, exp_qty) in enumerate(export_dates_sp1, start=1):
            exp_note = ExportNote(
                code=f"PX-SEED-SP1-0{idx}",
                recipient_name=random.choice(customers),
                created_by=thukho_user.id,
                note_date=exp_date,
                total_amount=p1.standard_price * exp_qty,
                status="COMPLETED",
                note=f"Xuất bán bàn phím Akko đợt {idx}",
            )
            db.add(exp_note)
            db.flush()
            db.add(
                ExportNoteDetail(
                    export_note_id=exp_note.id,
                    product_id=p1.id,
                    quantity=exp_qty,
                    unit_price=p1.standard_price,
                    subtotal=p1.standard_price * exp_qty,
                )
            )
            p1.current_stock -= exp_qty
            db.add(
                StockLedger(
                    product_id=p1.id,
                    transaction_type="EXPORT",
                    reference_code=exp_note.code,
                    quantity_change=-exp_qty,
                    balance_after=p1.current_stock,
                    created_by=thukho_user.id,
                    transaction_date=exp_date,
                    note=f"Xuất bán đơn lẻ đợt {idx}",
                )
            )

        # Kịch bản xuất cho SP002 (Chuột Logitech G304):
        # 30 ngày trước: xuất chỉ 5 chiếc
        # Trong 5 ngày gần đây: xuất đột biến 20 chiếc (ngày -3) và 15 chiếc (ngày -1) -> Tổng 35 chiếc tuần này!
        p2 = prod_map["SP002"]
        # Xuất bình thường trước đó
        exp_old = ExportNote(
            code="PX-SEED-SP2-OLD",
            recipient_name="Văn phòng Luật sư Nhân Đức",
            created_by=thukho_user.id,
            note_date=now - timedelta(days=25),
            total_amount=p2.standard_price * 5,
            status="COMPLETED",
            note="Xuất chuột Logitech thường kỳ",
        )
        db.add(exp_old)
        db.flush()
        db.add(ExportNoteDetail(export_note_id=exp_old.id, product_id=p2.id, quantity=5, unit_price=p2.standard_price, subtotal=p2.standard_price * 5))
        p2.current_stock -= 5
        db.add(StockLedger(product_id=p2.id, transaction_type="EXPORT", reference_code=exp_old.code, quantity_change=-5, balance_after=p2.current_stock, created_by=thukho_user.id, transaction_date=now - timedelta(days=25)))

        # Xuất đột biến tuần gần nhất
        surge_exports = [
            (now - timedelta(days=3), 20, "Trường Đại học Công nghệ FPT (Trang bị phòng máy mới)"),
            (now - timedelta(days=1), 15, "Hệ thống Phòng Net CyberCore (Thay thế toàn bộ dàn chuột)"),
        ]
        for idx, (s_date, s_qty, s_reason) in enumerate(surge_exports, start=1):
            s_note = ExportNote(
                code=f"PX-SEED-SURGE-0{idx}",
                recipient_name=s_reason.split(" (")[0],
                created_by=thukho_user.id,
                note_date=s_date,
                total_amount=p2.standard_price * s_qty,
                status="COMPLETED",
                note=s_reason,
            )
            db.add(s_note)
            db.flush()
            db.add(ExportNoteDetail(export_note_id=s_note.id, product_id=p2.id, quantity=s_qty, unit_price=p2.standard_price, subtotal=p2.standard_price * s_qty))
            p2.current_stock -= s_qty
            db.add(StockLedger(product_id=p2.id, transaction_type="EXPORT", reference_code=s_note.code, quantity_change=-s_qty, balance_after=p2.current_stock, created_by=thukho_user.id, transaction_date=s_date, note="Xuất đột biến quy mô lớn"))

        # Kịch bản SP003: TUYỆT ĐỐI KHÔNG CÓ PHIẾU XUẤT NÀO! (Tồn nguyên 60 chiếc sau 55 ngày -> DEAD STOCK)

        # Xuất rải rác một số mặt hàng khác để dữ liệu phong phú
        other_skus = ["SP004", "SP005", "SP006", "SP007", "SP010", "SP016", "SP017"]
        for idx, sku in enumerate(other_skus, start=1):
            item = prod_map[sku]
            qty_out = min(item.current_stock // 3, 5)
            if qty_out > 0:
                e_date = now - timedelta(days=random.randint(5, 40))
                e_note = ExportNote(
                    code=f"PX-SEED-GEN-{idx:02d}",
                    recipient_name=random.choice(customers),
                    created_by=thukho_user.id,
                    note_date=e_date,
                    total_amount=item.standard_price * qty_out,
                    status="COMPLETED",
                    note=f"Xuất hàng thương mại {item.name}",
                )
                db.add(e_note)
                db.flush()
                db.add(ExportNoteDetail(export_note_id=e_note.id, product_id=item.id, quantity=qty_out, unit_price=item.standard_price, subtotal=item.standard_price * qty_out))
                item.current_stock -= qty_out
                db.add(StockLedger(product_id=item.id, transaction_type="EXPORT", reference_code=e_note.code, quantity_change=-qty_out, balance_after=item.current_stock, created_by=thukho_user.id, transaction_date=e_date))

        db.commit()
        print("[SUCCESS] Hoan tat nap du lieu mau 60 ngay thanh cong!")
        print(f"   - SP001 (Ban chay): Ton hien tai = {prod_map['SP001'].current_stock} (Min: {prod_map['SP001'].min_stock})")
        print(f"   - SP002 (Dot bien): Ton hien tai = {prod_map['SP002'].current_stock} (Da xuat 35 chiec tuan nay)")
        print(f"   - SP003 (Ton chet): Ton hien tai = {prod_map['SP003'].current_stock} (0 giao dich xuat trong 55 ngay)")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Loi khi nap du lieu: {e}")
        raise
    finally:
        db.close()



if __name__ == "__main__":
    seed_database()
