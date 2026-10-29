import os
import threading
import time
from typing import Dict, Any, List

class StageTiming:
    def __init__(self):
        self.t_arrival: float = 0.0
        self.t_deps_start: float = 0.0
        self.t_auth_start: float = 0.0
        self.t_auth_end: float = 0.0
        self.t_handler_enter: float = 0.0
        self.t_tx_start: float = 0.0
        self.t_commit_start: float = 0.0
        self.t_commit_end: float = 0.0
        self.t_handler_exit: float = 0.0
        self.t_response_done: float = 0.0

class WriteMetricsCollector:
    def __init__(self):
        self.enabled = os.environ.get("WRITE_METRICS", "0").strip() == "1"
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.tx_count = 0
            self.retry_count = 0
            self.total_retry_sleep_ms = 0.0
            self.active_concurrent_writes = 0
            self.max_concurrent_writes = 0
            self.waiting_threads = 0
            self.max_waiting_threads = 0

            # Mảng lưu trữ chi tiết từng chặng (đơn vị: ms)
            self.samples_arrival_to_deps: List[float] = []
            self.samples_auth: List[float] = []
            self.samples_threadpool_wait: List[float] = []
            self.samples_tx_exec: List[float] = []
            self.samples_commit: List[float] = []
            self.samples_serialize_send: List[float] = []
            self.samples_total_server: List[float] = []

    def record_retry(self, sleep_ms: float):
        if not self.enabled:
            return
        with self._lock:
            self.retry_count += 1
            self.total_retry_sleep_ms += sleep_ms

    def enter_write_queue(self):
        if not self.enabled:
            return
        with self._lock:
            self.waiting_threads += 1
            if self.waiting_threads > self.max_waiting_threads:
                self.max_waiting_threads = self.waiting_threads

    def enter_transaction(self):
        if not self.enabled:
            return
        with self._lock:
            self.waiting_threads = max(0, self.waiting_threads - 1)
            self.active_concurrent_writes += 1
            if self.active_concurrent_writes > self.max_concurrent_writes:
                self.max_concurrent_writes = self.active_concurrent_writes

    def exit_transaction(self, tx_time_ms: float = 0.0, commit_time_ms: float = 0.0):
        if not self.enabled:
            return
        with self._lock:
            self.active_concurrent_writes = max(0, self.active_concurrent_writes - 1)
            self.tx_count += 1

    def record_stages(self, st: StageTiming):
        if not self.enabled:
            return
        with self._lock:
            t_arr = st.t_arrival
            t_deps = st.t_deps_start or t_arr
            t_a_start = st.t_auth_start or t_deps
            t_a_end = st.t_auth_end or t_a_start
            t_h_in = st.t_handler_enter or t_a_end
            t_tx_start = st.t_tx_start or t_h_in
            t_com_start = st.t_commit_start or t_tx_start
            t_com_end = st.t_commit_end or t_com_start
            t_h_out = st.t_handler_exit or t_com_end
            t_resp = st.t_response_done or t_h_out

            s1 = max(0.0, (t_deps - t_arr) * 1000.0)
            s2 = max(0.0, (t_a_end - t_a_start) * 1000.0)
            s3 = max(0.0, (t_tx_start - t_a_end) * 1000.0)
            s4_5 = max(0.0, (t_com_start - t_tx_start) * 1000.0)
            s6 = max(0.0, (t_com_end - t_com_start) * 1000.0)
            s7 = max(0.0, (t_resp - t_com_end) * 1000.0)
            s_total = max(0.0, (t_resp - t_arr) * 1000.0)

            self.samples_arrival_to_deps.append(s1)
            self.samples_auth.append(s2)
            self.samples_threadpool_wait.append(s3)
            self.samples_tx_exec.append(s4_5)
            self.samples_commit.append(s6)
            self.samples_serialize_send.append(s7)
            self.samples_total_server.append(s_total)

    @staticmethod
    def _calc_percentiles(samples: List[float]) -> Dict[str, float]:
        if not samples:
            return {"count": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
        s = sorted(samples)
        n = len(s)
        mean_val = sum(s) / n
        p50 = s[int(n * 0.50)]
        p95 = s[min(n - 1, int(n * 0.95))]
        p99 = s[min(n - 1, int(n * 0.99))]
        max_val = s[-1]
        return {
            "count": n,
            "mean": round(mean_val, 2),
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "max": round(max_val, 2),
        }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            avg_sleep = (self.total_retry_sleep_ms / self.retry_count) if self.retry_count else 0.0
            return {
                "enabled": self.enabled,
                "tx_count": self.tx_count,
                "retry_count": self.retry_count,
                "total_retry_sleep_ms": round(self.total_retry_sleep_ms, 2),
                "avg_retry_sleep_ms": round(avg_sleep, 2),
                "max_concurrent_writes": self.max_concurrent_writes,
                "max_waiting_threads": self.max_waiting_threads,
                "stages": {
                    "1_arrival_to_deps": self._calc_percentiles(self.samples_arrival_to_deps),
                    "2_auth_and_deps": self._calc_percentiles(self.samples_auth),
                    "3_threadpool_wait_to_handler": self._calc_percentiles(self.samples_threadpool_wait),
                    "4_tx_exec": self._calc_percentiles(self.samples_tx_exec),
                    "5_commit": self._calc_percentiles(self.samples_commit),
                    "6_serialize_and_send": self._calc_percentiles(self.samples_serialize_send),
                    "7_total_server_time": self._calc_percentiles(self.samples_total_server),
                }
            }

write_metrics = WriteMetricsCollector()
