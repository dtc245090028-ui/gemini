"""Endpoints xác thực tài khoản, cấp phát JWT và thông tin người dùng."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Xác thực & Người dùng"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập bằng JSON (dùng cho Frontend React)",
)
def login_json(
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """Đăng nhập bằng username/password qua JSON body và nhận JWT token."""
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này hiện đang bị tạm khóa.",
        )

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


@router.post(
    "/login-form",
    summary="Đăng nhập chuẩn OAuth2 Form (dùng cho Swagger UI Authorize)",
)
def login_oauth2_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Endpoint hỗ trợ nút Authorize trực tiếp trên giao diện tài liệu Swagger /docs."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này hiện đang bị tạm khóa.",
        )

    token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin tài khoản đang đăng nhập",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """Trả về thông tin chi tiết của người dùng hiện tại dựa trên Bearer token."""
    return current_user


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tài khoản mới (Chỉ dành cho ADMIN)",
)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN"])),
):
    """Quản trị viên tạo tài khoản mới trong hệ thống."""
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tên đăng nhập '{user_in.username}' đã được sử dụng.",
        )

    new_user = User(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role.value if hasattr(user_in.role, "value") else str(user_in.role),
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
