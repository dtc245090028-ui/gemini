# MASTER: Điều tra, sửa lỗi và dọn dẹp (warehouse_backend), chế độ chạy tự động nhiều phiên

Bạn chạy không có người giám sát, theo từng phiên. Mỗi phiên làm ĐÚNG MỘT hạng mục rồi thoát.

## 0. Quy trình mỗi phiên
1. Chạy `git branch --show-current`. Nếu là main hoặc master: ghi "STOP: đang ở nhánh chính" vào đầu docs/RUN_STATE.md và thoát.
2. Đọc docs/RUN_STATE.md (nếu chưa có thì tạo theo mẫu ở mục 7). Nếu có dòng "STOP" hoặc "DONE" ở đầu file: thoát ngay.
3. Chọn hạng mục đầu tiên chưa xong theo thứ tự: PREP → E → D → A → B → C → CLEANUP.
4. Làm hạng mục đó theo mục tương ứng bên dưới.
5. Cổng hoàn thành (mục 5). Chỉ đánh dấu "xong" khi đạt, kèm output thô trong RUN_STATE.md.
6. Không đạt sau 2 hướng khác nhau: hoàn tác về commit trước, ghi (đã thử gì, số đo, vì sao thất bại), thêm "STOP" ở đầu file, thoát.
7. Đạt: commit "[hạng mục] mô tả ngắn + số đo trước/sau", cập nhật RUN_STATE.md, thoát. Không tự sang hạng mục kế.
8. Khi mọi hạng mục xong: thêm "DONE" ở đầu RUN_STATE.md kèm bảng tổng kết.

## 1. Ràng buộc tuyệt đối
- Không chạy Bậc 5. Không git push. Không sửa/xóa warehouse.db (thử nghiệm dùng bản sao hoặc CSDL cô lập).
- Không xóa file nào: chỉ được chuyển vào `_quarantine/` (giữ nguyên cấu trúc đường dẫn).
- Không chuyển, sửa hay gỡ khỏi git index file đang tracked (liệt kê vào mục "Cần bạn quyết").
- Không đổi hợp đồng API (api_contract.md) hay định dạng mã phiếu. Gặp trường hợp bắt buộc thì ghi "Cần bạn quyết" và bỏ qua hạng mục đó.
- Mỗi lần chỉ đổi MỘT thứ, đo lại ngay sau đó.
- Trước mỗi phép đo ghi: giả thuyết, tiêu chí đúng, tiêu chí sai. Sau đó dán output thô.
- Mọi nhận định gắn nhãn: "đã đo" / "suy ra từ code" / "chưa kiểm chứng".

## 2. Bối cảnh (chỉ là số đo, chưa phải kết luận)
- Sau Bậc 4, BULK-01 và BULK-02: `products.current_stock` cao hơn kỳ vọng (tồn đầu − tổng xuất trong `stock_ledger`) lần lượt 1.916 và 1.944. Bậc 3: lệch 42 và 2.758.
- `stock_ledger` có nhiều dòng không thỏa `balance_n = balance_(n-1) + change_n` và nhiều `balance_after` lặp.
- Bậc 4: 418 lỗi 409 ở `POST /export-notes/`, 4 lỗi 500, độ trễ tối đa 5.079 ms (ship) và 6.298 ms (tạo phiếu).
- `note` 5.000 ký tự trả 201 trong khi kịch bản test kỳ vọng 4xx.
- Lệch 29 giữa số phiếu trong CSDL và số lượt Locust ghi nhận (cả create lẫn ship) chưa có lời giải khép kín.
- CPU container đạt 103% (Bậc 3) và 90% (Bậc 4).

## 3. Hạng mục (mỗi hạng mục: trả lời câu hỏi → chọn hướng bằng số đo → làm → đo lại)

### PREP
Tạo `tests/performance/check_invariants.py` (chỉ đọc CSDL, nhận đường dẫn DB qua tham số) kiểm tra 5 bất biến ở mục 5 và in kết quả từng SKU. Chạy thử trên bản sao DB hiện tại, ghi baseline (dự kiến đang vi phạm) vào RUN_STATE.md. Chạy pytest và ghi baseline.

### E. Điều tra điểm còn mở (chỉ đọc, không sửa code)
1. Chênh 29: so khớp timestamp từng dòng giữa log máy chủ, CSDL và CSV Locust. Kiểm tra cấu hình Locust (ramp-up, reset stats, thời điểm dừng). Chỉ kết luận khi khớp được từng dòng.
2. Số phiếu CONFIRMED còn lại là 7 hay 8? Truy vấn và thống nhất một con số.
3. CPU >100%: xác định số worker, số thread, cách docker stats tính.
4. Con số "1.298 ms hàng đợi Uvicorn": đã đo hay suy đoán? Nếu chưa đo thì ghi "chưa kiểm chứng".
Dự phòng: điểm nào không đủ dữ liệu để kết luận thì ghi rõ thiếu dữ liệu gì, không suy diễn.

### D. Validation `note`
1. Tài liệu dự án quy định độ dài tối đa bao nhiêu? Các trường văn bản tự do khác có tình trạng tương tự không?
2. Nếu có quy tắc: thêm ràng buộc ở schema. Nếu không có: chọn giá trị hợp lý, ghi vào "Cần bạn quyết", và sửa kịch bản test cho khớp hành vi mới.
Dự phòng: nếu thêm ràng buộc làm pytest hỏng, hoàn tác và chuyển sang phương án chỉ sửa kịch bản test, ghi chú đây là quyết định chờ xác nhận.

### A. Cập nhật tồn kho khi chạy đồng thời
Câu hỏi:
1. Những chỗ nào trong inventory_service.py thay đổi `current_stock` hoặc ghi `balance_after` (nhập, hủy, xuất, kiểm kê)? Liệt kê đủ.
2. Ở mỗi chỗ, giá trị tồn được đọc và được ghi ở thời điểm nào? Giữa hai thời điểm request khác có xen vào được không?
3. `balance_after` đang lấy từ đâu, có thể lấy từ nguồn khác không?
4. Khi tồn không đủ, nghiệp vụ muốn gì (từ chối/cho âm)? Tài liệu nói gì?
Các hướng (không theo thứ tự ưu tiên): (a) cập nhật bằng biểu thức tương đối ở tầng SQL; (b) mở transaction ghi ngay từ đầu; (c) khóa theo từng sản phẩm ở tầng ứng dụng; (d) version cho sản phẩm và thử lại khi xung đột. Tự chọn theo tính đúng đắn, độ phức tạp, ảnh hưởng độ trễ.
Dự phòng: hướng đã chọn vẫn vi phạm bất biến → hoàn tác, ghi số đo thất bại, thử hướng khác. Không hướng nào đạt → báo cáo hướng gần đạt nhất và điều gì đang chặn.

### B. Sinh mã chứng từ
Câu hỏi:
1. generate_note_code có mấy nơi gọi, mỗi nơi có vòng retry không?
2. Điều gì xảy ra giữa lúc đọc max(code) và lúc insert?
3. Khi retry, giá trị đọc lại có khác không, giữa các lần có độ trễ không?
4. Định dạng mã có ràng buộc nghiệp vụ nào?
Các hướng: (a) bảng bộ đếm theo tiền tố và ngày; (b) insert trước rồi sinh mã từ khóa chính; (c) giữ cách cũ, thêm độ trễ ngẫu nhiên khi retry; (d) mã có phần ngẫu nhiên hoặc UUID.
Dự phòng: hướng làm đổi định dạng mã trái tài liệu → bỏ hướng đó, ghi "Cần bạn quyết". Tỷ lệ 409 chưa chấp nhận được (tự đề xuất ngưỡng, nêu lý do) → thử hướng kế.

### C. Lỗi 500 và độ trễ dưới tải ghi
Câu hỏi:
1. Kiểm tra PRAGMA hiện có (journal_mode, busy_timeout, synchronous) bằng truy vấn trực tiếp, không đọc từ code.
2. Lúc xảy ra 500, log có traceback cụ thể không? Nếu không, vì sao?
3. Một transaction ghi giữ khóa bao lâu trong điều kiện test? Đo được không?
4. Khi quá tải mong muốn gì: chờ, từ chối có mã lỗi riêng, hay thử lại?
Các hướng: (a) đổi journal mode; (b) rút ngắn thời gian giữ khóa; (c) trả mã lỗi phản ánh đúng quá tải và log traceback; (d) đổi loại CSDL; (e) giới hạn số request ghi đồng thời ở tầng ứng dụng.
Dự phòng: đổi cấu hình không giảm được 500 và độ trễ → ghi số liệu trước/sau, kết luận giới hạn nằm ở loại CSDL, soạn bản đánh giá chi phí/rủi ro đổi CSDL vào docs/, KHÔNG tự triển khai.

### CLEANUP (dọn file phát sinh và cập nhật .gitignore)
Pha 1, kiểm kê (chỉ đọc), ghi bảng vào docs/cleanup_report.md với cột: đường dẫn | tracked/untracked/ignored | nguồn gốc | còn được tham chiếu bởi | nhóm.
Câu hỏi:
1. `git status` (cả untracked, ignored) và `git diff --stat` cho thấy gì?
2. Với mỗi file mới hoặc trong thư mục sinh dữ liệu (results/, thư mục tạm, __pycache__): lệnh nào tạo ra, còn nơi nào tham chiếu (tìm kiếm bằng lệnh)?
3. File nào chứa code đã cập nhật; file nào là test/script/tài liệu có thể cần sau (kể cả Bậc 5)?
4. File nào là bằng chứng đo (CSV, JSON, log) mà báo cáo còn cần?
Nhóm: Giữ (code cập nhật, file chưa dùng có thể cần sau) / Có thể chuyển / Cần bạn quyết (không rõ nguồn gốc, là bằng chứng đo, hoặc đang tracked).
Dự phòng: không chắc nhóm nào thì xếp "Cần bạn quyết". Không bao giờ coi `warehouse.db` hay CSDL không chắc do phiên này tạo là "Có thể chuyển".

Pha 2, dọn: chỉ chuyển nhóm "Có thể chuyển" vào `_quarantine/` bằng danh sách đường dẫn cụ thể (không dùng ký tự đại diện trên thư mục gốc). Sau đó chạy lại `git status` đối chiếu bảng, kiểm tra dự án vẫn import và khởi động được (không chạy tải) và container không bị ảnh hưởng.

Pha 3, .gitignore:
1. Quy tắc hiện có là gì, đã phủ loại file nào trong bảng?
2. Loại file phát sinh nào vẫn hiện trong `git status`, mỗi loại cần quy tắc ở mức nào (file, thư mục, mẫu tên)?
3. Mỗi quy tắc mới có che nhầm file đang tracked hoặc file cần đưa lên không? Kiểm tra bằng `git ls-files` và `git check-ignore -v`.
Thực hiện: thêm quy tắc kèm chú thích ngắn theo nhóm mục đích, không trùng quy tắc cũ, thêm `_quarantine/`. Nếu cần giữ thư mục nhưng bỏ nội dung, dùng cách giữ được thư mục (ví dụ .gitkeep). File tracked thuộc loại nên ignore: chỉ liệt kê vào "Cần bạn quyết", không tự gỡ.
Dự phòng: quy tắc mới làm ignore nhầm file quan trọng → thu hẹp hoặc thêm ngoại lệ rồi kiểm tra lại.

## 4. Nhắc lại thứ tự và quy mô
Mỗi phiên một hạng mục. Không gộp hạng mục để tiết kiệm lượt chạy, vì chất lượng phụ thuộc vào ngữ cảnh sạch.

## 5. Cổng hoàn thành (bắt buộc dán output thô)
Sau hạng mục A-C và CLEANUP, chạy `check_invariants.py` trên CSDL của lần chạy lại Bậc 3 và Bậc 4 (hoặc CSDL cô lập mô phỏng nếu không được phép chạy Bậc) và pytest:
1. Mỗi SKU: tồn hiện tại = tồn đầu + tổng thay đổi trong stock_ledger.
2. balance_after mỗi dòng = dòng trước + change, theo thứ tự ghi nhận.
3. Số phiếu SHIPPING = số dòng thẻ kho tương ứng.
4. Số lỗi 409 và 500 dưới ngưỡng bạn tự đề xuất (nêu lý do).
5. Không tồn kho âm nếu nghiệp vụ không cho phép.
Với E, D: cổng là có kết luận gắn nhãn đúng và pytest không giảm so với baseline.
Với CLEANUP: `git status` chỉ còn code cập nhật, file được giữ và thay đổi .gitignore; mỗi quy tắc mới có ví dụ `git check-ignore -v`; không file tracked nào bị ignore nhầm.
Với mọi hạng mục: pytest không có test mới hỏng so với baseline.

## 6. Báo cáo mỗi phiên (ghi vào RUN_STATE.md)
Hạng mục và hướng đã chọn (lý do bằng số đo) | giả thuyết, tiêu chí đúng/sai, output thô | bảng bất biến đạt/không đạt | điều chưa chứng minh được | mục "Cần bạn quyết".

## 7. Mẫu docs/RUN_STATE.md
```
(STOP / DONE nếu có)
Thứ tự: PREP, E, D, A, B, C, CLEANUP
Trạng thái: PREP [ ] E [ ] D [ ] A [ ] B [ ] C [ ] CLEANUP [ ]
## Baseline
## Nhật ký từng phiên
## Cần bạn quyết
```
