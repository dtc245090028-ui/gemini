"""Cổng điều phối ghi (Write Gate) & Cơ chế Backpressure cho SmartKho.

Đảm bảo:
1. Thread-safe: Sử dụng threading primitives (threading.Semaphore & Lock) tương thích hoàn toàn
   với các synchronous `def` endpoints chạy trong AnyIO worker threadpool. (KHÔNG dùng asyncio.Lock).
2. Kiểm soát Backpressure tầng ngoài: Tính thời gian chờ từ lúc request chạm server (arrival_time).
   Nếu thời gian chờ vượt quá `WRITE_QUEUE_TIMEOUT_SECONDS` hoặc số request đang chờ vượt quá
   `WRITE_QUEUE_MAX_SIZE`, chủ động trả về HTTP 503 kèm `Retry-After`.
3. Bảo vệ SQLite ACID: Điều phối số lượng giao dịch ghi đồng thời tối đa, hỗ trợ BEGIN IMMEDIATE.
"""

import os
import threading
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

class WriteGate:
    def __init__(self):
        self.enabled = os.environ.get("WRITE_GATE_ENABLED", "1").strip() == "1"
        self.max_queue_size = int(os.environ.get("WRITE_QUEUE_MAX_SIZE", "150"))
        self.timeout_seconds = float(os.environ.get("WRITE_QUEUE_TIMEOUT_SECONDS", "3.5"))
        self.concurrency_limit = int(os.environ.get("WRITE_CONCURRENCY_LIMIT", "10"))

        self._lock = threading.Lock()
        self._current_in_flight = 0
        self._waiting_count = 0
        self._semaphore = threading.Semaphore(self.concurrency_limit)
        
        # Thống kê hoạt động của Cổng ghi
        self.total_admitted = 0
        self.total_rejected_queue_full = 0
        self.total_rejected_timeout = 0

    def acquire(self, arrival_time: Optional[float] = None) -> bool:
        """Xin cấp quyền thực thi giao dịch ghi.
        
        Trả về True nếu được cấp quyền.
        Ném HTTPException(503) kèm header Retry-After nếu hàng đợi đầy hoặc quá hạn chờ.
        """
        if not self.enabled:
            return True

        now = time.perf_counter()
        arr_t = arrival_time if arrival_time is not None else now

        with self._lock:
            # 1. Kiểm tra độ sâu hàng đợi (Queue Depth Limit)
            if self._current_in_flight + self._waiting_count >= self.max_queue_size:
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

            self._waiting_count += 1

        # 3. Chờ nhận token từ Semaphore với thời gian còn lại
        time_already_waited = time.perf_counter() - arr_t
        remaining_time = max(0.05, self.timeout_seconds - time_already_waited)

        acquired = self._semaphore.acquire(timeout=remaining_time)
        with self._lock:
            self._waiting_count = max(0, self._waiting_count - 1)
            if not acquired:
                self.total_rejected_timeout += 1
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Không thể lấy khóa ghi trong thời gian cho phép. Hệ thống đang bảo vệ trạng thái giao dịch.",
                    headers={"Retry-After": "2"},
                )
            self._current_in_flight += 1
            self.total_admitted += 1
            return True

    def release(self):
        """Giải phóng token ghi sau khi hoàn tất giao dịch (kể cả khi thành công hay thất bại)."""
        if not self.enabled:
            return
        with self._lock:
            self._current_in_flight = max(0, self._current_in_flight - 1)
        self._semaphore.release()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "concurrency_limit": self.concurrency_limit,
                "max_queue_size": self.max_queue_size,
                "timeout_seconds": self.timeout_seconds,
                "current_in_flight": self._current_in_flight,
                "waiting_count": self._waiting_count,
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
