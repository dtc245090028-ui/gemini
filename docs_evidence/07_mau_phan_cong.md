# BẢNG PHÂN CÔNG NHIỆM VỤ THÀNH VIÊN VÀ THỐNG KÊ ĐÓNG GÓP TỪ GIT

**Đề tài 07:** Hệ thống Quản lý Kho Thông minh tích hợp AI  
**Kho lưu trữ mã nguồn:** `wms-ai`  
**Nhãn quy ước:** Bảng thông tin cá nhân gán nhãn `[CẦN NGƯỜI DÙNG]` để người dùng tự điền thông tin chính xác theo nhóm; Số liệu thống kê Git gán nhãn `[TỪ GIT/FILE]` trích xuất tự động từ `git log` và `git shortlog`.

---

## 1. MẪU BẢNG PHÂN CÔNG CÔNG VIỆC THÀNH VIÊN NHÓM

> *Lưu ý: Bảng này được để trống các trường Họ tên, MSSV, Vai trò để người dùng điền theo đúng danh sách nhóm thực tế bảo vệ đồ án.*

| STT | Họ và tên [CẦN NGƯỜI DÙNG] | Mã sinh viên (MSSV) [CẦN NGƯỜI DÙNG] | Vai trò trong nhóm [CẦN NGƯỜI DÙNG] | Phần việc đảm nhận chi tiết [CẦN NGƯỜI DÙNG] | Minh chứng sản phẩm / Commit tương ứng |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | *[Điền Họ và tên]* | *[Điền MSSV]* | *[Trưởng nhóm / Dev / BA...]* | *[Ví dụ: Thiết kế CSDL, Xây dựng API Phiếu nhập/xuất...]* | *[Mã commit / File code]* |
| 2 | *[Điền Họ và tên]* | *[Điền MSSV]* | *[Thành viên]* | *[Ví dụ: Thiết kế Prompt AI, Xây dựng Fallback Engine...]* | *[Mã commit / File code]* |
| 3 | *[Điền Họ và tên]* | *[Điền MSSV]* | *[Thành viên]* | *[Ví dụ: Xây dựng Giao diện React, Viết tài liệu báo cáo...]* | *[Mã commit / File code]* |
| 4 | *[Điền Họ và tên]* | *[Điền MSSV]* | *[Thành viên]* | *[Ví dụ: Viết bộ kiểm thử Pytest, Đóng gói Docker...]* | *[Mã commit / File code]* |

---

## 2. THỐNG KÊ ĐÓNG GÓP THỰC TẾ TRÍCH XUẤT TỪ LỊCH SỬ GIT

- **Phân loại nhãn:** `[TỪ GIT/FILE]`
- **Thời điểm trích xuất:** `2026-10-27T23:31:00+07:00`
- **Lệnh thực thi:** `git shortlog -sne --all` và `git log --oneline`

### 2.1. Thống kê theo tác giả Git (Git Authors)
* **Tác giả ghi nhận duy nhất trong repo:** `dtc245090028-ui <dtc245090028@ictu.edu.vn>`
* **Tổng số commit trên toàn bộ nhánh:** **37 commits** (100.0% commit trong kho lưu trữ).
* **Đóng góp dòng code chính:**
  * Khởi tạo và xây dựng mã nguồn: ~15.000 dòng code.
  * PR #1 (Tối ưu đồng thời & Hoàn thiện): +2.108 dòng, -857 dòng qua 16 commits.

### 2.2. Thống kê số lượng commit theo 4 giai đoạn SDLC

| Giai đoạn SDLC | Khoảng thời gian | Số commit | Tỷ lệ (%) | Các commit tiêu biểu | Nội dung công việc chính |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Giai đoạn 1 (KT1): Phân tích & Thiết kế** | 21/09/2026 | 3 | 8.1% | `5f45593`, `244f1f8`, `d61002c` | Khởi tạo cấu trúc dự án, hoàn thành bước 1 và bước 2. |
| **Giai đoạn 2 (KT2): Xây dựng chức năng kho** | 22/09/2026 | 1 | 2.7% | `d1a70b9` | Hoàn thiện bước 5-7, nghiệp vụ xuất nhập tồn, mốc KT2. |
| **Giai đoạn 3 (KT3): Tích hợp AI & Kiểm thử** | 23/09 – 25/09/2026 | 17 | 45.9% | `ec2e38b`, `cf136bf`, `6400c8e`, `325bb33`, `4babc12`, `a62f584` | Thêm prompt templates, cấu hình Gemini API, Heuristic Fallback, giao diện Figma, bộ test suites. |
| **Giai đoạn 4 (KT4): Tối ưu, Hoàn thiện & Triển khai** | 29/09 – 21/10/2026 | 16 | 43.3% | `739bbda`, `6fbafee`, `402ee5b`, `dc89507`, `70aaf91`, `067dc7b` | Viết tài liệu cuối kỳ, xử lý Lost Update, Exponential backoff jitter chống lock DB, ConfirmModal, Toast, Docker. |
| **TỔNG CỘNG** | **21/09 – 21/10/2026** | **37** | **100.0%** | | **Toàn bộ vòng đời phát triển dự án WMS AI** |

---

## 3. DANH SÁCH CHI TIẾT 37 COMMITS THEO LỊCH SỬ THỜI GIAN

```text
067dc7b | 2026-10-21 | feat: thay the window.confirm va alert bang ConfirmModal co ly do huy va he thong Toast dong bo
c5ae84d | 2026-10-21 | chore: don dep file rac, bo track ai_service.log, chuan hoa .gitignore va dong bo test suites
7603fea | 2026-10-21 | [CLEANUP] Don dep file phat sinh va cap nhat .gitignore
e3be4a5 | 2026-10-21 | [C] Toi uu SQLite PRAGMA synchronous NORMAL va bo sung logging traceback
70aaf91 | 2026-10-21 | [B] Nang retry len 7 va Exponential Backoff Jitter triet tieu loi 409 tu 15% xuong 0%
dc89507 | 2026-10-21 | [A] Cap nhat ton kho nguyen tu o tang SQL loai bo 100% Lost Update va lech the kho
3870be3 | 2026-10-21 | [D] Rang buoc max_length=500 cho note trong schemas phieu xuat va nhap
1d14f63 | 2026-10-21 | [E] Dieu tra va khep kin 4 diem con mo voi nhan bang chung ro rang
e6174dd | 2026-10-21 | [PREP] Thiet lap check_invariants.py va ghi nhan baseline vi pham
56737e5 | 2026-10-20 | cập nhật giao diện
402ee5b | 2026-10-02 | fix lỗi nhận đúp 2 yêu cầu trong lỗi đánh máy
bae775d | 2026-10-02 | sửa lỗi gọi lặp backend
0b0ddb7 | 2026-10-02 | xxx
6fbafee | 2026-09-30 | cập nhật hoạt ảnh chờ
583402d | 2026-09-29 | cập nhật tl1
739bbda | 2026-09-29 | cập nhật tài liệu
a62f584 | 2026-09-25 | test1.1
4babc12 | 2026-09-25 | final1.8
f5a4490 | 2026-09-25 | final1.7
86c2448 | 2026-09-25 | final1.6
7957546 | 2026-09-25 | final1.5
6085113 | 2026-09-25 | final1.4
6b4c72f | 2026-09-24 | final1.3
4b5733b | 2026-09-24 | cập nhật final1.2
325bb33 | 2026-09-23 | cập nhận giao diện dựa trên figma
3943c67 | 2026-09-23 | key
6400c8e | 2026-09-23 | bảo mật KEY
139ed09 | 2026-09-23 | test thành công
4446b63 | 2026-09-23 | test
cf136bf | 2026-09-23 | final1.1
ec2e38b | 2026-09-23 | final
d1a70b9 | 2026-09-22 | hoàn thiện bước 5-7 hoàn thành mốc KT2
d61002c | 2026-09-21 | hoàn thành bước 1 và 2
244f1f8 | 2026-09-21 | kiểm tra đường dẫn
5f45593 | 2026-09-21 | Add nội dung hệ thống quản lý kho
```
