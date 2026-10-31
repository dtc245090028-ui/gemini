"""Dịch vụ AI Trợ lý kho thông minh (Google Gemini API + Heuristic Fallback Engine).

Đặc tả:
1. Data Pre-processing Pipeline: SQL tính toán trước số liệu tổng hợp.
2. Bảo mật: Bắt buộc lọc sạch thông tin giá mua nhập hàng (unit_price) trước khi gửi prompt.
3. Fallback-first: Tự động dùng FallbackService nếu thiếu GEMINI_API_KEY hoặc mất mạng/lỗi quota.
4. Structured Output: Định dạng JSON đồng nhất giữa AI và Fallback.
"""

from datetime import date, datetime, timedelta
import json
import logging
from pathlib import Path
import random
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings, get_now_vn
from app.models.category import Category
from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.import_note import ImportNote, ImportNoteDetail
from app.models.product import Product
from app.models.stock_ledger import StockLedger
from app.schemas.ai import (
    AnomalyDetectionResponse,
    AnomalyItem,
    AskAIRequest,
    AskAIResponse,
    GenerateOrderResponse,
    MonthlyReportMetrics,
    MonthlyReportResponse,
    RestockSuggestionItem,
    RestockSuggestionsResponse,
    TopExportedProductItem,
)
from app.services.fallback_service import FallbackService
from app.services.ai_cache import AICacheManager

logger = logging.getLogger(__name__)

SCENARIOS_FILE = Path(__file__).resolve().parent.parent / "ai" / "data" / "order_scenarios.json"

# Cấu hình log lỗi ra file chuyên dụng logs/ai_service.log để phục vụ debug
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOGS_DIR / "ai_service.log"

if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s (line %(lineno)d): %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "ai" / "prompts"


class AIService:
    """Điều phối toàn bộ tính năng AI phân tích kho bãi và kích hoạt Fallback."""

    # =========================================================================
    # 1. TIỀN XỬ LÝ & TỔNG HỢP DỮ LIỆU (SQL AGGREGATION PIPELINE)
    # =========================================================================

    @staticmethod
    def get_period_aggregated_data(
        db: Session, start_d: date, end_d: date
    ) -> MonthlyReportMetrics:
        """SQL Pipeline tổng hợp số liệu theo khoảng ngày [start_d, end_d]. Tuyệt đối KHÔNG trả về giá mua."""
        start_dt = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0)
        end_dt = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59, 999999)

        # 1. Tổng số mặt hàng đang quản lý
        total_products = db.query(func.count(Product.id)).scalar() or 0

        # 2. Số lượng mặt hàng dưới mức tồn tối thiểu
        low_stock_count = (
            db.query(func.count(Product.id))
            .filter(Product.current_stock <= Product.min_stock)
            .scalar()
            or 0
        )

        # 3. Tổng lượng nhập trong kỳ (chỉ lấy tổng quantity của phiếu COMPLETED)
        total_imports_qty = (
            db.query(func.coalesce(func.sum(ImportNoteDetail.quantity), 0))
            .join(ImportNote, ImportNoteDetail.import_note_id == ImportNote.id)
            .filter(
                ImportNote.status == "COMPLETED",
                ImportNote.note_date >= start_dt,
                ImportNote.note_date <= end_dt,
            )
            .scalar()
            or 0
        )

        # 4. Tổng lượng xuất trong kỳ (chỉ lấy tổng quantity của phiếu COMPLETED)
        total_exports_qty = (
            db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
            .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
            .filter(
                ExportNote.status == "COMPLETED",
                ExportNote.note_date >= start_dt,
                ExportNote.note_date <= end_dt,
            )
            .scalar()
            or 0
        )

        # 5. Top 5 mặt hàng xuất nhiều nhất trong kỳ (chỉ lấy ID, Code, Name, Quantity)
        top_export_rows = (
            db.query(
                Product.id,
                Product.code,
                Product.name,
                func.sum(ExportNoteDetail.quantity).label("total_qty"),
            )
            .join(ExportNoteDetail, Product.id == ExportNoteDetail.product_id)
            .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
            .filter(
                ExportNote.status == "COMPLETED",
                ExportNote.note_date >= start_dt,
                ExportNote.note_date <= end_dt,
            )
            .group_by(Product.id, Product.code, Product.name)
            .order_by(func.sum(ExportNoteDetail.quantity).desc())
            .limit(5)
            .all()
        )

        top_exported_products = [
            TopExportedProductItem(
                product_id=row[0],
                product_code=row[1],
                product_name=row[2],
                quantity=int(row[3]),
            )
            for row in top_export_rows
        ]

        # 6. Đếm số mặt hàng có phát sinh giao dịch trong kỳ (qua thẻ kho)
        active_products = (
            db.query(func.count(func.distinct(StockLedger.product_id)))
            .filter(
                StockLedger.transaction_date >= start_dt,
                StockLedger.transaction_date <= end_dt,
            )
            .scalar()
            or 0
        )

        return MonthlyReportMetrics(
            total_products=int(total_products),
            active_products=int(active_products),
            total_imports_qty=int(total_imports_qty),
            total_exports_qty=int(total_exports_qty),
            low_stock_count=int(low_stock_count),
            top_exported_products=top_exported_products,
        )

    @classmethod
    def get_monthly_aggregated_data(
        cls, db: Session, month: int, year: int
    ) -> MonthlyReportMetrics:
        """SQL Pipeline tổng hợp số liệu tháng. Tuyệt đối KHÔNG trả về giá mua."""
        start_d, end_d, _, _ = AICacheManager.resolve_period_range(month=month, year=year)
        return cls.get_period_aggregated_data(db, start_d, end_d)

    @staticmethod
    def get_restock_candidates_data(
        db: Session,
        lookback_days: int = 30,
        start_d: Optional[date] = None,
        end_d: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Lọc danh sách các mặt hàng có nguy cơ thiếu tồn kho hoặc dưới tồn tối thiểu."""
        if start_d and end_d:
            start_dt = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0)
            end_dt = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59, 999999)
            effective_days = max((end_d - start_d).days + 1, 1)
        else:
            end_dt = get_now_vn()
            start_dt = end_dt - timedelta(days=lookback_days)
            effective_days = max(lookback_days, 1)

        # Lấy toàn bộ sản phẩm đang hoạt động
        products = db.query(Product).filter(Product.status != "DISCONTINUED").all()
        candidates: List[Dict[str, Any]] = []

        for p in products:
            total_exported = (
                db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
                .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
                .filter(
                    ExportNoteDetail.product_id == p.id,
                    ExportNote.status == "COMPLETED",
                    ExportNote.note_date >= start_dt,
                    ExportNote.note_date <= end_dt,
                )
                .scalar()
                or 0
            )

            daily_velocity = float(total_exported) / max(float(effective_days), 1.0)
            days_left = (
                (p.current_stock / daily_velocity)
                if daily_velocity > 0
                else (999.0 if p.current_stock > 0 else 0.0)
            )

            # Tiêu chí lọc: Tồn kho <= tồn tối thiểu HOẶC sắp hết hàng trong vòng 7 ngày tới
            if p.current_stock <= p.min_stock or (days_left is not None and days_left <= 7.0):
                candidates.append(
                    {
                        "product_id": p.id,
                        "product_code": p.code,
                        "product_name": p.name,
                        "current_stock": p.current_stock,
                        "min_stock": p.min_stock,
                        "daily_velocity": round(daily_velocity, 2),
                        "days_until_stockout": round(days_left, 1) if days_left < 999 else None,
                    }
                )

        return candidates

    @staticmethod
    def get_anomalies_candidates_data(
        db: Session,
        lookback_days: int = 30,
        start_d: Optional[date] = None,
        end_d: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Nhận diện 2 nhóm bất thường: Xuất tăng đột biến (>200%) và Hàng tồn lâu ngày (>30 ngày)."""
        if start_d and end_d:
            end_dt = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59, 999999)
            previous_cutoff = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0)
            effective_days = max((end_d - start_d).days + 1, 1)
            recent_window_days = min(7, max(1, effective_days // 2)) if effective_days > 7 else effective_days
            recent_7d_cutoff = end_dt - timedelta(days=recent_window_days)
        else:
            end_dt = get_now_vn()
            recent_7d_cutoff = end_dt - timedelta(days=7)
            previous_cutoff = end_dt - timedelta(days=lookback_days)
            effective_days = max(lookback_days, 1)

        products = db.query(Product).filter(Product.status != "DISCONTINUED").all()
        anomalies: List[Dict[str, Any]] = []

        for p in products:
            # 1. Kiểm tra xuất tăng đột biến:
            recent_7d_qty = (
                db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
                .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
                .filter(
                    ExportNoteDetail.product_id == p.id,
                    ExportNote.status == "COMPLETED",
                    ExportNote.note_date >= recent_7d_cutoff,
                    ExportNote.note_date <= end_dt,
                )
                .scalar()
                or 0
            )

            total_lookback_qty = (
                db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
                .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
                .filter(
                    ExportNoteDetail.product_id == p.id,
                    ExportNote.status == "COMPLETED",
                    ExportNote.note_date >= previous_cutoff,
                    ExportNote.note_date <= end_dt,
                )
                .scalar()
                or 0
            )

            earlier_qty = total_lookback_qty - recent_7d_qty
            earlier_weeks = max((effective_days - 7) / 7.0, 1.0)
            baseline_weekly = earlier_qty / earlier_weeks

            if recent_7d_qty >= 5 and (baseline_weekly == 0 or (recent_7d_qty >= baseline_weekly * 2.0)):
                ratio = (recent_7d_qty / baseline_weekly) if baseline_weekly > 0 else 3.0
                anomalies.append(
                    {
                        "product_id": p.id,
                        "product_code": p.code,
                        "product_name": p.name,
                        "anomaly_type": "SURGE_EXPORT",
                        "recent_7d_qty": int(recent_7d_qty),
                        "baseline_weekly_qty": round(baseline_weekly, 1),
                        "surge_ratio": round(ratio, 1),
                    }
                )

            # 2. Kiểm tra hàng tồn lâu ngày (Dead Stock / Slow Moving):
            if p.current_stock > 0 and total_lookback_qty == 0:
                last_export_date = (
                    db.query(func.max(ExportNote.note_date))
                    .join(ExportNoteDetail, ExportNote.id == ExportNoteDetail.export_note_id)
                    .filter(
                        ExportNoteDetail.product_id == p.id,
                        ExportNote.status == "COMPLETED",
                    )
                    .scalar()
                )
                days_inactive = (
                    (end_dt - last_export_date).days
                    if last_export_date
                    else effective_days
                )
                anomalies.append(
                    {
                        "product_id": p.id,
                        "product_code": p.code,
                        "product_name": p.name,
                        "anomaly_type": "DEAD_STOCK",
                        "current_stock": p.current_stock,
                        "days_inactive": max(days_inactive, effective_days),
                    }
                )

        return anomalies

    # =========================================================================
    # 2. NẠP PROMPT TEMPLATES
    # =========================================================================

    @staticmethod
    def _read_prompt_template(filename: str) -> str:
        """Đọc nội dung template từ thư mục prompts, có fallback string nếu file lỗi."""
        prompt_file = PROMPTS_DIR / filename
        if prompt_file.exists():
            try:
                return prompt_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Không thể đọc file prompt {filename}: {e}")
        return ""

    @classmethod
    def _call_gemini_with_models(cls, prompt_content: str, generation_config: Optional[dict] = None) -> str:
        """Gọi Gemini API với cơ chế tự động thử qua chuỗi model (Model Fallback Chain) nếu gặp giới hạn hạn mức (429 Quota)."""
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        config = generation_config or {"temperature": 0.2, "response_mime_type": "application/json"}

        # Danh sách model ứng viên theo thứ tự ưu tiên (Flash-Lite có quota Free Tier dồi dào và ổn định nhất)
        candidates = [
            settings.AI_MODEL_NAME or "gemini-3.5-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.6-flash",
        ]
        seen = set()
        model_names = [m for m in candidates if not (m in seen or seen.add(m))]

        last_exception = None
        for m_name in model_names:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt_content, generation_config=config)
                raw_text = response.text.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                return raw_text
            except Exception as e:
                last_exception = e
                logger.warning(f"Model {m_name} không khả dụng ({e}), đang thử model tiếp theo trong chuỗi...")

        if last_exception:
            raise last_exception
        raise RuntimeError("Không có model nào khả dụng")

    # =========================================================================
    # 3. GỌI GEMINI API VỚI LƯU TRỮ KHOẢNG NGÀY, DẤU VẾT DỮ LIỆU & FALLBACK
    # =========================================================================

    @classmethod
    def generate_monthly_report(
        cls,
        db: Session,
        month: Optional[int] = None,
        year: Optional[int] = None,
        force_refresh: bool = False,
        period_type: Optional[str] = None,
        target_date: Optional[date] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> MonthlyReportResponse:
        """Sinh Báo cáo Nhập-Xuất-Tồn theo khoảng thời gian:
        - Luôn tính lại số liệu thực tế từ DB.
        - Kiểm tra bản lưu nhận xét AI theo khoảng ngày + dấu vết dữ liệu (hoặc ngày biến động duy nhất).
        - Khoảng ngày không có biến động thẻ kho (khi lọc theo ngày/tuần/khoảng ngày) thì dùng ngay mẫu nội bộ không gọi AI.
        """
        start_d, end_d, period_str, is_subperiod = AICacheManager.resolve_period_range(
            period_type=period_type,
            target_date=target_date,
            start_date=start_date,
            end_date=end_date,
            month=month,
            year=year,
        )

        # 1. Luôn tính toán mới số liệu từ CSDL và lấy dấu vết dữ liệu (fingerprint)
        metrics = cls.get_period_aggregated_data(db, start_d, end_d)
        fingerprint, single_active_date = AICacheManager.compute_fingerprint(
            db, start_d, end_d, include_stock_state=False
        )

        # 2. Kiểm tra bản lưu nhận xét AI nếu không ép buộc Tạo lại (force_refresh=False)
        if not force_refresh:
            cached = AICacheManager.get_range_commentary(
                "monthly_report",
                start_d,
                end_d,
                fingerprint,
                single_active_date=single_active_date,
            )
            if cached:
                comm = cached["commentary"]
                return MonthlyReportResponse(
                    period=period_str,
                    is_fallback=False,
                    provider="gemini",
                    metrics=metrics,
                    executive_summary=comm.get("executive_summary", ""),
                    recommendations=comm.get("recommendations", []),
                    is_cached=True,
                    cached_at=cached.get("cached_at"),
                    start_date=start_d.isoformat(),
                    end_date=end_d.isoformat(),
                )

        # 3. Nếu chưa có GEMINI_API_KEY hoặc khoảng lọc không có biến động -> Dùng nội dung mẫu ngay, không gọi AI
        no_activity_in_range = (
            is_subperiod
            and fingerprint.get("ledger_count", 0) == 0
            and metrics.total_imports_qty == 0
            and metrics.total_exports_qty == 0
        )
        if not settings.GEMINI_API_KEY or metrics.total_products == 0 or no_activity_in_range:
            summary, recs = FallbackService.generate_monthly_report_fallback(metrics, period_str)
            return MonthlyReportResponse(
                period=period_str,
                is_fallback=True,
                provider="heuristic_fallback",
                metrics=metrics,
                executive_summary=summary,
                recommendations=recs,
                is_cached=False,
                cached_at=None,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

        # 4. Gọi Gemini API và chỉ lưu phần nhận xét của AI kèm dấu vết dữ liệu
        try:
            top_products_text = "\n".join(
                [f"- {p.product_code}: {p.product_name} (xuất {p.quantity} đơn vị)" for p in metrics.top_exported_products]
            ) or "Không có mặt hàng xuất trong kỳ."

            template = cls._read_prompt_template("inventory_report_prompt.txt")
            user_prompt = (
                f"Kỳ báo cáo: {period_str} ({start_d.isoformat()} đến {end_d.isoformat()})\n"
                f"- Tổng số mặt hàng quản lý: {metrics.total_products}\n"
                f"- Số mặt hàng có giao dịch: {metrics.active_products}\n"
                f"- Tổng lượng nhập kho: {metrics.total_imports_qty}\n"
                f"- Tổng lượng xuất kho: {metrics.total_exports_qty}\n"
                f"- Số mặt hàng dưới tồn tối thiểu: {metrics.low_stock_count}\n"
                f"- Top mặt hàng xuất nhiều nhất:\n{top_products_text}\n"
                "Hãy phân tích và trả về đúng định dạng JSON: "
                '{"executive_summary": "...", "recommendations": ["..."]}'
            )

            prompt_content = f"{template}\n\nUser Input:\n{user_prompt}" if template else user_prompt
            raw_text = cls._call_gemini_with_models(prompt_content)
            parsed = json.loads(raw_text)
            ai_summary = parsed.get("executive_summary", "")
            ai_recs = parsed.get("recommendations", [])

            cached_at = AICacheManager.set_range_commentary(
                "monthly_report",
                start_d,
                end_d,
                fingerprint,
                commentary={
                    "executive_summary": ai_summary,
                    "recommendations": ai_recs,
                },
                is_fallback=False,
                single_active_date=single_active_date,
            )

            return MonthlyReportResponse(
                period=period_str,
                is_fallback=False,
                provider="gemini",
                metrics=metrics,
                executive_summary=ai_summary,
                recommendations=ai_recs,
                is_cached=False,
                cached_at=cached_at,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

        except Exception as e:
            logger.error(
                f"Lỗi khi gọi Gemini API cho monthly-report: {e}. Kích hoạt Heuristic Fallback.",
                exc_info=True,
            )
            summary, recs = FallbackService.generate_monthly_report_fallback(metrics, period_str)
            AICacheManager.set_range_commentary(
                "monthly_report",
                start_d,
                end_d,
                fingerprint,
                commentary={"executive_summary": summary, "recommendations": recs},
                is_fallback=True,
            )
            return MonthlyReportResponse(
                period=period_str,
                is_fallback=True,
                provider="heuristic_fallback",
                metrics=metrics,
                executive_summary=summary,
                recommendations=recs,
                is_cached=False,
                cached_at=None,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

    @classmethod
    def generate_restock_suggestions(
        cls,
        db: Session,
        lookback_days: int = 30,
        force_refresh: bool = False,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> RestockSuggestionsResponse:
        """Gợi ý nhập hàng theo khoảng thời gian:
        - Số liệu tồn kho, tốc độ xuất luôn tính mới từ CSDL.
        - Tái sử dụng nhận xét AI nếu dấu vết dữ liệu trong khoảng chưa đổi.
        """
        today_d = get_now_vn().date()
        if start_date and end_date:
            start_d, end_d = (start_date, end_date) if start_date <= end_date else (end_date, start_date)
            effective_days = max((end_d - start_d).days + 1, 1)
        else:
            end_d = today_d
            start_d = end_d - timedelta(days=max(lookback_days - 1, 0))
            effective_days = lookback_days

        # 1. Luôn tính mới số liệu ứng viên nhập hàng từ DB
        candidates = cls.get_restock_candidates_data(
            db, lookback_days=effective_days, start_d=start_d, end_d=end_d
        )
        fallback_items, fallback_summary = FallbackService.generate_restock_suggestions_fallback(candidates)
        fingerprint, single_active_date = AICacheManager.compute_fingerprint(
            db, start_d, end_d, include_stock_state=True
        )

        def _apply_ai_item_map(ai_item_map: Dict[str, Any]) -> List[RestockSuggestionItem]:
            merged: List[RestockSuggestionItem] = []
            for item in fallback_items:
                if item.product_code in ai_item_map:
                    ai_rec = ai_item_map[item.product_code]
                    merged.append(
                        RestockSuggestionItem(
                            product_id=item.product_id,
                            product_code=item.product_code,
                            product_name=item.product_name,
                            current_stock=item.current_stock,
                            min_stock=item.min_stock,
                            daily_velocity=item.daily_velocity,
                            estimated_days_left=item.estimated_days_left,
                            suggested_quantity=int(ai_rec.get("suggested_quantity", item.suggested_quantity)),
                            priority=ai_rec.get("priority", item.priority),
                            reason=ai_rec.get("reason", item.reason),
                        )
                    )
                else:
                    merged.append(item)
            return merged

        # 2. Kiểm tra bản lưu nhận xét AI nếu không ép buộc Tạo lại
        if not force_refresh:
            cached = AICacheManager.get_range_commentary(
                "restock_suggestions",
                start_d,
                end_d,
                fingerprint,
                single_active_date=single_active_date,
            )
            if cached:
                comm = cached["commentary"]
                merged_items = _apply_ai_item_map(comm.get("ai_item_map", {}))
                return RestockSuggestionsResponse(
                    lookback_days=effective_days,
                    is_fallback=False,
                    provider="gemini",
                    total_suggested_items=len(merged_items),
                    items=merged_items,
                    executive_summary=comm.get("executive_summary", fallback_summary),
                    is_cached=True,
                    cached_at=cached.get("cached_at"),
                    start_date=start_d.isoformat(),
                    end_date=end_d.isoformat(),
                )

        # 3. Không có biến động cần nhập hoặc thiếu API key -> Dùng mẫu nội bộ, không gọi AI
        if not settings.GEMINI_API_KEY or not candidates:
            return RestockSuggestionsResponse(
                lookback_days=effective_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_suggested_items=len(fallback_items),
                items=fallback_items,
                executive_summary=fallback_summary,
                is_cached=False,
                cached_at=None,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

        # 4. Gọi Gemini API và chỉ lưu phần nhận xét của AI
        try:
            template = cls._read_prompt_template("reorder_suggestion_prompt.txt")
            user_prompt = (
                f"Danh sách mặt hàng cần xem xét bổ sung (phân tích {effective_days} ngày từ {start_d.isoformat()} đến {end_d.isoformat()}):\n"
                f"{json.dumps(candidates, ensure_ascii=False, indent=2)}\n"
                "Hãy trả về JSON theo schema: "
                '{"executive_summary": "...", "item_suggestions": [{"product_code": "...", "suggested_quantity": 0, "priority": "HIGH", "reason": "..."}]}'
            )

            prompt_content = f"{template}\n\nUser Input:\n{user_prompt}" if template else user_prompt
            raw_text = cls._call_gemini_with_models(prompt_content)

            parsed = json.loads(raw_text)
            ai_summary = parsed.get("executive_summary", fallback_summary)
            ai_item_map = {
                it.get("product_code"): it
                for it in parsed.get("item_suggestions", [])
                if isinstance(it, dict) and "product_code" in it
            }
            final_items = _apply_ai_item_map(ai_item_map)

            cached_at = AICacheManager.set_range_commentary(
                "restock_suggestions",
                start_d,
                end_d,
                fingerprint,
                commentary={
                    "executive_summary": ai_summary,
                    "ai_item_map": ai_item_map,
                },
                is_fallback=False,
                single_active_date=single_active_date,
            )

            return RestockSuggestionsResponse(
                lookback_days=effective_days,
                is_fallback=False,
                provider="gemini",
                total_suggested_items=len(final_items),
                items=final_items,
                executive_summary=ai_summary,
                is_cached=False,
                cached_at=cached_at,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

        except Exception as e:
            logger.error(
                f"Lỗi khi gọi Gemini API cho restock-suggestions: {e}. Dùng Fallback.",
                exc_info=True,
            )
            AICacheManager.set_range_commentary(
                "restock_suggestions",
                start_d,
                end_d,
                fingerprint,
                commentary={"executive_summary": fallback_summary, "ai_item_map": {}},
                is_fallback=True,
            )
            return RestockSuggestionsResponse(
                lookback_days=effective_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_suggested_items=len(fallback_items),
                items=fallback_items,
                executive_summary=fallback_summary,
                is_cached=False,
                cached_at=None,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

    @classmethod
    def generate_anomaly_detection(
        cls,
        db: Session,
        lookback_days: int = 30,
        force_refresh: bool = False,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> AnomalyDetectionResponse:
        """Tóm tắt biến động bất thường theo khoảng thời gian:
        - Số liệu bất thường luôn tính mới từ CSDL.
        - Tái sử dụng nhận xét AI nếu dấu vết dữ liệu trong khoảng chưa đổi.
        """
        today_d = get_now_vn().date()
        if start_date and end_date:
            start_d, end_d = (start_date, end_date) if start_date <= end_date else (end_date, start_date)
            effective_days = max((end_d - start_d).days + 1, 1)
        else:
            end_d = today_d
            start_d = end_d - timedelta(days=max(lookback_days - 1, 0))
            effective_days = lookback_days

        # 1. Luôn tính mới danh sách bất thường từ DB
        candidates = cls.get_anomalies_candidates_data(
            db, lookback_days=effective_days, start_d=start_d, end_d=end_d
        )
        fallback_anomalies, fallback_summary = FallbackService.generate_anomaly_detection_fallback(candidates)
        fingerprint, single_active_date = AICacheManager.compute_fingerprint(
            db, start_d, end_d, include_stock_state=True
        )

        def _apply_ai_action_map(ai_action_map: Dict[str, Any]) -> List[AnomalyItem]:
            merged: List[AnomalyItem] = []
            for item in fallback_anomalies:
                if item.product_code in ai_action_map:
                    ai_act = ai_action_map[item.product_code]
                    merged.append(
                        AnomalyItem(
                            product_id=item.product_id,
                            product_code=item.product_code,
                            product_name=item.product_name,
                            anomaly_type=item.anomaly_type,
                            description=ai_act.get("analysis", item.description),
                            details=item.details,
                            suggested_action=ai_act.get("suggested_action", item.suggested_action),
                        )
                    )
                else:
                    merged.append(item)
            return merged

        # 2. Kiểm tra bản lưu nhận xét AI nếu không ép buộc Tạo lại
        if not force_refresh:
            cached = AICacheManager.get_range_commentary(
                "anomaly_detection",
                start_d,
                end_d,
                fingerprint,
                single_active_date=single_active_date,
            )
            if cached:
                comm = cached["commentary"]
                merged_anomalies = _apply_ai_action_map(comm.get("ai_action_map", {}))
                return AnomalyDetectionResponse(
                    lookback_days=effective_days,
                    is_fallback=False,
                    provider="gemini",
                    total_anomalies=len(merged_anomalies),
                    anomalies=merged_anomalies,
                    executive_summary=comm.get("executive_summary", fallback_summary),
                    is_cached=True,
                    cached_at=cached.get("cached_at"),
                    start_date=start_d.isoformat(),
                    end_date=end_d.isoformat(),
                )

        # 3. Không có bất thường hoặc thiếu API key -> Dùng mẫu nội bộ, không gọi AI
        if not settings.GEMINI_API_KEY or not candidates:
            return AnomalyDetectionResponse(
                lookback_days=effective_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_anomalies=len(fallback_anomalies),
                anomalies=fallback_anomalies,
                executive_summary=fallback_summary,
                is_cached=False,
                cached_at=None,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

        # 4. Gọi Gemini API và chỉ lưu phần nhận xét của AI
        try:
            template = cls._read_prompt_template("anomaly_detection_prompt.txt")
            user_prompt = (
                f"Danh sách bất thường phát hiện được ({effective_days} ngày từ {start_d.isoformat()} đến {end_d.isoformat()}):\n"
                f"{json.dumps(candidates, ensure_ascii=False, indent=2)}\n"
                "Hãy phân tích và trả về JSON theo schema: "
                '{"executive_summary": "...", "anomaly_actions": [{"product_code": "...", "anomaly_type": "SURGE_EXPORT", "analysis": "...", "suggested_action": "..."}]}'
            )

            prompt_content = f"{template}\n\nUser Input:\n{user_prompt}" if template else user_prompt
            raw_text = cls._call_gemini_with_models(prompt_content)

            parsed = json.loads(raw_text)
            ai_summary = parsed.get("executive_summary", fallback_summary)
            ai_action_map = {
                it.get("product_code"): it
                for it in parsed.get("anomaly_actions", [])
                if isinstance(it, dict) and "product_code" in it
            }
            final_anomalies = _apply_ai_action_map(ai_action_map)

            cached_at = AICacheManager.set_range_commentary(
                "anomaly_detection",
                start_d,
                end_d,
                fingerprint,
                commentary={
                    "executive_summary": ai_summary,
                    "ai_action_map": ai_action_map,
                },
                is_fallback=False,
                single_active_date=single_active_date,
            )

            return AnomalyDetectionResponse(
                lookback_days=effective_days,
                is_fallback=False,
                provider="gemini",
                total_anomalies=len(final_anomalies),
                anomalies=final_anomalies,
                executive_summary=ai_summary,
                is_cached=False,
                cached_at=cached_at,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

        except Exception as e:
            logger.error(
                f"Lỗi khi gọi Gemini API cho anomalies: {e}. Dùng Fallback.",
                exc_info=True,
            )
            AICacheManager.set_range_commentary(
                "anomaly_detection",
                start_d,
                end_d,
                fingerprint,
                commentary={"executive_summary": fallback_summary, "ai_action_map": {}},
                is_fallback=True,
            )
            return AnomalyDetectionResponse(
                lookback_days=effective_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_anomalies=len(fallback_anomalies),
                anomalies=fallback_anomalies,
                executive_summary=fallback_summary,
                is_cached=False,
                cached_at=None,
                start_date=start_d.isoformat(),
                end_date=end_d.isoformat(),
            )

    @classmethod
    def generate_ai_order(
        cls, db: Session, force_refresh: bool = False
    ) -> GenerateOrderResponse:
        """Sinh Đơn hàng AI đề xuất: Có Cache trong ngày, tự động đọc kịch bản và tồn kho thực tế."""
        cache_key = "today"

        # 0. Kiểm tra Cache trong ngày nếu không ép buộc làm mới
        if not force_refresh:
            cached = AICacheManager.get("generated_order", cache_key)
            if cached:
                cached["is_cached"] = True
                return GenerateOrderResponse(**cached)

        # 1. Đọc kho kịch bản
        scenarios = []
        if SCENARIOS_FILE.exists():
            try:
                with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
                    scenarios = json.load(f)
            except Exception as e:
                logger.warning(f"Không thể đọc file {SCENARIOS_FILE}: {e}")

        if not scenarios:
            scenarios = [
                {
                    "id": "SCENARIO_01",
                    "persona_name": "Công ty TNHH Phần Mềm F-Tech",
                    "role": "company",
                    "desired_category": "Máy tính xách tay & Laptop",
                    "context_reason": "Trang bị máy tính làm việc cho nhân sự phòng kỹ thuật đợt tuyển dụng mới.",
                }
            ]

        # 2. Chọn ngẫu nhiên 2 - 4 kịch bản ứng viên
        sample_count = min(3, len(scenarios))
        candidate_scenarios = random.sample(scenarios, sample_count)

        # 3. Lọc danh sách sản phẩm còn tồn kho phù hợp với điều kiện:
        #    - role in ("company", "dealer") -> current_stock >= 10
        #    - role == "individual" -> current_stock >= 1
        candidate_products_map: Dict[int, dict] = {}
        for sc in candidate_scenarios:
            role = sc.get("role", "individual")
            cat_kw = sc.get("desired_category", "")
            min_stock = 10 if role in ("company", "dealer") else 1

            prods = (
                db.query(Product)
                .join(Category, Product.category_id == Category.id)
                .filter(Category.name.ilike(f"%{cat_kw}%"))
                .filter(Product.current_stock >= min_stock)
                .limit(5)
                .all()
            )
            for p in prods:
                candidate_products_map[p.id] = {
                    "product_id": p.id,
                    "product_code": p.code,
                    "product_name": p.name,
                    "category_name": p.category.name if p.category else "",
                    "current_stock": p.current_stock,
                    "standard_price": p.standard_price,
                }

        # Nếu không có sản phẩm nào thỏa mãn điều kiện min_stock, lấy bất kỳ sản phẩm nào còn tồn > 0
        if not candidate_products_map:
            prods = db.query(Product).filter(Product.current_stock > 0).limit(5).all()
            for p in prods:
                candidate_products_map[p.id] = {
                    "product_id": p.id,
                    "product_code": p.code,
                    "product_name": p.name,
                    "category_name": p.category.name if p.category else "",
                    "current_stock": p.current_stock,
                    "standard_price": p.standard_price,
                }

        candidate_products = list(candidate_products_map.values())
        if not candidate_products:
            raise RuntimeError("Kho hiện tại không còn sản phẩm nào có hàng tồn kho để tạo đơn.")

        def _build_fallback_order() -> GenerateOrderResponse:
            chosen_sc = candidate_scenarios[0]
            chosen_prod_dict = candidate_products[0]
            role = chosen_sc.get("role", "individual")
            stock = chosen_prod_dict["current_stock"]

            if role == "dealer":
                qty = min(50, stock)
                disc = 10.0
            elif role == "company":
                qty = min(15, stock)
                disc = 5.0
            else:
                qty = min(2, stock)
                disc = 0.0

            std_price = chosen_prod_dict["standard_price"]
            sug_price = round(std_price * (1 - disc / 100), 0)
            reason = f"Đơn hàng đề xuất theo kịch bản {chosen_sc['persona_name']} ({chosen_sc['context_reason']})."
            note = f"Đơn hàng AI: {chosen_sc['persona_name']} ({role}) - Đề xuất giảm giá {disc:.0f}%: {reason}"

            return GenerateOrderResponse(
                scenario_id=chosen_sc["id"],
                recipient_name=chosen_sc["persona_name"],
                role=role,
                product_id=chosen_prod_dict["product_id"],
                product_code=chosen_prod_dict["product_code"],
                product_name=chosen_prod_dict["product_name"],
                current_stock=stock,
                quantity=qty,
                unit_price=std_price,
                discount_percent=disc,
                suggested_unit_price=sug_price,
                reason=reason,
                note=note,
                is_fallback=True,
                provider="heuristic_fallback",
                is_cached=False,
            )

        if not settings.GEMINI_API_KEY:
            return _build_fallback_order()

        # 4. Gọi Gemini AI
        try:
            template = cls._read_prompt_template("generate_order_prompt.txt")
            user_prompt = (
                f"Danh sách Kịch bản Khách hàng ứng viên:\n"
                f"{json.dumps(candidate_scenarios, ensure_ascii=False, indent=2)}\n\n"
                f"Danh sách Sản phẩm Tồn kho Khả dụng:\n"
                f"{json.dumps(candidate_products, ensure_ascii=False, indent=2)}\n\n"
                "Hãy chọn 1 kịch bản và 1 sản phẩm chính xác, trả về JSON."
            )

            prompt_content = f"{template}\n\nUser Input:\n{user_prompt}" if template else user_prompt
            raw_text = cls._call_gemini_with_models(prompt_content)
            parsed = json.loads(raw_text)

            ai_sku = parsed.get("product_sku", "")
            # Validate SKU tồn tại trong DB
            matched_product = db.query(Product).filter(Product.code == ai_sku).first()
            if not matched_product or matched_product.current_stock <= 0:
                logger.warning(f"AI trả về SKU không hợp lệ hoặc hết tồn ({ai_sku}), chuyển sang Fallback.")
                return _build_fallback_order()

            # Validate số lượng xuất
            ai_qty = int(parsed.get("quantity", 1))
            if ai_qty <= 0 or ai_qty > matched_product.current_stock:
                ai_qty = max(1, min(ai_qty, matched_product.current_stock))

            disc = float(parsed.get("discount_percent", 0.0))
            std_price = matched_product.standard_price
            sug_price = round(std_price * (1 - disc / 100), 0)
            reason = parsed.get("reason", "Đơn hàng tối ưu từ Gemini AI.")
            sc_id = parsed.get("scenario_id", candidate_scenarios[0]["id"])
            rec_name = parsed.get("recipient_name", candidate_scenarios[0]["persona_name"])
            role = parsed.get("role", candidate_scenarios[0].get("role", "individual"))

            note_str = f"Đơn hàng AI: {rec_name} ({role}) - Đề xuất giảm giá {disc:.0f}%: {reason}"

            response_obj = GenerateOrderResponse(
                scenario_id=sc_id,
                recipient_name=rec_name,
                role=role,
                product_id=matched_product.id,
                product_code=matched_product.code,
                product_name=matched_product.name,
                current_stock=matched_product.current_stock,
                quantity=ai_qty,
                unit_price=std_price,
                discount_percent=disc,
                suggested_unit_price=sug_price,
                reason=reason,
                note=note_str,
                is_fallback=False,
                provider="gemini",
                is_cached=False,
            )

            # Lưu vào cache trong ngày để các lần bấm tiếp theo trong ngày không gọi lại API
            AICacheManager.set("generated_order", cache_key, response_obj.model_dump())
            return response_obj

        except Exception as e:
            logger.error(f"Lỗi khi gọi Gemini API cho generate_ai_order: {e}. Kích hoạt Fallback.", exc_info=True)
            return _build_fallback_order()

    @classmethod
    def ask_ai(
        cls,
        db: Session,
        question: str,
        month: Optional[int] = None,
        year: Optional[int] = None,
        include_smartkho: bool = False,
        period_type: Optional[str] = None,
        target_date: Optional[date] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> AskAIResponse:
        """Hỏi đáp tương tác với Trợ lý AI.

        - include_smartkho=False: Gửi thuần câu hỏi, để AI hoàn toàn tự do trả lời, không chèn số liệu kho hay đề mục báo cáo.
        - include_smartkho=True: Nạp ngữ cảnh số liệu #SmartKho và chèn cấu trúc phân tích điều hành kho bãi.
        """
        now = get_now_vn()
        timestamp_str = now.strftime("%H:%M:%S %d/%m/%Y")

        # ==============================================================
        # CHẾ ĐỘ 1: THUẦN CÂU HỎI (AI TỰ DO TRẢ LỜI, KHÔNG CHÈN DỮ LIỆU KHO)
        # ==============================================================
        if not include_smartkho:
            def _build_pure_fallback() -> AskAIResponse:
                return AskAIResponse(
                    question=question,
                    answer=f"Hệ thống đang ở chế độ ngoại tuyến. Để AI tự do giải đáp câu hỏi '{question}', vui lòng kết nối Gemini API.",
                    provider="heuristic_fallback",
                    is_fallback=True,
                    timestamp=timestamp_str,
                    include_smartkho=False,
                )

            if not settings.GEMINI_API_KEY:
                return _build_pure_fallback()

            try:
                prompt_content = (
                    "Hãy trả lời câu hỏi sau đây một cách tự nhiên, tự do, đầy đủ, súc tích và chính xác:\n\n"
                    f'"{question}"\n\n'
                    "Trả về duy nhất 1 JSON object theo định dạng:\n"
                    '{"answer": "<nội dung câu trả lời>"}'
                )

                raw_text = cls._call_gemini_with_models(prompt_content)
                parsed = json.loads(raw_text)
                ai_ans = parsed.get("answer", "")
                if not ai_ans:
                    ai_ans = raw_text

                return AskAIResponse(
                    question=question,
                    answer=ai_ans,
                    provider="gemini",
                    is_fallback=False,
                    timestamp=timestamp_str,
                    include_smartkho=False,
                )
            except Exception as e:
                logger.error(f"Lỗi khi gọi Gemini API cho ask_ai (pure mode): {e}", exc_info=True)
                return _build_pure_fallback()

        # ==============================================================
        # CHẾ ĐỘ 2: YÊU CẦU VỀ #SmartKho (CHÈN SỐ LIỆU & ĐỀ MỤC BÁO CÁO)
        # ==============================================================
        target_month = month or now.month
        target_year = year or now.year

        start_d, end_d, period_str, is_subperiod = AICacheManager.resolve_period_range(
            period_type=period_type,
            target_date=target_date,
            start_date=start_date,
            end_date=end_date,
            month=target_month,
            year=target_year,
        )
        metrics = (
            cls.get_period_aggregated_data(db, start_d, end_d)
            if is_subperiod
            else cls.get_monthly_aggregated_data(db, month=target_month, year=target_year)
        )
        top_str_list = [
            f"{p.product_code} - {p.product_name} (xuất {p.quantity})"
            for p in metrics.top_exported_products
        ]
        top_exports_text = ", ".join(top_str_list) if top_str_list else "Chưa có lượt xuất trong kỳ."

        # G. Tổng hợp số phiếu và tổng giá trị tiền nhập / xuất hợp lệ trong kỳ + tổng giá trị tồn kho ước tính
        start_dt = datetime(start_d.year, start_d.month, start_d.day, 0, 0, 0)
        end_dt = datetime(end_d.year, end_d.month, end_d.day, 23, 59, 59, 999999)

        valid_import_notes_count = int(
            db.query(func.count(ImportNote.id))
            .filter(
                ImportNote.status != "CANCELLED",
                ImportNote.status == "COMPLETED",
                ImportNote.note_date >= start_dt,
                ImportNote.note_date <= end_dt,
            )
            .scalar()
            or 0
        )
        total_import_money = int(
            round(
                float(
                    db.query(func.coalesce(func.sum(ImportNote.total_amount), 0.0))
                    .filter(
                        ImportNote.status != "CANCELLED",
                        ImportNote.status == "COMPLETED",
                        ImportNote.note_date >= start_dt,
                        ImportNote.note_date <= end_dt,
                    )
                    .scalar()
                    or 0.0
                )
            )
        )

        valid_export_notes_count = int(
            db.query(func.count(ExportNote.id))
            .filter(
                ExportNote.status != "CANCELLED",
                ExportNote.status == "COMPLETED",
                ExportNote.note_date >= start_dt,
                ExportNote.note_date <= end_dt,
            )
            .scalar()
            or 0
        )
        total_export_money = int(
            round(
                float(
                    db.query(func.coalesce(func.sum(ExportNote.total_amount), 0.0))
                    .filter(
                        ExportNote.status != "CANCELLED",
                        ExportNote.status == "COMPLETED",
                        ExportNote.note_date >= start_dt,
                        ExportNote.note_date <= end_dt,
                    )
                    .scalar()
                    or 0.0
                )
            )
        )

        estimated_inventory_money = int(
            round(
                float(
                    db.query(
                        func.coalesce(func.sum(Product.current_stock * Product.standard_price), 0.0)
                    ).scalar()
                    or 0.0
                )
            )
        )

        import_money_fmt = f"{total_import_money:,} VNĐ"
        export_money_fmt = f"{total_export_money:,} VNĐ"
        inventory_money_fmt = f"{estimated_inventory_money:,} VNĐ"

        # I. Truy vấn danh sách mặt hàng dưới tồn an toàn (current_stock <= min_stock), sắp theo mức thiếu giảm dần, tối đa 20 dòng
        low_stock_products = (
            db.query(Product.code, Product.name, Product.current_stock, Product.min_stock)
            .filter(Product.current_stock <= Product.min_stock)
            .order_by((Product.min_stock - Product.current_stock).desc(), Product.current_stock.asc(), Product.id.asc())
            .limit(20)
            .all()
        )
        if low_stock_products:
            low_stock_details_lines = [
                f"  + {row[0]} - {row[1]} (tồn hiện tại: {row[2]}, tồn an toàn tối thiểu: {row[3]}, thiếu: {max(0, row[3] - row[2])})"
                for row in low_stock_products
            ]
            low_stock_details_text = "\n".join(low_stock_details_lines)
        else:
            low_stock_details_text = "  + Không có mặt hàng nào dưới mức tồn an toàn."

        # H. Cập nhật diễn giải chính xác cho active_products + ghép đầy đủ thông tin tài chính & danh sách hàng dưới tồn an toàn
        context_info = (
            f"- Kỳ phân tích: {period_str} ({start_d.isoformat()} đến {end_d.isoformat()})\n"
            f"- Tổng số mặt hàng quản lý: {metrics.total_products} mặt hàng đang kinh doanh (trong đó {metrics.active_products} mặt hàng có phát sinh nhập/xuất trong kỳ)\n"
            f"- Số mặt hàng dưới mức tồn kho an toàn (low stock): {metrics.low_stock_count}\n"
            f"- Danh sách mặt hàng dưới mức tồn an toàn (tối đa 20 mã, sắp theo mức thiếu giảm dần):\n{low_stock_details_text}\n"
            f"- Tổng số lượng nhập kho trong kỳ: {metrics.total_imports_qty} đơn vị ({valid_import_notes_count} phiếu nhập hợp lệ)\n"
            f"- Tổng giá trị tiền nhập kho trong kỳ: {import_money_fmt}\n"
            f"- Tổng số lượng xuất kho trong kỳ: {metrics.total_exports_qty} đơn vị ({valid_export_notes_count} phiếu xuất hợp lệ)\n"
            f"- Tổng giá trị tiền xuất kho trong kỳ: {export_money_fmt}\n"
            f"- Tổng giá trị tồn kho hiện tại ước tính: {inventory_money_fmt}\n"
            f"- Top mặt hàng xuất nhiều nhất: {top_exports_text}\n"
        )

        def _build_smartkho_fallback() -> AskAIResponse:
            q_lower = question.lower()
            low_stock_inline = ", ".join(
                [f"{r[0]} ({r[1]}: tồn {r[2]}/{r[3]})" for r in low_stock_products[:10]]
            ) or "Không có"
            if any(k in q_lower for k in ["tồn kho", "an toàn", "dưới mức", "hết hàng", "thiếu"]):
                ans = (
                    f"**[Báo Cáo #SmartKho - Tồn Kho An Toàn Kỳ {target_month}/{target_year}]**\n\n"
                    f"• Quy mô: **{metrics.total_products} mặt hàng đang kinh doanh** (trong đó {metrics.active_products} mặt hàng có phát sinh nhập/xuất trong kỳ).\n"
                    f"• Ghi nhận **{metrics.low_stock_count} mặt hàng** đang dưới mức tồn kho an toàn (min_stock): {low_stock_inline}.\n"
                    f"• Tổng giá trị tồn kho hiện tại ước tính: **{inventory_money_fmt}**.\n"
                    f"• Đề xuất hành động: Ưu tiên nhập bổ sung ngay các mã hàng thiếu hụt cao nhất ở trên để tránh đứt gãy nguồn cung."
                )
            elif any(k in q_lower for k in ["tiền", "giá trị", "doanh thu", "chi phí", "ra vào"]):
                ans = (
                    f"**[Báo Cáo #SmartKho - Lưuuyển Hàng Hóa & Giá Trị Kỳ {target_month}/{target_year}]**\n\n"
                    f"• Nhập kho: **{metrics.total_imports_qty} sản phẩm** qua **{valid_import_notes_count} phiếu nhập hợp lệ** — Tổng tiền nhập: **{import_money_fmt}**.\n"
                    f"• Xuất kho: **{metrics.total_exports_qty} sản phẩm** qua **{valid_export_notes_count} phiếu xuất hợp lệ** — Tổng tiền xuất: **{export_money_fmt}**.\n"
                    f"• Tổng giá trị tồn kho hiện tại ước tính: **{inventory_money_fmt}**.\n"
                    f"• Mặt hàng dưới tồn an toàn ({metrics.low_stock_count} mã): {low_stock_inline}."
                )
            elif any(k in q_lower for k in ["xuất", "bán", "tiêu thụ", "chạy"]):
                ans = (
                    f"**[Báo Cáo #SmartKho - Xuất Kho & Tiêu Thụ Kỳ {target_month}/{target_year}]**\n\n"
                    f"• Tổng sản lượng xuất trong tháng: **{metrics.total_exports_qty} sản phẩm** ({valid_export_notes_count} phiếu xuất, tổng giá trị xuất **{export_money_fmt}**).\n"
                    f"• Top mặt hàng xuất nhiều nhất: {top_exports_text}."
                )
            elif any(k in q_lower for k in ["nhập", "mua", "nhà cung cấp"]):
                ans = (
                    f"**[Báo Cáo #SmartKho - Nhập Kho Kỳ {target_month}/{target_year}]**\n\n"
                    f"• Tổng số lượng nhập kho: **{metrics.total_imports_qty} sản phẩm** ({valid_import_notes_count} phiếu nhập, tổng giá trị nhập **{import_money_fmt}**) "
                    f"so với lượng xuất {metrics.total_exports_qty} sản phẩm ({export_money_fmt})."
                )
            else:
                ans = (
                    f"**[Báo Cáo #SmartKho Tổng Thể Kỳ {target_month}/{target_year}]**\n\n"
                    f"• Quy mô quản lý: {metrics.total_products} mặt hàng đang kinh doanh (trong đó {metrics.active_products} mặt hàng có phát sinh nhập/xuất trong kỳ).\n"
                    f"• Lưu chuyển trong kỳ: Nhập +{metrics.total_imports_qty} ({valid_import_notes_count} phiếu, {import_money_fmt}), Xuất -{metrics.total_exports_qty} ({valid_export_notes_count} phiếu, {export_money_fmt}).\n"
                    f"• Tổng giá trị tồn kho hiện tại ước tính: {inventory_money_fmt}.\n"
                    f"• Tồn kho an toàn: Có {metrics.low_stock_count} mặt hàng dưới mức tối thiểu ({low_stock_inline}).\n"
                    f"• Tư vấn cho câu hỏi '{question}': Cần bám sát kế hoạch cân đối tồn kho theo tốc độ tiêu thụ thực tế."
                )

            return AskAIResponse(
                question=question,
                answer=ans,
                provider="heuristic_fallback",
                is_fallback=True,
                timestamp=timestamp_str,
                include_smartkho=True,
            )

        if not settings.GEMINI_API_KEY:
            return _build_smartkho_fallback()

        try:
            prompt_content = (
                "Bạn là Trợ lý AI Chuyên gia Quản lý Kho Vận #SmartKho.\n"
                "Người dùng đã kích hoạt tùy chọn: [Yêu cầu về #SmartKho].\n"
                "Hãy kết hợp số liệu thực tế của hệ thống kho vận kỳ này để phân tích chuyên sâu, đưa ra các đề mục báo cáo và giải pháp điều hành cụ thể.\n\n"
                f"SỐ LIỆU KHO THỰC TẾ KỲ {target_month}/{target_year}:\n"
                f"{context_info}\n"
                f"CÂU HỎI/YÊU CẦU CỦA NGƯỜI DÙNG:\n"
                f'"{question}"\n\n'
                "YÊU CẦU ĐỊNH DẠNG ĐÁP ÁN:\n"
                "- Trình bày chuyên nghiệp theo các đề mục báo cáo kho rõ ràng kèm khuyến nghị hành động tương ứng.\n"
                "- Trả về duy nhất 1 JSON object theo định dạng:\n"
                '{"answer": "<Nội dung phân tích báo cáo kho #SmartKho chi tiết>"}\n'
            )

            raw_text = cls._call_gemini_with_models(prompt_content)
            parsed = json.loads(raw_text)
            ai_ans = parsed.get("answer", "")
            if not ai_ans:
                ai_ans = raw_text

            return AskAIResponse(
                question=question,
                answer=ai_ans,
                provider="gemini",
                is_fallback=False,
                timestamp=timestamp_str,
                include_smartkho=True,
            )
        except Exception as e:
            logger.error(f"Lỗi khi gọi Gemini API cho ask_ai (smartkho mode): {e}", exc_info=True)
            return _build_smartkho_fallback()



