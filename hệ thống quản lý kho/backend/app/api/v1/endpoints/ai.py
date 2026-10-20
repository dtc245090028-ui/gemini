"""API endpoints cho Module AI Trợ lý và Phân tích Kho thông minh."""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import check_ai_rate_limit, get_db, require_roles
from app.models.user import User
from app.schemas.ai import (
    AnomalyDetectionResponse,
    AskAIRequest,
    AskAIResponse,
    GenerateOrderResponse,
    MonthlyReportResponse,
    RestockSuggestionsResponse,
)
from app.schemas.user import UserRole
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["Trí tuệ nhân tạo (AI)"])


@router.get(
    "/monthly-report",
    response_model=MonthlyReportResponse,
    summary="AI sinh Báo cáo Nhập - Xuất - Tồn theo kỳ hoặc khoảng ngày",
    description=(
        "Tổng hợp số liệu xuất nhập tồn theo tháng, tuần, ngày hoặc khoảng ngày; kiểm tra bản lưu "
        "kèm dấu vết dữ liệu trước khi gọi Google Gemini hoặc Heuristic Fallback Engine."
    ),
)
def get_ai_monthly_report(
    month: Optional[int] = Query(None, ge=1, le=12, description="Tháng báo cáo (1-12)"),
    year: Optional[int] = Query(None, ge=2020, le=2100, description="Năm báo cáo"),
    period_type: Optional[str] = Query(None, description="Chuẩn hóa mốc: month | week | day | custom"),
    target_date: Optional[date] = Query(None, description="Ngày mốc YYYY-MM-DD (cho day/week/month)"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc YYYY-MM-DD"),
    force_refresh: bool = Query(False, description="Bỏ qua bản lưu và tạo lại bằng AI"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER, UserRole.ACCOUNTANT])
    ),
):
    if force_refresh:
        check_ai_rate_limit(current_user)
    return AIService.generate_monthly_report(
        db,
        month=month,
        year=year,
        force_refresh=force_refresh,
        period_type=period_type,
        target_date=target_date,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/restock-suggestions",
    response_model=RestockSuggestionsResponse,
    summary="AI gợi ý nhập hàng tối ưu",
    description=(
        "Phân tích tồn kho hiện tại, mức tồn an toàn và tốc độ xuất kho (daily velocity) "
        "để đề xuất số lượng nhập hàng và mức độ ưu tiên (HIGH, MEDIUM, LOW)."
    ),
)
def get_ai_restock_suggestions(
    lookback_days: int = Query(
        30, ge=1, le=365, description="Số ngày phân tích lịch sử xuất (mặc định 30 ngày)"
    ),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu phân tích YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc phân tích YYYY-MM-DD"),
    force_refresh: bool = Query(False, description="Bỏ qua bản lưu và phân tích lại"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER, UserRole.ACCOUNTANT])
    ),
):
    if force_refresh:
        check_ai_rate_limit(current_user)
    return AIService.generate_restock_suggestions(
        db,
        lookback_days=lookback_days,
        force_refresh=force_refresh,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/anomalies",
    response_model=AnomalyDetectionResponse,
    summary="AI tóm tắt biến động bất thường",
    description=(
        "Nhận diện và tóm tắt các hiện tượng bất thường trong kho: xuất tăng đột biến (> 200%) "
        "hoặc hàng tồn lâu ngày không luân chuyển (> 30 ngày)."
    ),
)
def get_ai_anomalies(
    lookback_days: int = Query(
        30, ge=1, le=365, description="Số ngày phân tích lịch sử (mặc định 30 ngày)"
    ),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu phân tích YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc phân tích YYYY-MM-DD"),
    force_refresh: bool = Query(False, description="Bỏ qua bản lưu và phân tích lại"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER, UserRole.ACCOUNTANT])
    ),
):
    if force_refresh:
        check_ai_rate_limit(current_user)
    return AIService.generate_anomaly_detection(
        db,
        lookback_days=lookback_days,
        force_refresh=force_refresh,
        start_date=start_date,
        end_date=end_date,
    )


@router.post(
    "/generate-order",
    response_model=GenerateOrderResponse,
    summary="AI tự động đề xuất đơn hàng xuất kho",
    description=(
        "Chọn ngẫu nhiên kịch bản khách hàng, phân tích tồn kho thực tế và sử dụng Gemini AI "
        "để đề xuất sản phẩm, số lượng xuất và chiết khấu phù hợp. Có cache kết quả trong ngày."
    ),
)
def generate_ai_order(
    force_refresh: bool = Query(False, description="Bỏ qua cache trong ngày và sinh đơn mới"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER])
    ),
):
    if force_refresh:
        check_ai_rate_limit(current_user)
    return AIService.generate_ai_order(db, force_refresh=force_refresh)


@router.post(
    "/ask",
    response_model=AskAIResponse,
    summary="Hỏi đáp chuyên sâu với Trợ lý AI",
    description=(
        "Gửi câu hỏi điều hành kho vận cho Trợ lý AI. Hệ thống tự động nạp số liệu ngữ cảnh "
        "thực tế (đã bảo mật giá mua) để AI phân tích và đưa ra giải pháp cụ thể."
    ),
)
def ask_ai_question(
    payload: AskAIRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER, UserRole.ACCOUNTANT])
    ),
):
    check_ai_rate_limit(current_user)
    return AIService.ask_ai(
        db,
        question=payload.question,
        month=payload.month,
        year=payload.year,
        include_smartkho=payload.include_smartkho,
    )


