"""Pydantic schemas cho module AI Trợ lý và Heuristic Fallback Engine."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ==========================================
# 1. Báo cáo Nhập - Xuất - Tồn theo tháng
# ==========================================

class TopExportedProductItem(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    quantity: int


class MonthlyReportMetrics(BaseModel):
    total_products: int = Field(..., description="Tổng số mặt hàng đang quản lý")
    active_products: int = Field(..., description="Số mặt hàng có phát sinh giao dịch trong kỳ")
    total_imports_qty: int = Field(..., description="Tổng số lượng hàng nhập trong kỳ")
    total_exports_qty: int = Field(..., description="Tổng số lượng hàng xuất trong kỳ")
    low_stock_count: int = Field(..., description="Số mặt hàng đang dưới mức tồn tối thiểu")
    top_exported_products: List[TopExportedProductItem] = Field(
        default_factory=list, description="Top mặt hàng xuất nhiều nhất trong kỳ"
    )


class MonthlyReportResponse(BaseModel):
    period: str = Field(..., description="Kỳ báo cáo định dạng MM/YYYY")
    is_fallback: bool = Field(..., description="True nếu báo cáo được sinh bởi Heuristic Fallback")
    provider: str = Field(..., description="gemini | heuristic_fallback")
    metrics: MonthlyReportMetrics
    executive_summary: str = Field(..., description="Tóm tắt nhận xét điều hành từ AI hoặc Fallback")
    recommendations: List[str] = Field(default_factory=list, description="Các khuyến nghị quản lý kho")
    is_cached: bool = Field(default=False, description="True nếu kết quả lấy từ bộ nhớ đệm trong ngày")


# ==========================================
# 2. Gợi ý Nhập hàng Tối ưu (Restock)
# ==========================================

class RestockSuggestionItem(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    current_stock: int
    min_stock: int
    daily_velocity: float = Field(..., description="Tốc độ xuất bình quân ngày (30 ngày qua)")
    estimated_days_left: Optional[float] = Field(
        None, description="Số ngày dự kiến hết hàng dựa trên tốc độ xuất"
    )
    suggested_quantity: int = Field(..., description="Số lượng đề xuất nhập")
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(..., description="Mức độ ưu tiên nhập hàng")
    reason: str = Field(..., description="Lý do đề xuất nhập")


class RestockSuggestionsResponse(BaseModel):
    lookback_days: int = Field(default=30, description="Khoảng thời gian phân tích (ngày)")
    is_fallback: bool = Field(..., description="True nếu được sinh bởi Heuristic Fallback")
    provider: str = Field(..., description="gemini | heuristic_fallback")
    total_suggested_items: int = Field(..., description="Tổng số mặt hàng được gợi ý nhập")
    items: List[RestockSuggestionItem] = Field(default_factory=list)
    executive_summary: str = Field(..., description="Tóm tắt tình hình bổ sung kho")
    is_cached: bool = Field(default=False, description="True nếu kết quả lấy từ bộ nhớ đệm trong ngày")


# ==========================================
# 3. Tóm tắt Biến động Bất thường (Anomalies)
# ==========================================

class AnomalyItem(BaseModel):
    product_id: int
    product_code: str
    product_name: str
    anomaly_type: Literal["SURGE_EXPORT", "DEAD_STOCK"] = Field(
        ..., description="SURGE_EXPORT: Xuất tăng đột biến | DEAD_STOCK: Hàng tồn lâu ngày"
    )
    description: str = Field(..., description="Mô tả hiện tượng bất thường")
    details: Dict[str, Any] = Field(default_factory=dict, description="Chi tiết thông số số học")
    suggested_action: str = Field(..., description="Hành động đề xuất giải quyết")


class AnomalyDetectionResponse(BaseModel):
    lookback_days: int = Field(default=30, description="Khoảng thời gian phân tích (ngày)")
    is_fallback: bool = Field(..., description="True nếu được sinh bởi Heuristic Fallback")
    provider: str = Field(..., description="gemini | heuristic_fallback")
    total_anomalies: int = Field(..., description="Tổng số trường hợp bất thường phát hiện")
    anomalies: List[AnomalyItem] = Field(default_factory=list)
    executive_summary: str = Field(..., description="Tóm tắt nhận định các bất thường")
    is_cached: bool = Field(default=False, description="True nếu kết quả lấy từ bộ nhớ đệm trong ngày")


# ==========================================
# 4. Sinh Đơn Hàng AI (AI Order Generation)
# ==========================================

class GenerateOrderResponse(BaseModel):
    scenario_id: str = Field(..., description="Mã kịch bản được chọn")
    recipient_name: str = Field(..., description="Tên người nhận / Tên tổ chức")
    role: Literal["individual", "company", "dealer"] = Field(..., description="Vai trò khách hàng")
    product_id: int = Field(..., description="ID sản phẩm trong CSDL")
    product_code: str = Field(..., description="Mã SKU sản phẩm")
    product_name: str = Field(..., description="Tên sản phẩm")
    current_stock: int = Field(..., description="Số lượng tồn kho hiện tại")
    quantity: int = Field(..., description="Số lượng đề xuất xuất kho")
    unit_price: float = Field(..., description="Đơn giá chuẩn của sản phẩm")
    discount_percent: float = Field(default=0.0, description="Phần trăm giảm giá đề xuất (%)")
    suggested_unit_price: float = Field(..., description="Đơn giá gợi ý sau chiết khấu (để tham khảo)")
    reason: str = Field(..., description="Lý do đề xuất từ AI")
    note: str = Field(..., description="Nội dung ghi chú tạo sẵn cho phiếu xuất")
    is_fallback: bool = Field(default=False, description="True nếu được sinh bởi fallback nội bộ")
    provider: str = Field(default="gemini", description="gemini | heuristic_fallback")
    is_cached: bool = Field(default=False, description="True nếu kết quả lấy từ bộ nhớ đệm trong ngày")


# ==========================================
# 5. Hỏi đáp Trợ lý AI (Interactive Q&A)
# ==========================================

class AskAIRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Nội dung câu hỏi gửi đến AI")
    month: Optional[int] = Field(None, ge=1, le=12, description="Tháng báo cáo ngữ cảnh")
    year: Optional[int] = Field(None, ge=2020, le=2100, description="Năm báo cáo ngữ cảnh")
    include_smartkho: bool = Field(
        default=False,
        description="Nút tích 'Yêu cầu về #SmartKho': Nếu tích chọn thì chèn số liệu kho và cấu trúc đề mục báo cáo; nếu không tích thì chỉ gửi thuần câu hỏi.",
    )


class AskAIResponse(BaseModel):
    question: str = Field(..., description="Câu hỏi người dùng đã gửi")
    answer: str = Field(..., description="Câu trả lời từ AI hoặc Fallback Engine")
    provider: str = Field(default="gemini", description="gemini | heuristic_fallback")
    is_fallback: bool = Field(default=False, description="True nếu câu trả lời sinh bởi Fallback")
    timestamp: str = Field(..., description="Thời điểm phản hồi")
    include_smartkho: bool = Field(default=False, description="True nếu câu trả lời kèm ngữ cảnh #SmartKho")

