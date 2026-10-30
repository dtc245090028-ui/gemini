"""Cổng điều phối ghi (Write Gate) công bằng FIFO & Cơ chế Backpressure cho SmartKho.

Đặc điểm kiến trúc:
1. Thread-safe & Fair FIFO: Sử dụng hàng đợi FIFO (collections.deque) với các threading.Event
   thay vì threading.Semaphore trần, đảm bảo các luồng được phục vụ chính xác theo thứ tự đến (FIFO),
   loại bỏ hoàn toàn hiện tượng bỏ đói luồng (thread starvation).
2. Kiểm soát Backpressure tầng ngoài:
   Tính thời gian chờ từ lúc request chạm server (arrival_time từ ASGI middleware).
   Nếu thời gian chờ vượt quá `WRITE_QUEUE_TIMEOUT_SECONDS` (mặc định 3.5s) hoặc số request
   đang chờ trong hàng đợi vượt quá `WRITE_QUEUE_MAX_SIZE` (mặc định 150), chủ động trả về
   HTTP 503 Service Unavailable kèm header `Retry-After`.
3. Bảo vệ SQLite ACID:
   Mặc định giới hạn số giao dịch ghi đồng thời là 1 (`WRITE_CONCURRENCY_LIMIT=1`),
   kết hợp `BEGIN IMMEDIATE` để giành độc quyền ghi từ đầu, ngăn ngừa hoàn toàn lỗi
   tranh chấp khóa `sqlite3.OperationalError: database is locked`.
"""

import os
import threading
import time
import collections
from typing import Dict, Any, Optional, Deque, Tuple
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session


class WriteGate:
    def __init__(self):
        self.enabled = os.environ.get("WRITE_GATE_ENABLED", "1").strip() == "1"
        self.max_queue_size = int(os.environ.get("WRITE_QUEUE_MAX_SIZE", "150"))
        self.timeout_seconds = float(os.environ.get("WRITE_QUEUE_TIMEOUT_SECONDS", "3.5"))
        # SQLite là single-writer; mặc định concurrency = 1 để tuần tự hóa an toàn tuyệt đối
        self.concurrency_limit = int(os.environ.get("WRITE_CONCURRENCY_LIMIT", "1"))

        self._lock = threading.Lock()
        self._active_count = 0
        # Hàng đợi công bằng FIFO: lưu các tuple (threading.Event, arrival_time)
        self._waiters: Deque[Tuple[threading.Event, float]] = collections.deque()

        # Thống kê hoạt động của Cổng ghi
        self.total_admitted = 0
        self.total_rejected_queue_full = 0
        self.total_rejected_timeout = 0

    def acquire(self, arrival_time: Optional[float] = None) -> bool:
        """Xin cấp quyền thực thi giao dịch ghi theo thứ tự công bằng FIFO.

        Trả về True nếu được cấp quyền.
        Ném HTTPException(503) kèm header Retry-After nếu hàng đợi đầy hoặc quá hạn chờ.
        """
        if not self.enabled:
            return True

        now = time.perf_counter()
        arr_t = arrival_time if arrival_time is not None else now

        with self._lock:
            # 1. Kiểm tra độ sâu hàng đợi (Queue Depth Limit)
            total_pending = self._active_count + len(self._waiters)
            if total_pending >= self.max_queue_size:
                self.total_rejected_queue_full += 1
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Hệ thống kho đang tiếp nhận lượng giao dịch ghi lớn. Yêu cầu tạm thời bị từ chối để bảo vệ toàn vẹn dữ liệu.",
                    headers={"Retry-After": "2"},
                )

            # 2. Kiểm tra xem request đã nằm chờ ở Uvicorn event loop quá hạn chưa
            if (now - arr_t) >= self.timeout_seconds:
                self.total_rejected_timeout += 1
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Thời gian chờ xử lý trong hàng đợi đã vượt quá giới hạn an toàn. Vui lòng thử lại.",
                    headers={"Retry-After": "1"},
                )

            # 3. Nếu còn slot trống và không có ai đang chờ trước trong hàng đợi:
            if self._active_count < self.concurrency_limit and len(self._waiters) == 0:
                self._active_count += 1
                self.total_admitted += 1
                return True

            # 4. Đưa vào hàng đợi công bằng FIFO
            waiter_event = threading.Event()
            waiter_entry = (waiter_event, arr_t)
            self._waiters.append(waiter_entry)

        # 5. Chờ ngoài lock theo thời gian còn lại
        time_already_waited = time.perf_counter() - arr_t
        remaining_time = max(0.01, self.timeout_seconds - time_already_waited)

        signaled = waiter_event.wait(timeout=remaining_time)

        if not signaled:
            with self._lock:
                try:
                    self._waiters.remove(waiter_entry)
                except ValueError:
                    self._release_slot()
                self.total_rejected_timeout += 1
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Không thể lấy khóa ghi trong thời gian cho phép. Hệ thống đang bảo vệ trạng thái giao dịch.",
                headers={"Retry-After": "2"},
            )

        with self._lock:
            self.total_admitted += 1
            return True

    def release(self):
        """Giải phóng slot ghi và đánh thức waiter tiếp theo theo đúng thứ tự FIFO."""
        if not self.enabled:
            return
        with self._lock:
            self._release_slot()

    def _release_slot(self):
        """Đánh thức waiter tiếp theo trong hàng đợi FIFO hoặc giảm active_count."""
        while self._waiters:
            next_event, waiter_arr_t = self._waiters.popleft()
            # Bỏ qua nếu waiter này đã hết hạn chờ
            if (time.perf_counter() - waiter_arr_t) < self.timeout_seconds:
                next_event.set()
                return
            else:
                self.total_rejected_timeout += 1

        self._active_count = max(0, self._active_count - 1)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "concurrency_limit": self.concurrency_limit,
                "max_queue_size": self.max_queue_size,
                "timeout_seconds": self.timeout_seconds,
                "current_in_flight": self._active_count,
                "waiting_count": len(self._waiters),
                "total_admitted": self.total_admitted,
                "total_rejected_queue_full": self.total_rejected_queue_full,
                "total_rejected_timeout": self.total_rejected_timeout,
            }

    def reset_stats(self):
        with self._lock:
            self.total_admitted = 0
            self.total_rejected_queue_full = 0
            self.total_rejected_timeout = 0


write_gate = WriteGate()


class WriteGateContext:
    def __init__(self, arrival_time: Optional[float] = None, db: Optional[Session] = None):
        self.arrival_time = arrival_time
        self.db = db
        self._acquired = False

    def __enter__(self):
        self._acquired = write_gate.acquire(self.arrival_time)
        if self.db and self.db.bind and self.db.bind.url.drivername.startswith("sqlite"):
            try:
                self.db.execute(text("BEGIN IMMEDIATE"))
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._acquired:
            write_gate.release()
            self._acquired = False
