"""API endpoints cho Module AI Trợ lý và Phân tích Kho thông minh."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.ai import (
    AnomalyDetectionResponse,
    MonthlyReportResponse,
    RestockSuggestionsResponse,
)
from app.schemas.user import UserRole
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["Trí tuệ nhân tạo (AI)"])


@router.get(
    "/monthly-report",
    response_model=MonthlyReportResponse,
    summary="AI sinh Báo cáo Nhập - Xuất - Tồn theo tháng",
    description=(
        "Tổng hợp số liệu xuất nhập tồn trong tháng, phân tích xu hướng và đưa ra nhận xét "
        "điều hành kèm khuyến nghị từ Google Gemini hoặc Heuristic Fallback Engine khi offline."
    ),
)
def get_ai_monthly_report(
    month: Optional[int] = Query(None, ge=1, le=12, description="Tháng báo cáo (1-12)"),
    year: Optional[int] = Query(None, ge=2020, le=2100, description="Năm báo cáo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER, UserRole.ACCOUNTANT])
    ),
):
    return AIService.generate_monthly_report(db, month=month, year=year)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER, UserRole.ACCOUNTANT])
    ),
):
    return AIService.generate_restock_suggestions(db, lookback_days=lookback_days)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.WAREHOUSE_KEEPER, UserRole.ACCOUNTANT])
    ),
):
    return AIService.generate_anomaly_detection(db, lookback_days=lookback_days)
