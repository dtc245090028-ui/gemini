"""Cơ chế Lưu & Tái sử dụng Báo cáo AI theo Khoảng thời gian kèm Dấu vết dữ liệu (Data Fingerprint).

Đặc tả:
1. Lưu theo khóa chuẩn: `{report_type}:{start_date}:{end_date}` (YYYY-MM-DD).
2. Dấu vết dữ liệu (Data Fingerprint): Ghi nhận `ledger_count`, `max_ledger_id` của `stock_ledger` trong khoảng ngày
   (và chữ ký tồn kho hiện tại đối với Gợi ý nhập hàng / Bất thường). Khi dữ liệu kho thay đổi, bản lưu cũ tự động hết hạn.
3. Tái sử dụng thông minh theo ngày biến động: Nếu một khoảng nhiều ngày chỉ có đúng 1 ngày phát sinh giao dịch
   (`single_active_date`), hệ thống đồng thời liên kết và tái sử dụng nhận xét AI của ngày biến động đó.
4. Tách biệt Số liệu & Nhận xét: Số liệu (metrics, danh sách mặt hàng, tồn kho) luôn tính mới từ CSDL; chỉ lưu phần nhận xét của AI.
5. Đánh dấu Fallback riêng (`is_fallback=True`): Không khóa cứng kết quả dự phòng để lần gọi sau có thể tạo lại bằng Gemini thật.
"""

import calendar
from datetime import date, datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.stock_ledger import StockLedger

logger = logging.getLogger("ai_service")

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CACHE_FILE = CACHE_DIR / "ai_cache.json"
VN_TZ = timezone(timedelta(hours=7))


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

    @staticmethod
    def resolve_period_range(
        period_type: Optional[str] = None,
        target_date: Optional[date] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> Tuple[date, date, str, bool]:
        """Chuẩn hóa khoảng yêu cầu về các mốc chuẩn (ngày / tuần / tháng / khoảng tùy chọn).

        Trả về: (start_date, end_date, period_label, is_custom_or_subperiod)
        """
        now_vn = datetime.now(VN_TZ)
        mode = (period_type or "").strip().lower()

        if start_date and end_date:
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            if start_date == end_date:
                label = f"Ngày {start_date.strftime('%d/%m/%Y')}"
            else:
                label = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
            return start_date, end_date, label, True

        if mode == "day":
            d = target_date or now_vn.date()
            return d, d, f"Ngày {d.strftime('%d/%m/%Y')}", True

        if mode == "week":
            d = target_date or now_vn.date()
            monday = d - timedelta(days=d.weekday())
            sunday = monday + timedelta(days=6)
            label = f"Tuần {monday.strftime('%d/%m/%Y')} - {sunday.strftime('%d/%m/%Y')}"
            return monday, sunday, label, True

        # Mặc định: chuẩn hóa theo Tháng (month/year hoặc tháng chứa target_date)
        if target_date and mode == "month":
            t_month = target_date.month
            t_year = target_date.year
        else:
            t_month = month or now_vn.month
            t_year = year or now_vn.year

        first_d = date(t_year, t_month, 1)
        last_day_num = calendar.monthrange(t_year, t_month)[1]
        last_d = date(t_year, t_month, last_day_num)
        return first_d, last_d, f"{t_month:02d}/{t_year}", False

    @staticmethod
    def compute_fingerprint(
        db: Session,
        start_d: date,
        end_d: date,
        include_stock_state: bool = False,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Tính 'dấu vết dữ liệu' (Data Fingerprint) của khoảng thời gian trên bảng stock_ledger.

        Trả về (fingerprint_dict, single_active_date_str).
        Nếu trong khoảng [start_d, end_d] chỉ có đúng 1 ngày phát sinh biến động thẻ kho,
        `single_active_date_str` sẽ trả về ngày đó (YYYY-MM-DD) để tái sử dụng báo cáo ngày.
        """
        start_dt = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0)
        end_dt = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59, 999999)

        ledger_stats = (
            db.query(
                func.count(StockLedger.id),
                func.coalesce(func.max(StockLedger.id), 0),
                func.coalesce(func.sum(StockLedger.quantity_change), 0),
            )
            .filter(
                StockLedger.transaction_date >= start_dt,
                StockLedger.transaction_date <= end_dt,
            )
            .first()
        )
        ledger_count = int(ledger_stats[0] or 0)
        max_ledger_id = int(ledger_stats[1] or 0)
        net_change = int(ledger_stats[2] or 0)

        active_date_rows = (
            db.query(func.date(StockLedger.transaction_date))
            .filter(
                StockLedger.transaction_date >= start_dt,
                StockLedger.transaction_date <= end_dt,
            )
            .distinct()
            .all()
        )
        active_dates = sorted(str(r[0]) for r in active_date_rows if r[0])
        single_active_date = active_dates[0] if len(active_dates) == 1 else None

        fingerprint: Dict[str, Any] = {
            "ledger_count": ledger_count,
            "max_ledger_id": max_ledger_id,
            "net_change": net_change,
            "active_days_count": len(active_dates),
        }

        if include_stock_state:
            prod_stats = (
                db.query(
                    func.count(Product.id),
                    func.coalesce(func.sum(Product.current_stock), 0),
                    func.coalesce(func.sum(Product.min_stock), 0),
                )
                .filter(Product.status != "DISCONTINUED")
                .first()
            )
            fingerprint["product_count"] = int(prod_stats[0] or 0)
            fingerprint["sum_current_stock"] = int(prod_stats[1] or 0)
            fingerprint["sum_min_stock"] = int(prod_stats[2] or 0)

        return fingerprint, single_active_date

    @classmethod
    def get_range_commentary(
        cls,
        report_type: str,
        start_d: date,
        end_d: date,
        fingerprint: Dict[str, Any],
        single_active_date: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Kiểm tra bản lưu AI theo khoảng ngày (hoặc ngày biến động duy nhất) và đối chiếu dấu vết dữ liệu."""
        with cls._lock:
            cache_data = cls._read_all()
            start_str = start_d.isoformat()
            end_str = end_d.isoformat()

            candidate_keys = [f"{report_type}:{start_str}:{end_str}"]
            if single_active_date and (start_str != single_active_date or end_str != single_active_date):
                candidate_keys.append(f"{report_type}:{single_active_date}:{single_active_date}")

            for key in candidate_keys:
                entry = cache_data.get(key)
                if not entry or not isinstance(entry, dict):
                    continue
                # Kết quả từ chế độ dự phòng (is_fallback=True) không được dùng làm bản lưu hợp lệ
                if entry.get("is_fallback", False):
                    continue
                if entry.get("fingerprint") == fingerprint and "commentary" in entry:
                    return {
                        "commentary": entry["commentary"],
                        "cached_at": entry.get("cached_at"),
                        "reused_from_key": key,
                    }

            return None

    @classmethod
    def set_range_commentary(
        cls,
        report_type: str,
        start_d: date,
        end_d: date,
        fingerprint: Dict[str, Any],
        commentary: Dict[str, Any],
        is_fallback: bool = False,
        single_active_date: Optional[str] = None,
    ) -> str:
        """Lưu phần nhận xét AI kèm dấu vết dữ liệu và đánh dấu rõ trạng thái is_fallback."""
        cached_at = datetime.now(VN_TZ).strftime("%H:%M:%S %d/%m/%Y")
        start_str = start_d.isoformat()
        end_str = end_d.isoformat()
        primary_key = f"{report_type}:{start_str}:{end_str}"

        record = {
            "report_type": report_type,
            "start_date": start_str,
            "end_date": end_str,
            "date": str(datetime.now(VN_TZ).date()),
            "cached_at": cached_at,
            "is_fallback": bool(is_fallback),
            "fingerprint": fingerprint,
            "commentary": commentary,
        }

        with cls._lock:
            cache_data = cls._read_all()
            cache_data[primary_key] = record
            # Nếu khoảng nhiều ngày chỉ có đúng 1 ngày phát sinh biến động và là kết quả AI thật,
            # lưu đồng thời cho mốc ngày đơn lẻ đó để tái sử dụng hai chiều.
            if single_active_date and not is_fallback:
                single_key = f"{report_type}:{single_active_date}:{single_active_date}"
                cache_data[single_key] = {
                    **record,
                    "start_date": single_active_date,
                    "end_date": single_active_date,
                }
            cls._write_all(cache_data)

        return cached_at

    @classmethod
    def get(cls, cache_type: str, key_suffix: str) -> Optional[Dict[str, Any]]:
        """Lấy kết quả từ cache theo ngày (dùng cho generate_ai_order)."""
        with cls._lock:
            cache_data = cls._read_all()
            cache_key = f"{cache_type}:{key_suffix}"
            entry = cache_data.get(cache_key)

            if not entry:
                return None

            today_str = str(date.today())
            if entry.get("date") != today_str or entry.get("is_fallback", False):
                if entry.get("date") != today_str:
                    del cache_data[cache_key]
                    cls._write_all(cache_data)
                return None

            data = entry.get("data")
            if isinstance(data, dict) and entry.get("cached_at"):
                data["cached_at"] = entry.get("cached_at")
            return data

    @classmethod
    def set(cls, cache_type: str, key_suffix: str, data: Dict[str, Any], is_fallback: bool = False):
        """Lưu kết quả phân tích AI vào cache trong ngày."""
        cached_at = datetime.now(VN_TZ).strftime("%H:%M:%S %d/%m/%Y")
        with cls._lock:
            cache_data = cls._read_all()
            cache_key = f"{cache_type}:{key_suffix}"
            if isinstance(data, dict):
                data["cached_at"] = cached_at
            cache_data[cache_key] = {
                "date": str(date.today()),
                "cached_at": cached_at,
                "is_fallback": bool(is_fallback),
                "data": data,
            }
            cls._write_all(cache_data)

    @classmethod
    def clear(cls):
        """Xóa toàn bộ cache."""
        with cls._lock:
            cls._write_all({})
