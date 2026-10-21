"""Create self-contained notebooks. All analysis/figure code lives in their cells."""
from pathlib import Path
import nbformat as nbf

OUT = Path(__file__).resolve().parents[1]
NB = OUT / 'notebooks'
NB.mkdir(parents=True, exist_ok=True)

CONFIG = r'''
from pathlib import Path
import sys, json, hashlib, warnings
import numpy as np
import pandas as pd
from IPython.display import display, Markdown

# Trên Colab: mount Drive trước, rồi điền BASE là thư mục PTDLNC đã tải lên.
# Không cần sửa khi mở notebook từ bên trong thư mục dự án trên máy cá nhân.
BASE = next((p for p in [Path.cwd(), *Path.cwd().parents, Path.cwd() / 'PTDLNC']
             if (p / 'data' / 'raw').is_dir()), None)
if BASE is None:
    raise FileNotFoundError('Đặt BASE tới thư mục PTDLNC có data/raw (xem README).')
RANDOM_STATE = 42
RAW, PROCESSED, META = [BASE / 'data' / x for x in ('raw', 'processed', 'metadata')]
DATASET = json.loads((META / 'dataset_config.json').read_text(encoding='utf-8'))
SNAPSHOT = pd.Timestamp(DATASET['snapshot'])
SNAPSHOT_VI = DATASET['snapshot_vi']
WORK = BASE / 'bai_lam_Anh_Chuong2'
FIGURES, TABLES = WORK / 'figures', WORK / 'tables'
for p in (PROCESSED, META, FIGURES, TABLES): p.mkdir(parents=True, exist_ok=True)
def save_json(obj, path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def table(frame, name):
    frame.to_csv(TABLES / (name + '.csv'), index=False, encoding='utf-8-sig', float_format='%.12g')
    display(frame.head(30))
'''

PIPELINE = r'''
files = [RAW / item['file'] for item in DATASET['sources']]
assert all(f.exists() for f in files), 'Thiếu CSV SBA đúng phiên bản trong dataset_config.json.'
dictionary_path = RAW / '7a_504_foia_data_dictionary.xlsx'
dictionary = pd.read_excel(dictionary_path, sheet_name='7(a) Data Dictionary')
definitions = dict(dictionary.iloc[:, :2].itertuples(index=False, name=None))
canonical = {str(k).lower(): str(k) for k in definitions}
canonical.update(subprogram='Subprogram', approvalfy='ApprovalFiscalYear')
KEEP = ['AsOfDate','Program','BorrState','BankName','GrossApproval','SBAGuaranteedApproval',
        'ApprovalDate','ApprovalFiscalYear','FirstDisbursementDate','ProcessingMethod',
        'InitialInterestRate','FixedorVariableInterestInd','TermInMonths','NaicsCode','NaicsDescription',
        'FranchiseCode','BusinessType','BusinessAge','LoanStatus','PaidInFullDate','ChargeOffDate',
        'GrossChargeOffAmount','JobsSupported','ProjectState','RevolverStatus','CollateralInd','SoldSecMrktInd']
NUMERIC = ['GrossApproval','SBAGuaranteedApproval','ApprovalFiscalYear','InitialInterestRate',
           'TermInMonths','GrossChargeOffAmount','JobsSupported']
DATES = ['AsOfDate','ApprovalDate','FirstDisbursementDate','PaidInFullDate','ChargeOffDate']
DENIED = {'BorrName','BorrStreet','BorrCity','BorrZip','LocationID','BankStreet','BankZip',
          'BankFDICNumber','BankNCUANumber','FranchiseName','ProjectCounty','CongressionalDistrict'}
fingerprints = set()
audits, parts, invalid = [], [], {}
existing = PROCESSED / 'loans_clean.parquet'
source_hashes = {f.name:sha256(f) for f in files}
previous = json.loads((META/'pipeline_audit.json').read_text(encoding='utf-8')) if (META/'pipeline_audit.json').exists() else {}
cache_matches = (existing.exists() and previous.get('snapshot') == DATASET['snapshot'] and
                 {r['file']:r['sha256'] for r in previous.get('files',[])} == source_hashes)
rebuilt = not cache_matches
if cache_matches:
    loans = pd.read_parquet(existing)
    assert not DENIED.intersection(loans.columns), 'Parquet hiện có chứa định danh.'
    assert {'fy','approval_month','target','is_resolved',*KEEP}.issubset(loans.columns), 'Parquet chưa đủ hợp đồng EDA.'
    assert loans.AsOfDate.eq(SNAPSHOT).all(), 'Cache khác ngày chụp được cấu hình.'
    print('Sử dụng Parquet có sẵn, không ghi đè:', len(loans))
else:
    for f, spec in zip(files, DATASET['sources']):
        lo,hi = spec['fy_start'],spec['fy_end']
        # Kiểm tra UTF-8 toàn bộ byte, không suy đoán encoding từ vài dòng đầu.
        import codecs
        decoder = codecs.getincrementaldecoder('utf-8-sig')('strict')
        try:
            with f.open('rb') as source:
                for block in iter(lambda: source.read(1024*1024), b''): decoder.decode(block)
                decoder.decode(b'', final=True)
            encoding = 'utf-8-sig'
        except UnicodeDecodeError:
            encoding = 'cp1252'
        n, repeated, normalized = 0, 0, 0
        header = pd.read_csv(f, nrows=0, encoding=encoding).columns.tolist()
        missing = set(KEEP) - {canonical.get(c.lower(),c) for c in header}
        assert not missing, f'Thiếu cột: {missing}'
        selected = KEEP + (['Subprogram'] if any(c.lower()=='subprogram' for c in header) else [])
        raw_status_counts = {}
        for chunk in pd.read_csv(f, dtype='string', encoding=encoding, chunksize=100_000, keep_default_na=False):
            n += len(chunk)
            # Fingerprint toàn hàng gốc chỉ phục vụ kiểm tra, không xuất và không xóa hàng.
            # Không có mã khoản vay duy nhất: đây không phải xác nhận trùng khoản vay.
            h = pd.util.hash_pandas_object(chunk, index=False).to_numpy()
            before = len(fingerprints)
            fingerprints.update(map(int,h))
            repeated += len(chunk) - (len(fingerprints)-before)
            chunk = chunk.rename(columns={c:canonical.get(c.lower(),c) for c in chunk.columns})[selected].copy()
            for c in chunk:
                chunk[c] = chunk[c].str.strip().replace('', pd.NA)
            for c in NUMERIC:
                parsed = pd.to_numeric(chunk[c], errors='coerce')
                invalid[c] = invalid.get(c,0) + int((chunk[c].notna() & parsed.isna()).sum())
                chunk[c] = parsed.astype('float64')
            for c in DATES:
                iso = chunk[c].str.match(r'^\d{4}-\d{2}-\d{2}$',na=False)
                parsed = pd.to_datetime(chunk[c].where(iso), format='%Y-%m-%d', errors='coerce')
                us_dates = pd.to_datetime(chunk[c].where(~iso), format='%m/%d/%Y', errors='coerce')
                parsed = parsed.fillna(us_dates)
                invalid[c] = invalid.get(c,0) + int((chunk[c].notna() & parsed.isna()).sum())
                chunk[c] = parsed
            original_status = chunk['LoanStatus']
            for code,count in original_status.value_counts(dropna=False).items():
                raw_status_counts[str(code)] = raw_status_counts.get(str(code),0)+int(count)
            chunk['LoanStatus'] = original_status.str.upper().str.replace(r'\s+', '', regex=True)
            normalized += int((original_status != chunk['LoanStatus']).fillna(False).sum())
            assert chunk.AsOfDate.eq(SNAPSHOT).all(), 'Sai ngày chụp SBA!'
            assert chunk.ApprovalFiscalYear.between(lo,hi).all(), 'FY ngoài phạm vi file!'
            chunk['source_file'] = f.name
            parts.append(chunk)
        audits.append(dict(file=f.name,rows=n,raw_columns=len(header),encoding=encoding,
                           sha256=sha256(f),raw_header=header,repeated_row_fingerprints=repeated,
                           status_normalized_rows=normalized,raw_status_counts=raw_status_counts,
                           date_formats=['ISO YYYY-MM-DD','US MM/DD/YYYY'],
                           unavailable_columns=['Subprogram'] if 'Subprogram' not in selected else [],
                           unique_loan_key='Not supplied; no deduplication'))
        print(f.name, n, 'hàng; encoding',encoding,'; fingerprint lặp:',repeated)
    loans = pd.concat(parts, ignore_index=True)
    del parts, fingerprints
    loans['fy'] = loans.ApprovalFiscalYear.astype('Int16')
    loans['approval_month'] = loans.ApprovalDate.dt.to_period('M').dt.to_timestamp()
    loans['is_resolved'] = loans.LoanStatus.isin(['CHGOFF','PIF'])
    loans['target'] = loans.LoanStatus.map({'CHGOFF':1,'PIF':0}).astype('Int8')
    assert not DENIED.intersection(loans.columns)
    assert loans.ApprovalDate.notna().all()
    assert loans.fy.eq((loans.ApprovalDate.dt.year + loans.ApprovalDate.dt.month.ge(10)).astype('Int16')).all()
    assert loans.LoanStatus.isin(['PIF','CHGOFF','CANCLD','EXEMPT','COMMIT']).all()
    assert loans.is_resolved.eq(loans.target.notna()).all()
    assert not any(invalid.values()), f'Lỗi chuyển kiểu cần kiểm tra: {invalid}'
    temporary = existing.with_suffix('.tmp.parquet')
    loans.to_parquet(temporary, index=False)
    temporary.replace(existing)
    save_json({'files':audits,'parse_failures':invalid,'rows':len(loans),
               'snapshot':DATASET['snapshot'],'source_hashes':source_hashes,
               'cache_policy':'Reuse only when configured snapshot and raw SHA-256 match.',
               'date_start':loans.ApprovalDate.min(),'date_end':loans.ApprovalDate.max(),
               'columns':loans.columns.tolist(),'duplicate_policy':'No loan ID; retain every row.',
               'dictionary_version':'Current official dictionary downloaded; no historical vintage claimed.'}, META/'pipeline_audit.json')
assert loans.fy.between(2000,2019).all()
assert loans.target.dropna().isin([0,1]).all()
assert loans.loc[~loans.is_resolved,'target'].isna().all()
assert loans.loc[loans.LoanStatus.eq('CHGOFF'),'target'].eq(1).all()
assert loans.loc[loans.LoanStatus.eq('PIF'),'target'].eq(0).all()
assert not DENIED.intersection(loans.columns)
table(loans.groupby('LoanStatus',dropna=False).size().rename('n').reset_index(), 'B2_trang_thai')
'''

FRED = r'''
official, local = RAW/'FRED_MD_2026-09.csv', RAW/'Fred_original.csv'
assert sha256(official) == sha256(local), 'Fred.csv không khớp byte với bản chính thức 09/2026.'
fred_raw = pd.read_csv(official)
assert fred_raw.iloc[0,0] == 'Transform:'
tcodes = pd.to_numeric(fred_raw.iloc[0,1:], errors='raise').astype(int)
tcodes.rename('tcode').rename_axis('variable').reset_index().to_csv(META/'fred_tcodes.csv',index=False)
fred = fred_raw.iloc[1:].copy()
fred['sasdate'] = pd.to_datetime(fred.sasdate,format='%m/%d/%Y',errors='raise')
fred = fred.set_index('sasdate').apply(pd.to_numeric,errors='raise').sort_index()
assert fred.index.is_unique and fred.index.is_monotonic_increasing
assert fred.index.equals(pd.date_range(fred.index.min(),fred.index.max(),freq='MS',name='sasdate'))
fred_path=PROCESSED/'fred_md_monthly.parquet'
if not fred_path.exists(): fred.to_parquet(fred_path)
else:
    supplied=pd.read_parquet(fred_path)
    pd.testing.assert_frame_equal(supplied,fred,check_dtype=False,check_freq=False)
monthly = loans.groupby('approval_month').agg(n_loans=('fy','size'),gross_approval=('GrossApproval','sum')).sort_index()
monthly_path=PROCESSED/'monthly_series.parquet'
if rebuilt or not monthly_path.exists(): monthly.to_parquet(monthly_path)
else: pd.testing.assert_frame_equal(pd.read_parquet(monthly_path),monthly,check_dtype=False,check_freq=False)
assert len(monthly)==240 and monthly.n_loans.sum()==len(loans)
source_profile = {'observations':len(fred),'macro_variables':len(fred.columns),
                  'first_month':str(fred.index.min().date()),'last_month':str(fred.index.max().date()),
                  'sha256':sha256(official),'local_matches_official':True,
                  'monthly_loan_observations':len(monthly),'loan_rows':len(loans)}
save_json(source_profile,META/'fred_profile.json')
table(pd.DataFrame([source_profile]),'B1_fred_nguon')
display(Markdown('**Hoàn tất:** dữ liệu gốc được giữ nguyên; ba Parquet không có định danh người vay. Không có thao tác bù thiếu, cắt ngoại lai hoặc huấn luyện mô hình.'))
'''

EDA_SETUP = r'''
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Patch
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from scipy.stats import chi2_contingency
import itertools
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                     'axes.spines.right':False,'figure.facecolor':'white','axes.titleweight':'bold'})
COLOR, ACCENT = '#164e63', '#c65d3b'
loans = pd.read_parquet(PROCESSED/'loans_clean.parquet')
fred = pd.read_parquet(PROCESSED/'fred_md_monthly.parquet')
assert loans.AsOfDate.eq(SNAPSHOT).all(), 'Parquet khác phiên bản đang dùng; chạy notebook 01 trước.'
audit=json.loads((META/'pipeline_audit.json').read_text(encoding='utf-8'))
assert audit.get('snapshot')==DATASET['snapshot'], 'Metadata pipeline lỗi thời.'
if all((RAW / item['file']).exists() for item in DATASET['sources']):
    assert audit.get('source_hashes') == {item['file']:sha256(RAW / item['file']) for item in DATASET['sources']}, 'CSV đã thay đổi; chạy lại notebook 01.'
assert not {'BorrName','BorrStreet','BorrCity','BorrZip','LocationID'}.intersection(loans.columns)
assert loans.is_resolved.eq(loans.target.notna()).all()
assert loans.fy.between(2000,2019).all()
raw_naics = loans.NaicsCode.str.replace(r'\.0$','',regex=True)
valid_naics = raw_naics.str.fullmatch(r'[1-9]\d{5}',na=False)
loans['NAICS2'] = raw_naics.where(valid_naics).str[:2].replace({'31':'31–33','32':'31–33','33':'31–33',
                  '44':'44–45','45':'44–45','48':'48–49','49':'48–49'})
SECTORS = {'11':'Nông, lâm, ngư nghiệp','21':'Khai khoáng','22':'Tiện ích','23':'Xây dựng',
 '31–33':'Chế biến, chế tạo','42':'Bán buôn','44–45':'Bán lẻ','48–49':'Vận tải, kho bãi',
 '51':'Thông tin','52':'Tài chính, bảo hiểm','53':'Bất động sản, cho thuê','54':'Chuyên môn, kỹ thuật',
 '55':'Quản lý doanh nghiệp','56':'Hỗ trợ, xử lý chất thải','61':'Giáo dục','62':'Y tế, trợ giúp xã hội',
 '71':'Nghệ thuật, giải trí','72':'Lưu trú, ăn uống','81':'Dịch vụ khác','92':'Hành chính công'}
loans['NAICS2'] = loans.NAICS2.where(loans.NAICS2.isin(SECTORS))
resolved = loans.loc[loans.is_resolved].copy()
SOURCE = f'Nguồn: tác giả tính toán từ SBA 7(a), bản chụp {SNAPSHOT_VI}.'
def savefig(fig, name, note=''):
    fig.text(0.01,0.012,SOURCE + ('\n'+note if note else ''),fontsize=8,va='bottom',color='#444444')
    fig.tight_layout(rect=(0,0.085,1,0.96))
    fig.savefig(FIGURES/(name+'.png'),dpi=200,bbox_inches='tight')
    plt.show()
    plt.close(fig)
def rate_table(group):
    allg=loans.groupby(group,dropna=False).agg(n_all=('fy','size'),mean_approval=('GrossApproval','mean'))
    r=resolved.groupby(group,dropna=False).agg(n_resolved=('target','size'),n_chgoff=('target','sum'))
    out=allg.join(r).reset_index()
    out[['n_resolved','n_chgoff']]=out[['n_resolved','n_chgoff']].fillna(0).astype(int)
    n=out.n_resolved.replace(0,np.nan); p=out.n_chgoff/n; z=1.959963984540054
    center=(p+z*z/(2*n))/(1+z*z/n)
    margin=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    out['rate']=p;out['ci_low']=center-margin;out['ci_high']=center+margin
    out['low_n']=out.n_resolved.lt(100)
    return out
'''

PROFILES = r'''
numeric=['GrossApproval','SBAGuaranteedApproval','TermInMonths','JobsSupported','InitialInterestRate']
desc=loans[numeric].describe(percentiles=[.01,.25,.5,.75,.95,.99]).T.reset_index(names='variable')
desc['skewness']=loans[numeric].skew().reindex(desc.variable).to_numpy()
table(desc,'B3_mo_ta_dinh_luong')
missing=pd.DataFrame({'variable':loans.columns,'missing_n':loans.isna().sum().to_numpy(),
                      'missing_pct':loans.isna().mean().to_numpy()*100}).sort_values('missing_pct',ascending=False)
table(missing,'B4_thieu_du_lieu')
cats=[c for c in ['BusinessType','BusinessAge','Subprogram','ProcessingMethod','NAICS2','BorrState','LoanStatus'] if c in loans.columns]
freq=[]
for c in cats:
    a=loans[c].fillna('(Thiếu)').value_counts(dropna=False).rename_axis('category').reset_index(name='n')
    a.insert(0,'variable',c);a['pct_all']=a.n/len(loans)*100;freq.append(a)
table(pd.concat(freq,ignore_index=True),'B5_tan_so_dinh_tinh')
missing_fy=loans.groupby('fy')[numeric+['BusinessAge','NaicsCode','BorrState']].agg(lambda s:s.isna().mean()*100)
table(missing_fy.reset_index(),'B6_thieu_theo_fy')
outliers=[]
for c in ['GrossApproval','TermInMonths','JobsSupported']:
    s=loans[c].dropna();q1,q3=s.quantile([.25,.75]);iqr=q3-q1
    outliers.append(dict(variable=c,n_valid=len(s),q1=q1,q3=q3,iqr=iqr,
      lower_fence=q1-1.5*iqr,upper_fence=q3+1.5*iqr,
      outside_iqr_n=int(((s<q1-1.5*iqr)|(s>q3+1.5*iqr)).sum()),
      zero_n=int(s.eq(0).sum()),negative_n=int(s.lt(0).sum()),maximum=s.max()))
table(pd.DataFrame(outliers),'B7_ngoai_lai')
cohort=loans.groupby('fy').agg(n_all=('fy','size'),n_resolved=('is_resolved','sum'),n_chgoff=('target','sum'))
statuses=pd.crosstab(loans.fy,loans.LoanStatus)
cohort=cohort.join(statuses);cohort['resolved_rate']=cohort.n_resolved/cohort.n_all
cohort['chgoff_rate_resolved']=cohort.n_chgoff/cohort.n_resolved
cohort['exempt_share']=cohort.get('EXEMPT',0)/cohort.n_all
table(cohort.reset_index(),'B8_cohort')
for c in [c for c in ['BusinessType','Subprogram','ProcessingMethod','NAICS2','BorrState'] if c in loans.columns]:
    table(rate_table(c),'B9_ty_le_'+c)
classes=resolved.target.value_counts().sort_index()
summary={'n_all':len(loans),'n_resolved':len(resolved),'n_chgoff':int(classes.get(1,0)),
 'n_pif':int(classes.get(0,0)),'chgoff_rate':float(resolved.target.mean()),
 'n_status':{str(k):int(v) for k,v in loans.LoanStatus.value_counts(dropna=False).items()},
 'approval_start':str(loans.ApprovalDate.min().date()),'approval_end':str(loans.ApprovalDate.max().date()),
 'n_naics_missing_or_invalid':int(loans.NAICS2.isna().sum()),
 'negative_gross_n':int(loans.GrossApproval.lt(0).sum()),'term_gt_300_n':int(loans.TermInMonths.gt(300).sum()),
 'zero_term_n':int(loans.TermInMonths.eq(0).sum()),'zero_jobs_n':int(loans.JobsSupported.eq(0).sum()),
 'gross_total':float(loans.GrossApproval.sum()),'processed_columns':len(loans.columns)-1}
save_json(summary,META/'eda_summary.json')
'''

MACRO = r'''
# Tính YoY trên toàn chuỗi trước khi cắt giai đoạn; giữ đủ lịch sử cho lag và YoY.
macro=pd.DataFrame({'unrate':fred.UNRATE,'fedfunds':fred.FEDFUNDS,'yield_spread':fred.T10YFFM,
 'cpi_yoy':fred.CPIAUCSL.pct_change(12,fill_method=None)*100,
 'indpro_yoy':fred.INDPRO.pct_change(12,fill_method=None)*100,
 'busloans_yoy':fred.BUSLOANS.pct_change(12,fill_method=None)*100})
macro_lag=macro.shift(1).add_suffix('_lag1').rename_axis('approval_month').reset_index()
assert macro_lag.approval_month.is_unique
month_keys=loans[['approval_month']].drop_duplicates().sort_values('approval_month')
joined_months=month_keys.merge(macro_lag,on='approval_month',how='left',validate='one_to_one',indicator=True)
joined_keys=loans[['approval_month']].merge(macro_lag[['approval_month']],on='approval_month',how='left',validate='many_to_one')
assert len(joined_keys)==len(loans)
assert joined_months['_merge'].eq('both').all()
assert joined_months.filter(like='_lag1').notna().all().all()
first=loans.approval_month.min()
assert macro_lag.set_index('approval_month').loc[first,'unrate_lag1']==macro.loc[first-pd.offsets.MonthBegin(1),'unrate']
table(joined_months.drop(columns='_merge'),'B10_vi_mo_lag1_theo_thang')
table(joined_months.filter(like='_lag1').describe().T.reset_index(names='variable'),'B11_mo_ta_vi_mo')
save_json({'n_before':len(loans),'n_after':len(joined_keys),'matched_months':len(joined_months),
 'missing_lag_cells':int(joined_months.filter(like='_lag1').isna().sum().sum()),
 'note':'Bảng vĩ mô tạm phục vụ mô tả; không ghi đè loans_clean và không tạo loans_features.'},META/'macro_join_audit.json')
'''

DIAGRAM = r'''
fig,ax=plt.subplots(figsize=(8.4,3));ax.set_xlim(0,10);ax.set_ylim(0,3.4);ax.axis('off')
boxes=[(.3,2,3.5,.9,'SBA 7(a)\nDữ liệu khoản vay'),
 (.3,.4,3.5,.9,'FRED-MD\nChỉ số kinh tế vĩ mô'),
 (6,1.2,3.5,.9,'Dữ liệu phân tích')]
for x,y,w,h,label in boxes:
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',facecolor='#edf5f7',edgecolor=COLOR))
 ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=14)
for start,end in [((3.95,2.45),(5.85,1.85)),((3.95,.85),(5.85,1.45))]:
 ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':COLOR,'lw':1.5})
fig.text(.02,.025,f'Nguồn: SBA 7(a), {SNAPSHOT_VI}; FRED-MD, 09/2026.',fontsize=9,color='#444444')
fig.tight_layout(rect=(0,.10,1,1))
fig.savefig(FIGURES/'S1_so_do_du_lieu.png',dpi=200,bbox_inches='tight')
plt.show();plt.close(fig)
'''

CHARTS = r'''
fig,ax=plt.subplots(figsize=(10,4.4))
ax.bar(cohort.index.astype(str),cohort.n_all/1000,color=COLOR)
ax.set(xlabel='Năm tài khóa SBA (FY)',ylabel='Số khoản vay (nghìn)',title='H1. Số khoản vay được phê duyệt theo năm tài khóa')
ax.tick_params(axis='x',rotation=45)
savefig(fig,'H1_so_khoan_vay_theo_fy',f'Tất cả {len(loans):,} khoản vay; bao gồm trạng thái hủy và chưa có nhãn.')
fig,axes=plt.subplots(1,2,figsize=(12,4.5))
axes[0].plot(cohort.index,cohort.resolved_rate*100,'o-',color=COLOR,label='PIF + CHGOFF / tất cả')
axes[0].set(xlabel='Năm tài khóa',ylabel='Tỷ lệ có kết quả (%)',ylim=(0,105),title='a. Tỷ lệ có kết quả quan sát được');axes[0].legend(fontsize=8)
status_order=[s for s in ['PIF','CHGOFF','EXEMPT','CANCLD','COMMIT'] if s in statuses]
shares=statuses[status_order].div(statuses.sum(axis=1),axis=0)*100
shares.plot.bar(stacked=True,ax=axes[1],color=['#164e63','#c65d3b','#d4a853','#bac8cf','#8a70a8'][:len(status_order)],width=.85)
axes[1].set(xlabel='Năm tài khóa',ylabel='Tỷ trọng (%)',title='b. Cơ cấu trạng thái, phân biệt EXEMPT và hủy')
axes[1].legend(fontsize=7,loc='upper center',ncol=3);axes[1].tick_params(axis='x',labelsize=8)
fig.suptitle('H2. Mức độ quan sát kết quả theo cohort phê duyệt',fontweight='bold')
savefig(fig,'H2_kiem_duyet_theo_fy','EXEMPT không đồng nghĩa vỡ nợ; CANCLD là hủy, không tự xem là kiểm duyệt phải.')

industry=rate_table('NAICS2').dropna(subset=['NAICS2','rate']).sort_values('NAICS2')
fig,ax=plt.subplots(figsize=(11,6))
size=industry.n_all/industry.n_all.max()*2400
ax.scatter(industry.mean_approval/1000,industry.rate*100,s=size,c=industry.rate,cmap='YlOrRd',alpha=.65,edgecolors='#555555',linewidths=.5)
# Mỗi bubble ghi mã ngành và số khoản vay, nhãn lệch luân phiên để hạn chế chồng lấn.
offsets={'23':(12,35),'48–49':(18,-26),'56':(-8,12),'51':(-35,18),'52':(14,18),
         '81':(15,-25),'55':(10,16),'44–45':(15,-24),'53':(20,-24),'42':(12,18)}
for i,row in enumerate(industry.itertuples()):
 ax.annotate(f'{row.NAICS2}: {row.n_all:,}',(row.mean_approval/1000,row.rate*100),
             xytext=offsets.get(row.NAICS2,((i%3-1)*8,12 if i%2 else -20)),textcoords='offset points',fontsize=7,
             arrowprops={'arrowstyle':'-','lw':.4,'color':'#555555'})
ax.set(xlabel='Giá trị phê duyệt trung bình (nghìn USD danh nghĩa; tất cả khoản vay trong ngành)',
 ylabel='Tỷ lệ xóa nợ trên khoản có nhãn (%)',title='H4. Quy mô khoản vay và tỷ lệ xóa nợ theo ngành NAICS')
savefig(fig,'H4_bubble_nganh','Diện tích bubble tỷ lệ thuận với số khoản vay; nhãn = mã ngành: số khoản vay; loại ngành thiếu/không hợp lệ.')

groups=[np.log1p(resolved.loc[resolved.target.eq(t)&resolved.GrossApproval.ge(0),'GrossApproval'].dropna()) for t in [0,1]]
fig,ax=plt.subplots(figsize=(8,4.4))
bp=ax.boxplot(groups,tick_labels=['Trả đủ (PIF)','Xóa nợ (CHGOFF)'],showfliers=False,patch_artist=True)
for patch,color in zip(bp['boxes'],[COLOR,ACCENT]):patch.set_facecolor(color);patch.set_alpha(.75)
ax.set(ylabel='ln(1 + giá trị phê duyệt bằng USD)',title='H5. Phân phối giá trị khoản vay theo kết quả')
savefig(fig,'H5_box_quy_mo_theo_nhan','Dùng toàn bộ khoản có nhãn và số tiền không âm; ẩn điểm ngoài râu chỉ khi vẽ, không xóa quan sát.')

miss_top=missing.loc[missing.missing_n.gt(0)].head(12).sort_values('missing_pct')
fig,ax=plt.subplots(figsize=(9,4.6));ax.barh(miss_top.variable,miss_top.missing_pct,color=COLOR)
ax.set(xlabel='Tỷ lệ thiếu trên tất cả khoản vay (%)',title='Hình bổ sung. Các biến có tỷ lệ thiếu cao nhất')
savefig(fig,'S2_thieu_du_lieu','Thiếu ngày trả đủ/xóa nợ thường gắn với trạng thái; không tự động bù các ngày kết quả.')
'''

MAP = r'''
# Giải mã TopoJSON của Plotly thành GeoJSON; cùng dữ liệu dùng cho PNG và choropleth HTML.
topo=json.loads((META/'usa_110m.json').read_text(encoding='utf-8'))
scale=np.array(topo['transform']['scale']);translate=np.array(topo['transform']['translate'])
decoded=[np.cumsum(np.array(a,dtype=float),axis=0)*scale+translate for a in topo['arcs']]
def ring(ids):
    segments=[decoded[i] if i>=0 else decoded[~i][::-1] for i in ids]
    return np.concatenate([s if j==0 else s[1:] for j,s in enumerate(segments)]).tolist()
features=[]
for geom in topo['objects']['subunits']['geometries']:
    if geom.get('properties',{}).get('gu')!='USA':continue
    coords=([ring(r) for r in geom['arcs']] if geom['type']=='Polygon' else
            [[ring(r) for r in poly] for poly in geom['arcs']])
    features.append({'type':'Feature','id':geom['id'],'properties':{'state':geom['id']},
                     'geometry':{'type':geom['type'],'coordinates':coords}})
geojson={'type':'FeatureCollection','features':features}
save_json(geojson,META/'usa_states.geojson')
state=rate_table('BorrState');state=state.dropna(subset=['BorrState'])
rates=state.set_index('BorrState').rate
norm=Normalize(vmin=0,vmax=float(rates.reindex([f['id'] for f in features]).max()*100));cmap=plt.get_cmap('YlOrRd')
fig=plt.figure(figsize=(11.5,6.6));ax=fig.add_axes([.04,.27,.88,.60]);ak=fig.add_axes([.06,.12,.22,.20]);hi=fig.add_axes([.30,.12,.16,.16])
for f in features:
    code=f['id'];a=ak if code=='AK' else hi if code=='HI' else ax
    v=rates.get(code,np.nan);color='#dadada' if pd.isna(v) else cmap(norm(v*100))
    polys=f['geometry']['coordinates']
    if f['geometry']['type']=='Polygon':polys=[polys]
    for poly in polys:
        outer=np.array(poly[0])
        if code=='AK':outer[:,0]=np.where(outer[:,0]>0,outer[:,0]-360,outer[:,0])
        a.add_patch(Polygon(outer,facecolor=color,edgecolor='white',lw=.45))
for a,limits in [(ax,(-125,-66,24,50)),(ak,(-180,-129,50,73)),(hi,(-161,-154,18,23))]:
 a.set_xlim(limits[:2]);a.set_ylim(limits[2:]);a.set_aspect(1.25);a.axis('off')
ak.set_title('Alaska',fontsize=9);hi.set_title('Hawaii',fontsize=9)
cb=fig.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=[ax,ak,hi],fraction=.025,pad=.02,shrink=.8)
cb.set_label('CHGOFF / (CHGOFF + PIF), %')
fig.legend(handles=[Patch(facecolor='#dadada',label='Không có tỷ lệ tính được')],loc='lower right',bbox_to_anchor=(.88,.15),fontsize=8)
fig.suptitle('H3. Tỷ lệ xóa nợ theo bang của người vay (BorrState)',fontweight='bold',y=.96)
fig.text(.02,.025,SOURCE+'\nMẫu số: khoản có nhãn từng bang; bản đồ gồm 50 bang + DC nếu hình học có sẵn. Lãnh thổ được lưu trong bảng riêng.\nNền địa lý: Plotly usa_110m (Natural Earth); màu xám khác tỷ lệ bằng 0.',fontsize=8)
fig.savefig(FIGURES/'H3_ban_do_bang.png',dpi=200,bbox_inches='tight');plt.show();plt.close(fig)
import plotly.express as px
mapdata=state[state.BorrState.isin([f['id'] for f in features])].copy();mapdata['rate_pct']=mapdata.rate*100
interactive=px.choropleth(mapdata,geojson=geojson,locations='BorrState',featureidkey='id',color='rate_pct',
 hover_data=['n_all','n_resolved','n_chgoff','ci_low','ci_high','low_n'],scope='usa',color_continuous_scale='YlOrRd',
 labels={'rate_pct':'Xóa nợ (%)','BorrState':'Bang'},title='H3. Tỷ lệ xóa nợ theo bang; mẫu số = CHGOFF + PIF')
interactive.update_geos(fitbounds='locations',visible=False)
interactive.write_html(FIGURES/'H3_ban_do_bang.html',include_plotlyjs=True)
table(state.loc[~state.BorrState.isin([f['id'] for f in features])],'B12_dia_ly_ngoai_ban_do')
'''

CORRELATIONS = r'''
# Biến kết quả và cohort không nằm trong ma trận đặc trưng định lượng.
num=['GrossApproval','SBAGuaranteedApproval','TermInMonths','JobsSupported','InitialInterestRate']
labels=['Tiền vay','Bảo lãnh','Kỳ hạn','Việc làm','Lãi suất đầu kỳ']
pearson=loans[num].corr(method='pearson');spearman=loans[num].corr(method='spearman')
table(pearson.reset_index(names='variable'),'B13_pearson')
table(spearman.reset_index(names='variable'),'B14_spearman')
pairn=pd.DataFrame({c:loans[c].notna().astype('int64') for c in num})
pairn=pairn.T.dot(pairn)
table(pairn.reset_index(names='variable'),'B15_n_cap_bien_so')
def heat(ax,frame,names,title,vmin=-1,vmax=1):
    a=frame.to_numpy(dtype=float);im=ax.imshow(a,cmap='RdBu_r' if vmin<0 else 'Blues',vmin=vmin,vmax=vmax)
    ax.set_xticks(range(len(names)),names,rotation=45,ha='right',fontsize=8)
    ax.set_yticks(range(len(names)),names,fontsize=8);ax.set_title(title)
    for i in range(len(names)):
        for j in range(len(names)):
            if np.isfinite(a[i,j]):ax.text(j,i,f'{a[i,j]:.2f}',ha='center',va='center',fontsize=8,color='white' if abs(a[i,j])>.65 else '#222222')
    return im
fig,axes=plt.subplots(1,2,figsize=(11.5,5.8))
heat(axes[0],pearson,labels,'a. Pearson: liên hệ tuyến tính');im=heat(axes[1],spearman,labels,'b. Spearman: liên hệ thứ hạng')
fig.colorbar(im,ax=axes[1],shrink=.65);fig.suptitle('H6a. Tương quan các biến định lượng',fontweight='bold')
savefig(fig,'H6a_tuong_quan_so','Tất cả khoản vay; loại thiếu theo từng cặp. Hệ số trên thang gốc; không suy ra nhân quả.')
cat=[c for c in ['BusinessType','ProcessingMethod','Subprogram','NAICS2','BorrState','LoanStatus'] if c in loans.columns]
V=pd.DataFrame(np.nan,index=cat,columns=cat);N=V.copy()
for a,b in itertools.combinations_with_replacement(cat,2):
    sub=loans[[a]].dropna() if a==b else loans[[a,b]].dropna()
    if a==b: value=1.0 if sub[a].nunique()>1 else np.nan
    else:
        contingency=pd.crosstab(sub[a],sub[b]);r,k=contingency.shape
        value=np.sqrt(chi2_contingency(contingency,correction=False)[0]/(len(sub)*min(r-1,k-1))) if min(r,k)>1 else np.nan
    V.loc[a,b]=V.loc[b,a]=value;N.loc[a,b]=N.loc[b,a]=len(sub)
table(V.reset_index(names='variable'),'B16_cramers_v')
table(N.reset_index(names='variable'),'B17_n_cap_bien_loai')
fig,ax=plt.subplots(figsize=(8.5,6.3));im=heat(ax,V,cat,"H6b. Cramér’s V giữa các biến phân loại",0,1)
fig.colorbar(im,ax=ax,shrink=.7)
savefig(fig,'H6b_cramers_v','V chuẩn, không hiệu chỉnh sai lệch; loại thiếu theo cặp; chỉ đo độ liên hệ, không báo cáo p-value.')
links=[]
for a,b in itertools.combinations(num,2):
 links.append({'a':a,'b':b,'pearson':float(pearson.loc[a,b]),'spearman':float(spearman.loc[a,b]),'n_pair':int(pairn.loc[a,b])})
save_json({'numeric_pairs':links,'cramers_v_with_status':V['LoanStatus'].drop('LoanStatus').to_dict()},META/'correlation_summary.json')
display(Markdown('**Giới hạn:** Wilson là khoảng mô tả dựa trên giả định nhị thức độc lập, chưa điều chỉnh cụm tháng/ngân hàng. Cramér’s V có thể tăng theo số nhóm. EDA không quyết định ngưỡng mô hình, chia test hoặc giả thuyết nhân quả.'))
'''

FINAL_CHECKS = r'''
required_figures=['S1_so_do_du_lieu','H1_so_khoan_vay_theo_fy','H2_kiem_duyet_theo_fy','H3_ban_do_bang',
 'H4_bubble_nganh','H5_box_quy_mo_theo_nhan','H6a_tuong_quan_so','H6b_cramers_v']
assert all((FIGURES/(name+'.png')).exists() for name in required_figures)
assert cohort.n_all.sum()==len(loans)
assert cohort.n_resolved.sum()==len(resolved)
assert cohort.n_chgoff.sum()==resolved.target.sum()
assert np.allclose(pearson.to_numpy(),pearson.to_numpy().T,equal_nan=True)
assert np.allclose(V.to_numpy(),V.to_numpy().T,equal_nan=True)
assert V.stack().between(0,1+1e-12).all()
assert len(joined_keys)==len(loans)
save_json({'local_execution':'passed','colab_execution':'not_verified_in_Colab',
 'snapshot':DATASET['snapshot'],'source_hashes':audit['source_hashes'],
 'figures':required_figures,'loan_rows':len(loans),'resolved_rows':len(resolved),
 'no_borrower_identifiers':True,'macro_merge_preserves_rows':True},META/'notebook_validation.json')
print('Hoàn tất EDA:',len(loans),'khoản vay;',len(resolved),'có nhãn;',len(required_figures),'hình chính.')
def fmt(x,d=0):return f'{x:,.{d}f}'.replace(',','_').replace('.',',').replace('_','.')
display(Markdown(f"""### Diễn giải kết quả thực nghiệm

**Cấu trúc mẫu.** Bộ dữ liệu có {fmt(len(loans))} khoản vay; {fmt(len(resolved))} khoản đã trả đủ hoặc xóa nợ. Tỷ lệ xóa nợ trong tập này là {fmt(resolved.target.mean()*100,2)}%. Đây là tỷ lệ trên kết quả đã quan sát, không phải xác suất vỡ nợ vòng đời của mọi khoản đã được phê duyệt.

**Cohort và dữ liệu thiếu.** Tỷ lệ có kết quả giảm từ {fmt(cohort.loc[2000,'resolved_rate']*100,2)}% ở FY2000 xuống {fmt(cohort.loc[2019,'resolved_rate']*100,2)}% ở FY2019. Cần đọc cùng tỷ trọng EXEMPT và CANCLD; không thể gán toàn bộ phần chưa có nhãn cho kiểm duyệt phải. InitialInterestRate thiếu hoàn toàn ở FY2000–FY2008, nên các tương quan có lãi suất đại diện cho cửa sổ thời gian hẹp hơn.

**Phân phối.** Giá trị phê duyệt trung bình {fmt(loans.GrossApproval.mean(),2)} USD vượt trung vị {fmt(loans.GrossApproval.median())} USD, phù hợp với phân phối lệch phải. IQR chỉ là quy tắc đánh dấu; số tiền lớn không tự chứng minh sai dữ liệu. JobsSupported là ước lượng tự báo cáo trên hồ sơ; không thể suy ra số việc làm thực tế được tạo ra.

**Liên hệ.** GrossApproval–SBAGuaranteedApproval có Pearson {fmt(pearson.loc['GrossApproval','SBAGuaranteedApproval'],3)}, chủ yếu phù hợp với quan hệ cấu trúc giữa khoản vay và phần bảo lãnh. GrossApproval–JobsSupported có Pearson {fmt(pearson.loc['GrossApproval','JobsSupported'],3)} và Spearman {fmt(spearman.loc['GrossApproval','JobsSupported'],3)}. Chênh lệch hai thước đo cho thấy cần đọc cả thang gốc và thứ hạng, không tự chứng minh nguyên nhân. Cramér’s V với LoanStatus dùng năm trạng thái, không phải riêng nhãn nhị phân.

**Bàn giao.** Các bảng B1–B17 trong tables/ là nguồn để viết Chương 2. Đọc đầy đủ phần giới hạn và tài liệu tham khảo trong report/Chuong_2.md. Việc chọn mô hình và kiểm định thuộc các chương sau.
"""))
'''

def notebook(title, sections, filename):
    nb=nbf.v4.new_notebook()
    nb.metadata.update(kernelspec={'display_name':'Python 3','language':'python','name':'python3'},language_info={'name':'python','version':'3.12'})
    nb.cells=[nbf.v4.new_markdown_cell(title),nbf.v4.new_code_cell(CONFIG)]
    for explanation, code in sections:
        nb.cells += [nbf.v4.new_markdown_cell(explanation),nbf.v4.new_code_cell(code)]
    nbf.write(nb,NB/filename)

notebook('# 01. Chuẩn bị dữ liệu Chương 2 — Anh\n\nSBA 7(a), FY2000–FY2019, bản chụp 30/06/2026; FRED-MD 09/2026. '
         'Chạy sau khi tải dữ liệu theo README. Không sửa CSV gốc. Trên Colab, upload cả thư mục và mount Drive trước. '
         'Nếu thiếu thư viện, chạy `%pip install pandas numpy pyarrow openpyxl requests`.\n\n'
         'Nguồn: [SBA](https://data.sba.gov/dataset/7a-504-foia); [FRED-MD](https://www.stlouisfed.org/research/economists/mccracken/fred-databases).',[
 ('## 1. Kiểm tra cấu trúc thực tế, bảo vệ định danh và tạo nhãn\n'
  'Bản 260630 dùng tên cột CamelCase, ngày ISO YYYY-MM-DD và trạng thái trả đủ `P I F`. '
  '`ApprovalFY` ánh xạ thành `ApprovalFiscalYear`; `P I F` chuẩn hóa thành `PIF` trước khi tạo nhãn. '
  'CSV không còn Subprogram: không tạo giả cột này; dùng ProcessingMethod. '
  'Cache chỉ dùng lại khi snapshot và SHA-256 từng CSV khớp; khác nguồn sẽ xây lại Parquet. '
  'Từ điển không cung cấp khóa duy nhất của khoản vay; LocationID là mã ngân hàng. Chỉ đếm fingerprint lặp và không xóa hàng. '
  'Đọc các trường gốc trong bộ nhớ theo khối chỉ để kiểm tra fingerprint, sau đó loại định danh ngay; không hiển thị hàng thô.',PIPELINE),
 ('## 2. FRED-MD và hợp đồng bàn giao\n'
  'Tách dòng Transform trước khi chuyển số, xác nhận chuỗi tháng liên tục và checksum của Fred.csv khớp bản chính thức. '
  'Giữ nguyên các trạng thái không có nhãn trong dữ liệu mô tả. Đầu ra: ba Parquet và metadata; không ghi đè dữ liệu nhóm có sẵn.',FRED)
 ],'01_data_pipeline_ch2.ipynb')

notebook('# 02. Mô tả và khám phá dữ liệu — Anh\n\n'
         'Ánh xạ báo cáo: 2.1 nguồn và cấu trúc; 2.2 thách thức; 2.3 mô tả, trực quan và tương quan. '
         'Notebook chỉ đọc Parquet, không huấn luyện mô hình. Nếu thiếu thư viện: '
         '`%pip install pandas numpy scipy matplotlib plotly pyarrow`.\n\n'
         'Phương pháp: McCracken & Ng (2016), doi:10.1080/07350015.2015.1086655; '
         'Spearman (1904), doi:10.2307/1412159; Wilson (1927), doi:10.1080/01621459.1927.10502953; '
         'Cramér (1946), Mathematical methods of statistics.',[
 ('## 1. Đọc dữ liệu và quy ước mẫu\nTất cả khoản vay dùng cho mô tả; PIF/CHGOFF dùng cho tỷ lệ xóa nợ. '
  'NAICS: giữ mã sáu chữ số, gộp các dải ngành 31–33, 44–45, 48–49; mã không hợp lệ để thiếu, không gán ngành tùy ý.',EDA_SETUP),
 ('## 2. Bảng bằng chứng cho 2.2 và 2.3.1\nKhông bù thiếu hoặc loại ngoại lai. Mốc 300 tháng chỉ đánh dấu rà soát, '
  'không phải kết luận vi phạm pháp lý. JobsSupported = 0 được giữ; đây là số tự báo cáo trên hồ sơ, không phải kết quả việc làm đã kiểm chứng. '
  'Khoảng Wilson 95% chỉ có nghĩa mô tả trên khoản có nhãn, chưa điều chỉnh cụm.',PROFILES),
 ('## 3. FRED-MD và kiểm tra ghép theo tháng (2.1.4)\nTính YoY trước khi cắt giai đoạn rồi shift(1). '
  'Phép ghép thử kiểm tra nhiều–một; không tạo loans_features hoặc thay đổi Parquet chung. '
  'Độ trễ không xử lý hoàn toàn lịch công bố và dữ liệu điều chỉnh về sau.',MACRO),
 ('## 4. Sơ đồ nguồn và liên kết dữ liệu (2.1)\nSơ đồ được vẽ bằng matplotlib trong ô mã bên dưới.',DIAGRAM),
 ('## 5. H1, H2, H4, H5 và biểu đồ thiếu (2.2–2.3.2)\nTất cả thống kê tính trên dữ liệu đầy đủ. '
  'Boxplot ẩn điểm ngoài râu để dễ đọc nhưng không loại chúng khỏi phép tính.',CHARTS),
 ('## 6. H3: bản đồ theo bang (2.3.2)\nPNG dựng trực tiếp từ TopoJSON, không cần Chrome/Kaleido. '
  'Xuất thêm choropleth Plotly HTML để xem mẫu số và khoảng tin cậy. Lãnh thổ không có hình học được lưu ở bảng B12. '
  'Mã nhóm dưới 100 khoản có nhãn được đánh dấu low_n trong bảng, không tự loại.',MAP),
 ('## 7. H6: Pearson, Spearman và Cramér’s V (2.3.3)\nPearson dùng thang gốc; Spearman dùng thứ hạng. '
  'Thiếu loại theo từng cặp, xuất ma trận số quan sát tương ứng. Không dùng mã số ngành như biến liên tục. '
  'Cramér’s V = sqrt(chi2 / [n × min(r−1,k−1)]), không hiệu chỉnh Yates và không diễn giải p-value.',CORRELATIONS),
 ('## 8. Kiểm tra đầu ra\nViệc chạy cục bộ không được coi là đã chạy Colab. Xem README và notebook_validation.json.',FINAL_CHECKS)
 ],'02_eda_viz.ipynb')
print('Created notebooks:',*[p.name for p in NB.glob('*.ipynb')])
