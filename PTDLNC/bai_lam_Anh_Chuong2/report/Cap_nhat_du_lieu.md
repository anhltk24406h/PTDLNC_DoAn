# Cập nhật Chương 2 theo FOIA 30/06/2026

Cập nhật ngày 21/10/2026 theo hai CSV thay thế do bạn cung cấp. Không trộn dữ liệu hai ngày chụp và không tải lại bản cũ. Bản bài làm trước được giữ tại `../../archive/chuong2_260331_truoc_cap_nhat_260630/`.

## Những thay đổi cấu trúc

- Ngày chụp chuyển từ 31/03/2026 sang 30/06/2026; phạm vi phê duyệt vẫn FY2000–FY2019.
- Mỗi CSV mới có 42 cột CamelCase thay vì 43 cột chữ thường; không còn Subprogram. Không suy diễn Subprogram từ ProcessingMethod. Bảng Subprogram cũ được chuyển vào bản lưu lịch sử; heatmap Cramér’s V hiện chỉ có các trường thực sự tồn tại.
- Ngày dạng ISO YYYY-MM-DD được đọc tường minh; ApprovalFY ánh xạ thành ApprovalFiscalYear.
- Chuẩn hóa 854.943 trạng thái P I F thành PIF trước khi tạo nhãn; lưu số đếm mã gốc trong pipeline_audit.json.
- Kiểm tra ngày chụp ở mọi dòng. Cache Parquet chỉ dùng lại khi ngày chụp và SHA-256 của từng CSV khớp với cấu hình; notebook EDA cũng kiểm tra phiên bản trước khi đọc.
- SHA-256 mô tả các tệp bạn cung cấp. URL chính thức dùng để dẫn nguồn; không tuyên bố đã tải lại hoặc xác minh byte từ máy chủ SBA trong lần cập nhật này.

## So sánh kết quả

| Chỉ tiêu | Bản 31/03/2026 | Bản 30/06/2026 | Thay đổi |
| --- | ---: | ---: | ---: |
| Tổng số dòng khoản vay | 1.236.084 | 1.236.084 | 0 |
| Khoản có nhãn (PIF + CHGOFF) | 1.029.770 | 1.033.447 | 3.677 |
| Trả đủ (PIF) | 851.597 | 854.943 | 3.346 |
| Xóa nợ (CHGOFF) | 178.173 | 178.504 | 331 |
| Tỷ lệ xóa nợ trên khoản có nhãn | 17,30% | 17,27% | -0,030 điểm % |
| Số khoản có kỳ hạn trên 300 tháng | 10.312 | 10.314 | 2 |
| Số cột trong loans_clean | 33 | 32 | -1 |
| Trạng thái EXEMPT | 57.249 | 53.573 | -3.676 |
| Trạng thái CANCLD | 149.016 | 149.020 | 4 |
| Trạng thái COMMIT | 49 | 44 | -5 |
| Tỷ lệ có nhãn FY2019 | 59,08% | 60,89% | 1,813 điểm % |

Các chênh lệch trên là so sánh tổng hợp giữa hai ngày chụp. Do không có mã khoản vay duy nhất, không diễn giải chúng thành số khoản vay cá biệt đã chuyển trạng thái.

## Bài viết và phân công

Giữ nguyên các mã tiểu mục 2.1–2.3.3. Riêng tiêu đề 2.1.1 đổi mốc asof sang 06/2026 để đúng dữ liệu mới; không sửa Excel hoặc playbook gốc. Các mục còn nhắc Subprogram trong tên phân công được giải thích rõ trong nội dung là trường không có ở bản hiện tại.

Cả hai notebook, Parquet, bảng, biểu đồ PNG/HTML, từ điển biến, sổ đối chiếu số liệu, báo cáo Word/Markdown/PDF, tài liệu tham khảo APA 7th và metadata đã được tái tạo theo nguồn mới. FRED-MD vẫn dùng bản 09/2026 khớp checksum với Fred.csv gốc.

Hai notebook đã chạy cục bộ trên toàn bộ dữ liệu. Chưa trực tiếp chạy Colab; xem README để tái lập.
