"""Cơ chế Cache kết quả AI theo ngày (In-Day AI Caching).

Mục tiêu:
1. Lưu kết quả phân tích AI thành công trong ngày (YYYY-MM-DD).
2. Khi người dùng bấm nhiều lần hoặc kiểm thử, kết quả được trả về tức thì (< 5ms) mà không tốn Quota API Gemini.
3. Hết ngày (qua ngày mới), cache tự động hết hạn để AI cập nhật số liệu mới nhất.
4. Hỗ trợ cờ `force_refresh=True` khi người dùng chủ động muốn tính toán lại ngay lập tức.
"""

from datetime import date, datetime
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger("ai_service")

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CACHE_FILE = CACHE_DIR / "ai_cache.json"


class AICacheManager:
    _lock = threading.Lock()

    @classmethod
    def _ensure_dir(cls):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def _read_all(cls) -> Dict[str, Any]:
        cls._ensure_dir()
        if not CACHE_FILE.exists():
            return {}
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Lỗi đọc ai_cache.json: {e}, khởi tạo cache rỗng.")
            return {}

    @classmethod
    def _write_all(cls, cache_data: Dict[str, Any]):
        cls._ensure_dir()
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi ghi ai_cache.json: {e}")

    @classmethod
    def get(cls, cache_type: str, key_suffix: str) -> Optional[Dict[str, Any]]:
        """Lấy kết quả từ cache nếu còn hiệu lực trong ngày hôm nay."""
        with cls._lock:
            cache_data = cls._read_all()
            cache_key = f"{cache_type}:{key_suffix}"
            entry = cache_data.get(cache_key)

            if not entry:
                return None

            today_str = str(date.today())
            if entry.get("date") != today_str:
                # Đã hết hạn qua ngày mới -> Xóa bỏ
                del cache_data[cache_key]
                cls._write_all(cache_data)
                return None

            return entry.get("data")

    @classmethod
    def set(cls, cache_type: str, key_suffix: str, data: Dict[str, Any]):
        """Lưu kết quả phân tích AI thành công vào cache trong ngày."""
        with cls._lock:
            cache_data = cls._read_all()
            cache_key = f"{cache_type}:{key_suffix}"
            cache_data[cache_key] = {
                "date": str(date.today()),
                "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data": data,
            }
            cls._write_all(cache_data)

    @classmethod
    def clear(cls):
        """Xóa toàn bộ cache."""
        with cls._lock:
            cls._write_all({})
