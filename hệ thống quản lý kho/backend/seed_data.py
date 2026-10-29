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
    from sqlalchemy import inspect, text
    with engine.connect() as conn:
        inspector = inspect(conn)
        if inspector.has_table("products"):
            prod_cols = [c["name"] for c in inspector.get_columns("products")]
            if "supplier_id" not in prod_cols:
                conn.execute(text("ALTER TABLE products ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_products_supplier_id ON products (supplier_id)"))
                conn.commit()
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
            ("SUP_E2E_160432804590", "văn phòng khánh hòa", "0988776655", "khanhhoa.office@partner.vn", "Khánh Hòa"),
            ("SUP_E2E_154720745019", "phong đà vân sơn", "0988776655", "phongdavanson@partner.vn", "Đà Nẵng"),
            ("SUP_E2E_151733885016", "dâm dồ diệc tu tiên hội nhóm", "0988776655", "damdodiec@partner.vn", "Hà Nội"),
            ("SUP_E2E_132517808823", "trường đại học lưu văn trú", "0988776655", "luuvantru@edu.vn", "TP. Hồ Chí Minh"),
            ("SUP_E2E_122956130472", "hội nhóm công nghệ thái nguyên", "0988776655", "thainguyen.tech@partner.vn", "Thái Nguyên"),
            ("SUP_E2E_121134649607", "nhà cung cấp AL TEST số 7", "0988776655", "altest7@partner.vn", "Hà Nội"),
            ("SUP_E2E_120920994502", "nhà cung cấp XXXX", "0988776655", "nccxxxx@partner.vn", "TP. Hồ Chí Minh"),
            ("SUP_E2E_120824350246", "cô ty cổ phần vin", "0988776655", "vin.corp@partner.vn", "Hà Nội"),
            ("SUP_E2E_130519140787", "VĂN PHÒNG làm việc khánh hòa", "0988776655", "vp.khanhhoa@partner.vn", "Khánh Hòa"),
            ("SUP_AI", "Nhà phân phối AI Test", "0909112233", "ai.distri@partner.vn", "TP. Hồ Chí Minh"),
            ("SUP-ACID-TEST", "Nhà cung cấp ACID Test", "0911223344", "acid.test@partner.vn", "Hà Nội"),
        ]
        sup_map = {}
        for code, name, phone, email, addr in suppliers_data:
            sup = db.query(Supplier).filter(Supplier.code == code).first()
            if not sup:
                sup = Supplier(code=code, name=name, phone=phone, email=email, address=addr, is_active=True)
                db.add(sup)
                db.commit()
                db.refresh(sup)
            else:
                if not sup.phone:
                    sup.phone = phone
                if not sup.email:
                    sup.email = email
                if not sup.address:
                    sup.address = addr
                db.commit()
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
            # 33 mặt hàng bổ sung cho 11 nhà cung cấp (SP077 -> SP109)
            # NCC 1 (SUP_E2E_160432804590)
            ("SP077", "SSD Samsung 970 EVO Plus 500GB", "CAT_LK", "Chiếc", 5, 1690000.0),
            ("SP078", "SSD Kingston NV2 1TB", "CAT_LK", "Chiếc", 5, 1890000.0),
            ("SP079", "RAM Kingston Fury 8GB DDR4 3200", "CAT_LK", "Thanh", 10, 650000.0),
            ("SP080", "RAM Corsair Vengeance 16GB DDR4 3200", "CAT_LK", "Thanh", 10, 1150000.0),
            # NCC 2 (SUP_E2E_154720745019)
            ("SP081", "Mainboard ASUS H510M-K", "CAT_LK", "Chiếc", 5, 1750000.0),
            ("SP082", "CPU Intel Core i3-12100F", "CAT_LK", "Chiếc", 5, 2150000.0),
            ("SP083", "Tản nhiệt khí DeepCool AG400", "CAT_LK", "Chiếc", 10, 450000.0),
            # NCC 3 (SUP_E2E_151733885016)
            ("SP084", "Nguồn máy tính Cooler Master 550W", "CAT_LK", "Chiếc", 10, 950000.0),
            ("SP085", "Ổ cứng HDD Seagate 1TB 7200rpm", "CAT_LK", "Chiếc", 10, 1050000.0),
            ("SP086", "Card đồ họa GTX 1650 4GB", "CAT_LK", "Chiếc", 5, 3990000.0),
            # NCC 4 (SUP_E2E_132517808823)
            ("SP087", "Cáp HDMI 2.0 Ugreen 2m", "CAT_PK", "Sợi", 15, 120000.0),
            ("SP088", "Cáp sạc USB-C to USB-C 100W 1m", "CAT_PK", "Sợi", 15, 190000.0),
            ("SP089", "Hub USB-C 7 in 1 Ugreen", "CAT_PK", "Cái", 10, 690000.0),
            # NCC 5 (SUP_E2E_122956130472)
            ("SP090", "Củ sạc nhanh Anker 20W", "CAT_PK", "Cái", 15, 290000.0),
            ("SP091", "Pin sạc dự phòng Xiaomi 10000mAh", "CAT_PK", "Cái", 10, 450000.0),
            ("SP092", "Ổ cắm điện đa năng Lioa 6 lỗ 3m", "CAT_PK", "Cái", 15, 185000.0),
            # NCC 6 (SUP_E2E_121134649607)
            ("SP093", "Đế tản nhiệt laptop có quạt", "CAT_PK", "Cái", 10, 320000.0),
            ("SP094", "Giá đỡ laptop nhôm gấp gọn", "CAT_PK", "Cái", 15, 280000.0),
            ("SP095", "Balo laptop chống nước 15.6 inch", "CAT_PK", "Cái", 10, 390000.0),
            # NCC 7 (SUP_E2E_120920994502)
            ("SP096", "Chuột không dây Logitech M331 Silent", "CAT_TB", "Chiếc", 15, 290000.0),
            ("SP097", "Chuột gaming Logitech G102 Lightsync", "CAT_TB", "Chiếc", 10, 420000.0),
            ("SP098", "Bàn phím cơ Akko 3087 v2 DS Horizon", "CAT_TB", "Chiếc", 5, 1590000.0),
            # NCC 8 (SUP_E2E_120824350246)
            ("SP099", "Bàn phím không dây Logitech K380", "CAT_TB", "Chiếc", 10, 790000.0),
            ("SP100", "Tai nghe Sony WH-CH520", "CAT_TB", "Chiếc", 10, 1290000.0),
            ("SP101", "Tai nghe Logitech H111 giắc 3.5mm", "CAT_TB", "Chiếc", 15, 190000.0),
            # NCC 9 (SUP_E2E_130519140787)
            ("SP102", "Loa vi tính Microlab B77", "CAT_TB", "Bộ", 10, 650000.0),
            ("SP103", "Webcam Logitech C920 HD Pro", "CAT_TB", "Chiếc", 5, 1890000.0),
            ("SP104", "Micro thu âm USB Fifine K669", "CAT_TB", "Chiếc", 10, 650000.0),
            # NCC 10 (SUP_AI)
            ("SP105", "Màn hình LG 22MK400H 22 inch", "CAT_TB", "Chiếc", 5, 2490000.0),
            ("SP106", "Màn hình Dell P2422H 24 inch", "CAT_TB", "Chiếc", 5, 3990000.0),
            ("SP107", "Máy in Canon LBP2900", "CAT_TB", "Chiếc", 5, 3290000.0),
            # NCC 11 (SUP-ACID-TEST)
            ("SP108", "Router Wi-Fi TP-Link Archer C6", "CAT_TB", "Chiếc", 10, 790000.0),
            ("SP109", "Lót chuột Logitech Desk Mat", "CAT_TB", "Cái", 15, 220000.0),
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

        product_supplier_map = {
            "SP001": "NCC_VIENDONG", "SP002": "NCC_VIENDONG", "SP003": "NCC_VIENDONG",
            "SP016": "NCC_VIENDONG", "SP017": "NCC_VIENDONG", "SP018": "NCC_VIENDONG",
            "SP019": "NCC_VIENDONG", "SP020": "NCC_VIENDONG", "SP021": "NCC_VIENDONG",
            "SP004": "NCC_SAIGON", "SP009": "NCC_SAIGON", "SP014": "NCC_SAIGON",
            "SP022": "NCC_SAIGON", "SP054": "NCC_SAIGON", "SP057": "NCC_SAIGON",
            "SP075": "NCC_SAIGON",
            "SP007": "NCC_ACHAU", "SP008": "NCC_ACHAU", "SP012": "NCC_ACHAU",
            "SP013": "NCC_ACHAU", "SP072": "NCC_ACHAU", "SP073": "NCC_ACHAU",
            "SP074": "NCC_ACHAU",
            "SP023": "NCC_FPTSHOP", "SP024": "NCC_FPTSHOP", "SP025": "NCC_FPTSHOP",
            "SP034": "NCC_FPTSHOP", "SP035": "NCC_FPTSHOP", "SP049": "NCC_FPTSHOP",
            "SP069": "NCC_FPTSHOP", "SP070": "NCC_FPTSHOP",
            "SP026": "NCC_TGDD", "SP027": "NCC_TGDD", "SP028": "NCC_TGDD",
            "SP031": "NCC_TGDD", "SP032": "NCC_TGDD", "SP033": "NCC_TGDD",
            "SP071": "NCC_TGDD",
            "SP029": "NCC_CELLPHONES", "SP030": "NCC_CELLPHONES", "SP064": "NCC_CELLPHONES",
            "SP065": "NCC_CELLPHONES", "SP066": "NCC_CELLPHONES", "SP067": "NCC_CELLPHONES",
            "SP068": "NCC_CELLPHONES", "SP076": "NCC_CELLPHONES",
            "SP036": "NCC_PHONGVU", "SP037": "NCC_PHONGVU", "SP040": "NCC_PHONGVU",
            "SP041": "NCC_PHONGVU", "SP042": "NCC_PHONGVU", "SP047": "NCC_PHONGVU",
            "SP048": "NCC_PHONGVU", "SP050": "NCC_PHONGVU", "SP053": "NCC_PHONGVU",
            "SP010": "NCC_GEARVN", "SP039": "NCC_GEARVN", "SP043": "NCC_GEARVN",
            "SP045": "NCC_GEARVN", "SP046": "NCC_GEARVN", "SP051": "NCC_GEARVN",
            "SP052": "NCC_GEARVN", "SP055": "NCC_GEARVN", "SP056": "NCC_GEARVN",
            "SP062": "NCC_GEARVN", "SP063": "NCC_GEARVN",
            "SP005": "NCC_ANPHAT", "SP006": "NCC_ANPHAT", "SP011": "NCC_ANPHAT",
            "SP015": "NCC_ANPHAT", "SP058": "NCC_ANPHAT", "SP059": "NCC_ANPHAT",
            "SP060": "NCC_ANPHAT", "SP061": "NCC_ANPHAT",
            "SP038": "NCC_HOANGHA", "SP044": "NCC_HOANGHA",
            # Gắn 33 sản phẩm bổ sung cho 11 nhà cung cấp
            "SP077": "SUP_E2E_160432804590", "SP078": "SUP_E2E_160432804590",
            "SP079": "SUP_E2E_160432804590", "SP080": "SUP_E2E_160432804590",
            "SP081": "SUP_E2E_154720745019", "SP082": "SUP_E2E_154720745019", "SP083": "SUP_E2E_154720745019",
            "SP084": "SUP_E2E_151733885016", "SP085": "SUP_E2E_151733885016", "SP086": "SUP_E2E_151733885016",
            "SP087": "SUP_E2E_132517808823", "SP088": "SUP_E2E_132517808823", "SP089": "SUP_E2E_132517808823",
            "SP090": "SUP_E2E_122956130472", "SP091": "SUP_E2E_122956130472", "SP092": "SUP_E2E_122956130472",
            "SP093": "SUP_E2E_121134649607", "SP094": "SUP_E2E_121134649607", "SP095": "SUP_E2E_121134649607",
            "SP096": "SUP_E2E_120920994502", "SP097": "SUP_E2E_120920994502", "SP098": "SUP_E2E_120920994502",
            "SP099": "SUP_E2E_120824350246", "SP100": "SUP_E2E_120824350246", "SP101": "SUP_E2E_120824350246",
            "SP102": "SUP_E2E_130519140787", "SP103": "SUP_E2E_130519140787", "SP104": "SUP_E2E_130519140787",
            "SP105": "SUP_AI", "SP106": "SUP_AI", "SP107": "SUP_AI",
            "SP108": "SUP-ACID-TEST", "SP109": "SUP-ACID-TEST",
        }

        product_image_map = {
            "SP001": "https://tse3.mm.bing.net/th/id/OIP.SCVLCozvpGq4rIxDrNNZ2AHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP002": "https://tse1.explicit.bing.net/th/id/OIP.LyDZ0OceJ7hzX65D2lTiIgHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP003": "https://down-vn.img.susercontent.com/file/b80a537a88cf310e1f01cc91381d7347",
            "SP004": "https://st3.tkcomputer.vn/uploads/dell_ultrasharp_u2422h_1682612567.jpg",
            "SP005": "https://tse2.mm.bing.net/th/id/OIP.g1xt0Z2tc96c3vLUvSfRowHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP006": "https://th.bing.com/th/id/OIP.a46mlfCpQVKBGaZR9m3OpwHaHa?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP007": "https://tse3.mm.bing.net/th/id/OIP.KMNDjTOO9lSQXglif5VFgwHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP008": "https://tse1.mm.bing.net/th/id/OIP.8WO4MhPqTyYVzhL-C0YSyQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP009": "https://tse1.mm.bing.net/th/id/OIP.oET03HyUCyTd3ccQVTHFdAHaHe?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP010": "https://down-vn.img.susercontent.com/file/vn-11134207-820l4-mguwa37adedk6e",
            "SP011": "https://salt.tikicdn.com/cache/w1200/ts/product/2c/ce/0a/8acd615a4bc7d56abf7bd2729ea4a288.png",
            "SP012": "https://tse2.mm.bing.net/th/id/OIP.GGx1oT3PsZCDpcJnfgYsDwHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP013": "https://khanhchaudigital.vn/uploads/source/o-cung/ssd-wd-my-pp/thiet-ke-chua-co-ten-16-6234.png",
            "SP014": "https://cellphones.com.vn/media/wysiwyg/accessories/speaker/loa-microlab-m108-den-1.jpg",
            "SP015": "https://tse2.mm.bing.net/th/id/OIP.qkFLEv8Kw05Fb40nolZpowHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP016": "https://tse2.mm.bing.net/th/id/OIP.xvG1qB-V3DhFpBguf4viYAHaIy?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP017": "https://th.bing.com/th/id/OIP.ViIdHBxDK7_5CcL1FnEk2gHaHa?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP018": "https://tse1.mm.bing.net/th/id/OIP.7SI7ezowXXD_s3IaDy8VtQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP019": "https://tse3.mm.bing.net/th/id/OIP.uz75uleBVOPpYDq78QMCEQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP020": "https://th.bing.com/th/id/OIP.2P70AQm39QR_bU79k7VsxAHaHa?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP021": "https://tse1.mm.bing.net/th/id/OIP.vQxaAtFgNcTotkfCAMh8-QHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP022": "https://www.lg.com/vn/images/man-hinh-may-tinh/md07527366/gallery/1100-1.jpg",
            "SP023": "https://www.pricerunner.dk/product/3136271184/Apple-iPhone-16-128GB.jpg",
            "SP024": "https://tse4.mm.bing.net/th/id/OIP.eMW7SH_D0ChxKcOG482AtwHaFI?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP025": "https://tse3.mm.bing.net/th/id/OIP.pTMGD0hI-xUBuSVFyCq7nAHaFI?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP026": "https://samnews.vn/wp-content/uploads/2026/05/Galaxy-S24-Ultra-hands-on-SamNews.jpg",
            "SP027": "https://tse2.mm.bing.net/th/id/OIF.L8jmbBxDZJ4qY1k2LTZGFA?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP028": "https://tse4.mm.bing.net/th/id/OIP.xCtSYU_Hm0ZV0n7kEECjywHaE8?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP029": "https://tse4.mm.bing.net/th/id/OIP._F1nttXfkUC8bYpTqltTIgHaJa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP030": "https://tse3.mm.bing.net/th/id/OIF.S5dldrYe3gsevTfrHkwFIg?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP031": "https://th.bing.com/th?id=OIF.XftTvyzYT5ME9hKPaKz%2btA&r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP032": "https://tse1.mm.bing.net/th/id/OIP.GpQ-jSuUG3MWipOfP5QRbwHaEI?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP033": "https://tse3.mm.bing.net/th/id/OIP.Uc1AqDD-r7-LTC2u4wHzCAHaE7?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP034": "https://tse4.mm.bing.net/th/id/OIP.hrX9V9HvG0HkxeIvFvzPiwHaFR?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP035": "https://tse1.explicit.bing.net/th/id/OIP.zarHFMhZNyJBtL6UeWPfVgHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP036": "https://tse1.mm.bing.net/th/id/OIP.HmZBeDyOP3Pn1lzBIzubUwHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP037": "https://tse4.mm.bing.net/th/id/OIP.-GtYQdMyHelii_6MMf7sYwHaEK?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP038": "https://th.bing.com/th/id/OIP.HD-6Qw9USZR_Ahf54y2FCgHaFj?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP039": "https://tse4.mm.bing.net/th/id/OIP.6AfpFmLCswf3j1l2pHFc1QHaEK?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP040": "https://tse1.mm.bing.net/th/id/OIP.n5J6U1andlQb0ktkX-qPQAHaEK?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP041": "https://tse1.mm.bing.net/th/id/OIP.htkcKQ05vpaPM1KW8XEtywHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP042": "https://tse3.mm.bing.net/th/id/OIP.ViyrevxyJoQnsHDYQMsExgHaE7?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP043": "https://tse4.mm.bing.net/th/id/OIP.FYRse55LIFudAChFVyQ6pAHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP044": "https://tse3.mm.bing.net/th/id/OIP.dwWlZq0zA4GrRShGR_Na9wHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP045": "https://tse3.mm.bing.net/th/id/OIP.KQmZd0zuQPmpYTOpeyu8AgHaFt?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP046": "https://tse4.mm.bing.net/th/id/OIP.OpneO1xDmvuH8kkQpPP3iwHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP047": "https://tse3.mm.bing.net/th/id/OIP.nX-M1aLPS517brABhUnErAHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP048": "https://tse3.mm.bing.net/th/id/OIP.jMG5WY_xgr8ADp2FG_lNJgHaGO?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP049": "https://tse2.mm.bing.net/th/id/OIP.t31NdllSc-cYMY4AleeLOAHaEK?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP050": "https://tse3.mm.bing.net/th/id/OIP.LccnLRD9UtJnFmq0e-vbhAHaGE?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP051": "https://th.bing.com/th/id/OIP.ay3LzoGZCPyjSCpPFjyP7wHaE7?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP052": "https://th.bing.com/th/id/OIP.RvXOCyCOgqKW6AEkXsJQdAHaD4?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP053": "https://tse3.mm.bing.net/th/id/OIP.-RDOsXsLXD7eIWSXbi9i9gHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP054": "https://tse3.mm.bing.net/th/id/OIP.og_BL_OITEewcT1u0MvoGQHaFy?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP055": "https://tse4.mm.bing.net/th/id/OIP.ikNBIrXLsIL9UyE1yNaPNgHaE6?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP056": "https://tse4.mm.bing.net/th/id/OIP.AuAf_Ra0JHH8mFq7JpU5MQHaGQ?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP057": "https://th.bing.com/th/id/OIP.Dc-5b65DnFwG197KHy5ALwHaHa?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP058": "https://tse3.mm.bing.net/th/id/OIP.TnW4LkzeCEHhVxgIeeVqMQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP059": "https://tse4.mm.bing.net/th/id/OIP.HG11wQImeiWAGnrcO8hIfAHaD2?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP060": "https://tse1.mm.bing.net/th/id/OIP.B9Bu2uurx32XQmMp8LgBxAHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP061": "https://tse2.mm.bing.net/th/id/OIP.9IhLm3kM3VHrvvSpxCaJ5gHaDt?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP062": "https://tse4.mm.bing.net/th/id/OIP.hyL0ToVTyrlQsnP-UhTPTQHaFz?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP063": "https://tse2.mm.bing.net/th/id/OIP.rTFqK3KgedID3d9P4RB9UAHaFr?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP064": "https://tse1.mm.bing.net/th/id/OIP.tb27GoM-vd0nkImcM-PR6AHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP065": "https://tse1.explicit.bing.net/th/id/OIP.wX_oXPluE8YegrW_lMZoMwHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP066": "https://tse1.mm.bing.net/th/id/OIP.TAZgaY69M-AkXKTCpod-4AHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP067": "https://tse1.mm.bing.net/th/id/OIP.tk4TnZw2c_fo6IqyDGKZYQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP068": "https://tse1.mm.bing.net/th/id/OIP.-appNsYtxT0hNMU85ANJQQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP069": "https://tse1.explicit.bing.net/th/id/OIP.XP7rboFXaJo6xfquOIZubQHaIx?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP070": "https://tse1.mm.bing.net/th/id/OIP.HUbty0qtRflzsPrguJVuRQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP071": "https://tse1.explicit.bing.net/th/id/OIP.z5yT4TThJZmDNNovhMhm7AHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP072": "https://tse2.mm.bing.net/th/id/OIP.eBgS93pccKAOxjeZNiBDxgHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP073": "https://th.bing.com/th/id/OIP.OkL91gRtYP2IldVcrjavRwHaE0?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP074": "https://tse1.mm.bing.net/th/id/OIP.BI2PWsT-1VRJkwBehDkt8wHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP075": "https://th.bing.com/th/id/OIP.kF-DuVY3iSQIU2rPH0ZsHAHaEK?w=329&h=184&c=7&r=0&o=7&dpr=1.3&pid=1.7&rm=3",
            "SP076": "https://th.bing.com/th/id/OIP.PZZ0utZCPKXahnYoUDNWDQHaHa?w=189&h=189&c=7&r=0&o=7&dpr=1.3&pid=1.7&rm=3",
            # 33 mặt hàng bổ sung (SP077 -> SP109)
            "SP077": "https://tse1.mm.bing.net/th/id/OIP.B9Bu2uurx32XQmMp8LgBxAHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP078": "https://tse3.mm.bing.net/th/id/OIP.4I0Vs7Lg-WdsiF_ixXzGDwHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP079": "https://tse3.mm.bing.net/th/id/OIP.TnW4LkzeCEHhVxgIeeVqMQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP080": "https://tse4.mm.bing.net/th/id/OIP.HG11wQImeiWAGnrcO8hIfAHaD2?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP081": "https://tse1.mm.bing.net/th/id/OIP.VqaJ7QBd4z7QmKnVD8b1_gHaJ4?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP082": "https://tse4.mm.bing.net/th/id/OIP.3aKKZ5RH5E2dbSLPOa7s3AHaE7?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP083": "https://tse2.mm.bing.net/th/id/OIP.qkFLEv8Kw05Fb40nolZpowHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP084": "https://tse3.mm.bing.net/th/id/OIP.c71yHCMxig5IwXw1LnAf-AHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP085": "https://tse3.mm.bing.net/th/id/OIP.XHNxTKaY2GtnRKereE3dQwHaFB?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP086": "https://tse3.mm.bing.net/th/id/OIP.qdF5B7GgFG5UHzcVWPMlNgAAAA?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP087": "https://tse1.mm.bing.net/th/id/OIP.OgHytCU2FsmKDOQtbiPFzgHaFO?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP088": "https://tse1.mm.bing.net/th/id/OIP.-appNsYtxT0hNMU85ANJQQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP089": "https://tse1.mm.bing.net/th/id/OIP.LzxheWgBW-EDM3Uxf-IwzAHaD4?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP090": "https://tse4.mm.bing.net/th/id/OIP.GtWWdFLt_KXBRySabtf_NgHaDt?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP091": "https://tse1.mm.bing.net/th/id/OIP.tk4TnZw2c_fo6IqyDGKZYQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP092": "https://tse4.mm.bing.net/th/id/OIP.COPjU3uwtbCuH6HuPc0fHAHaE8?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP093": "https://tse3.mm.bing.net/th/id/OIP.hxxZqVIFhAwLiE16Qlt0gQHaCp?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP094": "https://tse2.mm.bing.net/th/id/OIP.mOUGnw8nRMXnqrpZj3dv8gHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP095": "https://tse4.mm.bing.net/th/id/OIP.qnXNL_5Yn0w6R77lB_3EdQHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP096": "https://tse1.mm.bing.net/th/id/OIP.nVSw4B0GMzjzpw3q8a64EQHaEB?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP097": "https://th.bing.com/th/id/OIP.ay3LzoGZCPyjSCpPFjyP7wHaE7?r=0&o=7rm=3&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP098": "https://tse3.mm.bing.net/th/id/OIP.SCVLCozvpGq4rIxDrNNZ2AHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP099": "https://tse1.mm.bing.net/th/id/OIP.DnUR1JHfhVERqNOZxyGLRAHaE8?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP100": "https://tse1.mm.bing.net/th/id/OIP.tb27GoM-vd0nkImcM-PR6AHaHa?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP101": "https://tse1.explicit.bing.net/th/id/OIP.wX_oXPluE8YegrW_lMZoMwHaFj?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP102": "https://tse1.mm.bing.net/th/id/OIP.sPiQzY4uNswcLhAIKWsSpgHaDv?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP103": "https://tse1.mm.bing.net/th/id/OIP.oET03HyUCyTd3ccQVTHFdAHaHe?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP104": "https://tse3.mm.bing.net/th/id/OIP.vD13ZGbh4XSV0lim9AsGLgHaE7?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP105": "https://tse3.mm.bing.net/th/id/OIP.ilbikfGaPppJwCctywzFbgHaE7?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP106": "https://tse3.mm.bing.net/th/id/OIP.og_BL_OITEewcT1u0MvoGQHaFy?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP107": "https://tse1.mm.bing.net/th/id/OIP.2PTZ8zrn6WCVKgE7TxFp3QHaE6?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP108": "https://tse3.mm.bing.net/th/id/OIP.7uIxXZw_cLyr__740eKdHwHaEK?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
            "SP109": "https://tse4.mm.bing.net/th/id/OIP.VkUPdQq_Ncjz9ceSEgsWEgHaD4?r=0&rs=1&pid=ImgDetMain&o=7&rm=3",
        }

        prod_map = {}
        for code, name, cat_code, unit, min_stock, price in products_meta:
            sup_code = product_supplier_map.get(code, "NCC_VIENDONG")
            sup_id = sup_map[sup_code].id
            default_img = product_image_map.get(code, f"/static/products/{code}.jpg")
            p = db.query(Product).filter(Product.code == code).first()
            if not p:
                p = Product(
                    code=code,
                    name=name,
                    category_id=cat_map[cat_code].id,
                    supplier_id=sup_id,
                    unit=unit,
                    min_stock=min_stock,
                    current_stock=0,
                    standard_price=price,
                    image_url=default_img,
                    status="ACTIVE",
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            else:
                p.name = name
                p.category_id = cat_map[cat_code].id
                p.supplier_id = sup_id
                p.standard_price = price
                p.unit = unit
                p.min_stock = min_stock
                p.current_stock = 0  # Sẽ được tính lại chuẩn xác qua từng phiếu nhập/xuất
                p.status = "ACTIVE"
                if not p.image_url or p.image_url == f"/static/products/{code}.jpg":
                    p.image_url = default_img
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

        def record_adjustment(code: str, sku: str, diff_qty: int, note_date: datetime, note_text: str):
            events.append({
                "type": "ADJUSTMENT",
                "code": code,
                "sku": sku,
                "diff_qty": diff_qty,
                "note_date": note_date,
                "note_text": note_text,
                "status": "COMPLETED",
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

        # Nhập kho & Xuất kho định kỳ cho 11 nhà cung cấp bổ sung (SP077 -> SP109)
        extra_supplier_batches = [
            ("PN-202605-004", "SUP_E2E_160432804590", datetime(2026, 5, 23, 8, 30), ["SP077", "SP078", "SP079", "SP080"]),
            ("PN-202605-005", "SUP_E2E_154720745019", datetime(2026, 5, 23, 9, 30), ["SP081", "SP082", "SP083"]),
            ("PN-202605-006", "SUP_E2E_151733885016", datetime(2026, 5, 23, 10, 30), ["SP084", "SP085", "SP086"]),
            ("PN-202605-007", "SUP_E2E_132517808823", datetime(2026, 5, 23, 13, 30), ["SP087", "SP088", "SP089"]),
            ("PN-202605-008", "SUP_E2E_122956130472", datetime(2026, 5, 23, 14, 30), ["SP090", "SP091", "SP092"]),
            ("PN-202605-009", "SUP_E2E_121134649607", datetime(2026, 5, 23, 15, 30), ["SP093", "SP094", "SP095"]),
            ("PN-202605-010", "SUP_E2E_120920994502", datetime(2026, 5, 24, 8, 30), ["SP096", "SP097", "SP098"]),
            ("PN-202605-011", "SUP_E2E_120824350246", datetime(2026, 5, 24, 9, 30), ["SP099", "SP100", "SP101"]),
            ("PN-202605-012", "SUP_E2E_130519140787", datetime(2026, 5, 24, 13, 30), ["SP102", "SP103", "SP104"]),
            ("PN-202605-013", "SUP_AI", datetime(2026, 5, 25, 9, 0), ["SP105", "SP106", "SP107"]),
            ("PN-202605-014", "SUP-ACID-TEST", datetime(2026, 5, 25, 10, 30), ["SP108", "SP109"]),
        ]
        for imp_code, sup_code, dt, skus in extra_supplier_batches:
            batch_items = []
            for sku in skus:
                p = prod_map[sku]
                batch_items.append((sku, 35, round(p.standard_price * 0.76, -3)))
            record_import(imp_code, sup_code, dt, batch_items, f"Nhập hàng khởi tạo từ đối tác {sup_map[sup_code].name}")

        # Xuất luân chuyển đều đặn cho SP077 -> SP109 (đảm bảo không bị cảnh báo Dead Stock hoặc Low Stock)
        record_export(
            "PX-202607-15",
            "Công ty Cổ phần Phần mềm VTI Solutions",
            datetime(2026, 7, 15, 10, 0),
            [(f"SP{i:03d}", 3) for i in range(77, 94)],
            "Xuất linh kiện và phụ kiện nâng cấp định kỳ đợt 1",
        )
        record_export(
            "PX-202607-20",
            "Trường Đại học Công nghệ FPT",
            datetime(2026, 7, 20, 14, 0),
            [(f"SP{i:03d}", 3) for i in range(94, 110)],
            "Xuất thiết bị ngoại vi trang bị phòng thực hành đợt 2",
        )
        record_export(
            "PX-202610-012",
            "Cửa hàng Bán lẻ Tin học Nguyễn Kim",
            datetime(2026, 10, 4, 9, 30),
            [(f"SP{i:03d}", 2) for i in range(77, 94)],
            "Xuất sỉ linh kiện và phụ kiện bổ sung kệ hàng tháng 10",
        )
        record_export(
            "PX-202610-013",
            "Hệ thống CyberCore Gaming Stadium",
            datetime(2026, 10, 6, 15, 0),
            [(f"SP{i:03d}", 2) for i in range(94, 110)],
            "Xuất thiết bị ngoại vi và gaming gear đầu tháng 10",
        )

        # Biên bản kiểm kê kho định kỳ rải qua các tháng (ADJUSTMENT)
        record_adjustment(
            "KK-202606-001",
            "SP017",
            2,
            datetime(2026, 6, 30, 17, 30),
            "Kiểm kê định kỳ cuối tháng 06/2026: Phát hiện dư 2 sản phẩm do nhập sót chứng từ lô phụ kiện",
        )
        record_adjustment(
            "KK-202607-001",
            "SP068",
            -1,
            datetime(2026, 7, 31, 17, 15),
            "Kiểm kê định kỳ cuối tháng 07/2026: Xuất hủy 1 sản phẩm hỏng bao bì trong quá trình lưu kho",
        )
        record_adjustment(
            "KK-202608-001",
            "SP016",
            3,
            datetime(2026, 8, 31, 17, 45),
            "Kiểm kê định kỳ mùa tựu trường tháng 08/2026: Điều chỉnh tăng 3 sợi cáp mạng kiểm đếm thực tế tại kệ B2",
        )
        record_adjustment(
            "KK-202609-001",
            "SP087",
            -2,
            datetime(2026, 9, 30, 17, 30),
            "Kiểm kê định kỳ cuối quý 3/2026: Điều chỉnh giảm 2 sợi cáp HDMI lỗi đầu kết nối khi kiểm tra kỹ thuật",
        )

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

            elif ev_type == "ADJUSTMENT":
                sku = ev["sku"]
                diff_qty = int(ev["diff_qty"])
                p = prod_map[sku]
                if p.current_stock + diff_qty >= 0 and diff_qty != 0:
                    p.current_stock += diff_qty
                    db.add(
                        StockLedger(
                            product_id=p.id,
                            transaction_type="ADJUSTMENT",
                            reference_code=ev["code"],
                            quantity_change=diff_qty,
                            balance_after=p.current_stock,
                            created_by=thukho_user.id,
                            transaction_date=note_date,
                            note=ev["note_text"],
                        )
                    )

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
