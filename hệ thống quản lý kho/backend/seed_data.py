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
            ("CAT_PK", "Phụ kiện máy tính", "Bàn phím, chuột, tai nghe, lót chuột"),
            ("CAT_LK", "Linh kiện phần cứng", "Ổ cứng SSD, RAM, nguồn, tản nhiệt"),
            ("CAT_TB", "Thiết bị ngoại vi", "Màn hình, webcam, máy in, loa"),
            ("CAT_NET", "Thiết bị mạng", "Router Wifi, switch chia mạng, cáp mạng"),
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
                    status="ACTIVE",
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            prod_map[code] = p

        # =====================================================================
        # 5. SINH LỊCH SỬ GIAO DỊCH 60 NGÀY (NHẬP - XUẤT - THẺ KHO)
        # =====================================================================
        print("[INFO] 5. Sinh chuoi giao dich nhap xuat 60 ngay theo kich ban logic...")
        now = datetime.now()

        # Kiểm tra nếu đã có phiếu nhập của SP001 thì bỏ qua bước sinh giao dịch để tránh nhân đôi
        existing_import = (
            db.query(ImportNote).filter(ImportNote.code == "PN-SEED-INIT-01").first()
        )
        if existing_import:
            print("[INFO] Du lieu giao dich 60 ngay da ton tai, hoan tat cap nhat!")
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
