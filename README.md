# PTDLNC — Phân tích dữ liệu SBA 7(a) và FRED-MD

Đồ án phân tích rủi ro xóa nợ của khoản vay doanh nghiệp nhỏ tại Hoa Kỳ. Phần triển khai hiện tại là **Chương 2 — Mô tả, phân tích tổng quan về dữ liệu**, phụ trách: **Anh**.

## Bài làm

- [Báo cáo Chương 2](PTDLNC/bai_lam_Anh_Chuong2/report/Chuong_2.md), [Word](PTDLNC/bai_lam_Anh_Chuong2/report/Chuong_2.docx), [PDF](PTDLNC/bai_lam_Anh_Chuong2/report/Chuong_2.pdf).
- [Notebook chuẩn bị dữ liệu](PTDLNC/bai_lam_Anh_Chuong2/notebooks/01_data_pipeline_ch2.ipynb) và [notebook phân tích](PTDLNC/bai_lam_Anh_Chuong2/notebooks/02_eda_viz.ipynb).
- [Hướng dẫn tái lập, phương pháp và giới hạn](PTDLNC/bai_lam_Anh_Chuong2/README.md).
- [Playbook của nhóm](PTDLNC/PTDLNC_Final_Playbook.md) và [bảng phân công](PTDLNC/PTDLNC.xlsx).

## Dữ liệu và tái lập

Sử dụng SBA 7(a), phê duyệt FY2000–FY2019, bản chụp **30/06/2026**, kết hợp FRED-MD **09/2026**. Repository chứa dữ liệu Parquet đã loại định danh người vay, bảng kết quả và metadata nguồn. Hai CSV SBA gốc được giữ ở máy, không đưa vào lịch sử Git; có thể tải đúng phiên bản bằng script dưới đây.

Chạy từ thư mục gốc của repository:

```powershell
python -m venv --system-site-packages .venv
.\.venv\Scripts\python.exe -m pip install -r PTDLNC\bai_lam_Anh_Chuong2\requirements.txt
.\.venv\Scripts\python.exe PTDLNC\bai_lam_Anh_Chuong2\scripts\download_sources.py
.\.venv\Scripts\python.exe PTDLNC\bai_lam_Anh_Chuong2\scripts\run_notebooks.py
```

Không cần tải CSV gốc nếu chỉ đọc báo cáo hoặc chạy riêng notebook EDA từ Parquet có sẵn. Hướng dẫn Colab nằm trong README chi tiết; đã kiểm chứng chạy cục bộ, chưa trực tiếp kiểm chứng trên Colab.

Các kết quả chỉ mô tả khoản vay đã được phê duyệt; tỷ lệ xóa nợ dựa trên khoản có nhãn PIF/CHGOFF. Không diễn giải kết quả khám phá thành quan hệ nhân quả.
