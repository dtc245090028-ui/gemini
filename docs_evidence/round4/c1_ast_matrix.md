# BẰNG CHỨNG C1: MA TRẬN AST CALL-GRAPH 1 CẤP CỦA CÁC ENDPOINT GHI

## 1. Bảng Ma Trận Quét AST Call-Graph 1 Cấp (27 Write Endpoints)

| Module | Method | Path | Function | Service Callees | WriteGate | Updates Stock | Conditional Update |
|---|---|---|---|---|---|---|---|
| ai.py | POST | /generate-order | generate_ai_order | - | KHONG | KHONG | KHONG |
| ai.py | POST | /ask | ask_ai_question | - | KHONG | KHONG | KHONG |
| auth.py | POST | /login | login_json | - | KHONG | KHONG | KHONG |
| auth.py | POST | /login-form | login_oauth2_form | - | KHONG | KHONG | KHONG |
| auth.py | POST | /users | create_user | - | KHONG | KHONG | KHONG |
| bench.py | POST | /write-gate | write_gate_bench | - | CO | KHONG | KHONG |
| bench.py | POST | /reset | reset_traffic_stats | - | KHONG | KHONG | KHONG |
| categories.py | POST | / | create_category | - | KHONG | KHONG | KHONG |
| categories.py | PUT | /{category_id} | update_category | - | KHONG | KHONG | KHONG |
| categories.py | DELETE | /{category_id} | delete_category | - | KHONG | KHONG | KHONG |
| export_notes.py | POST | / | create_new_export_note | create_export_note | CO | CO | CO |
| export_notes.py | POST | /{export_note_id}/ship | ship_existing_export_note | ship_export_note | CO | CO | CO |
| export_notes.py | POST | /{export_note_id}/complete | complete_existing_export_note | complete_export_note | CO | KHONG | KHONG |
| export_notes.py | POST | /{export_note_id}/cancel | cancel_existing_export_note | cancel_export_note | CO | CO | KHONG |
| export_notes.py | DELETE | /{export_note_id} | delete_existing_export_note | delete_export_note | CO | KHONG | KHONG |
| import_notes.py | POST | / | create_new_import_note | create_import_note | CO | CO | KHONG |
| import_notes.py | POST | /{import_note_id}/cancel | cancel_existing_import_note | cancel_import_note | CO | CO | CO |
| products.py | POST | / | create_product | create_import_note | KHONG | CO | KHONG |
| products.py | PUT | /{product_id} | update_product | - | KHONG | KHONG | KHONG |
| products.py | POST | /{product_id}/image | upload_product_image | - | KHONG | KHONG | KHONG |
| products.py | DELETE | /{product_id} | delete_product | - | CO | KHONG | KHONG |
| reports.py | POST | /write-metrics/reset | reset_write_metrics | - | KHONG | KHONG | KHONG |
| reports.py | POST | /write-gate/reset | reset_write_gate_stats | - | KHONG | KHONG | KHONG |
| stock_ledger.py | POST | /adjust | create_stock_adjustment | adjust_stock | CO | CO | KHONG |
| suppliers.py | POST | / | create_supplier | - | KHONG | KHONG | KHONG |
| suppliers.py | PUT | /{supplier_id} | update_supplier | - | KHONG | KHONG | KHONG |
| suppliers.py | DELETE | /{supplier_id} | delete_supplier | - | KHONG | KHONG | KHONG |

## 2. Giải Thích Tại Sao Bảng Cũ Ghi "UPDATE Có Điều Kiện = KHONG"

1. **Phạm vi phân tích cú pháp AST cục bộ**: Script quét AST của vòng báo cáo trước chỉ phân tích cục bộ trong thân hàm endpoint của file router (`app/api/v1/endpoints/*.py`). Trong mô hình phân lớp của SmartKho, các endpoint router chỉ đóng vai trò nhận request, giải mã tham số và ủy quyền cho tầng nghiệp vụ `app.services.inventory_service.*`. Thân hàm endpoint không chứa câu lệnh SQL UPDATE hay `.update()` trực tiếp.
2. **Khai báo ủy quyền service**: Khi phân tích cú pháp dừng ở cấp hàm router, AST parser không tìm thấy biểu thức `update()` hay `WHERE` nào trong hàm router, dẫn đến kết luận cơ học sai lệch là "UPDATE có điều kiện = KHONG".
3. **Thực tế khi duyệt Call-Graph 1 cấp**: Khi mở rộng cây gọi hàm (call-graph 1 cấp) sang các hàm trong `inventory_service.py`:
   - `create_export_note`: Có kiểm tra điều kiện tồn kho `if product.current_stock < detail.quantity:` trước khi tạo chi tiết.
   - `ship_export_note`: Có câu lệnh `UPDATE products SET current_stock = current_stock - :qty WHERE id = :id AND current_stock >= :qty` bảo vệ 2 lớp chống tồn âm.
   - `cancel_import_note`: Có kiểm tra tồn kho hiện tại để từ chối hủy nếu hàng đã xuất làm thiếu tồn.
   - Mọi thao tác cập nhật tồn kho trọng yếu đều được bảo vệ tuần tự hóa bằng `WriteGateContext`.
