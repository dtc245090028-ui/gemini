import threading
import time
from typing import Dict, Any

class WriteMetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.tx_count = 0
            self.retry_count = 0
            self.total_retry_sleep_ms = 0.0
            self.total_commit_time_ms = 0.0
            self.total_tx_time_ms = 0.0
            self.active_concurrent_writes = 0
            self.max_concurrent_writes = 0
            self.waiting_threads = 0
            self.max_waiting_threads = 0

    def record_retry(self, sleep_ms: float):
        with self._lock:
            self.retry_count += 1
            self.total_retry_sleep_ms += sleep_ms

    def enter_write_queue(self):
        with self._lock:
            self.waiting_threads += 1
            if self.waiting_threads > self.max_waiting_threads:
                self.max_waiting_threads = self.waiting_threads

    def enter_transaction(self):
        with self._lock:
            self.waiting_threads = max(0, self.waiting_threads - 1)
            self.active_concurrent_writes += 1
            if self.active_concurrent_writes > self.max_concurrent_writes:
                self.max_concurrent_writes = self.active_concurrent_writes

    def exit_transaction(self, tx_time_ms: float, commit_time_ms: float):
        with self._lock:
            self.active_concurrent_writes = max(0, self.active_concurrent_writes - 1)
            self.tx_count += 1
            self.total_tx_time_ms += tx_time_ms
            self.total_commit_time_ms += commit_time_ms

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            avg_tx = (self.total_tx_time_ms / self.tx_count) if self.tx_count else 0.0
            avg_commit = (self.total_commit_time_ms / self.tx_count) if self.tx_count else 0.0
            avg_sleep = (self.total_retry_sleep_ms / self.retry_count) if self.retry_count else 0.0
            return {
                "tx_count": self.tx_count,
                "retry_count": self.retry_count,
                "total_retry_sleep_ms": round(self.total_retry_sleep_ms, 2),
                "avg_retry_sleep_ms": round(avg_sleep, 2),
                "avg_tx_time_ms": round(avg_tx, 2),
                "avg_commit_time_ms": round(avg_commit, 2),
                "max_concurrent_writes": self.max_concurrent_writes,
                "max_waiting_threads": self.max_waiting_threads,
            }

write_metrics = WriteMetricsCollector()
