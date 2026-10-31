"""Dependencies dùng chung cho các API endpoints (Authentication, Authorization & Rate Limiting)."""

from collections import defaultdict, deque
import math
import threading
import time
from typing import Callable, Deque, Dict, List, Optional, Tuple
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User


class SlidingWindowRateLimiter:
    """Bộ giới hạn tần suất (Rate Limiter) In-Memory theo thuật toán cửa sổ trượt (Sliding Window)."""

    def __init__(self) -> None:
        self._buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, max_requests: int = 10, window_seconds: int = 60) -> Tuple[bool, int]:
        """Kiểm tra và ghi nhận lượt gọi trong cửa sổ trượt.

        Trả về (allowed, retry_after_seconds).
        """
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            q = self._buckets[key]
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= max_requests:
                retry_after = max(1, int(math.ceil(window_seconds - (now - q[0]))))
                return False, retry_after
            q.append(now)
            return True, 0

    def reset(self) -> None:
        """Xóa toàn bộ bộ đếm (phục vụ kiểm thử tự động)."""
        with self._lock:
            self._buckets.clear()


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Trích xuất đúng địa chỉ IP thực của client phía sau Reverse Proxy (Nginx)."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def rate_limit_login(request: Request) -> None:
    """Giới hạn đăng nhập tối đa 10 lần/phút trên mỗi IP client."""
    client_ip = get_client_ip(request)
    allowed, retry_after = rate_limiter.check(f"login:{client_ip}", max_requests=10, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quá nhiều yêu cầu đăng nhập từ địa chỉ IP của bạn (tối đa 10 lần/phút). Vui lòng thử lại sau {retry_after} giây.",
            headers={"Retry-After": str(retry_after)},
        )


def check_ai_rate_limit(current_user: User) -> None:
    """Giới hạn gọi trực tiếp AI (/ai/ask hoặc force_refresh=true) tối đa 10 lần/phút trên mỗi tài khoản."""
    allowed, retry_after = rate_limiter.check(f"ai:{current_user.username}", max_requests=10, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Bạn đã vượt quá giới hạn gọi tác vụ AI (tối đa 10 lần/phút). Vui lòng thử lại sau {retry_after} giây.",
            headers={"Retry-After": str(retry_after)},
        )


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login-form",
    auto_error=False,
)


def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    st = getattr(request.state, "stage_timing", None)
    if st:
        st.t_deps_start = time.perf_counter()
        st.t_auth_start = st.t_deps_start
    """Dependency trích xuất và xác thực người dùng từ Bearer JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa cung cấp mã xác thực (Token) trong header Authorization.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã xác thực không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng tương ứng với token không tồn tại trong hệ thống.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản này hiện đang bị tạm khóa.",
        )

    if st:
        st.t_auth_end = time.perf_counter()
    return user


def require_roles(allowed_roles: List[str]) -> Callable[[User], User]:
    """Dependency Factory kiểm tra vai trò người dùng (RBAC).

    Trả về HTTP 403 nếu người dùng không thuộc danh sách vai trò cho phép.
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền truy cập bị từ chối. Thao tác này yêu cầu một trong các vai trò: {', '.join(allowed_roles)}.",
            )
        return current_user

    return role_checker
