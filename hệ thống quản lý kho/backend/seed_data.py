"""Script nạp lại toàn bộ dữ liệu mẫu thực tế 5 tháng (150 ngày - Storytelling Enterprise Seed Data).

Bối cảnh hệ thống:
- Hệ thống Kho Công Nghệ WMS AI đã vận hành ổn định liên tục 5 tháng (từ 20/05/2026 đến 20/10/2026).
- 3 tài khoản người dùng chuẩn 3 vai trò:
  + admin / admin123 (Quản Trị Viên)
  + thukho / thukho123 (Thủ Kho Chính)
  + ketoan / ketoan123 (Kế Toán Kho)
- 7 nhóm hàng (Categories) & 10 nhà cung cấp đối tác uy tín (Suppliers).
- 76 sản phẩm công nghệ thực tế (Điện thoại, Laptop, PC, Màn hình, Linh kiện, Phụ kiện, Thiết bị mạng).
- Chuỗi giao dịch 5 tháng liên tục (Tháng 5 -> Tháng 10/2026):
  + Tháng 5/2026: Khởi tạo kho, đại nhập hàng khai trương từ các hãng lớn và các đơn xuất đầu tiên.
  + Tháng 6/2026: Vận hành luân chuyển đều đặn mùa hè (văn phòng, trường học).
  + Tháng 7/2026: Cung ứng phụ kiện, linh kiện nâng cấp, bảo dưỡng phòng net, doanh nghiệp.
  + Tháng 8/2026: Đợt cao điểm "Back to School" (nhập lượng lớn laptop, bàn phím, chuột; xuất kho mạnh).
  + Tháng 9/2026: Đợt mở bán iPhone 16 series, linh kiện PC Gaming, xuất bán đại lý.
  + Tháng 10/2026 (01/10 đến 20/10/2026 - hiện tại):
    * SP001 (Bàn phím Akko): Bán rất chạy qua 5 tháng, hiện tồn cạn kiệt (4/15) -> AI đề xuất nhập khẩn cấp (HIGH).
    * SP002 (Chuột Logitech G304): Bán đều, đột nhiên tuần qua (17-19/10) xuất 35 chiếc -> AI báo động SURGE_EXPORT (>200%).
    * SP003 (Cáp VGA to HDMI): Tồn 60 sợi suốt 5 tháng (153 ngày) không xuất đơn nào -> AI cảnh báo DEAD_STOCK.
    * SP005, SP023, SP036, SP050: Tồn cận mức tối thiểu để gợi ý nhập đa dạng các phân khúc.
- Bảo toàn tuyệt đối số dư Thẻ kho (StockLedger) chuẩn ACID, không bao giờ để tồn âm.
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
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


def seed_database():
    print("===============================================================================")
    print("     BẮT ĐẦU NẠP DỮ LIỆU MẪU ENTERPRISE 5 THÁNG HOẠT ĐỘNG LIÊN TỤC (WMS AI)")
    print("===============================================================================")
    random.seed(42)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # =====================================================================
        # 1. TÀI KHOẢN NGƯỜI DÙNG (3 ROLES)
        # =====================================================================
        print("[INFO] 1. Kiểm tra và khởi tạo tài khoản người dùng...")
        users_data = [
            ("admin", "admin123", "Quản Trị Viên Hệ Thống", "ADMIN"),
            ("thukho", "thukho123", "Nguyễn Văn Kho (Thủ kho Chính)", "WAREHOUSE_KEEPER"),
            ("ketoan", "ketoan123", "Trần Thị Toán (Kế toán Kho)", "ACCOUNTANT"),
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
            else:
                user.full_name = full_name
                user.role = role
                user.is_active = True
                db.commit()
            user_map[username] = user

        admin_user = user_map["admin"]
        thukho_user = user_map["thukho"]

        # =====================================================================
        # 2. NHÓM HÀNG (CATEGORIES)
        # =====================================================================
        print("[INFO] 2. Kiểm tra danh mục hàng hóa...")
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
        print("[INFO] 3. Kiểm tra nhà cung cấp đối tác...")
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
        # 4. DANH SÁCH 76 MẶT HÀNG (PRODUCTS)
        # =====================================================================
        print("[INFO] 4. Khởi tạo 76 sản phẩm công nghệ chuẩn...")
        products_meta = [
            ("SP001", "Bàn phím cơ Akko 3087", "CAT_PK", "Chiếc", 15, 950000.0),
            ("SP002", "Chuột không dây Logitech G304", "CAT_PK", "Chiếc", 10, 750000.0),
            ("SP003", "Cáp chuyển đổi VGA to HDMI", "CAT_PK", "Sợi", 5, 85000.0),
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

        # Xóa các giao dịch cũ để chuẩn hóa lại chuỗi 5 tháng
        print("[INFO] Dọn dẹp các giao dịch cũ để tái lập chuỗi 5 tháng đồng bộ ACID...")
        db.query(StockLedger).delete()
        db.query(ExportNoteDetail).delete()
        db.query(ExportNote).delete()
        db.query(ImportNoteDetail).delete()
        db.query(ImportNote).delete()

        # Dọn các mã test ngoài danh mục SP
        db.query(Product).filter(~Product.code.startswith("SP")).delete(synchronize_session=False)
        db.commit()

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
                    current_stock=0,
                    standard_price=price,
                    image_url=f"/static/products/{code}.jpg",
                    status="ACTIVE",
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            else:
                p.name = name
                p.category_id = cat_map[cat_code].id
                p.standard_price = price
                p.unit = unit
                p.min_stock = min_stock
                p.current_stock = 0  # Sẽ được tính lại chuẩn xác qua từng phiếu nhập/xuất
                p.status = "ACTIVE"
                if not p.image_url:
                    p.image_url = f"/static/products/{code}.jpg"
                db.commit()
            prod_map[code] = p

        # =====================================================================
        # 5. MÔ PHỎNG VẬN HÀNH DOANH NGHIỆP 5 THÁNG (20/05/2026 -> 20/10/2026)
        # =====================================================================
        print("[INFO] 5. Bắt đầu sinh chuỗi dữ liệu giao dịch thực tế 5 tháng...")

        customers = [
            "Trường Đại học Công nghệ FPT",
            "Hệ thống CyberCore Gaming Stadium",
            "Công ty Cổ phần Truyền thông & Công nghệ Alpha",
            "Văn phòng Luật sư Nhân Đức",
            "Cửa hàng Bán lẻ Tin học Nguyễn Kim",
            "Ngân hàng TMCP Phương Nam (Chi nhánh số 3)",
            "Công ty Cổ phần Phần mềm VTI Solutions",
            "Viện Đào tạo Quốc tế Kent",
            "Chuỗi Cafe Công nghệ The Workshop",
            "Tập đoàn Bất động sản Đất Việt",
            "Công ty TNHH Kỹ thuật Cơ điện Sao Việt",
            "Khách hàng Bán lẻ & Đối tác Doanh nghiệp",
            "Khách hàng Đặt hàng Online (Giao nhanh)",
        ]

        events = []

        def record_import(code: str, sup_code: str, note_date: datetime, items: list, note_text: str, status: str = "COMPLETED"):
            events.append({
                "type": "IMPORT",
                "code": code,
                "sup_code": sup_code,
                "note_date": note_date,
                "items": items,
                "note_text": note_text,
                "status": status,
            })

        def record_export(code: str, recipient: str, note_date: datetime, items: list, note_text: str, status: str = "COMPLETED"):
            events.append({
                "type": "EXPORT",
                "code": code,
                "recipient": recipient,
                "note_date": note_date,
                "items": items,
                "note_text": note_text,
                "status": status,
            })

        # ---------------------------------------------------------------------
        # THÁNG 5/2026: ĐẠI NHẬP KHO KHAI TRƯƠNG & XUẤT ĐƠN ĐẦU TIÊN
        # ---------------------------------------------------------------------
        print("  -> Đang sinh dữ liệu Tháng 05/2026...")
        # Lô 1: FPT Shop (Điện thoại, Laptop, iMac)
        imp_items_05_1 = []
        for i in range(23, 50):
            sku = f"SP{i:03d}"
            p = prod_map[sku]
            qty = 10 if p.standard_price >= 20000000 else 18
            imp_items_05_1.append((sku, qty, round(p.standard_price * 0.78, -3)))
        record_import("PN-202605-001", "NCC_FPTSHOP", datetime(2026, 5, 20, 8, 30), imp_items_05_1, "Nhập kiện hàng công nghệ cao cấp FPT Shop đợt khai trương")

        # Lô 2: Viễn Đông (Linh kiện, Bàn phím Akko, Chuột G304, Cáp VGA HDMI)
        imp_items_05_2 = [
            ("SP001", 50, 710000.0),  # Bàn phím Akko: Nhập ban đầu 50 cái
            ("SP002", 80, 560000.0),  # Chuột G304: Nhập ban đầu 80 cái
            ("SP003", 60, 60000.0),   # Cáp VGA to HDMI: Nhập 60 sợi (Sẽ giữ nguyên không xuất)
        ]
        for i in range(4, 23):
            sku = f"SP{i:03d}"
            p = prod_map[sku]
            qty = 25 if p.standard_price >= 2000000 else 45
            imp_items_05_2.append((sku, qty, round(p.standard_price * 0.75, -3)))
        record_import("PN-202605-002", "NCC_VIENDONG", datetime(2026, 5, 21, 9, 15), imp_items_05_2, "Nhập kho linh kiện PC, gaming gear & phụ kiện Viễn Đông")

        # Lô 3: Phong Vũ (Phụ kiện, màn hình, tai nghe SP050 -> SP076)
        imp_items_05_3 = []
        for i in range(50, 77):
            sku = f"SP{i:03d}"
            p = prod_map[sku]
            qty = 20 if p.standard_price >= 2000000 else 40
            imp_items_05_3.append((sku, qty, round(p.standard_price * 0.76, -3)))
        record_import("PN-202605-003", "NCC_PHONGVU", datetime(2026, 5, 22, 14, 0), imp_items_05_3, "Nhập kiện thiết bị ngoại vi, màn hình đồ họa Phong Vũ")

        # Xuất hàng cuối tháng 5 (5 phiếu xuất)
        record_export("PX-202605-001", "Cửa hàng Bán lẻ Tin học Nguyễn Kim", datetime(2026, 5, 24, 10, 0), [
            ("SP001", 6), ("SP002", 4), ("SP017", 8), ("SP050", 5), ("SP027", 2)
        ], "Xuất cung ứng đại lý Nguyễn Kim đợt 1")

        record_export("PX-202605-002", "Công ty Cổ phần Truyền thông & Công nghệ Alpha", datetime(2026, 5, 26, 15, 30), [
            ("SP004", 4), ("SP005", 5), ("SP006", 6), ("SP036", 3), ("SP047", 2)
        ], "Trang bị phòng làm việc bộ phận Media & Kỹ thuật")

        record_export("PX-202605-003", "Trường Đại học Công nghệ FPT", datetime(2026, 5, 28, 11, 20), [
            ("SP001", 4), ("SP002", 3), ("SP007", 3), ("SP008", 4), ("SP016", 15)
        ], "Bổ sung thiết bị phòng lab mạng sinh viên")

        record_export("PX-202605-004", "Văn phòng Luật sư Nhân Đức", datetime(2026, 5, 29, 16, 45), [
            ("SP036", 2), ("SP017", 4), ("SP020", 3), ("SP073", 5)
        ], "Cung cấp laptop & phụ kiện văn phòng công chứng")

        record_export("PX-202605-005", "Khách hàng Bán lẻ & Đối tác Doanh nghiệp", datetime(2026, 5, 31, 17, 0), [
            ("SP023", 2), ("SP034", 1), ("SP010", 3), ("SP066", 4)
        ], "Đơn bán lẻ & khách hàng doanh nghiệp cuối tháng")

        # ---------------------------------------------------------------------
        # THÁNG 6/2026: VẬN HÀNH ĐỀU ĐẶN ĐẦU HÈ
        # ---------------------------------------------------------------------
        print("  -> Đang sinh dữ liệu Tháng 06/2026...")
        record_import("PN-202606-001", "NCC_ACHAU", datetime(2026, 6, 5, 9, 0), [
            ("SP007", 15, 940000.0), ("SP008", 20, 340000.0), ("SP012", 10, 1010000.0), ("SP016", 50, 48000.0)
        ], "Nhập bổ sung thiết bị mạng cáp quang Á Châu")

        record_import("PN-202606-002", "NCC_CELLPHONES", datetime(2026, 6, 14, 10, 30), [
            ("SP066", 25, 440000.0), ("SP067", 20, 370000.0), ("SP068", 40, 140000.0), ("SP070", 30, 440000.0)
        ], "Nhập phụ kiện sạc nhanh & pin dự phòng CellphoneS")

        record_import("PN-202606-003", "NCC_ANPHAT", datetime(2026, 6, 22, 14, 15), [
            ("SP005", 20, 1650000.0), ("SP006", 25, 860000.0), ("SP011", 15, 1050000.0), ("SP015", 20, 285000.0)
        ], "Nhập bổ sung linh kiện nâng cấp PC An Phát")

        # 12 phiếu xuất tháng 6
        for day, cust, p1_qty, p2_qty in [
            (2, "Hệ thống CyberCore Gaming Stadium", 4, 2),
            (5, "Công ty Cổ phần Phần mềm VTI Solutions", 3, 2),
            (7, "Ngân hàng TMCP Phương Nam (Chi nhánh số 3)", 0, 1),
            (10, "Cửa hàng Bán lẻ Tin học Nguyễn Kim", 3, 2),
            (13, "Viện Đào tạo Quốc tế Kent", 2, 1),
            (16, "Công ty Cổ phần Truyền thông & Công nghệ Alpha", 3, 1),
            (19, "Chuỗi Cafe Công nghệ The Workshop", 0, 1),
            (22, "Tập đoàn Bất động sản Đất Việt", 0, 0),
            (24, "Trường Đại học Công nghệ FPT", 0, 0),
            (26, "Khách hàng Đặt hàng Online (Giao nhanh)", 0, 0),
            (28, "Công ty TNHH Kỹ thuật Cơ điện Sao Việt", 0, 0),
            (30, "Khách hàng Bán lẻ & Đối tác Doanh nghiệp", 0, 0),
        ]:
            exp_code = f"PX-202606-{day:02d}"
            exp_items = []
            if p1_qty > 0:
                exp_items.append(("SP001", p1_qty))
            if p2_qty > 0:
                exp_items.append(("SP002", p2_qty))
            # Thêm ngẫu nhiên một số sản phẩm khác
            exp_items.extend([
                (f"SP{random.randint(4, 22):03d}", random.randint(1, 3)),
                (f"SP{random.randint(23, 49):03d}", random.randint(1, 2)),
                (f"SP{random.randint(50, 76):03d}", random.randint(2, 5)),
            ])
            record_export(exp_code, cust, datetime(2026, 6, day, random.randint(9, 16), random.randint(10, 50)), exp_items, f"Xuất kho định kỳ ngày {day:02d}/06")

        # ---------------------------------------------------------------------
        # THÁNG 7/2026: NÂNG CẤP VÀ DUY TRÌ HỆ THỐNG
        # ---------------------------------------------------------------------
        print("  -> Đang sinh dữ liệu Tháng 07/2026...")
        record_import("PN-202607-001", "NCC_GEARVN", datetime(2026, 7, 4, 8, 45), [
            ("SP010", 15, 1390000.0), ("SP051", 25, 260000.0), ("SP052", 15, 970000.0), ("SP055", 8, 6740000.0)
        ], "Nhập thiết bị Gaming Gear & Màn hình GearVN")

        record_import("PN-202607-002", "NCC_SAIGON", datetime(2026, 7, 16, 11, 0), [
            ("SP004", 12, 4125000.0), ("SP017", 40, 68000.0), ("SP018", 35, 90000.0), ("SP020", 25, 120000.0)
        ], "Nhập thiết bị ngoại vi văn phòng Tổng đại lý Sài Gòn")

        record_import("PN-202607-003", "NCC_TGDD", datetime(2026, 7, 26, 15, 15), [
            ("SP025", 8, 10910000.0), ("SP027", 10, 7010000.0), ("SP030", 12, 4280000.0), ("SP032", 10, 4670000.0)
        ], "Nhập điện thoại thông minh phổ thông Thế Giới Di Động")

        # 14 phiếu xuất tháng 7
        for day, cust, p1_qty, p2_qty in [
            (3, "Hệ thống CyberCore Gaming Stadium", 3, 2),
            (5, "Công ty Cổ phần Phần mềm VTI Solutions", 2, 2),
            (8, "Cửa hàng Bán lẻ Tin học Nguyễn Kim", 3, 1),
            (11, "Trường Đại học Công nghệ FPT", 2, 1),
            (14, "Công ty Cổ phần Truyền thông & Công nghệ Alpha", 2, 1),
            (17, "Ngân hàng TMCP Phương Nam (Chi nhánh số 3)", 0, 1),
            (19, "Văn phòng Luật sư Nhân Đức", 1, 0),
            (21, "Viện Đào tạo Quốc tế Kent", 1, 1),
            (23, "Khách hàng Bán lẻ & Đối tác Doanh nghiệp", 1, 0),
            (25, "Chuỗi Cafe Công nghệ The Workshop", 0, 0),
            (27, "Tập đoàn Bất động sản Đất Việt", 0, 0),
            (29, "Công ty TNHH Kỹ thuật Cơ điện Sao Việt", 0, 0),
            (30, "Khách hàng Đặt hàng Online (Giao nhanh)", 0, 0),
            (31, "Cửa hàng Bán lẻ Tin học Nguyễn Kim", 0, 0),
        ]:
            exp_code = f"PX-202607-{day:02d}"
            exp_items = []
            if p1_qty > 0:
                exp_items.append(("SP001", p1_qty))
            if p2_qty > 0:
                exp_items.append(("SP002", p2_qty))
            exp_items.extend([
                (f"SP{random.randint(4, 22):03d}", random.randint(1, 4)),
                (f"SP{random.randint(23, 49):03d}", random.randint(1, 2)),
                (f"SP{random.randint(50, 76):03d}", random.randint(2, 6)),
            ])
            record_export(exp_code, cust, datetime(2026, 7, day, random.randint(9, 16), random.randint(10, 50)), exp_items, f"Xuất kho định kỳ ngày {day:02d}/07")

        # ---------------------------------------------------------------------
        # THÁNG 8/2026: ĐỢT CAO ĐIỂM "BACK TO SCHOOL" (MÙA TỰU TRƯỜNG)
        # ---------------------------------------------------------------------
        print("  -> Đang sinh dữ liệu Tháng 08/2026 (Mùa Tựu Trường Back to School)...")
        # Nhập lớn đợt tựu trường: SP001 nhập thêm 30 chiếc, SP002 nhập thêm 60 chiếc
        record_import("PN-202608-001", "NCC_VIENDONG", datetime(2026, 8, 2, 8, 30), [
            ("SP001", 30, 710000.0),  # Nhập thêm 30 bàn phím Akko
            ("SP002", 60, 560000.0),  # Nhập thêm 60 chuột Logitech G304
            ("SP005", 25, 1650000.0),
            ("SP006", 30, 860000.0),
        ], "Đại nhập hàng phụ kiện & linh kiện Viễn Đông đón mùa tựu trường")

        record_import("PN-202608-002", "NCC_FPTSHOP", datetime(2026, 8, 8, 10, 0), [
            ("SP034", 8, 21830000.0), ("SP036", 15, 11690000.0), ("SP038", 12, 10910000.0), ("SP044", 15, 10130000.0)
        ], "Nhập đợt lớn Laptop sinh viên & nhân viên văn phòng FPT Shop")

        record_import("PN-202608-003", "NCC_PHONGVU", datetime(2026, 8, 16, 13, 45), [
            ("SP004", 15, 4125000.0), ("SP054", 20, 2090000.0), ("SP057", 20, 1860000.0), ("SP017", 50, 68000.0)
        ], "Nhập màn hình học tập và chuột văn phòng giá rẻ Phong Vũ")

        record_import("PN-202608-004", "NCC_ANPHAT", datetime(2026, 8, 25, 15, 0), [
            ("SP046", 6, 17930000.0), ("SP047", 10, 8570000.0), ("SP048", 10, 7010000.0), ("SP011", 15, 1050000.0)
        ], "Nhập PC Gaming & PC Văn phòng đồng bộ An Phát")

        # 16 phiếu xuất tháng 8 (Doanh số xuất bán tăng mạnh)
        for day, cust, p1_qty, p2_qty in [
            (2, "Trường Đại học Công nghệ FPT", 3, 2),
            (4, "Viện Đào tạo Quốc tế Kent", 2, 2),
            (6, "Cửa hàng Bán lẻ Tin học Nguyễn Kim", 2, 1),
            (9, "Công ty Cổ phần Phần mềm VTI Solutions", 2, 1),
            (12, "Hệ thống CyberCore Gaming Stadium", 2, 1),
            (14, "Công ty Cổ phần Truyền thông & Công nghệ Alpha", 1, 1),
            (17, "Ngân hàng TMCP Phương Nam (Chi nhánh số 3)", 0, 1),
            (19, "Văn phòng Luật sư Nhân Đức", 1, 0),
            (21, "Tập đoàn Bất động sản Đất Việt", 1, 0),
            (23, "Chuỗi Cafe Công nghệ The Workshop", 1, 1),
            (25, "Khách hàng Bán lẻ & Đối tác Doanh nghiệp", 1, 0),
            (27, "Khách hàng Đặt hàng Online (Giao nhanh)", 1, 0),
            (28, "Cửa hàng Bán lẻ Tin học Nguyễn Kim", 1, 0),
            (29, "Trường Đại học Công nghệ FPT", 0, 0),
            (30, "Công ty TNHH Kỹ thuật Cơ điện Sao Việt", 0, 0),
            (31, "Khách hàng Bán lẻ & Đối tác Doanh nghiệp", 0, 0),
        ]:
            exp_code = f"PX-202608-{day:02d}"
            exp_items = []
            if p1_qty > 0:
                exp_items.append(("SP001", p1_qty))
            if p2_qty > 0:
                exp_items.append(("SP002", p2_qty))
            exp_items.extend([
                (f"SP{random.randint(4, 22):03d}", random.randint(2, 5)),
                (f"SP{random.randint(23, 49):03d}", random.randint(1, 3)),
                (f"SP{random.randint(50, 76):03d}", random.randint(3, 8)),
            ])
            record_export(exp_code, cust, datetime(2026, 8, day, random.randint(9, 16), random.randint(10, 50)), exp_items, f"Xuất kho phục vụ mùa tựu trường ngày {day:02d}/08")

        # ---------------------------------------------------------------------
        # THÁNG 9/2026: MÙA CÔNG NGHỆ THU 2026
        # ---------------------------------------------------------------------
        print("  -> Đang sinh dữ liệu Tháng 09/2026 (Mùa Công Nghệ Thu 2026)...")
        record_import("PN-202609-001", "NCC_FPTSHOP", datetime(2026, 9, 5, 9, 30), [
            ("SP023", 10, 16210000.0), ("SP024", 8, 13250000.0), ("SP028", 5, 31970000.0), ("SP029", 8, 12470000.0)
        ], "Nhập thiết bị điện thoại cao cấp mùa thu FPT Shop")

        record_import("PN-202609-002", "NCC_CELLPHONES", datetime(2026, 9, 14, 11, 15), [
            ("SP068", 30, 140000.0), ("SP069", 25, 380000.0), ("SP070", 25, 460000.0), ("SP071", 30, 770000.0)
        ], "Nhập ốp lưng và phụ kiện chính hãng Apple CellphoneS")

        record_import("PN-202609-003", "NCC_GEARVN", datetime(2026, 9, 21, 14, 0), [
            ("SP046", 5, 17930000.0), ("SP039", 6, 15590000.0), ("SP043", 5, 19490000.0), ("SP055", 6, 7010000.0)
        ], "Nhập PC Gaming và Laptop đồ họa GearVN")

        # 16 phiếu xuất tháng 9
        for day, cust, p1_qty, p2_qty in [
            (2, "Cửa hàng Bán lẻ Tin học Nguyễn Kim", 2, 1),
            (4, "Công ty Cổ phần Truyền thông & Công nghệ Alpha", 2, 1),
            (7, "Hệ thống CyberCore Gaming Stadium", 2, 1),
            (10, "Trường Đại học Công nghệ FPT", 1, 1),
            (13, "Công ty Cổ phần Phần mềm VTI Solutions", 1, 1),
            (16, "Viện Đào tạo Quốc tế Kent", 1, 1),
            (18, "Ngân hàng TMCP Phương Nam (Chi nhánh số 3)", 1, 1),
            (21, "Chuỗi Cafe Công nghệ The Workshop", 1, 1),
            (24, "Văn phòng Luật sư Nhân Đức", 1, 0),
            (26, "Tập đoàn Bất động sản Đất Việt", 0, 0),
            (27, "Khách hàng Bán lẻ & Đối tác Doanh nghiệp", 0, 0),
            (28, "Công ty TNHH Kỹ thuật Cơ điện Sao Việt", 0, 0),
            (29, "Khách hàng Đặt hàng Online (Giao nhanh)", 0, 0),
            (30, "Cửa hàng Bán lẻ Tin học Nguyễn Kim", 0, 0),
        ]:
            exp_code = f"PX-202609-{day:02d}"
            exp_items = []
            if p1_qty > 0:
                exp_items.append(("SP001", p1_qty))
            if p2_qty > 0:
                exp_items.append(("SP002", p2_qty))
            exp_items.extend([
                (f"SP{random.randint(4, 22):03d}", random.randint(1, 3)),
                (f"SP{random.randint(23, 49):03d}", random.randint(1, 2)),
                (f"SP{random.randint(50, 76):03d}", random.randint(2, 5)),
            ])
            record_export(exp_code, cust, datetime(2026, 9, day, random.randint(9, 16), random.randint(10, 50)), exp_items, f"Xuất hàng bán tháng 9 ngày {day:02d}/09")

        # ---------------------------------------------------------------------
        # THÁNG 10/2026 (01/10 ĐẾN 20/10/2026 - THÁNG HIỆN HÀNH): TẠO CÁC TÌNH HUỐNG AI
        # ---------------------------------------------------------------------
        print("  -> Đang sinh dữ liệu Tháng 10/2026 (Tháng hiện hành & Kịch bản AI)...")
        record_import("PN-202610-001", "NCC_ANPHAT", datetime(2026, 10, 3, 9, 0), [
            ("SP005", 10, 1650000.0), ("SP006", 15, 860000.0), ("SP021", 20, 98000.0)
        ], "Nhập linh kiện bảo dưỡng quý 4 An Phát")

        record_import("PN-202610-002", "NCC_HOANGHA", datetime(2026, 10, 12, 10, 30), [
            ("SP064", 4, 6620000.0), ("SP065", 10, 770000.0), ("SP076", 12, 538000.0)
        ], "Nhập bổ sung thiết bị âm thanh Hoàng Hà Mobile")

        # Phiếu nhập gần nhất ngày 20/10/2026 (hôm nay)
        record_import("PN-202610-003", "NCC_VIENDONG", datetime(2026, 10, 20, 8, 15), [
            ("SP019", 10, 115000.0), ("SP020", 15, 120000.0)
        ], "Nhập phụ kiện mở rộng văn phòng Viễn Đông")

        # Xuất hàng đầu tháng 10:
        # SP001 xuất đều để đến ngày 20/10 tồn kho chỉ còn đúng 4 chiếc (4 < min_stock 15)
        # SP002 xuất bình thường từ 01/10 -> 13/10 (chỉ 4 chiếc)
        record_export("PX-202610-001", "Cửa hàng Bán lẻ Tin học Nguyễn Kim", datetime(2026, 10, 2, 10, 15), [
            ("SP001", 3), ("SP002", 2), ("SP004", 2), ("SP050", 4)
        ], "Xuất phụ kiện bán lẻ Nguyễn Kim")

        record_export("PX-202610-002", "Công ty Cổ phần Truyền thông & Công nghệ Alpha", datetime(2026, 10, 5, 14, 0), [
            ("SP001", 3), ("SP002", 2), ("SP005", 2), ("SP036", 1)
        ], "Xuất thiết bị thay thế cho bộ phận dựng video")

        record_export("PX-202610-003", "Văn phòng Luật sư Nhân Đức", datetime(2026, 10, 8, 11, 30), [
            ("SP017", 4), ("SP020", 3), ("SP068", 5)
        ], "Cung cấp cáp kết nối & chuột văn phòng")

        record_export("PX-202610-004", "Ngân hàng TMCP Phương Nam (Chi nhánh số 3)", datetime(2026, 10, 11, 15, 45), [
            ("SP008", 2), ("SP016", 10), ("SP073", 6)
        ], "Bảo trì hệ thống mạng nội bộ chi nhánh")

        # ---------------------------------------------------------------------
        # KỊCH BẢN ĐỘT BIẾN TUẦN GẦN NHẤT (14/10 -> 20/10):
        # SP002: Xuất 20 chiếc (ngày 17/10) và 15 chiếc (ngày 19/10) -> Tổng 35 chiếc tuần này!
        # Tăng trưởng > 200% so với tuần trước -> AI kích hoạt SURGE_EXPORT!
        # ---------------------------------------------------------------------
        record_export("PX-202610-005", "Trường Đại học Công nghệ FPT", datetime(2026, 10, 17, 9, 30), [
            ("SP002", 20),  # Đột biến 1
            ("SP007", 2),
            ("SP016", 10),
        ], "Trường Đại học Công nghệ FPT (Trang bị mới phòng máy thực hành chuyên ngành)")

        record_export("PX-202610-006", "Hệ thống CyberCore Gaming Stadium", datetime(2026, 10, 19, 14, 20), [
            ("SP002", 15),  # Đột biến 2
            ("SP010", 4),
            ("SP018", 10),
        ], "Hệ thống Phòng Net CyberCore (Thay thế toàn bộ dàn chuột phòng VIP)")

        # Phiếu xuất hôm nay 20/10/2026
        record_export("PX-202610-007", "Khách hàng Bán lẻ & Đối tác Doanh nghiệp", datetime(2026, 10, 20, 10, 0), [
            ("SP023", 1), ("SP034", 1), ("SP070", 2)
        ], "Đơn giao hàng công nghệ trong ngày")

        # Tinh chỉnh tồn kho cuối cùng cho SP001 về đúng 4 chiếc nếu còn lệch (kịch bản AI)
        events.append({
            "type": "EXPORT_TARGET",
            "code": "PX-202610-008",
            "recipient": "Cửa hàng Bán lẻ Tin học Nguyễn Kim",
            "note_date": datetime(2026, 10, 20, 11, 0),
            "target_sku": "SP001",
            "target_stock": 4,
            "note_text": "Xuất bổ sung hoàn tất hợp đồng cung ứng bàn phím Akko",
            "status": "COMPLETED",
        })

        # Tinh chỉnh một vài sản phẩm khác để danh sách gợi ý nhập đa dạng (SP023, SP036, SP050)
        events.append({
            "type": "EXPORT_TARGET",
            "code": "PX-202610-009",
            "recipient": "Khách hàng Đặt hàng Online (Giao nhanh)",
            "note_date": datetime(2026, 10, 20, 14, 0),
            "target_sku": "SP023",
            "target_stock": 2,
            "note_text": "Xuất giao nhanh iPhone 16 cho khách hàng VIP",
            "status": "COMPLETED",
        })

        events.append({
            "type": "EXPORT_TARGET",
            "code": "PX-202610-010",
            "recipient": "Viện Đào tạo Quốc tế Kent",
            "note_date": datetime(2026, 10, 20, 15, 0),
            "target_sku": "SP036",
            "target_stock": 3,
            "note_text": "Xuất trang bị máy tính Dell Inspiron phòng học",
            "status": "COMPLETED",
        })

        events.append({
            "type": "EXPORT_TARGET",
            "code": "PX-202610-011",
            "recipient": "Tập đoàn Bất động sản Đất Việt",
            "note_date": datetime(2026, 10, 20, 16, 0),
            "target_sku": "SP050",
            "target_stock": 8,
            "note_text": "Cung ứng chuột không dây văn phòng Đất Việt",
            "status": "COMPLETED",
        })

        # Sắp xếp toàn bộ chuỗi sự kiện theo đúng thứ tự thời gian thực tế
        # Nếu cùng thời điểm, ưu tiên NHẬP trước XUẤT để bảo toàn tồn kho ACID
        events.sort(key=lambda ev: (ev["note_date"], 0 if ev["type"] == "IMPORT" else 1))

        print(f"  -> Đang thực thi tuần tự {len(events)} giao dịch 5 tháng theo đúng thứ tự thời gian...")
        for ev in events:
            ev_type = ev["type"]
            note_date = ev["note_date"]
            status = ev.get("status", "COMPLETED")

            if ev_type == "IMPORT":
                sup_code = ev["sup_code"]
                imp = ImportNote(
                    code=ev["code"],
                    supplier_id=sup_map[sup_code].id,
                    created_by=thukho_user.id,
                    note_date=note_date,
                    total_amount=0.0,
                    status=status,
                    note=ev["note_text"],
                )
                db.add(imp)
                db.flush()

                total_amount = 0.0
                for sku, qty, unit_price in ev["items"]:
                    p = prod_map[sku]
                    subtotal = float(qty * unit_price)
                    total_amount += subtotal
                    db.add(
                        ImportNoteDetail(
                            import_note_id=imp.id,
                            product_id=p.id,
                            quantity=qty,
                            unit_price=unit_price,
                            subtotal=subtotal,
                        )
                    )
                    if status == "COMPLETED":
                        p.current_stock += qty
                        db.add(
                            StockLedger(
                                product_id=p.id,
                                transaction_type="IMPORT",
                                reference_code=imp.code,
                                quantity_change=qty,
                                balance_after=p.current_stock,
                                created_by=thukho_user.id,
                                transaction_date=note_date,
                                note=f"Nhập kho từ {sup_map[sup_code].name}",
                            )
                        )
                imp.total_amount = total_amount

            elif ev_type in ("EXPORT", "EXPORT_TARGET"):
                items = []
                if ev_type == "EXPORT_TARGET":
                    sku = ev["target_sku"]
                    p = prod_map[sku]
                    target_stock = ev["target_stock"]
                    if p.current_stock > target_stock:
                        items = [(sku, p.current_stock - target_stock)]
                    else:
                        items = []
                else:
                    items = ev["items"]

                if not items:
                    continue

                exp = ExportNote(
                    code=ev["code"],
                    recipient_name=ev["recipient"],
                    created_by=thukho_user.id,
                    note_date=note_date,
                    total_amount=0.0,
                    status=status,
                    note=ev["note_text"],
                )
                db.add(exp)
                db.flush()

                total_amount = 0.0
                for sku, requested_qty in items:
                    if sku == "SP003":  # Kịch bản DEAD STOCK: tuyệt đối không xuất!
                        continue
                    p = prod_map[sku]
                    price = p.standard_price

                    safe_margin = 0 if ev_type == "EXPORT_TARGET" else (4 if sku == "SP001" else 1)
                    qty_can_export = max(0, p.current_stock - safe_margin)
                    actual_qty = min(requested_qty, qty_can_export)

                    if actual_qty > 0:
                        subtotal = float(actual_qty * price)
                        total_amount += subtotal
                        db.add(
                            ExportNoteDetail(
                                export_note_id=exp.id,
                                product_id=p.id,
                                quantity=actual_qty,
                                unit_price=price,
                                subtotal=subtotal,
                            )
                        )
                        if status == "COMPLETED":
                            p.current_stock -= actual_qty
                            db.add(
                                StockLedger(
                                    product_id=p.id,
                                    transaction_type="EXPORT",
                                    reference_code=exp.code,
                                    quantity_change=-actual_qty,
                                    balance_after=p.current_stock,
                                    created_by=thukho_user.id,
                                    transaction_date=note_date,
                                    note=f"Xuất kho cho {ev['recipient']}",
                                )
                            )
                exp.total_amount = total_amount

        db.commit()

        # =====================================================================
        # 6. LÀM SẠCH VÀ CHUẨN BỊ CACHE AI
        # =====================================================================
        print("[INFO] 6. Dọn dẹp cache AI để đồng bộ dấu vết dữ liệu mới...")
        cache_file = Path(__file__).resolve().parent / "data" / "ai_cache.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
                print("   -> Đã dọn sạch cache cũ (ai_cache.json).")
            except Exception as e:
                print(f"   -> Không thể xóa cache: {e}")

        # Thống kê kết quả
        total_imp = db.query(ImportNote).count()
        total_exp = db.query(ExportNote).count()
        total_ledger = db.query(StockLedger).count()

        print("\n===============================================================================")
        print("          NẠP DỮ LIỆU MẪU ENTERPRISE 5 THÁNG HOÀN TẤT THÀNH CÔNG!")
        print("===============================================================================")
        print(f" - Tổng số Phiếu Nhập Kho qua 5 tháng:  {total_imp} phiếu")
        print(f" - Tổng số Phiếu Xuất Kho qua 5 tháng:  {total_exp} phiếu")
        print(f" - Tổng số dòng Thẻ Kho (StockLedger): {total_ledger} bản ghi (Chuẩn ACID)")
        print(f" - Trạng thái kịch bản AI cốt lõi:")
        print(f"   * SP001 (Bàn phím Akko): Tồn = {prod_map['SP001'].current_stock} / Min = {prod_map['SP001'].min_stock} (Bán chạy, cạn kho -> Gợi ý nhập HIGH)")
        print(f"   * SP002 (Chuột G304):    Tồn = {prod_map['SP002'].current_stock} (Đã xuất 35 chiếc tuần qua -> Đột biến SURGE_EXPORT >200%)")
        print(f"   * SP003 (Cáp VGA-HDMI):  Tồn = {prod_map['SP003'].current_stock} (0 lượt xuất trong suốt 153 ngày -> DEAD_STOCK)")
        print(f"   * SP023 (iPhone 16):     Tồn = {prod_map['SP023'].current_stock} / Min = {prod_map['SP023'].min_stock} (Cận tồn tối thiểu)")
        print(f"   * SP036 (Dell Inspiron): Tồn = {prod_map['SP036'].current_stock} / Min = {prod_map['SP036'].min_stock} (Cận tồn tối thiểu)")
        print(f"   * SP050 (Logitech M185): Tồn = {prod_map['SP050'].current_stock} / Min = {prod_map['SP050'].min_stock} (Cận tồn tối thiểu)")
        print("===============================================================================\n")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Thất bại khi nạp dữ liệu: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
