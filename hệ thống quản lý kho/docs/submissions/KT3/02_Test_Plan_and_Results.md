# KẾ HOẠCH VÀ KẾT QUẢ KIỂM THỬ TỰ ĐỘNG (BÀI KT3)

## Đề tài 07: Hệ thống Quản lý Kho Thông minh tích hợp AI

> **Mục tiêu tài liệu:** Báo cáo chi tiết chiến lược kiểm thử, ma trận các ca kiểm thử tự động (Unit / Integration Tests) và bằng chứng nghiệm thu kỹ thuật thực tế phục vụ buổi đánh giá mốc KT3.

---

## 1. CHIẾN LƯỢC KIỂM THỬ TỰ ĐỘNG (TESTING STRATEGY)

Dự án tuân thủ nghiêm ngặt **Luật kiểm thử** tại `GEMINI.md §7`:

1. **Không Mock lớp đang kiểm thử (No Self-mocking):**
   - Không mock `InventoryService` hay `FallbackService`. Mọi logic nghiệp vụ kho và tính toán đều chạy trực tiếp trên cơ sở dữ liệu SQLite thật.
   - Mock duy nhất được áp dụng tại ranh giới ngoài: Google Gemini API (để giả lập các tình huống kết nối thành công hoặc lỗi mạng).
2. **Kiểm thử bao phủ Biên & Chống tồn kho âm (Negative Boundary Testing):**
   - Bắt buộc kiểm tra các trường hợp xuất hàng vượt tồn kho: hệ thống phải trả về HTTP 400 và không làm suy giảm tồn kho thực tế.
3. **Kiểm thử An toàn Dữ liệu AI (Data Privacy Assertion):**
   - Viết các test case duyệt qua toàn bộ payload đầu ra của Pipeline tổng hợp dữ liệu, xác nhận không rò rỉ bất kỳ trường giá mua (`unit_price`) nào.

---

## 2. MA TRẬN 30 CA KIỂM THỬ TỰ ĐỘNG (TEST MATRIX)

Toàn bộ 30 bài test được phân bổ trong thư mục `backend/tests/`:

| STT | Tập tin kiểm thử | Ca kiểm thử (Test Function) | Mục đích kiểm tra | Kết quả |
| :---: | --- | --- | --- | :---: |
| 1 | `test_foundation.py` | `test_health_check` | Kiểm tra endpoint /health trả về 200 OK | ✅ PASS |
| 2 | `test_foundation.py` | `test_models_creation` | Đảm bảo 9 bảng CSDL được tạo đầy đủ | ✅ PASS |
| 3 | `test_foundation.py` | `test_prevent_negative_current_stock` | Kiểm tra CheckConstraint CSDL chặn tồn âm | ✅ PASS |
| 4 | `test_auth.py` | `test_login_success_admin` | Đăng nhập Admin thành công trả về JWT token | ✅ PASS |
| 5 | `test_auth.py` | `test_login_success_thukho` | Đăng nhập Thủ kho thành công | ✅ PASS |
| 6 | `test_auth.py` | `test_login_success_ketoan` | Đăng nhập Kế toán thành công | ✅ PASS |
| 7 | `test_auth.py` | `test_login_wrong_password` | Đăng nhập sai mật khẩu trả về HTTP 401 | ✅ PASS |
| 8 | `test_auth.py` | `test_login_nonexistent_user` | Đăng nhập tài khoản không tồn tại trả về 401 | ✅ PASS |
| 9 | `test_auth.py` | `test_login_oauth2_form` | Hỗ trợ Swagger OAuth2 form login | ✅ PASS |
| 10 | `test_auth.py` | `test_get_current_user_me` | Endpoint /me trả về đúng thông tin định danh | ✅ PASS |
| 11 | `test_auth.py` | `test_get_current_user_invalid_token` | Token giả mạo hoặc hết hạn bị từ chối 401 | ✅ PASS |
| 12 | `test_auth.py` | `test_rbac_admin_create_user` | Admin có quyền tạo thêm tài khoản mới | ✅ PASS |
| 13 | `test_auth.py` | `test_rbac_non_admin_cannot_create_user` | Thủ kho/Kế toán bị chặn tạo tài khoản (403) | ✅ PASS |
| 14 | `test_auth.py` | `test_sqlite_foreign_key_enforcement` | PRAGMA foreign_keys = ON; hoạt động chuẩn | ✅ PASS |
| 15 | `test_master_data.py` | `test_category_delete_blocked_when_has_products` | Chặn xóa nhóm hàng khi còn sản phẩm liên kết | ✅ PASS |
| 16 | `test_master_data.py` | `test_crud_product_lifecycle_and_filters` | CRUD sản phẩm, tìm kiếm, lọc is_low_stock | ✅ PASS |
| 17 | `test_master_data.py` | `test_crud_supplier_and_deactivate` | Quản lý nhà cung cấp, bảo vệ lịch sử đối tác | ✅ PASS |
| 18 | `test_master_data.py` | `test_rbac_restrictions_on_master_data` | Phân quyền 3 vai trò trên dữ liệu danh mục | ✅ PASS |
| 19 | `test_stock_transactions.py` | `test_import_stock_transaction_and_ledger` | Nhập kho: tăng tồn + sinh thẻ kho balance_after | ✅ PASS |
| 20 | `test_stock_transactions.py` | `test_export_stock_transaction_and_ledger` | Xuất kho: giảm tồn + sinh thẻ kho chuẩn | ✅ PASS |
| 21 | `test_stock_transactions.py` | `test_prevent_negative_stock_export_failure` | **Chặn xuất quá tồn kho: rollback 100%, 400** | ✅ PASS |
| 22 | `test_stock_transactions.py` | `test_cancel_completed_notes_guard` | State machine: Hủy phiếu có kiểm tra an toàn | ✅ PASS |
| 23 | `test_stock_transactions.py` | `test_stock_adjustment_inventory` | Điều chỉnh kiểm kê thực tế bù trừ chuẩn | ✅ PASS |
| 24 | `test_stock_transactions.py` | `test_inventory_summary_report` | Báo cáo: Tồn đầu + Nhập - Xuất = Tồn cuối | ✅ PASS |
| 25 | `test_ai.py` | `test_ai_pipeline_excludes_unit_price` | **Bảo mật: Không lộ giá mua vào context AI** | ✅ PASS |
| 26 | `test_ai.py` | `test_ai_monthly_report_endpoint` | Endpoint báo cáo tháng sinh nhận xét hợp lệ | ✅ PASS |
| 27 | `test_ai.py` | `test_ai_restock_suggestions_endpoint` | Gợi ý nhập đúng mặt hàng bán chạy sắp hết | ✅ PASS |
| 28 | `test_ai.py` | `test_ai_anomalies_endpoint` | Nhận diện đúng xuất đột biến & hàng tồn chết | ✅ PASS |
| 29 | `test_ai.py` | `test_ai_mock_gemini_success` | Mock Gemini API: is_fallback=False thành công | ✅ PASS |
| 30 | `test_ai.py` | `test_ai_rbac_and_unauthorized` | Chưa đăng nhập bị từ chối 401 khi gọi AI | ✅ PASS |

---

## 3. BẰNG CHỨNG THỰC THI KIỂM THỬ (EXECUTION LOGS)

Lệnh thực thi tại thư mục `backend/`:

```bash
python -m pytest
```

Kết quả nghiệm thu:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-8.2.2, pluggy-1.6.0
rootdir: E:\gemini\hệ thống quản lý kho\backend
plugins: anyio-4.14.2, cov-7.1.0, flask-1.3.0
collected 30 items

tests\test_ai.py ......                                                  [ 20%]
tests\test_auth.py ...........                                           [ 56%]
tests\test_foundation.py ...                                             [ 66%]
tests\test_master_data.py ....                                           [ 80%]
tests\test_stock_transactions.py ......                                  [100%]

======================= 30 passed in 11.98s =======================
```

**Tỷ lệ đạt:** **30 / 30 Passed (100%)**.

---

## 4. KỊCH BẢN DỮ LIỆU MẪU CHUẨN DEMO (SEED DATA 60 NGÀY)

Hệ thống cung cấp script nạp dữ liệu mẫu thực tế tại `backend/seed_data.py`. Chạy bằng lệnh:

```bash
python seed_data.py
```

### Kịch bản Storytelling phục vụ kiểm thử & bảo vệ đồ án

1. **SP001 (Bàn phím cơ Akko 3087):**
   - Tồn kho ban đầu nhập 50 cái, xuất 46 cái trong 30 ngày qua $\rightarrow$ Tồn hiện tại còn **4 chiếc** ($< \text{min\_stock } 15$).
   - Kết quả kiểm thử AI: Endpoint `/ai/restock-suggestions` nhận diện chính xác và đề xuất nhập **26 chiếc** với độ ưu tiên **HIGH**.
2. **SP002 (Chuột không dây Logitech G304):**
   - Bình thường xuất rất ít, nhưng trong 3 ngày qua phát sinh 2 đơn xuất lớn tổng cộng **35 chiếc**.
   - Kết quả kiểm thử AI: Endpoint `/ai/anomalies` gắn cờ **SURGE_EXPORT** với tỷ lệ tăng trưởng $> 200\%$.
3. **SP003 (Cáp chuyển đổi VGA to HDMI):**
   - Nhập 60 chiếc cách đây 55 ngày, trong 55 ngày qua **không có bất kỳ phiếu xuất nào**.
   - Kết quả kiểm thử AI: Endpoint `/ai/anomalies` gắn cờ **DEAD_STOCK** kèm khuyến nghị xả hàng giảm giá.

---

## 5. KẾT LUẬN

Hệ thống đã hoàn thành trọn vẹn toàn bộ các mục tiêu kiểm thử tự động của bài KT3:

- Không phát sinh lỗi logic, không có lỗi tồn kho âm.
- Bảo mật thông tin tuyệt đối đối với các luồng tích hợp AI.
- Sẵn sàng chuyển giao dữ liệu và tích hợp lên tầng giao diện người dùng.
