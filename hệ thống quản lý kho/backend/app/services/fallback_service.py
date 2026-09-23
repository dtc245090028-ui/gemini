"""Heuristic Fallback Engine - Động cơ suy luận quy tắc dự phòng khi offline / thiếu API Key.

Đảm bảo:
- 100% Offline-safe: hoạt động độc lập không cần Internet hoặc API Key.
- Thời gian đáp ứng cực nhanh (< 50ms).
- Định dạng JSON trả về hoàn toàn đồng nhất với phản hồi từ Gemini LLM.
- Tính toán dựa trên số liệu thực tế trong CSDL (Deterministic Statistical Rules).
"""

from typing import Any, Dict, List, Tuple
from app.schemas.ai import (
    AnomalyItem,
    MonthlyReportMetrics,
    RestockSuggestionItem,
)


class FallbackService:
    """Xử lý phân tích dữ liệu kho bằng thuật toán quy tắc heuristic."""

    @staticmethod
    def generate_monthly_report_fallback(
        metrics: MonthlyReportMetrics, period: str
    ) -> Tuple[str, List[str]]:
        """Sinh nhận xét điều hành và khuyến nghị cho báo cáo nhập xuất tồn tháng."""
        if metrics.total_products == 0:
            summary = (
                f"Kỳ báo cáo {period}: Hiện tại hệ thống chưa ghi nhận mặt hàng nào trong kho. "
                "Cần khởi tạo danh mục hàng hóa và nhà cung cấp để bắt đầu vận hành."
            )
            recommendations = [
                "Thiết lập danh mục hàng hóa ban đầu và định mức tồn kho tối thiểu.",
                "Khai báo thông tin các đối tác nhà cung cấp chính.",
            ]
            return summary, recommendations

        if metrics.active_products == 0:
            summary = (
                f"Kỳ báo cáo {period}: Quản lý tổng cộng {metrics.total_products} mặt hàng nhưng không phát sinh "
                "bất kỳ giao dịch nhập hay xuất kho nào trong kỳ. Kho bãi đang ở trạng thái bất động."
            )
            recommendations = [
                "Kiểm tra lại việc cập nhật các chứng từ nhập/xuất kho còn tồn đọng.",
                "Rà soát nhu cầu luân chuyển hàng hóa của các bộ phận kinh doanh.",
            ]
            return summary, recommendations

        net_flow = metrics.total_imports_qty - metrics.total_exports_qty
        flow_comment = (
            f"Lượng nhập ròng đạt {net_flow} sản phẩm (tăng quy mô tồn trữ)."
            if net_flow > 0
            else f"Lượng xuất vượt lượng nhập {abs(net_flow)} sản phẩm (kho đang giải phóng tồn kho)."
            if net_flow < 0
            else "Lượng nhập và xuất cân bằng hoàn toàn trong kỳ."
        )

        top_item_str = ""
        if metrics.top_exported_products:
            best = metrics.top_exported_products[0]
            top_item_str = (
                f" Mặt hàng luân chuyển mạnh nhất là '{best.product_name}' "
                f"({best.product_code}) với tổng cộng {best.quantity} đơn vị xuất kho."
            )

        low_stock_str = (
            f" Hiện có {metrics.low_stock_count} mặt hàng đang ở ngưỡng báo động dưới tồn tối thiểu."
            if metrics.low_stock_count > 0
            else " Tồn kho các mặt hàng cơ bản đảm bảo trên định mức an toàn."
        )

        summary = (
            f"Kỳ báo cáo {period}: Tổng nhập {metrics.total_imports_qty} sản phẩm, "
            f"tổng xuất {metrics.total_exports_qty} sản phẩm qua {metrics.active_products}/{metrics.total_products} mặt hàng hoạt động. "
            f"{flow_comment}{top_item_str}{low_stock_str}"
        )

        recommendations = []
        if metrics.low_stock_count > 0:
            recommendations.append(
                f"Ưu tiên lập kế hoạch bổ sung hàng cho {metrics.low_stock_count} mặt hàng đang dưới tồn tối thiểu để tránh đứt gãy cung ứng."
            )
        if metrics.top_exported_products:
            recommendations.append(
                f"Duy trì hạn mức tồn an toàn cao hơn cho nhóm hàng luân chuyển nhanh như '{metrics.top_exported_products[0].product_name}'."
            )
        recommendations.append(
            "Thực hiện kiểm kê định kỳ đối soát giữa thẻ kho điện tử và thực tế tại kho."
        )

        return summary, recommendations

    @staticmethod
    def generate_restock_suggestions_fallback(
        items_data: List[Dict[str, Any]]
    ) -> Tuple[List[RestockSuggestionItem], str]:
        """Tính toán số lượng gợi ý nhập hàng và mức độ ưu tiên theo quy tắc thống kê."""
        suggested_items: List[RestockSuggestionItem] = []

        for item in items_data:
            current_stock = item["current_stock"]
            min_stock = item["min_stock"]
            daily_velocity = float(item.get("daily_velocity", 0.0))
            days_left = item.get("days_until_stockout")

            # Công thức gợi ý: Đủ dùng cho 30 ngày tới hoặc đạt mức an toàn (2 * min_stock)
            needed_for_demand = round(daily_velocity * 30) - current_stock
            needed_for_safety = (min_stock * 2) - current_stock
            suggested_qty = max(needed_for_demand, needed_for_safety, min_stock)
            if suggested_qty <= 0:
                suggested_qty = min_stock

            # Xác định mức độ ưu tiên
            if current_stock == 0:
                priority = "HIGH"
                reason = "Đã hết sạch hàng trong kho (tồn = 0), cần nhập gấp để tránh gián đoạn bán hàng."
            elif current_stock < min_stock / 2:
                priority = "HIGH"
                reason = (
                    f"Tồn kho ({current_stock}) nghiêm trọng dưới 50% mức an toàn ({min_stock}), "
                    f"tốc độ xuất {daily_velocity:.1f} sp/ngày."
                )
            elif current_stock <= min_stock:
                priority = "MEDIUM"
                reason = (
                    f"Tồn kho ({current_stock}) chạm ngưỡng tối thiểu ({min_stock}), "
                    f"tốc độ xuất {daily_velocity:.1f} sp/ngày."
                )
            else:
                priority = "LOW"
                days_left_str = f"{days_left:.1f}" if days_left is not None else "N/A"
                reason = (
                    f"Tồn kho hiện tại ({current_stock}) sắp cạn trong khoảng {days_left_str} ngày tới "
                    f"do tốc độ tiêu thụ cao ({daily_velocity:.1f} sp/ngày)."
                )

            suggested_items.append(
                RestockSuggestionItem(
                    product_id=item["product_id"],
                    product_code=item["product_code"],
                    product_name=item["product_name"],
                    current_stock=current_stock,
                    min_stock=min_stock,
                    daily_velocity=round(daily_velocity, 2),
                    estimated_days_left=round(days_left, 1) if days_left is not None else None,
                    suggested_quantity=int(suggested_qty),
                    priority=priority,
                    reason=reason,
                )
            )

        # Sắp xếp ưu tiên: HIGH -> MEDIUM -> LOW, sau đó theo tồn kho tăng dần
        priority_weight = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        suggested_items.sort(
            key=lambda x: (priority_weight.get(x.priority, 3), x.current_stock)
        )

        high_count = sum(1 for x in suggested_items if x.priority == "HIGH")
        if not suggested_items:
            summary = "Toàn bộ mặt hàng trong kho đang có số lượng tồn an toàn, chưa cần bổ sung hàng mới."
        else:
            summary = (
                f"Phát hiện {len(suggested_items)} mặt hàng cần xem xét đặt hàng, "
                f"trong đó có {high_count} mặt hàng ở mức ưu tiên CAO cần bổ sung khẩn cấp."
            )

        return suggested_items, summary

    @staticmethod
    def generate_anomaly_detection_fallback(
        anomalies_data: List[Dict[str, Any]]
    ) -> Tuple[List[AnomalyItem], str]:
        """Tóm tắt các biến động bất thường (xuất đột biến, hàng ế lâu ngày)."""
        anomaly_items: List[AnomalyItem] = []
        surge_count = 0
        dead_count = 0

        for item in anomalies_data:
            anomaly_type = item["anomaly_type"]
            product_id = item["product_id"]
            product_code = item["product_code"]
            product_name = item["product_name"]

            if anomaly_type == "SURGE_EXPORT":
                surge_count += 1
                recent_qty = item.get("recent_7d_qty", 0)
                baseline_qty = item.get("baseline_weekly_qty", 0)
                ratio = item.get("surge_ratio", 0.0)
                description = (
                    f"Lượng xuất kho 7 ngày gần đây tăng đột biến đạt {recent_qty} đơn vị, "
                    f"gấp {ratio:.1f} lần so với mức trung bình ({baseline_qty} đơn vị/tuần)."
                )
                suggested_action = (
                    "Kiểm tra lại các phiếu xuất lớn gần đây để xác nhận nhu cầu thị trường đột xuất, "
                    "đồng thời chủ động liên hệ nhà cung cấp tăng định mức an toàn."
                )
                details = {
                    "recent_7d_qty": recent_qty,
                    "baseline_weekly_qty": baseline_qty,
                    "surge_ratio": ratio,
                }
            else:  # DEAD_STOCK
                dead_count += 1
                current_stock = item.get("current_stock", 0)
                days_inactive = item.get("days_inactive", 30)
                description = (
                    f"Mặt hàng tồn đọng {current_stock} đơn vị trong kho nhưng không phát sinh "
                    f"bất kỳ giao dịch xuất kho nào trong hơn {days_inactive} ngày qua."
                )
                suggested_action = (
                    "Đánh giá lại chất lượng sản phẩm, lên chương trình khuyến mãi/giải phóng tồn kho "
                    "hoặc tạm dừng kế hoạch nhập hàng mới để tránh chôn vốn."
                )
                details = {
                    "current_stock": current_stock,
                    "days_inactive": days_inactive,
                }

            anomaly_items.append(
                AnomalyItem(
                    product_id=product_id,
                    product_code=product_code,
                    product_name=product_name,
                    anomaly_type=anomaly_type,
                    description=description,
                    details=details,
                    suggested_action=suggested_action,
                )
            )

        if not anomaly_items:
            summary = "Kho bãi hoạt động bình thường, không ghi nhận bất kỳ đột biến xuất kho hay hàng tồn đọng bất thường nào."
        else:
            summary = (
                f"Hệ thống phát hiện {len(anomaly_items)} biến động cần chú ý: "
                f"{surge_count} mặt hàng xuất tăng đột biến và {dead_count} mặt hàng tồn kho ứ đọng lâu ngày."
            )

        return anomaly_items, summary
