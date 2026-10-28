# BƯỚC 11: ĐÓNG GÓI, TÀI LIỆU SDLC & KỊCH BẢN DEMO (FINAL POLISH)

> **TÍNH CHẤT TÀI LIỆU:** Đây là một **Prompt / Nhiệm vụ thực thi độc lập (Self-contained Spec)**. Bất kỳ AI hoặc lập trình viên nào khi đọc tài liệu này đều có đầy đủ 100% bối cảnh, yêu cầu và tiêu chuẩn nghiệm thu để thực hiện mà không cần tra cứu thêm.
>
> **RANH GIỚI TÀI LIỆU:**
>
> - `docs/plans/Buoc-11-...md`: Tài liệu KẾ HOẠCH & CHECKLIST thực thi (nơi bạn đang đọc).
> - `docs/SDLC/final/`: Chứa toàn bộ BÁO CÁO KỸ THUẬT, HƯỚNG DẪN SỬ DỤNG, SLIDE THUYẾT TRÌNH dùng để nộp bài và chấm điểm cuối kỳ.
> - `README.md`: Hướng dẫn khởi chạy dự án tại thư mục gốc.

---

## 1. Mục tiêu bước 11

- Hoàn thiện toàn bộ hồ sơ minh chứng học phần theo 4 mốc đánh giá SDLC (KT1, KT2, KT3, Cuối kỳ) trong thư mục `docs/SDLC/`.
- Viết tài liệu `README.md` tại thư mục gốc với hướng dẫn cài đặt và khởi chạy 1-Click qua Docker Compose hoặc chạy cục bộ.
- Xây dựng Kịch bản Demo 5 phút để sinh viên tự tin thuyết trình và đạt điểm tối đa trước hội đồng chấm thi.

---

## 2. Nội dung công việc chi tiết

### 2.1. Hoàn thiện Tài liệu 4 Giai đoạn SDLC

1. **Thư mục `docs/SDLC/KT1/`**:
   - `01_SRS_and_UseCases.md`: Phân tích quy trình, 3 Actor, Use Case, ma trận RBAC.
   - `02_Database_Design_ERD.md`: Thiết kế bảng CSDL, Data Dictionary, sơ đồ Mermaid ERD.
   - `03_AI_Architecture_and_Prompts.md`: Kiến trúc module AI (Gemini 3.5 Flash Lite) và prompt mẫu.
   - `04_Wireframes.md`: Phác thảo cấu trúc các màn hình giao diện (kèm Dark mode và tích hợp báo cáo vào AIAssistant).
2. **Thư mục `docs/SDLC/KT2/`**:
   - `01_API_Specifications.md`: Tài liệu đặc tả 44 RESTful APIs.
   - `02_Transaction_Design_and_Negative_Stock_Prevention.md`: Thiết kế Transaction, luồng xuất 3 bước và chống tồn âm.
   - `03_AI_Assisted_Development_Evidence.md`: Minh chứng dùng AI hỗ trợ viết code.
3. **Thư mục `docs/SDLC/KT3/`**:
   - `01_Prompt_Engineering_and_Evaluation.md`: Báo cáo so sánh các phiên bản Prompt.
   - `02_Test_Plan_and_Results.md`: Kết quả chạy bộ kiểm thử Pytest (70 tests pass 100%, 83% coverage).
   - `03_AI_Integration_Architecture.md`: Kiến trúc tích hợp AI, Fallback Heuristic và AI In-Day Cache.
4. **Thư mục `docs/SDLC/final/`**:
   - `01_Final_Technical_Report.md`: Báo cáo kỹ thuật tổng kết đồ án.
   - `02_User_Guide_and_Demo_Script.md`: Hướng dẫn sử dụng và kịch bản demo chấm thi.
   - `03_Presentation_Slides.md`: Nội dung slide thuyết trình bảo vệ đồ án.

### 2.2. Tài liệu Hướng dẫn Khởi chạy 1-Click (`README.md`)

- Hướng dẫn cài đặt nhanh qua Docker:

  ```bash
  docker compose up -d --build
  ```

- Hướng dẫn chạy cục bộ bằng Python & Node:

  ```bash
  # 1. Chạy Backend
  cd backend
  pip install -r requirements.txt
  python seed_data.py
  uvicorn app.main:app --reload

  # 2. Chạy Frontend
  cd frontend
  npm install
  npm run dev
  ```

- Danh sách tài khoản đăng nhập mẫu (`admin`, `thukho`, `ketoan`).

### 2.3. Kịch bản Demo 5 Phút Chuẩn Chấm Thi

1. **Phút 1**: Giới thiệu bài toán doanh nghiệp nhỏ và cấu trúc phân quyền 3 vai trò (Admin, Thủ kho, Kế toán).
2. **Phút 2**: Đăng nhập vai trò Thủ kho $\rightarrow$ Thực hiện Lập phiếu xuất với số lượng vượt tồn kho $\rightarrow$ Cho giảng viên thấy hệ thống chặn đứng tồn kho âm và trả thông báo lỗi HTTP 400.
3. **Phút 3**: Nhập số lượng hợp lệ $\rightarrow$ Chuyển trạng thái xuất kho (`SHIPPING` trừ tồn kho tức thời) $\rightarrow$ Mở Thẻ kho cho thấy số dư được trừ tức thì và lịch sử được ghi nhận chuẩn xác $\rightarrow$ Thử xuất file Excel Thẻ kho.
4. **Phút 4**: Chuyển sang màn hình Trợ lý AI & Báo cáo $\rightarrow$ Tab 1: Xem Báo cáo NXT và xuất Excel $\rightarrow$ Tab 2: Xem AI Gợi ý nhập hàng $\rightarrow$ Tab 3: Cảnh báo bất thường $\rightarrow$ Tab 4: Hỏi đáp tự do với SmartKho Copilot.
5. **Phút 5**: Giới thiệu bộ kiểm thử Pytest 70 tests pass 100%, code coverage 83% và cơ chế Fallback Heuristic hoạt động mượt mà khi ngắt mạng / hết quota.

---

## 3. Cấu trúc file/thư mục cần sinh

```text
he-thong-quan-ly-kho/
├── README.md                                  # File hướng dẫn chạy 1-click tại thư mục gốc
├── docker-compose.yml                         # 2 services: warehouse_backend & warehouse_frontend
└── docs/
    └── SDLC/
        ├── KT1/
        │   ├── 01_SRS_and_UseCases.md
        │   ├── 02_Database_Design_ERD.md
        │   ├── 03_AI_Architecture_and_Prompts.md
        │   └── 04_Wireframes.md
        ├── KT2/
        │   ├── 01_API_Specifications.md
        │   ├── 02_Transaction_Design_and_Negative_Stock_Prevention.md
        │   └── 03_AI_Assisted_Development_Evidence.md
        ├── KT3/
        │   ├── 01_Prompt_Engineering_and_Evaluation.md
        │   ├── 02_Test_Plan_and_Results.md
        │   └── 03_AI_Integration_Architecture.md
        └── final/
            ├── 01_Final_Technical_Report.md   # Báo cáo kỹ thuật tổng kết đồ án
            ├── 02_User_Guide_and_Demo_Script.md # Hướng dẫn sử dụng & Kịch bản demo 5 phút
            └── 03_Presentation_Slides.md      # Nội dung Slide thuyết trình bảo vệ đồ án
```

---

## 4. Ràng buộc kỹ thuật & Tiêu chí hoàn thành (Definition of Done)

- [x] Tất cả các file tài liệu markdown không bị lỗi định dạng, sơ đồ Mermaid render rõ ràng.
- [x] Khởi chạy thành công hệ thống trong 5 phút qua Docker Compose (`docker compose up -d --build`).
- [x] Kịch bản demo mạch lạc, chứng minh đầy đủ 100% yêu cầu của `de_tai_07.md`.
- [x] Đã hoàn thành và đồng bộ đầy đủ văn bản Báo cáo tổng hợp Word (`Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`) và Slide bảo vệ đồ án PowerPoint (`Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx`).

---

## 5. Cập nhật tiến độ

Đã cập nhật file [docs/plans/TIEN-DO.md](file:///E:/gemini/h%E1%BB%87%20th%E1%BB%91ng%20qu%E1%BA%A3n%20l%C3%BD%20kho/docs/plans/TIEN-DO.md) dòng **Bước 11**:

```markdown
| 2026-09-25 | Bước 11 | Đóng gói, Tài liệu SDLC & Kịch bản Demo | Hoàn thành | `README.md`, `docker-compose.yml`, `docs/SDLC/final/...`, `Bao_Cao_Kien_Truc_He_Thong_Quan_Ly_Kho.docx`, `Thuyet_Trinh_Kien_Truc_He_Thong_Quan_Ly_Kho.pptx` | Đã hoàn tất đóng gói toàn bộ dự án, hồ sơ SDLC 4 giai đoạn, tài liệu Word/PowerPoint và kịch bản demo (70 tests pass, coverage 83%) |
```

---

## 6. Lịch sử đồng bộ

- **Ngày đồng bộ:** 2026-10-28
- **Nội dung điều chỉnh theo thực tế mã nguồn:**
  - **Tên file KT3:** Chuẩn hóa tên file `03_AI_Integration_Architecture.md` (khớp với tài liệu thực tế tại `docs/SDLC/KT3/`).
  - **Số lượng test:** Cập nhật từ 60 tests lên 70 tests pass 100%, độ bao phủ 83%.
  - **Phương thức triển khai:** Bổ sung hướng dẫn Docker Compose (2 containers `warehouse_backend` và `warehouse_frontend`) là phương thức triển khai chuẩn.
  - **Cập nhật kịch bản demo:** Bổ sung các bước demo luồng xuất kho 3 bước (`CONFIRMED` $\rightarrow$ `SHIPPING`), xuất Excel thẻ kho / báo cáo NXT, và tính năng chat SmartKho Copilot.
