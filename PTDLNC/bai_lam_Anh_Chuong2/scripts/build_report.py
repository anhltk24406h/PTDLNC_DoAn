"""Build the Vietnamese chapter from the notebook's exported evidence tables."""
from pathlib import Path
import json
import re
import pandas as pd
import numpy as np
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

WORK=Path(__file__).resolve().parents[1]
BASE=WORK.parent
TABLES=WORK/'tables'; REPORT=WORK/'report';REPORT.mkdir(exist_ok=True)
META=BASE/'data'/'metadata'
load=lambda name:pd.read_csv(TABLES/(name+'.csv'))
s=json.loads((META/'eda_summary.json').read_text(encoding='utf-8'))
audit=json.loads((META/'pipeline_audit.json').read_text(encoding='utf-8'))
desc=load('B3_mo_ta_dinh_luong').set_index('variable')
missing=load('B4_thieu_du_lieu').set_index('variable')
outliers=load('B7_ngoai_lai').set_index('variable')
cohort=load('B8_cohort').set_index('fy')
business=load('B9_ty_le_BusinessType').set_index('BusinessType')
industry=load('B9_ty_le_NAICS2').set_index('NAICS2')
states=load('B9_ty_le_BorrState').set_index('BorrState')
pearson=load('B13_pearson').set_index('variable')
spearman=load('B14_spearman').set_index('variable')
V=load('B16_cramers_v').set_index('variable')
source='Nguồn: tác giả tính toán từ SBA 7(a), bản chụp ngày 30/06/2026.'
evidence=[]
def f(x,d=0):
    return f'{x:,.{d}f}'.replace(',','_').replace('.',',').replace('_','.')
def pct(x,d=2): return f(x*100,d)+'%'
def fact(key,value,source_file,locator,d=0,percentage=False):
    text=pct(value,d) if percentage else f(value,d)
    evidence.append(dict(fact=key,value=float(value),display=text,source=source_file,locator=locator))
    return text
def total(key):return fact(key,s[key],'data/metadata/eda_summary.json',key)
def stat(var,field,d=2):return fact(var+'.'+field,desc.loc[var,field],'tables/B3_mo_ta_dinh_luong.csv',var+'/'+field,d)
def share(var):return fact(var+'.missing_pct',missing.loc[var,'missing_pct']/100,'tables/B4_thieu_du_lieu.csv',var+'/missing_pct',2,True)
def cohort_pct(year,field):return fact(str(year)+'.'+field,cohort.loc[year,field],'tables/B8_cohort.csv',str(year)+'/'+field,2,True)
blocks=[]
def h(level,text):blocks.append(('h',level,text))
def p(text):blocks.append(('p',text))
def tbl(title,headers,rows,note=source):blocks.append(('table',title,headers,rows,note))
def fig(file,caption,width=16):blocks.append(('fig',file,caption,width))
def page():blocks.append(('page',))

# Page 1: source and schema.
h(1,'Chương 2: Mô tả, phân tích tổng quan về dữ liệu')
h(2,'2.1. Nguồn gốc và mô tả bộ dữ liệu')
h(3,'2.1.1. Nguồn dữ liệu: SBA 7(a) FOIA, bản asof 06/2026, cập nhật hằng quý')
p('SBA (Small Business Administration – Cơ quan Quản lý Doanh nghiệp Nhỏ Hoa Kỳ) cung cấp dữ liệu hành chính cấp khoản vay của chương trình bảo lãnh 7(a). Nghiên cứu sử dụng hai tệp FOIA có trạng thái tại ngày 30/06/2026, lần lượt bao phủ FY2000–FY2009 và FY2010–FY2019 (U.S. Small Business Administration [SBA], 2026a, 2026b). Dữ liệu được công bố theo quý; thời điểm phê duyệt và thời điểm quan sát kết quả vì vậy là hai mốc khác nhau.')
p(f'Tệp thứ nhất có {fact("rows_2000_2009",audit["files"][0]["rows"],"data/metadata/pipeline_audit.json","files[0].rows")} dòng và tệp thứ hai có {fact("rows_2010_2019",audit["files"][1]["rows"],"data/metadata/pipeline_audit.json","files[1].rows")} dòng; tổng cộng {total("n_all")} dòng, mỗi tệp có {audit["files"][0]["raw_columns"]} cột gốc. Ngày phê duyệt thực tế từ 01/10/1999 đến 30/09/2019, tương ứng 240 tháng. FY2000 bắt đầu tháng 10/1999; việc dùng năm dương lịch thay cho FY sẽ làm lệch nhóm quan sát.')
h(3,'2.1.2. Cấu trúc file và nhóm biến: khoản vay, ngân hàng, doanh nghiệp, ngành, địa lý, trạng thái')
tbl('Bảng 2.1. Cấu trúc các nhóm biến sử dụng trong phân tích',
 ['Nhóm','Biến tiêu biểu','Ý nghĩa và lưu ý'],[
 ['Khoản vay','GrossApproval; TermInMonths','Quy mô (USD danh nghĩa), kỳ hạn (tháng).'],
 ['Bảo lãnh','SBAGuaranteedApproval','Số tiền được SBA bảo lãnh, khác tổng tiền vay.'],
 ['Ngân hàng','BankName','Ngân hàng được gán hiện tại; chưa xác nhận là bên duyệt ban đầu.'],
 ['Doanh nghiệp','BusinessType; BusinessAge','Loại hình pháp lý và nhóm tuổi doanh nghiệp.'],
 ['Ngành, địa lý','NaicsCode; BorrState','Ngành hoạt động và bang của người vay.'],
 ['Thời gian, kết quả','ApprovalDate; LoanStatus','Ngày duyệt và trạng thái tại ngày chụp.'],
 ],'Nguồn: tổng hợp từ cấu trúc CSV và từ điển SBA (n.d.). Từ điển chi tiết: Phu_luc_tu_dien_bien.csv.')
p('Chuẩn hóa ApprovalFY → ApprovalFiscalYear và P I F → PIF trước khi tạo nhãn. LocationID là mã ngân hàng, không phải mã khoản vay. Có '+f(sum(x['repeated_row_fingerprints'] for x in audit['files']))+' fingerprint hàng lặp; do thiếu khóa khoản vay, giữ nguyên mọi dòng. Bản mới không có Subprogram; phân tích dùng ProcessingMethod.')
fig('S1_so_do_du_lieu.png','Hình 2.1. Sơ đồ nguồn và liên kết dữ liệu. Nguồn: tác giả xây dựng từ cấu trúc SBA và FRED-MD.',12.5)

# Page 2: target, release-time limitations, macro variables.
page()
h(3,'2.1.3. Biến mục tiêu (LoanStatus: CHGOFF/PIF) và các biến rò rỉ')
p('Trong nghiên cứu này, “vỡ nợ” được định nghĩa vận hành bằng trạng thái xóa nợ CHGOFF, thay vì mọi biểu hiện chậm trả. Biến target nhận 1 khi CHGOFF và 0 khi PIF (trả đủ); EXEMPT, CANCLD và COMMIT không được gán vào lớp trả đủ. is_resolved đánh dấu hai trạng thái có nhãn và không đồng nghĩa mọi trạng thái kết thúc theo nghĩa hành chính đều đã được đưa vào bài toán phân loại (SBA, n.d.).')
p('LoanStatus tạo nhãn nên không được dùng làm đặc trưng. PaidInFullDate, ChargeOffDate và GrossChargeOffAmount phản ánh kết quả sau khi cho vay; FirstDisbursementDate và SoldSecMrktInd cũng không được mặc nhiên coi là thông tin đã biết khi phê duyệt. BankName mô tả ngân hàng đang được gán khoản vay, nên cần kiểm chứng lịch sử trước khi dùng cho dự báo tại thời điểm duyệt. Trong Chương 2, các trường này chỉ phục vụ mô tả, không tạo tập đặc trưng mô hình.')
h(3,'2.1.4. Biến vĩ mô bổ sung từ FRED-MD (ghép theo tháng phê duyệt)')
p('FRED-MD là cơ sở dữ liệu vĩ mô theo tháng được thiết kế để hỗ trợ nghiên cứu thực nghiệm có thể tái lập (McCracken & Ng, 2016). Tệp Fred.csv hiện có khớp SHA-256 với bản chính thức tháng 09/2026: 126 biến và 812 quan sát từ 01/1959 đến 08/2026. Như vậy, 09/2026 là phiên bản phát hành, không phải tháng quan sát cuối (Federal Reserve Bank of St. Louis, 2026).')
tbl('Bảng 2.2. Sáu chỉ tiêu vĩ mô nền và cách biểu diễn',
 ['Chuỗi gốc','Nội dung','Biểu diễn khi ghép'],[
 ['UNRATE','Tỷ lệ thất nghiệp','Mức, %; trễ một tháng.'],
 ['FEDFUNDS','Lãi suất quỹ liên bang','Mức, %; trễ một tháng.'],
 ['T10YFFM','Chênh lệch lãi suất 10 năm – quỹ liên bang','Mức, điểm %; trễ một tháng.'],
 ['CPIAUCSL','Chỉ số giá tiêu dùng','Tăng trưởng so cùng kỳ, %.'],
 ['INDPRO','Chỉ số sản xuất công nghiệp','Tăng trưởng so cùng kỳ, %.'],
 ['BUSLOANS','Dư nợ cho vay thương mại, công nghiệp','Tăng trưởng so cùng kỳ, %.'],
 ],'Nguồn: FRED-MD (Federal Reserve Bank of St. Louis, 2026); cách biến đổi do tác giả quy định cho bài toán.')
p('Dòng Transform: được tách thành bảng mã biến đổi, không được tính là quan sát. CPI, sản xuất công nghiệp và dư nợ được đổi sang 100 × (Xₜ/Xₜ₋₁₂ − 1) trước khi cắt giai đoạn. Sau đó, sáu chỉ tiêu được dịch một tháng và liên kết nhiều–một với approval_month. Kiểm tra cho thấy đủ 240 tháng, không thiếu giá trị trong cửa sổ ghép và số khoản vay không tăng sau liên kết.')
p('Độ trễ này giảm khả năng dùng số liệu cùng tháng chưa công bố, nhưng không tái lập đầy đủ tập thông tin ngân hàng từng có. Lịch công bố khác nhau và phiên bản 2026 chứa số liệu lịch sử đã điều chỉnh. Do đó, phân tích mang tính hồi cứu; không thể tuyên bố đã loại hết sai lệch nhìn trước chỉ bằng lag một tháng.')

# Page 3: data quality.
page()
h(2,'2.2. Thách thức của bộ dữ liệu')
h(3,'2.2.1. Giá trị thiếu')
p('Giá trị thiếu tập trung không đồng đều giữa các biến. Bảng 2.3 cho thấy cần phân biệt thiếu thông tin nền với thiếu có điều kiện theo trạng thái; chẳng hạn, ngày xóa nợ thường không áp dụng cho khoản không bị xóa nợ. Bởi vậy, không thể đánh giá chất lượng dữ liệu chỉ bằng tỷ lệ ô trống chung hoặc bù tất cả ô trống bằng cùng một quy tắc.')
missvars=['FranchiseCode','ChargeOffDate','SoldSecMrktInd','InitialInterestRate','NaicsCode']
tbl('Bảng 2.3. Một số trường có dữ liệu thiếu đáng chú ý',['Biến','Số thiếu','Tỷ lệ trên toàn mẫu'],
 [[v,f(missing.loc[v,'missing_n']),share(v)] for v in missvars])
p('InitialInterestRate thiếu hoàn toàn trong FY2000–FY2008, trong khi FY2010–FY2019 có dữ liệu đầy đủ cho biến này. Thiếu dữ liệu vì thế gắn với thời gian quan sát; bù một giá trị trung bình chung có thể che khuất sự thay đổi phạm vi thu thập. FranchiseCode trống cũng không tự chứng minh doanh nghiệp không nhượng quyền. BusinessAge còn có nhóm Unanswered; đây là thiếu thông tin về mặt nội dung dù không phải ô rỗng. Chưa có căn cứ để khẳng định cơ chế MCAR, MAR hoặc MNAR.')
h(3,'2.2.2. Ngoại lai: khoản vay rất lớn, kỳ hạn bất thường')
p('Quy tắc IQR đánh dấu quan sát ngoài [Q1 − 1,5IQR; Q3 + 1,5IQR]. Đây là tiêu chí rà soát phân phối, không phải quy tắc xác nhận sai dữ liệu. Tiền vay có độ lệch phải và quy mô kinh tế khác nhau, nên loại tự động các khoản lớn sẽ làm thay đổi đối tượng nghiên cứu.')
tbl('Bảng 2.4. Quan sát cần rà soát theo quy tắc IQR',['Biến','Ngưỡng trên','Số vượt khoảng IQR','Giá trị lớn nhất'],
 [[v,f(outliers.loc[v,'upper_fence'],1),f(outliers.loc[v,'outside_iqr_n']),f(outliers.loc[v,'maximum'])]
 for v in ['GrossApproval','TermInMonths','JobsSupported']])
p(f'Kỳ hạn lớn nhất là {stat("TermInMonths","max",0)} tháng; có {total("zero_term_n")} khoản ghi 0 tháng và {total("term_gt_300_n")} khoản trên 300 tháng. Những giá trị này cần đối chiếu hồ sơ, không tự kết luận vi phạm quy định. JobsSupported có {total("zero_jobs_n")} quan sát bằng 0 và cực đại {stat("JobsSupported","max",0)}. SBA (n.d.) xác định đây là ước lượng việc làm tạo mới cộng duy trì do bên cho vay tự báo cáo, chưa được SBA kiểm chứng; không thể diễn giải thành số việc làm thực tế đã tạo ra. EDA giữ nguyên dữ liệu và dùng log1p cho hình phân phối tiền vay.')

# Page 4: imbalance and censoring.
page()
h(3,'2.2.3. Mất cân bằng lớp (xóa nợ là thiểu số)')
p(f'Tập có nhãn gồm {total("n_pif")} khoản trả đủ và {total("n_chgoff")} khoản xóa nợ, tương ứng {fact("chgoff_rate",s["chgoff_rate"],"data/metadata/eda_summary.json","chgoff_rate",2,True)} xóa nợ. Tỷ số số khoản trả đủ trên xóa nợ là {f(s["n_pif"]/s["n_chgoff"],2)} lần. Đây là bằng chứng về mất cân bằng lớp; việc đánh giá mô hình sau này cần xem xét khả năng phát hiện lớp xóa nợ bên cạnh độ chính xác chung. Chương này không tái lấy mẫu hoặc thay đổi tỷ trọng lớp.')
h(3,'2.2.4. Khoản vay chưa có kết quả (kiểm duyệt phải) và rò rỉ dữ liệu')
p(f'Ngoài tập có nhãn, dữ liệu chứa {f(s["n_status"]["CANCLD"])} khoản CANCLD (hủy), {f(s["n_status"]["EXEMPT"])} khoản EXEMPT và {f(s["n_status"]["COMMIT"])} khoản COMMIT (chưa giải ngân). Theo SBA (n.d.), EXEMPT là khoản đã giải ngân nhưng chưa hủy, trả đủ hoặc xóa nợ, với một số thông tin được miễn công bố. Vì vậy, không đồng nhất trạng thái hủy với việc đang tiếp tục theo dõi kết quả.')
fig('H2_kiem_duyet_theo_fy.png','Hình 2.2 (H2). Tỷ lệ có kết quả và cơ cấu trạng thái theo FY. Mẫu số: toàn bộ khoản vay từng FY.',16)
p(f'Tỷ lệ có nhãn giảm từ {cohort_pct(2000,"resolved_rate")} ở FY2000 xuống {cohort_pct(2019,"resolved_rate")} ở FY2019; riêng tỷ trọng EXEMPT của FY2019 đạt {cohort_pct(2019,"exempt_share")}. Hình 2.2 cho thấy thời gian theo dõi giữa các cohort không tương đương. Tỷ lệ xóa nợ trên các khoản đã có kết quả vì thế có thể bị chọn lọc theo thời gian kết thúc; hướng và mức thiên lệch không thể xác định chỉ từ đồ thị. Đây là vấn đề quan sát chưa đầy đủ cần được phân biệt trong phân tích thời gian đến sự kiện (Kaplan & Meier, 1958).')
h(3,'2.2.5. Chỉ có khoản vay đã được duyệt (thiên lệch chọn mẫu) và thông tin định danh cần loại bỏ')
p('Mẫu không bao gồm hồ sơ bị từ chối, nên kết quả chỉ mô tả khoản vay đã được SBA phê duyệt; không suy rộng trực tiếp sang mọi doanh nghiệp xin vay. Tên, địa chỉ, thành phố, ZIP của người vay và mã định danh không được đưa vào dữ liệu xử lý hoặc đầu ra notebook. Bang được giữ ở mức tổng hợp. CSV gốc được lưu riêng để tái lập và không dùng làm bảng minh họa trong báo cáo.')

# Page 5: quantitative and categorical profiles.
page()
h(2,'2.3. Khám phá dữ liệu')
h(3,'2.3.1. Phân tích mô tả: biến định lượng (GrossApproval, TermInMonths, JobsSupported...); biến định tính (BusinessType, Subprogram, ngành, bang)')
p('Bảng 2.5 mô tả toàn bộ khoản vay với số quan sát hợp lệ theo từng biến; các khoản chưa có nhãn vẫn được giữ. Bản 30/06/2026 không có Subprogram; thống kê phương thức cho vay dùng ProcessingMethod, không tự tạo cột Subprogram. Tiền vay là USD danh nghĩa, chưa điều chỉnh lạm phát; biến động quy mô tiền tệ không được tự diễn giải thành thay đổi sức mua tương ứng.')
tbl('Bảng 2.5. Thống kê mô tả các biến định lượng chính', ['Biến','Trung bình','ĐLC','Trung vị','Q1–Q3'],
 [[{'GrossApproval':'Tiền vay (USD)','SBAGuaranteedApproval':'Bảo lãnh (USD)','TermInMonths':'Kỳ hạn (tháng)','JobsSupported':'Việc làm (ước lượng)'}[v],
   f(desc.loc[v,'mean'],2),f(desc.loc[v,'std'],2),f(desc.loc[v,'50%']),f(desc.loc[v,'25%'])+'–'+f(desc.loc[v,'75%'])]
  for v in ['GrossApproval','SBAGuaranteedApproval','TermInMonths','JobsSupported']],
 source+f' ĐLC: độ lệch chuẩn mẫu. N = {f(s["n_all"])}, riêng JobsSupported có N = {f(desc.loc["JobsSupported","count"])}.')
p(f'GrossApproval có trung bình {stat("GrossApproval","mean")} USD, cao hơn trung vị {stat("GrossApproval","50%",0)} USD; độ lệch {stat("GrossApproval","skewness",2)} phù hợp với đuôi phải dài. Khoảng tứ phân vị từ {stat("GrossApproval","25%",0)} đến {stat("GrossApproval","75%",0)} USD thể hiện sự không đồng nhất đáng kể về quy mô tài trợ. Vì vậy, trung vị và tứ phân vị bổ sung thông tin cần thiết cho trung bình.')
p(f'Kỳ hạn trung vị là {stat("TermInMonths","50%",0)} tháng, trong khi việc làm ước lượng trung vị là {stat("JobsSupported","50%",0)}. Lãi suất đầu kỳ chỉ có {stat("InitialInterestRate","count",0)} quan sát hợp lệ; số trung bình {stat("InitialInterestRate","mean")} phần trăm của biến này không đại diện đồng đều cho toàn bộ giai đoạn. Các thống kê tần số chi tiết và nhóm thiếu được lưu riêng để tránh đánh đồng mẫu số giữa các bảng.')
p('Về loại hình pháp lý, CORPORATION chiếm '+pct(business.loc['CORPORATION','n_all']/s['n_all'])+', INDIVIDUAL chiếm '+pct(business.loc['INDIVIDUAL','n_all']/s['n_all'])+' và PARTNERSHIP chiếm '+pct(business.loc['PARTNERSHIP','n_all']/s['n_all'])+' toàn mẫu. Nhãn được giữ theo dữ liệu gốc, tránh quy đổi tùy ý sang loại hình pháp lý của Việt Nam. Với NAICS, các dải 31–33, 44–45 và 48–49 được gộp theo nhóm ngành; '+f(s['n_naics_missing_or_invalid'])+' khoản thiếu hoặc không có mã hợp lệ không được gán ngành suy đoán.')
tbl('Bảng 2.6. Tỷ lệ xóa nợ theo loại hình doanh nghiệp', ['Nhóm','Có nhãn','Xóa nợ','Tỷ lệ','KTC Wilson 95%'],
 [[v,f(business.loc[v,'n_resolved']),f(business.loc[v,'n_chgoff']),pct(business.loc[v,'rate']),
   pct(business.loc[v,'ci_low'])+'–'+pct(business.loc[v,'ci_high'])] for v in ['CORPORATION','INDIVIDUAL','PARTNERSHIP']],
 source+' Mẫu số là PIF + CHGOFF trong từng nhóm; nhóm thiếu được giữ trong bảng đầy đủ B9.')
p('INDIVIDUAL có tỷ lệ xóa nợ quan sát cao hơn hai nhóm còn lại, nhưng chênh lệch này chưa kiểm soát cơ cấu ngành, thời gian phê duyệt hoặc độ dài theo dõi. Khoảng Wilson (Wilson, 1927) chỉ mô tả độ bất định nhị thức với giả định độc lập; chưa điều chỉnh phụ thuộc theo tháng hoặc ngân hàng, và không phải bằng chứng nhân quả.')

# Pages 6–7: all mandatory plots and substantive interpretation.
page()
h(3,'2.3.2. Trực quan hóa tổng quan: xu hướng theo năm, bản đồ theo bang, bubble theo ngành (mỗi bubble ghi số), violin/box')
fig('H1_so_khoan_vay_theo_fy.png','Hình 2.3 (H1). Số khoản vay phê duyệt theo năm tài khóa. Mẫu: tất cả khoản vay trong phạm vi nghiên cứu.',16)
peak=int(cohort.n_all.idxmax())
p(f'Số khoản vay đạt cao nhất ở FY{peak}, với {fact("peak_fy_n",cohort.loc[peak,"n_all"],"tables/B8_cohort.csv",str(peak)+"/n_all")} khoản, sau đó giảm xuống {fact("fy2009_n",cohort.loc[2009,"n_all"],"tables/B8_cohort.csv","2009/n_all")} ở FY2009. Hình 2.3 phản ánh thay đổi số lượng phê duyệt; riêng diễn biến này chưa đủ tách tác động của nhu cầu tín dụng, chính sách chương trình và điều kiện kinh tế. Phân tích chuỗi thời gian thuộc phần nghiên cứu tiếp theo.')
fig('H3_ban_do_bang.png','Hình 2.4 (H3). Bản đồ tỷ lệ xóa nợ theo BorrState. Tỷ lệ chỉ tính trên khoản có nhãn; hình học nền từ Plotly/Natural Earth.',15)
p('Florida có tỷ lệ xóa nợ '+pct(states.loc['FL','rate'])+' trên '+f(states.loc['FL','n_resolved'])+' khoản có nhãn, so với '+pct(states.loc['CA','rate'])+' trên '+f(states.loc['CA','n_resolved'])+' khoản tại California. Màu bản đồ thể hiện tỷ lệ, không phải số lượng khoản vay hoặc mức tổn thất tiền tệ. Lãnh thổ và mã địa lý ngoài lớp bản đồ được lưu ở bảng riêng; không gán tỷ lệ 0 cho địa bàn không có dữ liệu tính được.')
page()
p('Trực quan hóa tổng quan (tiếp theo)')
fig('H4_bubble_nganh.png','Hình 2.5 (H4). Quy mô, tỷ lệ xóa nợ và số khoản vay theo ngành. Mỗi bubble ghi mã ngành và số khoản vay.',16)
p('Bán lẻ (44–45) có '+f(industry.loc['44–45','n_all'])+' khoản vay và tỷ lệ xóa nợ '+pct(industry.loc['44–45','rate'])+' trên khoản có nhãn; y tế và trợ giúp xã hội (62) có '+f(industry.loc['62','n_all'])+' khoản với tỷ lệ '+pct(industry.loc['62','rate'])+'. Trục hoành dùng quy mô trung bình của tất cả khoản vay trong ngành, còn trục tung dùng tập có nhãn. Sự khác biệt mẫu số được giữ minh bạch để tránh diễn giải sai vị trí các nhóm.')
p('Nhóm hành chính công (92) có tỷ lệ '+pct(industry.loc['92','rate'])+' nhưng chỉ '+f(industry.loc['92','n_resolved'])+' khoản có nhãn; khoảng Wilson từ '+pct(industry.loc['92','ci_low'])+' đến '+pct(industry.loc['92','ci_high'])+'. Vì vậy, không nên xếp hạng ngành chỉ theo tỷ lệ điểm mà bỏ qua quy mô và độ bất định. Mã NAICS được diễn giải ở cấp ngành rộng; chưa thực hiện quy đổi đầy đủ giữa mọi phiên bản hệ thống ngành qua thời gian.')
fig('H5_box_quy_mo_theo_nhan.png','Hình 2.6 (H5). Boxplot ln(1 + GrossApproval) theo nhãn. Dùng toàn bộ khoản có nhãn, ẩn điểm ngoài râu khi vẽ.',14)
p('Phép log1p làm giảm chênh lệch thị giác giữa các khoản nhỏ và lớn; không thay đổi dữ liệu gốc hoặc tự loại ngoại lai. Hình 2.6 cho phép so sánh vị trí và độ phân tán giữa hai nhóm, nhưng mức độ chồng lấn của phân phối cần được giữ trong diễn giải. Không kết luận tiền vay gây xóa nợ hoặc thay thế kiểm định nhóm bằng quan sát hình.')

# Page 8: correlations.
page()
h(3,"2.3.3. Phân tích tương quan: heatmap, Pearson vs Spearman, Cramér's V, tỷ lệ xóa nợ theo nhóm")
p('Pearson đo liên hệ tuyến tính trên thang gốc, còn Spearman đo liên hệ theo thứ hạng, phù hợp để đối chiếu khi phân phối lệch (Pearson, 1895; Spearman, 1904). Thiếu được loại theo từng cặp; các cặp có lãi suất chỉ dùng cửa sổ dữ liệu có thông tin. Không coi mã ngành hoặc mã bang là đại lượng liên tục.')
fig('H6a_tuong_quan_so.png','Hình 2.7 (H6a). Pearson và Spearman giữa các biến định lượng; số quan sát theo cặp được lưu ở B15.',15)
p('GrossApproval và SBAGuaranteedApproval có Pearson '+fact('r_gross_guarantee',pearson.loc['GrossApproval','SBAGuaranteedApproval'],'tables/B13_pearson.csv','GrossApproval/SBAGuaranteedApproval',3)+'; đây là liên hệ phù hợp với cấu trúc phần bảo lãnh thuộc khoản vay. Với JobsSupported, Pearson là '+fact('r_gross_jobs',pearson.loc['GrossApproval','JobsSupported'],'tables/B13_pearson.csv','GrossApproval/JobsSupported',3)+' và Spearman là '+fact('rho_gross_jobs',spearman.loc['GrossApproval','JobsSupported'],'tables/B14_spearman.csv','GrossApproval/JobsSupported',3)+'. Sự khác nhau giữa hai hệ số cho thấy thang đo và các giá trị lớn ảnh hưởng đến cách mô tả liên hệ; không tự xác định nguyên nhân của khác biệt.')
fig('H6b_cramers_v.png',"Hình 2.8 (H6b). Cramér’s V chuẩn giữa các biến phân loại. LoanStatus gồm cả năm trạng thái, không phải riêng target nhị phân.",10)
p('Cramér’s V nằm trong [0; 1] và không biểu diễn chiều liên hệ (Cramér, 1946). ProcessingMethod–LoanStatus có V = '+fact('V_method_status',V.loc['ProcessingMethod','LoanStatus'],'tables/B16_cramers_v.csv','ProcessingMethod/LoanStatus',3)+', trong khi BusinessType–LoanStatus có V = '+fact('V_business_status',V.loc['BusinessType','LoanStatus'],'tables/B16_cramers_v.csv','BusinessType/LoanStatus',3)+'. Không dùng ngưỡng cứng hoặc p-value để gọi các liên hệ này là quyết định rủi ro. Các bảng tỷ lệ nhóm bổ sung hướng khác biệt, nhưng vẫn chịu giới hạn cohort, chọn mẫu và quan sát chưa đầy đủ.')

references=[
 'Cramér, H. (1946). *Mathematical methods of statistics (PMS-9)*. Princeton University Press. https://doi.org/10.1515/9781400883868',
 'Federal Reserve Bank of St. Louis. (2026). *FRED-MD: Monthly database for macroeconomic research* (September 2026 vintage) [Data set]. https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md/monthly/2026-09-md.csv',
 'Kaplan, E. L., & Meier, P. (1958). Nonparametric estimation from incomplete observations. *Journal of the American Statistical Association, 53*(282), 457–481. https://doi.org/10.1080/01621459.1958.10501452',
 'McCracken, M. W., & Ng, S. (2016). FRED-MD: A monthly database for macroeconomic research. *Journal of Business & Economic Statistics, 34*(4), 574–589. https://doi.org/10.1080/07350015.2015.1086655',
 'Pearson, K. (1895). Note on regression and inheritance in the case of two parents. *Proceedings of the Royal Society of London, 58*, 240–242. https://doi.org/10.1098/rspl.1895.0041',
 'Spearman, C. (1904). The proof and measurement of association between two things. *The American Journal of Psychology, 15*(1), 72–101. https://doi.org/10.2307/1412159',
 'U.S. Small Business Administration. (n.d.). *7(a) and 504 FOIA data dictionary* [Data dictionary]. Retrieved October 20, 2026, from https://data.sba.gov/sites/default/files/uploaded_resources/7a_504_foia_data_dictionary.xlsx',
 'U.S. Small Business Administration. (2026a). *FOIA 7(a), FY2000–FY2009, as of June 30, 2026* [Data set]. https://data.sba.gov/sites/default/files/uploaded_resources/FOIA_7a_FY2000_FY2009_asof_260630.csv',
 'U.S. Small Business Administration. (2026b). *FOIA 7(a), FY2010–FY2019, as of June 30, 2026* [Data set]. https://data.sba.gov/sites/default/files/uploaded_resources/FOIA_7a_FY2010_FY2019_asof_260630.csv',
 'Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association, 22*(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953',
]
page();h(2,'Tài liệu tham khảo')
for ref in references:blocks.append(('ref',ref))
(REPORT/'Tai_lieu_tham_khao.md').write_text('# Tài liệu tham khảo\n\n'+'\n\n'.join(references)+'\n',encoding='utf-8')

# Detailed variable dictionary, including source names, types, and approval-time caveats.
definitions=pd.read_excel(BASE/'data/raw/7a_504_foia_data_dictionary.xlsx',sheet_name=0)
defs=dict(definitions.iloc[:,:2].itertuples(index=False,name=None))
loans=pd.read_parquet(BASE/'data/processed/loans_clean.parquet')
role={
 'AsOfDate':('Thời gian','Ngày chụp','Ngày','metadata; không phải đặc trưng'),
 'Program':('Chương trình','Chương trình SBA','Danh mục','Mô tả; chỉ 7(a)'),
 'BorrState':('Địa lý','Bang người vay','Danh mục','Địa lý tổng hợp tại hồ sơ'),
 'BankName':('Ngân hàng','Ngân hàng đang được gán','Danh mục','Chỉ mô tả; chưa xác nhận tại lúc phê duyệt'),
 'GrossApproval':('Khoản vay','Tổng tiền phê duyệt','USD danh nghĩa','Thông tin phê duyệt'),
 'SBAGuaranteedApproval':('Khoản vay','Số tiền bảo lãnh SBA','USD danh nghĩa','Thông tin phê duyệt'),
 'ApprovalDate':('Thời gian','Ngày phê duyệt','Ngày','Thông tin phê duyệt'),
 'ApprovalFiscalYear':('Thời gian','Năm tài khóa phê duyệt','FY','Thông tin phê duyệt'),
 'FirstDisbursementDate':('Thời gian','Ngày giải ngân đầu tiên','Ngày','Sau phê duyệt; mặc định loại khỏi đặc trưng'),
 'ProcessingMethod':('Chương trình','Phương thức xử lý','Danh mục','Phương thức phê duyệt'),
 'Subprogram':('Chương trình','Tiểu chương trình','Danh mục','Có trong CSV; không có mục tương ứng trong từ điển hiện tại'),
 'InitialInterestRate':('Khoản vay','Lãi suất ban đầu','%','Tại phê duyệt; thiếu có hệ thống theo FY'),
 'FixedorVariableInterestInd':('Khoản vay','Lãi suất cố định/biến đổi','Danh mục','Cần kiểm chứng thời điểm trước khi mô hình hóa'),
 'TermInMonths':('Khoản vay','Kỳ hạn','Tháng','Giá trị trong hồ sơ; cần rà soát bất thường'),
 'NaicsCode':('Ngành','Mã NAICS','Danh mục','Mã ngành; lưu dạng chuỗi'),
 'NaicsDescription':('Ngành','Mô tả ngành','Văn bản','Mô tả ngành; tránh dùng mã như biến số'),
 'FranchiseCode':('Doanh nghiệp','Mã nhượng quyền','Danh mục','Ô trống chưa đủ để xác nhận không nhượng quyền'),
 'BusinessType':('Doanh nghiệp','Loại hình pháp lý','Danh mục','Giữ nhóm gốc; chưa tự quy đổi theo pháp luật Việt Nam'),
 'BusinessAge':('Doanh nghiệp','Nhóm tuổi doanh nghiệp','Danh mục','Thời điểm tham chiếu chưa nêu rõ; cần xác minh'),
 'LoanStatus':('Kết quả','Trạng thái hiện tại','Danh mục','Tạo nhãn; cấm dùng làm đặc trưng dự báo'),
 'PaidInFullDate':('Kết quả','Ngày trả đủ','Ngày','Kết quả sau vay; cấm dùng làm đặc trưng'),
 'ChargeOffDate':('Kết quả','Ngày xóa nợ','Ngày','Kết quả sau vay; cấm dùng làm đặc trưng'),
 'GrossChargeOffAmount':('Kết quả','Dư nợ xóa nợ gồm phần bảo lãnh và không bảo lãnh','USD danh nghĩa','Kết quả sau vay; cấm dùng làm đặc trưng'),
 'JobsSupported':('Doanh nghiệp','Việc làm tạo mới và duy trì ước lượng','Số việc làm','Tự báo cáo trên hồ sơ; SBA không kiểm chứng'),
 'ProjectState':('Địa lý','Bang dự án','Danh mục','Không thay thế BorrState trong bản đồ người vay'),
 'RevolverStatus':('Khoản vay','0=kỳ hạn; 1=hạn mức quay vòng','Danh mục','Giữ mã gốc'),
 'CollateralInd':('Khoản vay','Chỉ báo tài sản bảo đảm do bên cho vay báo cáo','Danh mục','Thời điểm cập nhật chưa nêu rõ; cần xác minh'),
 'SoldSecMrktInd':('Sau phê duyệt','Đã bán trên thị trường thứ cấp','Danh mục','Có thể thay đổi sau phê duyệt; mặc định loại'),
 'source_file':('Nguồn','Tên file nguồn','Văn bản','Dẫn xuất; truy xuất nguồn'),
 'fy':('Thời gian','Năm tài khóa chuẩn hóa','FY','Dẫn xuất từ ApprovalFiscalYear'),
 'approval_month':('Thời gian','Tháng phê duyệt, ngày đầu tháng','Tháng','Dẫn xuất từ ApprovalDate'),
 'is_resolved':('Nhãn','Thuộc PIF hoặc CHGOFF','Boolean','Dẫn xuất từ kết quả; không phải đặc trưng'),
 'target':('Nhãn','1=CHGOFF; 0=PIF; còn lại thiếu','Nhị phân nullable','Nhãn; không phải đặc trưng'),
}
raw_header=audit['files'][0]['raw_header']
raw_names={name.lower():name for name in raw_header}
records=[]
for c in loans.columns:
    group,meaning,unit,timing=role[c]
    original='ApprovalFY' if c=='ApprovalFiscalYear' else c
    records.append(dict(variable=c,raw_column=raw_names.get(original.lower(),'(derived)'),
                        group=group,meaning_vi=meaning,dtype=str(loans[c].dtype),unit=unit,role_timing=timing,
                        official_definition=defs.get(original,'Not supplied in current dictionary; see role_timing')))
pd.DataFrame(records).to_csv(TABLES/'Phu_luc_tu_dien_bien.csv',index=False,encoding='utf-8-sig')

doc=Document();section=doc.sections[0]
section.page_height=Cm(29.7);section.page_width=Cm(21)
section.top_margin=Cm(1.8);section.bottom_margin=Cm(1.8);section.left_margin=Cm(2);section.right_margin=Cm(2)
normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(13)
normal.paragraph_format.space_after=Pt(5);normal.paragraph_format.line_spacing=1.05
for name,size in [('Heading 1',15),('Heading 2',13),('Heading 3',13)]:
    style=doc.styles[name];style.font.name='Times New Roman';style.font.size=Pt(size);style.font.bold=True
    style.font.color.rgb=RGBColor.from_string('123C4A')
    style.paragraph_format.space_before=Pt(5);style.paragraph_format.space_after=Pt(4)
header=section.header.paragraphs[0];header.text='PTDLNC  |  Chương 2  |  Anh'
header.style=doc.styles['Normal'];header.runs[0].font.size=Pt(9)
footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=footer.add_run();field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');r._r.addnext(field)
doc.core_properties.title='Chương 2: Mô tả, phân tích tổng quan về dữ liệu'
doc.core_properties.author='Anh'
def inline(paragraph,text):
    for part in re.split(r'(\*\*.*?\*\*|\*[^*]+\*)',str(text)):
        r=paragraph.add_run(part.strip('*') if part.startswith('*') else part)
        if part.startswith('**'):r.bold=True
        elif part.startswith('*'):r.italic=True
def avoid_split(row):
    prop=row._tr.get_or_add_trPr();prop.append(OxmlElement('w:cantSplit'))
markdown=[]
for block in blocks:
    kind=block[0]
    if kind=='h':
        _,level,text=block;doc.add_heading(text,level=level);markdown.extend(['#'*level+' '+text,''])
    elif kind in ['p','ref']:
        paragraph=doc.add_paragraph();inline(paragraph,block[1]);paragraph.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
        if kind=='ref':
            paragraph.alignment=WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.left_indent=Cm(.75);paragraph.paragraph_format.first_line_indent=Cm(-.75)
        markdown.extend([block[1],''])
    elif kind=='page':
        doc.add_page_break();markdown.extend(['<!-- Ngắt trang bản Word -->',''])
    elif kind=='fig':
        _,file,caption,width=block
        paragraph=doc.add_paragraph();paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run().add_picture(str(WORK/'figures'/file),width=Cm(width))
        paragraph.paragraph_format.space_after=Pt(0)
        cap=doc.add_paragraph();inline(cap,caption);cap.alignment=WD_ALIGN_PARAGRAPH.CENTER
        for run in cap.runs:run.font.size=Pt(10);run.italic=True
        markdown.extend([f'![{caption}](../figures/{file})','',f'*{caption}*',''])
    elif kind=='table':
        _,title,headers,rows,note=block
        caption=doc.add_paragraph();caption.paragraph_format.keep_with_next=True;inline(caption,'**'+title+'**')
        t=doc.add_table(rows=1,cols=len(headers));t.style='Table Grid'
        for cell,text in zip(t.rows[0].cells,headers):
            cell.text=str(text)
            for run in cell.paragraphs[0].runs:run.bold=True
        for row in rows:
            for cell,text in zip(t.add_row().cells,row):cell.text=str(text)
        if title.startswith('Bảng 2.1.'):
            t.autofit=False
            for row in t.rows:
                for cell,width in zip(row.cells,[2.6,5.3,9.1]):cell.width=Cm(width)
        for row in t.rows:
            avoid_split(row)
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after=Pt(1);paragraph.paragraph_format.line_spacing=1
                    for run in paragraph.runs:run.font.name='Times New Roman';run.font.size=Pt(11)
        headerprop=t.rows[0]._tr.get_or_add_trPr();headerprop.append(OxmlElement('w:tblHeader'))
        notepara=doc.add_paragraph(note)
        for run in notepara.runs:run.font.size=Pt(10);run.italic=True
        markdown.extend(['**'+title+'**','', '| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |'])
        for row in rows:markdown.append('| '+' | '.join(map(str,row))+' |')
        markdown.extend(['','*'+note+'*',''])
doc.save(REPORT/'Chuong_2.docx')
(REPORT/'Chuong_2.md').write_text('\n'.join(markdown),encoding='utf-8')
pd.DataFrame(evidence).to_csv(TABLES/'Doi_chieu_so_lieu_bao_cao.csv',index=False,encoding='utf-8-sig',float_format='%.15g')
save={'n_evidence_facts':len(evidence),'data_source':'Full data, not a sample','planned_main_pages':8,
      'actual_pagination':'Not yet measured in Word','reference_count':len(references)}
(META/'report_build.json').write_text(json.dumps(save,ensure_ascii=False,indent=2),encoding='utf-8')
print('Built Word and Markdown;',len(evidence),'traceable numerical facts;',len(references),'references.')
