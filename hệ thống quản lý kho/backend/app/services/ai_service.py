"""Dịch vụ AI Trợ lý kho thông minh (Google Gemini API + Heuristic Fallback Engine).

Đặc tả:
1. Data Pre-processing Pipeline: SQL tính toán trước số liệu tổng hợp.
2. Bảo mật: Bắt buộc lọc sạch thông tin giá mua nhập hàng (unit_price) trước khi gửi prompt.
3. Fallback-first: Tự động dùng FallbackService nếu thiếu GEMINI_API_KEY hoặc mất mạng/lỗi quota.
4. Structured Output: Định dạng JSON đồng nhất giữa AI và Fallback.
"""

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.export_note import ExportNote, ExportNoteDetail
from app.models.import_note import ImportNote, ImportNoteDetail
from app.models.product import Product
from app.models.stock_ledger import StockLedger
from app.schemas.ai import (
    AnomalyDetectionResponse,
    AnomalyItem,
    MonthlyReportMetrics,
    MonthlyReportResponse,
    RestockSuggestionItem,
    RestockSuggestionsResponse,
    TopExportedProductItem,
)
from app.services.fallback_service import FallbackService
from app.services.ai_cache import AICacheManager

logger = logging.getLogger(__name__)

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
    def get_monthly_aggregated_data(
        db: Session, month: int, year: int
    ) -> MonthlyReportMetrics:
        """SQL Pipeline tổng hợp số liệu tháng. Tuyệt đối KHÔNG trả về giá mua."""
        # Xác định khoảng thời gian đầu tháng - cuối tháng
        start_date = datetime(year, month, 1, 0, 0, 0)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0)

        # 1. Tổng số mặt hàng đang quản lý
        total_products = db.query(func.count(Product.id)).scalar() or 0

        # 2. Số lượng mặt hàng dưới mức tồn tối thiểu
        low_stock_count = (
            db.query(func.count(Product.id))
            .filter(Product.current_stock <= Product.min_stock)
            .scalar()
            or 0
        )

        # 3. Tổng lượng nhập trong tháng (chỉ lấy tổng quantity của phiếu COMPLETED)
        total_imports_qty = (
            db.query(func.coalesce(func.sum(ImportNoteDetail.quantity), 0))
            .join(ImportNote, ImportNoteDetail.import_note_id == ImportNote.id)
            .filter(
                ImportNote.status == "COMPLETED",
                ImportNote.note_date >= start_date,
                ImportNote.note_date < end_date,
            )
            .scalar()
            or 0
        )

        # 4. Tổng lượng xuất trong tháng (chỉ lấy tổng quantity của phiếu COMPLETED)
        total_exports_qty = (
            db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
            .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
            .filter(
                ExportNote.status == "COMPLETED",
                ExportNote.note_date >= start_date,
                ExportNote.note_date < end_date,
            )
            .scalar()
            or 0
        )

        # 5. Top 5 mặt hàng xuất nhiều nhất trong tháng (chỉ lấy ID, Code, Name, Quantity)
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
                ExportNote.note_date >= start_date,
                ExportNote.note_date < end_date,
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
                StockLedger.transaction_date >= start_date,
                StockLedger.transaction_date < end_date,
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

    @staticmethod
    def get_restock_candidates_data(
        db: Session, lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Lọc danh sách các mặt hàng có nguy cơ thiếu tồn kho hoặc dưới tồn tối thiểu."""
        cutoff_date = datetime.now() - timedelta(days=lookback_days)

        # Lấy toàn bộ sản phẩm đang hoạt động
        products = db.query(Product).filter(Product.status != "DISCONTINUED").all()
        candidates: List[Dict[str, Any]] = []

        for p in products:
            # Tính tổng lượng xuất 30 ngày qua
            total_exported = (
                db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
                .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
                .filter(
                    ExportNoteDetail.product_id == p.id,
                    ExportNote.status == "COMPLETED",
                    ExportNote.note_date >= cutoff_date,
                )
                .scalar()
                or 0
            )

            daily_velocity = float(total_exported) / max(float(lookback_days), 1.0)
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
        db: Session, lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """Nhận diện 2 nhóm bất thường: Xuất tăng đột biến (>200%) và Hàng tồn lâu ngày (>30 ngày)."""
        now = datetime.now()
        recent_7d_cutoff = now - timedelta(days=7)
        previous_cutoff = now - timedelta(days=lookback_days)

        products = db.query(Product).filter(Product.status != "DISCONTINUED").all()
        anomalies: List[Dict[str, Any]] = []

        for p in products:
            # 1. Kiểm tra xuất tăng đột biến:
            # Lượng xuất 7 ngày gần nhất
            recent_7d_qty = (
                db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
                .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
                .filter(
                    ExportNoteDetail.product_id == p.id,
                    ExportNote.status == "COMPLETED",
                    ExportNote.note_date >= recent_7d_cutoff,
                )
                .scalar()
                or 0
            )

            # Lượng xuất trong toàn bộ lookback period (30 ngày)
            total_lookback_qty = (
                db.query(func.coalesce(func.sum(ExportNoteDetail.quantity), 0))
                .join(ExportNote, ExportNoteDetail.export_note_id == ExportNote.id)
                .filter(
                    ExportNoteDetail.product_id == p.id,
                    ExportNote.status == "COMPLETED",
                    ExportNote.note_date >= previous_cutoff,
                )
                .scalar()
                or 0
            )

            # Tính mức bình quân tuần của khoảng thời gian trước đó
            earlier_qty = total_lookback_qty - recent_7d_qty
            earlier_weeks = max((lookback_days - 7) / 7.0, 1.0)
            baseline_weekly = earlier_qty / earlier_weeks

            # Nếu 7 ngày qua xuất >= 5 đơn vị và gấp > 2.0 lần (200%) mức bình quân tuần trước
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
            # Tồn kho > 0 nhưng trong 30 ngày qua không có bất kỳ phiếu xuất nào
            if p.current_stock > 0 and total_lookback_qty == 0:
                # Kiểm tra ngày giao dịch xuất cuối cùng nếu có
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
                    (now - last_export_date).days
                    if last_export_date
                    else lookback_days
                )
                anomalies.append(
                    {
                        "product_id": p.id,
                        "product_code": p.code,
                        "product_name": p.name,
                        "anomaly_type": "DEAD_STOCK",
                        "current_stock": p.current_stock,
                        "days_inactive": max(days_inactive, lookback_days),
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
    # 3. GỌI GEMINI API VỚI HEURISTIC FALLBACK DỰ PHÒNG
    # =========================================================================

    @classmethod
    def generate_monthly_report(
        cls, db: Session, month: Optional[int] = None, year: Optional[int] = None, force_refresh: bool = False
    ) -> MonthlyReportResponse:
        """Sinh Báo cáo Nhập-Xuất-Tồn tháng: Có Cache trong ngày, ưu tiên Gemini LLM, tự động fallback nếu offline."""
        now = datetime.now()
        target_month = month or now.month
        target_year = year or now.year
        period_str = f"{target_month:02d}/{target_year}"
        cache_key = f"{target_year}_{target_month:02d}"

        # 0. Kiểm tra Cache trong ngày nếu không ép buộc làm mới
        if not force_refresh:
            cached = AICacheManager.get("monthly_report", cache_key)
            if cached:
                cached["is_cached"] = True
                return MonthlyReportResponse(**cached)

        # 1. SQL tiền xử lý số liệu
        metrics = cls.get_monthly_aggregated_data(db, target_month, target_year)

        # 2. Kiểm tra nếu chưa cấu hình GEMINI_API_KEY -> Dùng ngay Fallback Engine
        if not settings.GEMINI_API_KEY:
            summary, recs = FallbackService.generate_monthly_report_fallback(metrics, period_str)
            return MonthlyReportResponse(
                period=period_str,
                is_fallback=True,
                provider="heuristic_fallback",
                metrics=metrics,
                executive_summary=summary,
                recommendations=recs,
                is_cached=False,
            )

        # 3. Cố gắng gọi Gemini API nếu đã có key
        try:
            top_products_text = "\n".join(
                [f"- {p.product_code}: {p.product_name} (xuất {p.quantity} đơn vị)" for p in metrics.top_exported_products]
            ) or "Không có mặt hàng xuất trong kỳ."

            template = cls._read_prompt_template("inventory_report_prompt.txt")
            user_prompt = (
                f"Kỳ báo cáo: {period_str}\n"
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
            response_obj = MonthlyReportResponse(
                period=period_str,
                is_fallback=False,
                provider="gemini",
                metrics=metrics,
                executive_summary=parsed.get("executive_summary", ""),
                recommendations=parsed.get("recommendations", []),
                is_cached=False,
            )
            # Lưu vào cache trong ngày để các lần xem tiếp theo không tốn quota
            AICacheManager.set("monthly_report", cache_key, response_obj.model_dump())
            return response_obj

        except Exception as e:
            logger.error(
                f"Lỗi khi gọi Gemini API cho monthly-report: {e}. Kích hoạt Heuristic Fallback.",
                exc_info=True,
            )
            summary, recs = FallbackService.generate_monthly_report_fallback(metrics, period_str)
            return MonthlyReportResponse(
                period=period_str,
                is_fallback=True,
                provider="heuristic_fallback",
                metrics=metrics,
                executive_summary=summary,
                recommendations=recs,
                is_cached=False,
            )

    @classmethod
    def generate_restock_suggestions(
        cls, db: Session, lookback_days: int = 30, force_refresh: bool = False
    ) -> RestockSuggestionsResponse:
        """Gợi ý nhập hàng: Có Cache trong ngày, ưu tiên Gemini LLM, tự động fallback nếu offline."""
        cache_key = f"{lookback_days}"

        # 0. Kiểm tra Cache trong ngày nếu không ép buộc làm mới
        if not force_refresh:
            cached = AICacheManager.get("restock_suggestions", cache_key)
            if cached:
                cached["is_cached"] = True
                return RestockSuggestionsResponse(**cached)

        candidates = cls.get_restock_candidates_data(db, lookback_days=lookback_days)

        # Mặc định tạo kết quả chuẩn qua Fallback Engine trước
        fallback_items, fallback_summary = FallbackService.generate_restock_suggestions_fallback(candidates)

        if not settings.GEMINI_API_KEY or not candidates:
            return RestockSuggestionsResponse(
                lookback_days=lookback_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_suggested_items=len(fallback_items),
                items=fallback_items,
                executive_summary=fallback_summary,
                is_cached=False,
            )

        # Cố gắng tối ưu nhận xét qua Gemini API
        try:
            template = cls._read_prompt_template("reorder_suggestion_prompt.txt")
            user_prompt = (
                f"Danh sách mặt hàng cần xem xét bổ sung (phân tích {lookback_days} ngày qua):\n"
                f"{json.dumps(candidates, ensure_ascii=False, indent=2)}\n"
                "Hãy trả về JSON theo schema: "
                '{"executive_summary": "...", "item_suggestions": [{"product_code": "...", "suggested_quantity": 0, "priority": "HIGH", "reason": "..."}]}'
            )

            prompt_content = f"{template}\n\nUser Input:\n{user_prompt}" if template else user_prompt
            raw_text = cls._call_gemini_with_models(prompt_content)

            parsed = json.loads(raw_text)
            ai_summary = parsed.get("executive_summary", fallback_summary)

            # Cập nhật lý do và số lượng từ AI nếu khớp mã sản phẩm
            ai_item_map = {
                it.get("product_code"): it
                for it in parsed.get("item_suggestions", [])
                if isinstance(it, dict) and "product_code" in it
            }

            final_items: List[RestockSuggestionItem] = []
            for item in fallback_items:
                if item.product_code in ai_item_map:
                    ai_rec = ai_item_map[item.product_code]
                    final_items.append(
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
                    final_items.append(item)

            response_obj = RestockSuggestionsResponse(
                lookback_days=lookback_days,
                is_fallback=False,
                provider="gemini",
                total_suggested_items=len(final_items),
                items=final_items,
                executive_summary=ai_summary,
                is_cached=False,
            )
            # Lưu vào cache trong ngày để các lần xem tiếp theo không tốn quota
            AICacheManager.set("restock_suggestions", cache_key, response_obj.model_dump())
            return response_obj

        except Exception as e:
            logger.error(
                f"Lỗi khi gọi Gemini API cho restock-suggestions: {e}. Dùng Fallback.",
                exc_info=True,
            )
            return RestockSuggestionsResponse(
                lookback_days=lookback_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_suggested_items=len(fallback_items),
                items=fallback_items,
                executive_summary=fallback_summary,
                is_cached=False,
            )

    @classmethod
    def generate_anomaly_detection(
        cls, db: Session, lookback_days: int = 30, force_refresh: bool = False
    ) -> AnomalyDetectionResponse:
        """Tóm tắt biến động bất thường: Có Cache trong ngày, ưu tiên Gemini LLM, tự động fallback nếu offline."""
        cache_key = f"{lookback_days}"

        # 0. Kiểm tra Cache trong ngày nếu không ép buộc làm mới
        if not force_refresh:
            cached = AICacheManager.get("anomaly_detection", cache_key)
            if cached:
                cached["is_cached"] = True
                return AnomalyDetectionResponse(**cached)

        candidates = cls.get_anomalies_candidates_data(db, lookback_days=lookback_days)

        fallback_anomalies, fallback_summary = FallbackService.generate_anomaly_detection_fallback(candidates)

        if not settings.GEMINI_API_KEY or not candidates:
            return AnomalyDetectionResponse(
                lookback_days=lookback_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_anomalies=len(fallback_anomalies),
                anomalies=fallback_anomalies,
                executive_summary=fallback_summary,
                is_cached=False,
            )

        try:
            template = cls._read_prompt_template("anomaly_detection_prompt.txt")
            user_prompt = (
                f"Danh sách bất thường phát hiện được ({lookback_days} ngày qua):\n"
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

            final_anomalies: List[AnomalyItem] = []
            for item in fallback_anomalies:
                if item.product_code in ai_action_map:
                    ai_act = ai_action_map[item.product_code]
                    final_anomalies.append(
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
                    final_anomalies.append(item)

            response_obj = AnomalyDetectionResponse(
                lookback_days=lookback_days,
                is_fallback=False,
                provider="gemini",
                total_anomalies=len(final_anomalies),
                anomalies=final_anomalies,
                executive_summary=ai_summary,
                is_cached=False,
            )
            # Lưu vào cache trong ngày để các lần xem tiếp theo không tốn quota
            AICacheManager.set("anomaly_detection", cache_key, response_obj.model_dump())
            return response_obj

        except Exception as e:
            logger.error(
                f"Lỗi khi gọi Gemini API cho anomalies: {e}. Dùng Fallback.",
                exc_info=True,
            )
            return AnomalyDetectionResponse(
                lookback_days=lookback_days,
                is_fallback=True,
                provider="heuristic_fallback",
                total_anomalies=len(fallback_anomalies),
                anomalies=fallback_anomalies,
                executive_summary=fallback_summary,
                is_cached=False,
            )
