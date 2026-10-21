"""Document the user-authorized replacement snapshot without mixing vintages."""
from pathlib import Path
import json
import shutil
import pandas as pd

BASE=Path(__file__).resolve().parents[2]
WORK=BASE/'bai_lam_Anh_Chuong2';META=BASE/'data/metadata'
ARCHIVE=BASE/'archive/chuong2_260331_truoc_cap_nhat_260630'
summary=json.loads((META/'eda_summary.json').read_text(encoding='utf-8'))
old=json.loads((ARCHIVE/'data/metadata/eda_summary.json').read_text(encoding='utf-8'))
audit=json.loads((META/'pipeline_audit.json').read_text(encoding='utf-8'))
cohort=pd.read_csv(WORK/'tables/B8_cohort.csv').set_index('fy')
oldcohort=pd.read_csv(ARCHIVE/'bai_lam_Anh_Chuong2/tables/B8_cohort.csv').set_index('fy')
f=lambda x,d=0:f'{x:,.{d}f}'.replace(',','_').replace('.',',').replace('_','.')
pct=lambda x:f(x*100,2)+'%'

# Retire one generated table which no longer has a source field. Check resolved paths first.
obsolete=(WORK/'tables/B9_ty_le_Subprogram.csv').resolve()
target=(ARCHIVE/'retired_outputs/B9_ty_le_Subprogram.csv').resolve()
assert obsolete.is_relative_to(BASE.resolve()) and target.is_relative_to(ARCHIVE.resolve())
if obsolete.exists():
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists()
    shutil.move(str(obsolete),str(target))

rows=[]
labels={'n_all':'Tổng số dòng khoản vay','n_resolved':'Khoản có nhãn (PIF + CHGOFF)',
        'n_pif':'Trả đủ (PIF)','n_chgoff':'Xóa nợ (CHGOFF)','chgoff_rate':'Tỷ lệ xóa nợ trên khoản có nhãn',
        'term_gt_300_n':'Số khoản có kỳ hạn trên 300 tháng','processed_columns':'Số cột trong loans_clean'}
for key,label in labels.items():
    rows.append({'metric':label,'key':key,'old_value':old[key],'new_value':summary[key],
                 'change':summary[key]-old[key], 'unit':'proportion' if key=='chgoff_rate' else 'count'})
for key in ['EXEMPT','CANCLD','COMMIT']:
    rows.append({'metric':'Trạng thái '+key,'key':key,'old_value':old['n_status'][key],
                 'new_value':summary['n_status'][key],
                 'change':summary['n_status'][key]-old['n_status'][key],'unit':'count'})
rows.append({'metric':'Tỷ lệ có nhãn FY2019','key':'fy2019_resolved_rate',
             'old_value':oldcohort.loc[2019,'resolved_rate'],'new_value':cohort.loc[2019,'resolved_rate'],
             'change':cohort.loc[2019,'resolved_rate']-oldcohort.loc[2019,'resolved_rate'],'unit':'proportion'})
comparison=pd.DataFrame(rows)
comparison.to_csv(WORK/'tables/So_sanh_hai_phien_ban_FOIA.csv',index=False,encoding='utf-8-sig',float_format='%.15g')
body=['# Cập nhật Chương 2 theo FOIA 30/06/2026','',
      'Cập nhật ngày 21/10/2026 theo hai CSV thay thế do bạn cung cấp. Không trộn dữ liệu hai ngày chụp và không tải lại bản cũ. Bản bài làm trước được giữ tại `../../archive/chuong2_260331_truoc_cap_nhat_260630/`.',
      '', '## Những thay đổi cấu trúc','',
      '- Ngày chụp chuyển từ 31/03/2026 sang 30/06/2026; phạm vi phê duyệt vẫn FY2000–FY2019.',
      '- Mỗi CSV mới có 42 cột CamelCase thay vì 43 cột chữ thường; không còn Subprogram. Không suy diễn Subprogram từ ProcessingMethod. Bảng Subprogram cũ được chuyển vào bản lưu lịch sử; heatmap Cramér’s V hiện chỉ có các trường thực sự tồn tại.',
      '- Ngày dạng ISO YYYY-MM-DD được đọc tường minh; ApprovalFY ánh xạ thành ApprovalFiscalYear.',
      f'- Chuẩn hóa {f(sum(x["status_normalized_rows"] for x in audit["files"]))} trạng thái P I F thành PIF trước khi tạo nhãn; lưu số đếm mã gốc trong pipeline_audit.json.',
      '- Kiểm tra ngày chụp ở mọi dòng. Cache Parquet chỉ dùng lại khi ngày chụp và SHA-256 của từng CSV khớp với cấu hình; notebook EDA cũng kiểm tra phiên bản trước khi đọc.',
      '- SHA-256 mô tả các tệp bạn cung cấp. URL chính thức dùng để dẫn nguồn; không tuyên bố đã tải lại hoặc xác minh byte từ máy chủ SBA trong lần cập nhật này.',
      '', '## So sánh kết quả','',
      '| Chỉ tiêu | Bản 31/03/2026 | Bản 30/06/2026 | Thay đổi |',
      '| --- | ---: | ---: | ---: |']
for row in comparison.itertuples():
    if row.unit=='proportion':a,b,delta=pct(row.old_value),pct(row.new_value),f(row.change*100,3)+' điểm %'
    else:a,b,delta=f(row.old_value),f(row.new_value),f(row.change)
    body.append(f'| {row.metric} | {a} | {b} | {delta} |')
body += ['', 'Các chênh lệch trên là so sánh tổng hợp giữa hai ngày chụp. Do không có mã khoản vay duy nhất, không diễn giải chúng thành số khoản vay cá biệt đã chuyển trạng thái.',
         '', '## Bài viết và phân công','',
         'Giữ nguyên các mã tiểu mục 2.1–2.3.3. Riêng tiêu đề 2.1.1 đổi mốc asof sang 06/2026 để đúng dữ liệu mới; không sửa Excel hoặc playbook gốc. Các mục còn nhắc Subprogram trong tên phân công được giải thích rõ trong nội dung là trường không có ở bản hiện tại.',
         '', 'Cả hai notebook, Parquet, bảng, biểu đồ PNG/HTML, từ điển biến, sổ đối chiếu số liệu, báo cáo Word/Markdown/PDF, tài liệu tham khảo APA 7th và metadata đã được tái tạo theo nguồn mới. FRED-MD vẫn dùng bản 09/2026 khớp checksum với Fred.csv gốc.',
         '', 'Hai notebook đã chạy cục bộ trên toàn bộ dữ liệu. Chưa trực tiếp chạy Colab; xem README để tái lập.', '']
(WORK/'report/Cap_nhat_du_lieu.md').write_text('\n'.join(body),encoding='utf-8')

# Refresh explanatory passages while preserving the existing run instructions.
readme=WORK/'README.md';text=readme.read_text(encoding='utf-8')
paragraphs=text.split('\n\n')
for i,paragraph in enumerate(paragraphs):
    if paragraph.startswith('SBA: FY2000'):
        paragraphs[i]=('SBA hiện dùng hai CSV bạn cung cấp, bản **30/06/2026 (260630)**: FY2000–FY2009 có '+f(audit['files'][0]['rows'])+' dòng; FY2010–FY2019 có '+f(audit['files'][1]['rows'])+' dòng. Mỗi tệp có 42 cột CamelCase, ngày ISO và trạng thái trả đủ ghi `P I F`. SHA-256 được ghi từ tệp cục bộ, không giả định đây là lần tải mới từ Internet. Phiên bản và danh sách nguồn cấu hình tại `../data/metadata/dataset_config.json`; xem source_manifest.json để biết nguồn từng tệp. [Chi tiết thay đổi và số liệu trước–sau](report/Cap_nhat_du_lieu.md).')
    elif paragraph.startswith('Bản Word đã được phân trang'):
        paragraphs[i]='Bản Word được kiểm tra phân trang bằng Microsoft Word; số trang và kết quả kiểm tra mới nhất nằm trong `../data/metadata/deliverable_validation.json`. Chưa chạy trực tiếp trên Colab.'
text='\n\n'.join(paragraphs)
text=text.replace('CSV gốc SBA 260331','CSV gốc SBA 260630')
text=text.replace('**chưa xác nhận đây là từ điển lưu trữ của 03/2026**','**chưa xác nhận đây là từ điển lưu trữ riêng của 06/2026**')
text=text.replace('Notebook 01 không ghi đè Parquet; nếu có sẵn, kiểm tra hợp đồng rồi dùng lại.',
                  'Notebook 01 chỉ dùng lại Parquet khi ngày chụp và checksum của từng CSV khớp nguồn đã xử lý. Khi CSV thay đổi, xây lại Parquet theo cấu hình thay vì dùng cache cũ; notebook EDA cũng từ chối nguồn chưa được xử lý lại.')
lines=text.splitlines()
for i,line in enumerate(lines):
    if line.startswith('- Tập có nhãn:'):
        lines[i]=f'- Tập có nhãn: {f(summary["n_resolved"])} khoản; {f(summary["n_pif"])} PIF, {f(summary["n_chgoff"])} CHGOFF; tỷ lệ xóa nợ có điều kiện = **{pct(summary["chgoff_rate"])}**. Không diễn giải thành xác suất vòng đời cho mọi khoản đã duyệt.'
    elif line.startswith('- Ngoài nhãn:'):
        lines[i]=f'- Ngoài nhãn: {f(summary["n_status"]["CANCLD"])} CANCLD, {f(summary["n_status"]["EXEMPT"])} EXEMPT, {f(summary["n_status"]["COMMIT"])} COMMIT. Không xem trạng thái hủy là kiểm duyệt phải.'
    elif line.startswith('- Tỷ lệ có nhãn FY2019:'):
        lines[i]=f'- Tỷ lệ có nhãn FY2019: **{pct(cohort.loc[2019,"resolved_rate"])}**; EXEMPT chiếm **{pct(cohort.loc[2019,"exempt_share"])}** cohort này. So sánh cohort chịu khác biệt thời gian theo dõi và cơ cấu trạng thái.'
    elif line.startswith('- `approvalfy` ánh xạ'):
        lines[i]='- `ApprovalFY` ánh xạ thành `ApprovalFiscalYear`; `PaidInFullDate` giữ chính tả từ điển. Bản 260630 không có Subprogram; dùng ProcessingMethod và không tạo cột thay thế giả. Tên Subprogram trong một số tiêu đề gốc của phân công được giải thích trong bài. Riêng tiêu đề 2.1.1 cập nhật mốc 06/2026; Excel/playbook giữ nguyên.'
text='\n'.join(lines)+'\n'
readme.write_text(text,encoding='utf-8')
print('Updated revision note, comparison CSV, README; retired obsolete Subprogram table.')
