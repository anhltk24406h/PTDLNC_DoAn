# PTDLNC – Đồ án cuối kì: Playbook thực hiện cho cả nhóm

**Tên đề tài (đề xuất, chờ nhóm chốt bản cuối):** Dự báo rủi ro vỡ nợ của các khoản vay doanh nghiệp nhỏ được chính phủ Hoa Kỳ bảo lãnh

**Phụ đề:** Phân tích dữ liệu SBA 7(a) kết hợp chỉ số vĩ mô FRED-MD bằng kiểm định thống kê, chuỗi thời gian và học máy

**Lĩnh vực:** kinh tế – tài chính – ngân hàng

**Cách dùng file này:** mỗi thành viên đọc mục 0–2 và 4–5, sau đó làm đúng phần của mình ở mục 3\. Mọi quyết định kỹ thuật dùng chung nằm ở mục 1 và 2; muốn đổi thì báo nhóm trưởng và sửa trong file này, không tự đổi trong notebook riêng.

---

## 0\. Tóm tắt dự án

**Câu chuyện:** Chương trình SBA 7(a) bảo lãnh một phần cho các khoản vay doanh nghiệp nhỏ do ngân hàng thương mại cấp. Ngân hàng cần biết khoản vay nào có nguy cơ bị xóa nợ để thẩm định và giám sát. Nhóm phân tích dữ liệu cấp khoản vay giai đoạn FY2000–FY2019, ghép với chỉ số kinh tế vĩ mô hàng tháng để trả lời bốn câu hỏi:

| RQ | Câu hỏi | Kỹ thuật chính |
| :---- | :---- | :---- |
| RQ1 | Tỷ lệ vỡ nợ khác nhau thế nào giữa các nhóm khoản vay (loại hình doanh nghiệp, ngành, bang, quy mô, kỳ hạn) và giữa thời kỳ suy thoái với mở rộng? | Kiểm định, effect size, Bayes (Slide 2\) |
| RQ2 | Số khoản vay phê duyệt theo tháng có xu hướng và mùa vụ gì, dự báo 12 tháng tới bằng mô hình nào tốt nhất? | Chuỗi thời gian (Slide 6\) |
| RQ3 | Dự đoán khoản vay nào sẽ vỡ nợ tốt đến đâu, mô hình nâng cao có hơn baseline không? | Học máy có giám sát (ngoài Slide 1–6) |
| RQ4 | Yếu tố nào quyết định rủi ro, và điều kiện vĩ mô lúc cho vay có thêm giá trị dự báo không? | SHAP, so sánh có và không có biến FRED-MD |

**Ba nguồn dữ liệu:**

1. SBA 7(a) FOIA FY2000–FY2009 (bản asof 03/2026)  
2. SBA 7(a) FOIA FY2010–FY2019 (bản asof 03/2026)  
3. FRED-MD của Cục Dự trữ Liên bang St. Louis (bản 2026-09)

**Sản phẩm phải nộp:** (a) báo cáo Word hoặc PDF, tối thiểu 20 trang ngoài bìa, font 13, đúng 5 đầu mục theo mẫu của thầy, kèm Phần 2 phân công; (b) notebook Colab chạy được từ đầu đến cuối; (c) bài thuyết trình 10 phút; (d) thư mục Google Drive chung (link ghi trong báo cáo).

---

## 1\. Nguyên tắc làm việc (bắt buộc)

### 1.1. Chạy được trên Colab là điều kiện tiên quyết

- Mỗi notebook phải chạy được bằng Runtime → Run all trên Colab bản mới, không lỗi, không cần sửa tay.  
- Không hard-code đường dẫn máy cá nhân; dùng biến `BASE` ở ô cấu hình.  
- Đặt `RANDOM_STATE = 42` ở mọi nơi có tính ngẫu nhiên.  
- Mỗi biểu đồ có tiêu đề, nhãn trục, đơn vị, chú thích tiếng Việt; bubble chart ghi số trên từng bubble.

### 1.2. Cấu trúc thư mục Drive (một thư mục chung)

PTDLNC\_Final/

├── data/

│   ├── raw/          \# CSV gốc tải về, KHÔNG sửa

│   └── processed/    \# file Parquet do notebook tạo ra (xem 1.3)

├── notebooks/        \# 01\_... đến 07\_...

├── figures/          \# ảnh xuất ra cho báo cáo (png, 200 dpi)

├── report/           \# bản Word, PDF

└── README.md         \# file này

### 1.3. Hợp đồng dữ liệu giữa các notebook (để làm song song)

Mỗi notebook chỉ **đọc** các file dưới đây, không tự đọc CSV gốc.

| File trong `data/processed/` | Do ai tạo | Nội dung |
| :---- | :---- | :---- |
| `loans_clean.parquet` | Notebook 01 (Khải) | Một dòng một khoản vay, đã gộp hai file SBA, bỏ cột định danh, parse ngày, thêm `fy`, `approval_month`, `is_resolved`, `target` |
| `fred_md_monthly.parquet` | Notebook 01 (Khải) | Bảng FRED-MD theo tháng, đã bỏ dòng Transform, kèm bảng `tcodes` |
| `monthly_series.parquet` | Notebook 01 (Khải) | Số khoản vay và tổng giá trị phê duyệt theo tháng |
| `loans_features.parquet` | Notebook 03 (Minh) | Đặc trưng đã mã hóa, đã ghép FRED-MD (lag 1 tháng), nhãn, cột `split` (train, valid, test) |

Nếu cần thêm hoặc đổi cột trong các file trên, báo người tạo file; không tự tạo bản sao riêng.

### 1.4. Quy tắc khoa học (đây là chỗ ăn điểm)

- **Không để rò rỉ dữ liệu:** các cột chỉ biết sau khi khoản vay kết thúc tuyệt đối không là đặc trưng (xem 2.5).  
- **Không chia ngẫu nhiên:** train và test chia theo năm phê duyệt (xem 3.3).  
- **Mẫu rất lớn thì p-value luôn nhỏ:** mọi kiểm định phải kèm effect size (Cramér's V, rank-biserial, chênh lệch tỷ lệ kèm khoảng tin cậy). Kết luận dựa trên mức độ ảnh hưởng, không chỉ p \< 0.05.  
- **Không nói quá:** dữ liệu chỉ gồm khoản vay đã được duyệt, nên mô hình dự đoán rủi ro **trong số khoản đã duyệt**, không dự đoán quyết định duyệt hay từ chối. Nhân quả không được suy ra từ mô hình dự báo.  
- **Quyền riêng tư:** file SBA có tên và địa chỉ người vay. Bỏ các cột định danh ngay ở notebook 01, không đưa vào ảnh chụp, bảng hay báo cáo.

---

## 2\. Dữ liệu

### 2.1. Ba nguồn

| Nguồn | File | Trang tải |
| :---- | :---- | :---- |
| SBA 7(a) | `FOIA - 7(a) (FY2000-FY2009) asof 260331.csv` | [https\://web.data.sba.gov/en/dataset/7-a-504-foia/resource/cffcdfdf-0516-41a5-b25a-ee7cb06de55b](https://web.data.sba.gov/en/dataset/7-a-504-foia/resource/cffcdfdf-0516-41a5-b25a-ee7cb06de55b) |
| SBA 7(a) | `FOIA - 7(a) (FY2010-FY2019) asof 260331.csv` (213,6 MiB theo trang SBA) | [https\://web.data.sba.gov/en/dataset/7-a-504-foia/resource/1defde4c-e0ad-470f-851f-8b0f18848757](https://web.data.sba.gov/en/dataset/7-a-504-foia/resource/1defde4c-e0ad-470f-851f-8b0f18848757) |
| FRED-MD | `2026-09.csv` (mục Monthly Data) | [https\://www\.stlouisfed.org/research/economists/mccracken/fred-databases](https://www.stlouisfed.org/research/economists/mccracken/fred-databases) |

- Trang chủ dataset SBA: [https\://data.sba.gov/dataset/7-a-504-foia](https://data.sba.gov/dataset/7-a-504-foia) (cập nhật hằng quý; tên file đổi mỗi quý).  
- Cách lấy link tải trực tiếp: mở trang, bấm chuột phải nút Download, chọn Copy link address.  
- Lưu một bản CSV gốc vào `data/raw/` để cả nhóm dùng cùng một phiên bản, phòng khi SBA đổi tên file.  
- Trích dẫn FRED-MD: McCracken & Ng (2016), *FRED-MD: A Monthly Database for Macroeconomic Research*, Journal of Business & Economic Statistics, 34(4), 574–589.

### 2.2. Việc đầu tiên của nhóm trưởng: kiểm tra những điều CHƯA xác nhận

Tại thời điểm viết file này chưa ai tải được dữ liệu thật, nên các mục sau cần kiểm tra rồi cập nhật lại tài liệu:

- [ ] Tên cột thật (`df.columns`) có khớp với danh sách dự kiến ở sheet "Từ điển cột" không.  
- [ ] Số dòng mỗi file, tổng số dòng sau khi gộp.  
- [ ] Các giá trị của `LoanStatus` và ý nghĩa từng giá trị (đối chiếu data dictionary của SBA). Dự kiến: `PIF` (trả đủ), `CHGOFF` (xóa nợ), còn lại là chưa có kết quả hoặc đã hủy.  
- [ ] Bảng mã của file CSV (`latin-1` hay `utf-8`).  
- [ ] Hai file có trùng khoản vay hoặc lệch cột không.  
- [ ] Giai đoạn thật của dữ liệu: năm tài khóa của SBA chạy từ tháng 10 đến tháng 9, nên FY2000 bắt đầu từ 10/1999.  
- [ ] Tên cột các biến FRED-MD cần dùng (dự kiến: `UNRATE`, `FEDFUNDS`, `T10YFFM`, `CPIAUCSL`, `INDPRO`, `BUSLOANS`, `GS10`, `S&P 500`).  
- [ ] Dữ liệu FRED-MD thật sự kết thúc ở tháng nào.

### 2.3. Nạp dữ liệu (khung code cho notebook 01\)

Chỉ đọc các cột cần dùng, đọc theo khối, rồi lưu Parquet.

import pandas as pd

SBA\_URLS \= {

    "fy2000\_2009": "\<dán link tải trực tiếp\>",

    "fy2010\_2019": "\<dán link tải trực tiếp\>",

}

USECOLS \= \["BorrState", "BankName", "GrossApproval", "SBAGuaranteedApproval",

           "ApprovalDate", "ApprovalFiscalYear", "FirstDisbursementDate",

           "ProcessingMethod", "Subprogram", "TermInMonths", "NaicsCode",

           "FranchiseCode", "BusinessType", "BusinessAge", "LoanStatus",

           "PaidinFullDate", "ChargeOffDate", "GrossChargeOffAmount",

           "JobsSupported", "ProjectState", "RevolverStatus", "CollateralInd",

           "SoldSecMrktInd"\]          \# sửa theo df.columns sau khi kiểm tra ở 2.2

parts \= \[\]

for name, url in SBA\_URLS.items():

    for chunk in pd.read\_csv(url, usecols=lambda c: c in USECOLS,

                             chunksize=200\_000, encoding="latin-1",

                             low\_memory=False):

        chunk\["source\_file"\] \= name

        parts.append(chunk)

loans \= pd.concat(parts, ignore\_index=True)

FRED-MD (dòng thứ hai của file là mã biến đổi `Transform:`):

fred \= pd.read\_csv(FRED\_URL)

tcodes \= fred.iloc\[0, 1:\].astype(float)            \# mã biến đổi của từng biến

fred \= fred.iloc\[1:\].dropna(subset=\["sasdate"\]).copy()

fred\["sasdate"\] \= pd.to\_datetime(fred\["sasdate"\], format="%m/%d/%Y")

fred \= fred.set\_index("sasdate").astype(float)

Sau đó lưu `loans_clean.parquet`, `fred_md_monthly.parquet`, `monthly_series.parquet` vào `data/processed/`. Khi viết code trong VS Code, dùng bản mẫu `loans.sample(50_000, random_state=42)` cho nhanh, rồi chạy bản đầy đủ trên Colab.

### 2.4. Nhãn, phạm vi và kiểm duyệt phải

- **Nhãn:** `target = 1` nếu `LoanStatus == "CHGOFF"`, `target = 0` nếu `LoanStatus == "PIF"`. Các trạng thái còn lại (khoản vay đang hoạt động, đã hủy, chưa giải ngân...) **không có nhãn**: giữ trong `loans_clean` với `is_resolved = False` để dùng cho thống kê mô tả và chuỗi thời gian, nhưng loại khỏi tập huấn luyện ML.  
- **Kiểm duyệt phải (right-censoring):** khoản vay phê duyệt càng gần 2019 càng có nhiều khoản chưa có kết quả. Làm một biểu đồ tỷ lệ `is_resolved` theo năm phê duyệt; đây là hình bắt buộc trong báo cáo.  
- **Hệ quả:** tỷ lệ vỡ nợ của các cohort mới (tính trên các khoản đã có kết quả) bị thiên lệch. Phải nêu rõ trong Chương 2 (thách thức) và Chương 5 (hạn chế).

### 2.5. Cột phải loại hoặc xử lý đặc biệt

| Nhóm | Cột | Xử lý |
| :---- | :---- | :---- |
| Định danh | `BorrName`, `BorrStreet`, `BorrCity`, `BorrZip` (và các cột tương tự) | Loại ngay ở notebook 01 |
| Rò rỉ (biết sau khi vay kết thúc) | `LoanStatus` (là mục tiêu), `PaidinFullDate`, `ChargeOffDate`, `GrossChargeOffAmount` | Không được là đặc trưng |
| Nghi rò rỉ (xảy ra sau phê duyệt) | `FirstDisbursementDate`, `SoldSecMrktInd` | Mặc định loại; chỉ giữ nếu data dictionary chứng minh biết tại thời điểm phê duyệt |
| Cardinality cao | `NaicsCode`, `BankName`, `ProjectState` | Frequency encoding, gom ngành về cấp 2 chữ số |

### 2.6. Ghép FRED-MD (lag 1 tháng)

Dùng giá trị vĩ mô của **tháng liền trước tháng phê duyệt**, vì số liệu tháng hiện tại chưa công bố khi ngân hàng quyết định cho vay.

loans\["approval\_month"\] \= loans\["ApprovalDate"\].dt.to\_period("M").dt.to\_timestamp()

macro \= pd.DataFrame({

    "unrate": fred\["UNRATE"\],

    "fedfunds": fred\["FEDFUNDS"\],

    "yield\_spread": fred\["T10YFFM"\],

    "cpi\_yoy": fred\["CPIAUCSL"\].pct\_change(12) \* 100,

    "indpro\_yoy": fred\["INDPRO"\].pct\_change(12) \* 100,

    "busloans\_yoy": fred\["BUSLOANS"\].pct\_change(12) \* 100,

})

macro\_lag1 \= macro.shift(1).add\_suffix("\_lag1")

macro\_lag1.index.name \= "approval\_month"

loans \= loans.merge(macro\_lag1.reset\_index(), on="approval\_month", how="left")

Chỉ giữ một nhóm nhỏ biến vĩ mô (khoảng 6–10 biến có ý nghĩa kinh tế). Không đưa cả 126 biến vào mô hình.

### 2.7. Cờ suy thoái (NBER)

Hard-code các tháng suy thoái trong giai đoạn 2000–2019 theo NBER, nêu nguồn trong báo cáo: 03/2001–11/2001 và 12/2007–06/2009. Tạo cột `recession` cho `approval_month`.

---

## 3\. Kế hoạch phân tích theo từng câu hỏi

### 3.1. RQ1 – Thống kê và Bayes (Notebook 04, phụ trách: Thụy)

Slide tham chiếu: Slide 2\.

1. **Tỷ lệ vỡ nợ theo nhóm** (chỉ tính trên khoản vay đã có nhãn): `BusinessType`, `Subprogram`/`ProcessingMethod`, cờ nhượng quyền, ngành cấp 2 chữ số, bang (top N bang \+ nhóm "khác"), nhóm quy mô khoản vay, nhóm kỳ hạn. Bảng và biểu đồ cột có khoảng tin cậy.  
2. **Chi-square độc lập** giữa từng biến phân loại và `target`, kèm **Cramér's V**. Dùng hiệu chỉnh Holm hoặc Bonferroni khi chạy nhiều kiểm định.  
3. **Biến số theo nhãn** (`GrossApproval`, `TermInMonths`, `JobsSupported`): kiểm tra phân phối bằng biểu đồ và Q-Q (không dùng Shapiro trên cả tập vì mẫu rất lớn). Dùng **Mann-Whitney U** với **rank-biserial**; làm thêm Welch t-test trên log làm kiểm tra độ vững.  
4. **So sánh từ 3 nhóm:** Kruskal-Wallis trên `GrossApproval` theo `BusinessType` hoặc ngành, kèm hậu kiểm Dunn; làm thêm ANOVA \+ Tukey trên log làm đối chiếu. Levene cho tính đồng nhất phương sai.  
5. **Suy thoái và mở rộng:** so sánh tỷ lệ vỡ nợ của khoản vay phê duyệt trong tháng suy thoái và ngoài suy thoái, bằng chi-square và hiệu số tỷ lệ với khoảng tin cậy bootstrap theo tháng phê duyệt.  
6. **Bayes:** P(vỡ nợ | nhóm) \= P(nhóm | vỡ nợ) × P(vỡ nợ) / P(nhóm). Bảng prior (tỷ lệ chung) so với posterior theo nhóm, kèm lift. Chỉ nêu các nhóm có đủ quan sát.

**Đầu ra bắt buộc:** 1 bảng tổng hợp kiểm định (kiểm định, thống kê, p đã hiệu chỉnh, effect size, kết luận một câu); 3–4 biểu đồ; đoạn diễn giải cho nhà quản lý.

### 3.2. RQ2 – Chuỗi thời gian (Notebook 05, phụ trách: Phương Trúc)

Slide tham chiếu: Slide 6, và Slide 1.18 (ngày tháng, resample).

1. **Tổng hợp theo tháng:** số khoản vay phê duyệt và tổng `GrossApproval` (lấy log). Dùng **tất cả** khoản vay (cả chưa có nhãn). Khoảng thời gian dự kiến 10/1999–09/2019 (240 tháng).  
2. **Mô tả:** biểu đồ đường có tô nền các giai đoạn suy thoái; phân rã STL với chu kỳ 12; biểu đồ theo tháng trong năm để thấy mùa vụ năm tài khóa.  
3. **Tính dừng:** ADF và KPSS trên chuỗi gốc, chuỗi log, chuỗi sai phân bậc 1 và sai phân mùa vụ; ghi bảng kết quả và cách đọc kết hợp hai kiểm định.  
4. **Nhận dạng mô hình:** ACF/PACF của chuỗi đã làm dừng.  
5. **Mô hình ứng viên:** naive, seasonal naive, ARIMA, SARIMA (chu kỳ 12), ETS (Holt-Winters), SARIMAX với biến ngoại sinh từ FRED-MD (ví dụ `unrate`, `yield_spread`, cờ suy thoái, dùng giá trị đã lag).  
6. **Đánh giá:** giữ lại 36 tháng cuối làm tập kiểm tra; dùng walk-forward (cửa sổ mở rộng); chỉ số RMSE, MAE, MAPE (số khoản vay luôn dương nên MAPE dùng được), kèm AIC cho trong mẫu.  
7. **Chẩn đoán phần dư:** Ljung-Box, Q-Q, ACF của phần dư.  
8. **Dự báo 12 tháng** kèm khoảng tin cậy 95% bằng mô hình tốt nhất. Giải thích cú sốc 2008–2009.

**Lưu ý:** dữ liệu dừng ở 09/2019 nên không có đáp án thật cho dự báo. Nếu nhóm muốn kiểm chứng ngoài mẫu (ví dụ cú sốc 2020), phải tải thêm file FY2020–nay; đây là phần tùy chọn, chỉ làm khi dư thời gian.

**Đầu ra bắt buộc:** bảng so sánh mô hình (RMSE, MAE, MAPE, AIC); biểu đồ dự báo so với thực tế; chẩn đoán phần dư; kết luận mô hình nào tốt nhất và vì sao.

### 3.3. RQ3 – Học máy (Notebook 06, phụ trách: Tuấn Anh; Minh hỗ trợ chuẩn bị đặc trưng)

Đây là phần nằm ngoài Slide 1–6. Làm sau khi lõi dữ liệu đã chạy ổn.

**Chia dữ liệu theo thời gian** (chỉ trên khoản vay có nhãn). Cắt mặc định, điều chỉnh sau khi xem biểu đồ kiểm duyệt ở 2.4:

- train: `fy` 2000–2011  
- valid: `fy` 2012–2013 (chọn ngưỡng, chọn siêu tham số)  
- test: `fy` 2014–2015, chỉ dùng **một lần** ở cuối

Nếu cohort nào có tỷ lệ chưa có kết quả quá cao thì cắt bỏ cohort đó khỏi tập test và ghi rõ lý do.

**Đặc trưng** (chỉ dùng thông tin biết tại thời điểm phê duyệt):

- Khoản vay: `log1p(GrossApproval)`, tỷ lệ bảo lãnh `SBAGuaranteedApproval / GrossApproval`, `TermInMonths`, vốn vay trên mỗi việc làm, `JobsSupported`.  
- Doanh nghiệp: `BusinessType`, `BusinessAge`, cờ nhượng quyền, ngành cấp 2 chữ số (frequency encoding).  
- Địa lý và ngân hàng: bang, ngân hàng (frequency encoding **tính trên tập train**).  
- Vĩ mô: nhóm biến lag 1 tháng ở 2.6 (dùng cho phần so sánh ở RQ4).  
- Thời gian: tháng, quý, năm tài khóa (cẩn thận với năm tài khóa vì mô hình có thể chỉ học "cohort").

**Mô hình:**

1. Baseline: Logistic Regression (chuẩn hóa, `class_weight="balanced"`).  
2. Nâng cao: Random Forest và XGBoost (hoặc LightGBM), dùng trọng số lớp (`scale_pos_weight`).  
3. Xử lý mất cân bằng: ưu tiên trọng số lớp; nếu dùng SMOTE thì chỉ áp dụng trên tập train, không bao giờ trên valid hay test.  
4. Tinh chỉnh: RandomizedSearchCV với **chia fold theo thời gian** (TimeSeriesSplit, chừa khoảng đệm giữa train và valid).

**Đánh giá (báo cáo trên test):**

- ROC-AUC và **PR-AUC** (chỉ số chính vì lớp thiểu số), KS, F1, Precision, Recall tại ngưỡng đã chọn trên valid.  
- Ma trận nhầm lẫn, đường ROC và PR, đường hiệu chỉnh xác suất (calibration).  
- Bảng **decile lift**: top 10% khoản vay rủi ro nhất bắt được bao nhiêu % khoản vỡ nợ.  
- Ngưỡng quyết định chọn theo chi phí: nêu rõ giả định minh họa (ví dụ bỏ sót một khoản vỡ nợ tốn gấp 5 lần từ chối nhầm một khoản tốt) và nói rõ đây là giả định, không phải số liệu thật.

**Đầu ra bắt buộc:** bảng so sánh ba mô hình; biểu đồ ROC/PR/calibration; decile lift; lựa chọn ngưỡng; nhận xét mô hình nâng cao có hơn baseline bao nhiêu và có đáng phức tạp hơn không. Nếu XGBoost không vượt Logistic Regression thì đó là kết luận hợp lệ, vẫn ghi vào báo cáo.

### 3.4. RQ4 – Yếu tố rủi ro và giá trị của biến vĩ mô (Notebook 06 và 07, phụ trách: Minh và Khải)

1. **So sánh có và không có biến FRED-MD** trên cùng mô hình tốt nhất: chênh lệch ROC-AUC và PR-AUC trên test, kèm khoảng tin cậy bootstrap. Nếu chênh lệch không đáng kể thì nói thẳng như vậy.  
2. **Diễn giải:** feature importance và SHAP (lấy mẫu 10–20 nghìn dòng để chạy nhanh); biểu đồ SHAP tổng hợp và 2–3 biểu đồ phụ thuộc cho biến quan trọng.  
3. **Theo phân khúc:** hiệu năng và tỷ lệ vỡ nợ theo ngành, quy mô khoản vay, giai đoạn suy thoái.  
4. **Độ ổn định theo thời gian:** AUC theo từng năm trong tập valid và test.  
5. **Khuyến nghị:** phân tầng rủi ro xanh, vàng, đỏ theo xác suất dự đoán (ngưỡng lấy từ valid); đề xuất cách dùng cho thẩm định, giám sát và đặt giới hạn; nêu rõ mô hình không thay quyết định của thẩm định viên; lưu ý công bằng và quyền riêng tư.  
6. **Sản phẩm trình bày (tùy chọn, làm cuối):** một dashboard Plotly gọn hoặc một bảng điều khiển trong notebook để minh họa luồng chấm điểm rủi ro.

---

## 4\. Notebook và phân công

| \# | Notebook | Nội dung | Phụ trách (đề xuất) |
| :---- | :---- | :---- | :---- |
| 01 | `01_data_pipeline` | Nạp, gộp, bỏ cột định danh, tạo nhãn, lưu Parquet và SQLite, kiểm tra ở mục 2.2 | Khải |
| 02 | `02_eda_viz` | Mô tả, trực quan hóa tổng quan, tương quan, biểu đồ kiểm duyệt | Tuấn Anh |
| 03 | `03_cleaning_features` | Thiếu, ngoại lai, mã hóa, ghép FRED-MD, chia train/valid/test | Minh |
| 04 | `04_stats_tests` | RQ1: kiểm định, effect size, Bayes | Thụy |
| 05 | `05_time_series` | RQ2: chuỗi thời gian và dự báo | Phương Trúc |
| 06 | `06_ml_models` | RQ3 và RQ4: mô hình, đánh giá, SHAP | Tuấn Anh (Minh hỗ trợ) |
| 07 | `07_recommendation` | Phân tầng rủi ro, dashboard, tổng hợp kết quả | Khải |

**Viết báo cáo:** Thụy viết Chương 1; Phương Trúc viết Chương 2; mỗi người viết phần phương pháp và kết quả của notebook mình phụ trách; Khải viết Tóm tắt, 3.1, 3.2, 4.5, Chương 5 và hợp nhất. Khớp với Google Sheet PTDLNC.

**Thứ tự phụ thuộc:** 01 → (02, 03\) → (04, 05, 06\) → 07\. Trong lúc chờ 01, những người khác viết phần lý thuyết của báo cáo và chuẩn bị code trên bản mẫu 50.000 dòng.

---

## 5\. Lộ trình (điền hạn thật vào cột cuối)

| Giai đoạn | Việc | Cổng kiểm tra để sang giai đoạn sau | Hạn |
| :---- | :---- | :---- | :---- |
| 0\. Khởi động | Tạo thư mục Drive, tải 3 file, điền link vào sheet Dataset, mỗi người chạy được notebook mẫu | Cả nhóm đọc được `loans_clean.parquet` |  |
| 1\. Dữ liệu | Notebook 01, danh sách kiểm tra 2.2 hoàn tất, cập nhật tài liệu này | Số dòng, cột, giá trị `LoanStatus` đã được ghi lại |  |
| 2\. Khám phá và làm sạch | Notebook 02 và 03 | `loans_features.parquet` có cột `split`; biểu đồ kiểm duyệt xong |  |
| 3\. Phân tích song song | Notebook 04, 05, 06 (bản baseline) | Mỗi notebook chạy Run all không lỗi; có bảng kết quả chính |  |
| 4\. Học máy hoàn chỉnh và diễn giải | Hoàn tất 06, 07 | Bảng so sánh mô hình và SHAP đã duyệt |  |
| 5\. Báo cáo | Viết, hợp nhất, định dạng theo mẫu UEL | Đủ 20 trang, đủ 5 đầu mục, bảng đóng góp |  |
| 6\. Thuyết trình | Slide, tập 2 lần, chuẩn bị hỏi đáp | Đúng 10 phút |  |

**Cắt giảm nếu thiếu thời gian (theo thứ tự cắt):** dashboard → SARIMAX → SHAP phụ thuộc → phân tích theo phân khúc → kiểm chứng ngoài mẫu. **Không cắt:** nạp và làm sạch dữ liệu, kiểm định kèm effect size, ARIMA/SARIMA/ETS, so sánh baseline và mô hình nâng cao.

---

## 6\. Danh mục hình và bảng bắt buộc

| Hình/bảng | Nội dung | Notebook |
| :---- | :---- | :---- |
| H1 | Số khoản vay phê duyệt theo năm tài khóa | 02 |
| H2 | Tỷ lệ khoản vay đã có kết quả theo năm phê duyệt (kiểm duyệt) | 02 |
| H3 | Bản đồ tỷ lệ vỡ nợ theo bang (Plotly choropleth) | 02 |
| H4 | Bubble chart theo ngành: x là quy mô khoản vay trung bình, y là tỷ lệ vỡ nợ, kích thước là số khoản vay; **ghi số trên từng bubble** | 02 |
| H5 | Violin hoặc box của `GrossApproval` (log) theo nhãn | 02 |
| H6 | Heatmap tương quan biến số (và Cramér's V cho biến phân loại) | 02 |
| H7 | Chuỗi thời gian có tô nền suy thoái, phân rã STL | 05 |
| H8 | Dự báo so với thực tế, phần dư | 05 |
| H9 | ROC, PR, calibration | 06 |
| H10 | SHAP tổng hợp | 06 |
| B1 | Bảng kiểm định tổng hợp (p đã hiệu chỉnh, effect size) | 04 |
| B2 | Bảng prior so với posterior theo nhóm (Bayes) | 04 |
| B3 | Bảng so sánh mô hình chuỗi thời gian | 05 |
| B4 | Bảng so sánh mô hình học máy, decile lift | 06 |
| B5 | Bảng so sánh có và không có biến vĩ mô | 06 |

Xuất ảnh vào `figures/` bằng `fig.savefig(..., dpi=200, bbox_inches="tight")` hoặc `fig.write_image` (Plotly); đặt tên `H1_...png` để dễ chèn vào báo cáo.

---

## 7\. Báo cáo (đúng 5 đầu mục của thầy)

Chi tiết tiểu mục nằm trong Google Sheet PTDLNC. Khung:

| Phần | Nội dung | Số trang gợi ý |
| :---- | :---- | :---- |
| Tóm tắt | Kết quả chính trong một trang | 1 |
| 1\. Giới thiệu | Lý do, mục tiêu kinh doanh, mục tiêu phân tích, RQ1–RQ4 | 3 |
| 2\. Mô tả, phân tích tổng quan dữ liệu | Nguồn, cấu trúc, thách thức, khám phá, tương quan | 8 |
| 3\. Phương pháp luận | Sơ đồ quy trình, từng giai đoạn kèm kỹ thuật môn học, bảng ánh xạ kỹ thuật với slide | 5 |
| 4\. Thử nghiệm, kết quả, khuyến nghị | Kết quả RQ1–RQ4, khuyến nghị cho nhà quản lý | 9 |
| 5\. Kết luận | Ưu điểm, đóng góp, hạn chế và lý do, hướng phát triển | 2 |
| Phần 2 | Phân công và mức đóng góp (mức 1–5), link Drive | 1 |

**Định dạng:** bìa theo mẫu UEL, font 13, tối thiểu 20 trang không kể bìa, nộp Word hoặc PDF.

**Câu giải thích ở lần nhắc đầu tiên:**

> SBA (Small Business Administration – Cơ quan Quản lý Doanh nghiệp Nhỏ Hoa Kỳ) bảo lãnh một phần các khoản vay doanh nghiệp nhỏ do ngân hàng thương mại cấp, thông qua chương trình 7(a). Khoản vay được xem là "vỡ nợ" khi bị ngân hàng xóa nợ (trạng thái CHGOFF trong dữ liệu).

**Hạn chế bắt buộc phải nêu ở Chương 5:** chỉ có khoản vay đã được duyệt (thiên lệch chọn mẫu); kiểm duyệt phải của các cohort mới; dữ liệu Hoa Kỳ; quan sát tháng có tự tương quan; mô hình dự báo không suy ra nhân quả; ngưỡng chi phí chỉ là giả định minh họa.

---

## 8\. Thuyết trình 10 phút

| Thời lượng | Nội dung |
| :---- | :---- |
| 1 phút | Vấn đề và câu hỏi nghiên cứu |
| 1,5 phút | Dữ liệu (ba nguồn) và thách thức lớn nhất (kiểm duyệt, rò rỉ) |
| 1,5 phút | Phát hiện chính từ khám phá và kiểm định (RQ1) |
| 1,5 phút | Chuỗi thời gian và dự báo (RQ2) |
| 2,5 phút | Mô hình học máy và giá trị của biến vĩ mô (RQ3, RQ4) |
| 1 phút | Khuyến nghị cho nhà quản lý |
| 1 phút | Hạn chế và hướng phát triển |

**Chuẩn bị hỏi đáp (mỗi người nắm phần của mình):** vì sao chia train/test theo thời gian; vì sao loại một số cột; tại sao dùng PR-AUC; vì sao p-value nhỏ mà vẫn cần effect size; ARIMA khác SARIMA thế nào; mô hình có dùng để quyết định duyệt vay được không (không, vì chỉ có khoản đã được duyệt).

---

## 9\. Checklist trước khi nộp

- [ ] Mọi notebook chạy Run all trên Colab mới, không lỗi.  
- [ ] Không còn cột định danh người vay trong bất kỳ bảng hay hình nào.  
- [ ] Không cột rò rỉ nào nằm trong đặc trưng (có ô kiểm tra tự động `assert` trong notebook 03).  
- [ ] Test chỉ được dùng một lần.  
- [ ] Mỗi kiểm định có effect size; có hiệu chỉnh đa kiểm định.  
- [ ] Mọi biểu đồ có tiêu đề, nhãn trục, chú thích; bubble chart có số.  
- [ ] Mỗi con số trong báo cáo khớp với notebook (nhóm trưởng đối chiếu ngẫu nhiên ít nhất 10 số).  
- [ ] Báo cáo đủ 20 trang, đủ 5 đầu mục, font 13, bìa UEL, bảng đóng góp, link Drive mở được.  
- [ ] Trích dẫn nguồn: SBA (data.sba.gov), McCracken & Ng (2016), NBER.  
- [ ] Đã tập thuyết trình đủ 10 phút.

---

## 10\. Rủi ro và phương án dự phòng

| Rủi ro | Cách xử lý |
| :---- | :---- |
| File SBA nặng, Colab hết RAM | Chỉ đọc cột cần dùng, đọc theo khối, ép kiểu; lọc về khoản vay có nhãn cho ML; dùng Parquet |
| Link tải SBA đổi hoặc hỏng | Dùng bản CSV đã lưu trong `data/raw/` |
| Tên cột khác dự kiến | Sửa ở một nơi duy nhất (danh sách `USECOLS` và mục 2.5 của file này) |
| Mô hình nâng cao không hơn baseline | Báo cáo trung thực; phân tích vì sao (đặc trưng ít, phân phối thay đổi theo thời gian) |
| Cohort mới có nhãn quá ít | Cắt cohort khỏi tập test, nêu lý do |
| Chuỗi thời gian có cú sốc khiến mô hình kém | Thêm cờ suy thoái làm biến ngoại sinh; báo cáo kết quả có và không có giai đoạn sốc |
| Trễ tiến độ | Cắt theo thứ tự ở mục 5 |
| Thầy không chấp nhận phần ML | Giữ chuỗi thời gian và kiểm định làm lõi; chuyển ML thành phần phụ ở Chương 4 |

---

## 11\. Phụ lục: thuật ngữ dùng thống nhất

| Thuật ngữ trong báo cáo | Nghĩa |
| :---- | :---- |
| Vỡ nợ | Khoản vay bị ngân hàng xóa nợ (`LoanStatus = CHGOFF`) |
| Trả đủ | Khoản vay đã tất toán (`LoanStatus = PIF`) |
| Có nhãn | Khoản vay thuộc một trong hai trạng thái trên |
| Cohort | Nhóm khoản vay cùng năm hoặc tháng phê duyệt |
| Kiểm duyệt phải | Khoản vay chưa có kết quả tại thời điểm dữ liệu được xuất |
| Lag 1 tháng | Giá trị của biến vĩ mô ở tháng liền trước tháng phê duyệt |
| Năm tài khóa (FY) | Năm của SBA chạy từ 10 năm trước đến 09 năm đó (FY2000 bắt đầu từ 10/1999) |

