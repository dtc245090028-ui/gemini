"""Hệ thống Quản lý Sự kiện Thời gian thực (Real-time SSE Event Broadcaster).

Đặc điểm kiến trúc:
1. In-Memory Pub/Sub: Quản lý danh sách kết nối SSE clients thông qua asyncio.Queue có giới hạn (bounded queue)
   để loại bỏ hoàn toàn nguy cơ rò rỉ bộ nhớ (memory leak).
2. Event Debouncing & Batching (Gom sự kiện):
   Khi có dồn tải ghi lớn (hàng trăm transaction/giây), cơ chế gom sự kiện (~150ms-250ms) tự động
   tổng hợp các tài nguyên bị thay đổi thành một sự kiện duy nhất để trình duyệt không bị treo/quá tải.
   Chứng minh: số sự kiện phát ra << số transaction ghi.
3. Heartbeat: Định kỳ phát ': keepalive\\n\\n' mỗi 15 giây để ngăn chặn timeout từ Nginx / Proxy.
4. An toàn ACID: Sự kiện CHỈ ĐƯỢC PHÁT SAU KHI GIAO DỊCH DATABASE COMMIT THÀNH CÔNG.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Set

logger = logging.getLogger("app.events")


class EventResource:
    """Định danh tài nguyên chuẩn cho hệ thống sự kiện thời gian thực (Single Source of Truth)."""
    PRODUCTS = "products"
    CATEGORIES = "categories"
    SUPPLIERS = "suppliers"
    IMPORT_NOTES = "import_notes"
    EXPORT_NOTES = "export_notes"
    STOCK_LEDGER = "stock_ledger"
    REPORTS = "reports"

    @classmethod
    def all_resources(cls) -> Set[str]:
        return {
            cls.PRODUCTS,
            cls.CATEGORIES,
            cls.SUPPLIERS,
            cls.IMPORT_NOTES,
            cls.EXPORT_NOTES,
            cls.STOCK_LEDGER,
            cls.REPORTS,
        }


class EventBroadcaster:
    def __init__(self, debounce_window_s: float = 0.2, heartbeat_interval_s: float = 15.0):
        self.debounce_window_s = debounce_window_s
        self.heartbeat_interval_s = heartbeat_interval_s
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock: Optional[asyncio.Lock] = None
        
        # Debounce buffer
        self._pending_events: Dict[str, Dict] = {}
        self._debounce_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Metrics theo dõi hiệu năng gom sự kiện
        self.total_mutations_recorded = 0
        self.total_events_emitted = 0

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def _get_loop(self):
        if self._loop is not None and not self._loop.is_closed():
            return self._loop
        try:
            self._loop = asyncio.get_running_loop()
            return self._loop
        except RuntimeError:
            return None

    async def subscribe(self) -> asyncio.Queue:
        """Đăng ký một subscriber mới với hàng đợi giới hạn kích thước (maxsize=100)."""
        q = asyncio.Queue(maxsize=100)
        async with self.lock:
            self._subscribers.add(q)
            logger.debug(f"[SSE] Client connected. Total active subscribers: {len(self._subscribers)}")
        return q

    async def unsubscribe(self, q: asyncio.Queue):
        """Hủy đăng ký và giải phóng tài nguyên khi client ngắt kết nối."""
        async with self.lock:
            self._subscribers.discard(q)
            logger.debug(f"[SSE] Client disconnected. Remaining subscribers: {len(self._subscribers)}")

    def publish_after_commit(
        self,
        resource: str,
        action: str,
        client_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Hàm đồng bộ an toàn được gọi từ worker thread sau khi `db.commit()` thành công.
        
        Tự động ủy quyền vào Async Event Loop để gom và phát sự kiện.
        Hoàn toàn an toàn trong môi trường synchronous unit testing (nếu không có event loop thì bỏ qua).
        """
        self.total_mutations_recorded += 1
        try:
            from app.core.http_cache import increment_resource_version
            increment_resource_version(resource)
        except Exception:
            pass
        loop = self._get_loop()
        if loop is not None and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._schedule_debounced_event(resource, action, client_id, metadata),
                    loop,
                )
            except Exception as e:
                logger.warning(f"[SSE] Không thể điều phối sự kiện: {e}")

    async def _schedule_debounced_event(
        self,
        resource: str,
        action: str,
        client_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """Gom các thay đổi trong cửa sổ debounce_window_s."""
        async with self.lock:
            key = f"{resource}:{action}"
            if key not in self._pending_events:
                self._pending_events[key] = {
                    "resource": resource,
                    "action": action,
                    "count": 1,
                    "client_ids": {client_id} if client_id else set(),
                    "first_seen": time.perf_counter(),
                    "last_seen": time.perf_counter(),
                }
            else:
                entry = self._pending_events[key]
                entry["count"] += 1
                entry["last_seen"] = time.perf_counter()
                if client_id:
                    entry["client_ids"].add(client_id)

            if self._debounce_task is None or self._debounce_task.done():
                self._debounce_task = asyncio.create_task(self._flush_debounced_events())

    async def _flush_debounced_events(self):
        """Chờ hết cửa sổ debounce rồi phát một mẻ sự kiện tổng hợp cho mọi clients."""
        await asyncio.sleep(self.debounce_window_s)
        
        async with self.lock:
            events_to_emit = list(self._pending_events.values())
            self._pending_events.clear()
            subscribers_snapshot = list(self._subscribers)

        if not events_to_emit or not subscribers_snapshot:
            return

        for ev in events_to_emit:
            self.total_events_emitted += 1
            payload = {
                "event": "data_changed",
                "resource": ev["resource"],
                "action": ev["action"],
                "mutation_count": ev["count"],
                "client_ids": list(ev["client_ids"]),
                "timestamp": time.time(),
                "delay_ms": round((time.perf_counter() - ev["first_seen"]) * 1000.0, 2),
            }
            msg = f"event: data_changed\ndata: {json.dumps(payload)}\n\n"
            
            for q in subscribers_snapshot:
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    # Client xử lý quá chậm hoặc bị treo, bỏ qua để bảo vệ bộ nhớ
                    pass

    def get_stats(self) -> Dict:
        return {
            "active_subscribers": len(self._subscribers),
            "total_mutations_recorded": self.total_mutations_recorded,
            "total_events_emitted": self.total_events_emitted,
            "batching_efficiency_ratio": (
                round(self.total_mutations_recorded / self.total_events_emitted, 2)
                if self.total_events_emitted > 0
                else 1.0
            ),
        }

broadcaster = EventBroadcaster()
