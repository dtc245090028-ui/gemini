"""API Endpoints cho Server-Sent Events (SSE) thời gian thực."""

import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.core.events import broadcaster
from app.models.user import User

logger = logging.getLogger("app.events.api")

router = APIRouter(prefix="/events", tags=["Thời gian thực & Sự kiện (Real-time Events)"])


@router.get(
    "/stream",
    summary="Đăng ký nhận luồng sự kiện thời gian thực (Server-Sent Events)",
    response_description="Luồng sự kiện văn bản định dạng text/event-stream",
)
async def event_stream(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Cung cấp kết nối Server-Sent Events (SSE) liên tục cho trình duyệt:
    
    - Xác thực an toàn qua Header Authorization: Bearer <token> (không để lộ token trên URL).
    - Tự động phát heartbeat định kỳ mỗi 15 giây để duy trì kết nối qua proxy.
    - Hàng đợi có giới hạn (bounded queue) chống rò rỉ bộ nhớ.
    - Tự động giải phóng tài nguyên khi client đóng kết nối.
    """
    queue = await broadcaster.subscribe()

    async def event_generator():
        # 1. Phát thông điệp kết nối thành công và heartbeat ban đầu
        yield ": connected\n\n"
        try:
            while True:
                # Kiểm tra xem client đã ngắt kết nối chưa
                if await request.is_disconnected():
                    break
                try:
                    # Chờ sự kiện mới hoặc timeout heartbeat
                    msg = await asyncio.wait_for(queue.get(), timeout=broadcaster.heartbeat_interval_s)
                    yield msg
                except asyncio.TimeoutError:
                    # Phát heartbeat giữ kết nối
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Yêu cầu Nginx không buffer dữ liệu SSE
        },
    )


@router.get(
    "/stats",
    summary="Thống kê trạng thái luồng SSE và hiệu quả gom sự kiện (Debounce)",
)
def get_event_stats(current_user: User = Depends(get_current_user)):
    """Trả về số subscriber đang kết nối, số thay đổi ghi nhận và số sự kiện đã gom."""
    return broadcaster.get_stats()
