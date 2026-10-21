# Chương 2 — Anh

Bài làm theo các mục **2.1–2.3.3** trong PTDLNC.xlsx. Dữ liệu và kết quả được tính trên toàn bộ **1.236.084 khoản vay**, không dùng dữ liệu giả hoặc mẫu 50.000 dòng. Không thay đổi playbook và Excel. Cột PHỤ TRÁCH ghi Anh; cột Viết bài còn ghi PTruc; bản này triển khai cho Anh theo yêu cầu.

## Mở bài làm

- [Bản Word](report/Chuong_2.docx): nội dung thân bài Times New Roman 13; bảng 11, chú thích 10; đủ hình, bảng và tài liệu tham khảo APA 7th.
- [Bản Markdown](report/Chuong_2.md): cùng nội dung với Word, ảnh liên kết tới figures/.
- [Bản PDF xem trước](report/Chuong_2.pdf): xuất bằng Microsoft Word để kiểm tra bố cục.
- [Tài liệu tham khảo](report/Tai_lieu_tham_khao.md): 10 nguồn.
- [Notebook chuẩn bị](notebooks/01_data_pipeline_ch2.ipynb) và [notebook EDA](notebooks/02_eda_viz.ipynb): đã lưu đầu ra sau khi chạy cục bộ.
- [Sổ đối chiếu số liệu](tables/Doi_chieu_so_lieu_bao_cao.csv): 35 số liệu, giá trị đầy đủ, cách làm tròn, nguồn và vị trí trong bảng.
- [Từ điển biến chi tiết](tables/Phu_luc_tu_dien_bien.csv): tên gốc, tên chuẩn, kiểu, đơn vị, ý nghĩa và giới hạn thời điểm thông tin.
- Bản đồ tương tác bổ sung: `figures/H3_ban_do_bang.html`; hình PNG có thể xem độc lập, không cần Chrome hay Kaleido.

Bản Word được kiểm tra phân trang bằng Microsoft Word; số trang và kết quả kiểm tra mới nhất nằm trong `../data/metadata/deliverable_validation.json`. Chưa chạy trực tiếp trên Colab.

## Dữ liệu nằm riêng

Thư mục `../data/` chứa:

```text
raw/          CSV gốc SBA 260630, bản FRED gốc, FRED chính thức và từ điển SBA
processed/    loans_clean.parquet, fred_md_monthly.parquet, monthly_series.parquet
metadata/     nguồn, SHA-256, kiểm tra pipeline, FRED, ghép tháng và kết quả kiểm chứng
```

SBA hiện dùng hai CSV bạn cung cấp, bản **30/06/2026 (260630)**: FY2000–FY2009 có 690.333 dòng; FY2010–FY2019 có 545.751 dòng. Mỗi tệp có 42 cột CamelCase, ngày ISO và trạng thái trả đủ ghi `P I F`. SHA-256 được ghi từ tệp cục bộ, không giả định đây là lần tải mới từ Internet. Phiên bản và danh sách nguồn cấu hình tại `../data/metadata/dataset_config.json`; xem source_manifest.json để biết nguồn từng tệp. [Chi tiết thay đổi và số liệu trước–sau](report/Cap_nhat_du_lieu.md).

Fred.csv gốc khớp SHA-256 với FRED-MD 09/2026: **126 biến, 812 tháng, 01/1959–08/2026**. Phiên bản và tháng cuối là hai khái niệm khác nhau. Từ điển SBA tải từ đường dẫn hiện hành; **chưa xác nhận đây là từ điển lưu trữ riêng của 06/2026**.

CSV thô có định danh người vay, được giữ nguyên trong raw/ để tái lập. Không dùng bảng xem trước dữ liệu thô trong notebook. Đầu ra phân tích dùng danh sách cột cho phép và không có tên/địa chỉ/ZIP người vay. Không tải thư mục raw/ lên kho mã công khai khi chỉ cần bàn giao báo cáo và bảng tổng hợp.

## Chạy lại trên máy cá nhân

Chạy lệnh tại thư mục workspace chứa PTDLNC/:

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r PTDLNC\bai_lam_Anh_Chuong2\requirements.txt
.\.venv\Scripts\python.exe PTDLNC\bai_lam_Anh_Chuong2\scripts\download_sources.py
.\.venv\Scripts\python.exe PTDLNC\bai_lam_Anh_Chuong2\scripts\run_notebooks.py
.\.venv\Scripts\python.exe PTDLNC\bai_lam_Anh_Chuong2\scripts\build_report.py
.\.venv\Scripts\python.exe PTDLNC\bai_lam_Anh_Chuong2\scripts\validate_deliverables.py
```

Bỏ qua bước tải nếu raw/ đã đầy đủ. Downloader không ghi đè tệp có sẵn. Notebook 01 chỉ dùng lại Parquet khi ngày chụp và checksum của từng CSV khớp nguồn đã xử lý. Khi CSV thay đổi, xây lại Parquet theo cấu hình thay vì dùng cache cũ; notebook EDA cũng từ chối nguồn chưa được xử lý lại. Muốn thay phiên bản hoặc xây lại pipeline phải lưu một bản dự án riêng và xác minh nguồn, không tự sửa CSV gốc. Kernel của script chạy notebook được đăng ký tạm dưới `.cache/jupyter/` trong workspace, không thay kernel toàn hệ thống.

`scripts/build_notebooks.py` là nguồn tạo hai notebook độc lập, toàn bộ mã phân tích và vẽ nằm trong các ô notebook. Không cần gọi script này để chạy notebook đã bàn giao; chạy lại sẽ tạo lại notebook và xóa đầu ra đang lưu.

Trên Windows có Microsoft Word, `scripts/render_word.ps1` xuất lại PDF ở chế độ ẩn. Đây là bước riêng sau khi thay đổi bản Word, không cần cho phân tích dữ liệu.

## Chạy trên Colab

1. Tải cả thư mục PTDLNC lên Google Drive, giữ đúng cấu trúc data/ và bai_lam_Anh_Chuong2/.
2. Mở notebook bằng Colab. Mount Drive bằng giao diện Colab hoặc ô chuẩn:

```python
from google.colab import drive
drive.mount('/content/drive')
```

3. Ô cấu hình dùng biến `BASE`. Để tự tìm thư mục, trước khi chạy notebook đổi thư mục làm việc đến nơi đã tải lên:

```python
%cd /content/drive/MyDrive/PTDLNC
```

Nếu thư mục Drive có tên khác, sửa đúng dòng `%cd` theo vị trí của bạn; không có đường dẫn máy cá nhân trong notebook. Có thể gán `BASE = Path(...)` tại ô cấu hình thay cho cơ chế tự tìm.

4. Colab thường có các gói khoa học cơ bản. Nếu thiếu, chạy một lần:

```python
%pip install pandas numpy scipy matplotlib plotly pyarrow openpyxl requests
```

5. Chạy notebook 01 rồi notebook 02 bằng Run all. Nếu chỉ có dữ liệu Parquet đã được nhóm chuẩn bị đúng hợp đồng, có thể chạy riêng notebook 02; vẫn cần `data/metadata/usa_110m.json` để vẽ bản đồ.

**Đã kiểm chứng Run all bằng kernel Python cục bộ; chưa trực tiếp chạy trên tài khoản Colab.** Không đồng nhất tính tương thích thiết kế với kiểm chứng thực tế. Trước khi nộp, nhóm cần chạy lại hai notebook trên Colab và cập nhật trạng thái kiểm chứng.

## Các phát hiện và giới hạn cần giữ khi hợp nhất

- Tập có nhãn: 1.033.447 khoản; 854.943 PIF, 178.504 CHGOFF; tỷ lệ xóa nợ có điều kiện = **17,27%**. Không diễn giải thành xác suất vòng đời cho mọi khoản đã duyệt.
- Ngoài nhãn: 149.020 CANCLD, 53.573 EXEMPT, 44 COMMIT. Không xem trạng thái hủy là kiểm duyệt phải.
- Tỷ lệ có nhãn FY2019: **60,89%**; EXEMPT chiếm **27,10%** cohort này. So sánh cohort chịu khác biệt thời gian theo dõi và cơ cấu trạng thái.
- InitialInterestRate thiếu toàn bộ FY2000–FY2008. Các tương quan với lãi suất có tập quan sát khác các cặp tiền vay/kỳ hạn.
- BankName là ngân hàng hiện được gán khoản vay; không tự coi là ngân hàng tại thời điểm duyệt. JobsSupported là ước lượng tự báo cáo trên đơn xin vay, không phải việc làm thực tế đã kiểm chứng.
- Không có mã khoản vay duy nhất. Phát hiện 1.414 fingerprint hàng gốc lặp, không xóa dòng và không tuyên bố đây là số khoản vay trùng đã xác minh. LocationID là mã ngân hàng.
- `ApprovalFY` ánh xạ thành `ApprovalFiscalYear`; `PaidInFullDate` giữ chính tả từ điển. Bản 260630 không có Subprogram; dùng ProcessingMethod và không tạo cột thay thế giả. Tên Subprogram trong một số tiêu đề gốc của phân công được giải thích trong bài. Riêng tiêu đề 2.1.1 cập nhật mốc 06/2026; Excel/playbook giữ nguyên.
- Phân tích thiếu chỉ đo ô thiếu; BusinessAge = Unanswered là thiếu thông tin về nội dung, được giữ nguyên nhóm để minh bạch. Không tự coi FranchiseCode trống là không nhượng quyền.
- Không bù thiếu, winsorize, SMOTE, chia train/test hoặc học mô hình. IQR và mốc kỳ hạn chỉ để đánh dấu rà soát. Boxplot ẩn điểm ngoài râu khi vẽ nhưng giữ chúng trong thống kê.
- Bản đồ dùng BorrState. PNG gồm 50 bang + DC từ lớp hình học Plotly. Địa bàn ngoài lớp này được lưu ở B12; bảng tỷ lệ đầy đủ vẫn giữ mọi nhóm. Mẫu nhỏ có cờ low_n < 100, không tự loại.
- NAICS là nhóm rộng; chưa quy đổi hoàn chỉnh giữa mọi phiên bản phân ngành. Bubble x dùng tất cả khoản trong ngành, y dùng khoản có nhãn, diện tích tỷ lệ với số khoản; từng bubble có số.
- Wilson 95% chưa điều chỉnh cụm tháng/ngân hàng. Pearson/Spearman loại thiếu theo cặp và có bảng N. Cramér’s V chuẩn không hiệu chỉnh sai lệch, dùng toàn bộ năm trạng thái LoanStatus trong H6b; không phải riêng target nhị phân.
- FRED được tính YoY trên lịch sử đầy đủ rồi lag một tháng. Ghép đủ 240 tháng và không tăng số dòng; EDA không ghi đè loans_clean hoặc tạo loans_features. Lag một tháng chưa giải quyết hết độ trễ công bố và dữ liệu điều chỉnh về sau.
- Chỉ khoản vay đã phê duyệt được quan sát; kết quả khám phá không suy ra nhân quả. EDA toàn mẫu được mô tả hồi cứu, không dùng kết quả này để chọn ngưỡng trên tập test mô hình.

## Kiểm chứng và bàn giao

Xem `../data/metadata/deliverable_validation.json`, `notebook_validation.json`, `pipeline_audit.json`, `macro_join_audit.json` và `source_manifest.json`. Script kiểm chứng kiểm tra schema, nhãn, checksum, đối chiếu số liệu, các mục bài viết, hình/bảng và trạng thái thực thi notebook. Bản xem trước PDF được kiểm tra bằng Word; phân trang có thể thay đổi nếu nhóm đổi lề, font hoặc chèn chương vào báo cáo chung.

Thụy/Khải có thể lấy bảng tỷ lệ và chẩn đoán để viết các chương tiếp theo, nhưng các kiểm định và lựa chọn mô hình chưa được thực hiện trong phần việc này.
