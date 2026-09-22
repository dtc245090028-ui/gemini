"""Khởi tạo dữ liệu mẫu ban đầu (Seed Data) với cơ chế Idempotent an toàn."""

from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models.user import User


def seed_default_users(db: Session) -> None:
    """Tự động tạo 3 tài khoản mặc định (Admin, Thủ kho, Kế toán) nếu chưa tồn tại.

    Cơ chế Idempotent: Kiểm tra sự tồn tại của username trước khi thêm mới,
    tránh lỗi trùng khóa chính hoặc vi phạm ràng buộc Unique khi server khởi động lại nhiều lần.
    """
    default_users = [
        {
            "username": "admin",
            "password": "admin123",
            "full_name": "Quản trị viên Hệ thống",
            "role": "ADMIN",
        },
        {
            "username": "thukho",
            "password": "thukho123",
            "full_name": "Thủ kho Chính",
            "role": "WAREHOUSE_KEEPER",
        },
        {
            "username": "ketoan",
            "password": "ketoan123",
            "full_name": "Kế toán Kho",
            "role": "ACCOUNTANT",
        },
    ]

    has_new_user = False
    for u in default_users:
        existing = db.query(User).filter_by(username=u["username"]).first()
        if not existing:
            new_user = User(
                username=u["username"],
                password_hash=get_password_hash(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True,
            )
            db.add(new_user)
            has_new_user = True

    if has_new_user:
        db.commit()
