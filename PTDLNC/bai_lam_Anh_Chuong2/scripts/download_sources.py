"""Retrieve immutable source snapshots; never substitute another SBA vintage."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import concurrent.futures
import hashlib
import json
import shutil
import requests

BASE = Path(__file__).resolve().parents[2]
RAW = BASE / 'data' / 'raw'
META = BASE / 'data' / 'metadata'
SBA = 'https://data.sba.gov/sites/default/files/uploaded_resources/'
DATASET = json.loads((META / 'dataset_config.json').read_text(encoding='utf-8'))
URLS = {
    **{item['file']:SBA + item['file'] for item in DATASET['sources']},
    '7a_504_foia_data_dictionary.xlsx': SBA + '7a_504_foia_data_dictionary.xlsx',
    'FRED_MD_2026-09.csv': 'https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md/monthly/2026-09-md.csv',
    'usa_110m.json': 'https://cdn.plot.ly/un/usa_110m.json',
}

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def download(item):
    name, url = item
    folder = META if name.endswith('.json') else RAW
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    record = {'file': str(path.relative_to(BASE)), 'url': url}
    try:
        was_present = path.exists()
        if not path.exists():
            with requests.get(url, stream=True, timeout=(20, 180)) as response:
                response.raise_for_status()
                ctype = response.headers.get('Content-Type', '')
                if 'text/html' in ctype:
                    raise ValueError('HTML response instead of source data')
                temporary = path.with_suffix(path.suffix + '.part')
                with temporary.open('wb') as output:
                    for block in response.iter_content(2 * 1024 * 1024):
                        output.write(block)
                temporary.replace(path)
                record['http_last_modified'] = response.headers.get('Last-Modified')
                record['content_type'] = ctype
        now=datetime.now(timezone(timedelta(hours=7))).isoformat()
        is_user_source=was_present and name in {item['file'] for item in DATASET['sources']}
        record.update(status='user_supplied_local_file' if is_user_source else 'verified_local' if was_present else 'downloaded',
                      sha256=digest(path), bytes=path.stat().st_size,verified_at=now)
        if is_user_source:
            record['origin']='Replacement CSV supplied by user; official URL is for attribution, not an asserted byte-for-byte online comparison.'
            record['snapshot']=DATASET['snapshot']
        elif not was_present:record['retrieved_at']=now
        print(name, record['bytes'], flush=True)
    except Exception as exc:
        record.update(status='unavailable', error=f'{type(exc).__name__}: {exc}')
        print(name, 'UNAVAILABLE', record['error'], flush=True)
    return record

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    local_fred = BASE / 'Fred.csv'
    copied = RAW / 'Fred_original.csv'
    if not copied.exists():
        shutil.copy2(local_fred, copied)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(download, URLS.items()))
    downloaded = RAW / 'FRED_MD_2026-09.csv'
    records.append({'file': str(copied.relative_to(BASE)), 'origin': 'Existing PTDLNC/Fred.csv',
                    'sha256': digest(copied), 'bytes': copied.stat().st_size,
                    'matches_official_2026_09': downloaded.exists() and digest(copied) == digest(downloaded)})
    (META / 'source_manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    if any(r.get('status') == 'unavailable' for r in records):
        raise SystemExit('One or more sources unavailable; see source_manifest.json')

if __name__ == '__main__':
    main()
