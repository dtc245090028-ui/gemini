import os
import time
import threading
from typing import Dict, Any, List
import anyio.to_thread

class BenchTrafficMonitor:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.arrivals_by_sec: Dict[int, int] = {}
            self.completions_by_sec: Dict[int, int] = {}
            self.limiter_samples: List[Dict[str, Any]] = []
            self.t_start = time.time()

    def record_arrival(self):
        sec = int(time.time())
        with self._lock:
            self.arrivals_by_sec[sec] = self.arrivals_by_sec.get(sec, 0) + 1

    def record_completion(self):
        sec = int(time.time())
        with self._lock:
            self.completions_by_sec[sec] = self.completions_by_sec.get(sec, 0) + 1

    def sample_limiter(self):
        try:
            limiter = anyio.to_thread.current_default_thread_limiter()
            stats = limiter.statistics()
            now = time.time()
            with self._lock:
                # Giữ tối đa 1.000 mẫu để không tốn RAM
                if len(self.limiter_samples) < 1000:
                    self.limiter_samples.append({
                        "t": round(now - self.t_start, 3),
                        "borrowed": stats.borrowed_tokens,
                        "total": stats.total_tokens,
                        "waiting": stats.tasks_waiting
                    })
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            # Sắp xếp theo giây tương đối từ giây đầu tiên
            all_secs = sorted(set(list(self.arrivals_by_sec.keys()) + list(self.completions_by_sec.keys())))
            t0 = all_secs[0] if all_secs else int(time.time())

            timeline = []
            for s in all_secs:
                timeline.append({
                    "relative_sec": s - t0 + 1,
                    "arrivals": self.arrivals_by_sec.get(s, 0),
                    "completions": self.completions_by_sec.get(s, 0),
                })

            max_borrowed = max((s["borrowed"] for s in self.limiter_samples), default=0)
            max_waiting = max((s["waiting"] for s in self.limiter_samples), default=0)
            cur_total = self.limiter_samples[-1]["total"] if self.limiter_samples else 40

            return {
                "timeline": timeline,
                "limiter": {
                    "total_tokens": cur_total,
                    "max_borrowed_tokens": max_borrowed,
                    "max_tasks_waiting": max_waiting,
                    "sample_count": len(self.limiter_samples)
                }
            }

bench_traffic = BenchTrafficMonitor()
