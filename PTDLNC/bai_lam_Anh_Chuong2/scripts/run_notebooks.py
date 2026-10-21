"""Execute notebooks with an isolated, workspace-local kernel specification."""
from pathlib import Path
import argparse
import json
import os
import sys
import time
import nbformat
from nbclient import NotebookClient

WORK=Path(__file__).resolve().parents[1]
ROOT=WORK.parents[1]
SPEC=ROOT/'.cache'/'jupyter'/'kernels'/'python3'
SPEC.mkdir(parents=True,exist_ok=True)
(SPEC/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
 'display_name':'Python 3 (PTDLNC)','language':'python'}),encoding='utf-8')
os.environ['JUPYTER_PATH']=str(SPEC.parents[1])
os.environ['JUPYTER_RUNTIME_DIR']=str(ROOT/'.cache'/'jupyter'/'runtime')
os.environ['IPYTHONDIR']=str(ROOT/'.cache'/'ipython')
Path(os.environ['JUPYTER_RUNTIME_DIR']).mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('names',nargs='*');args=parser.parse_args()
paths=[WORK/'notebooks'/name for name in args.names] if args.names else sorted((WORK/'notebooks').glob('*.ipynb'))
for path in paths:
    start=time.monotonic()
    print('RUN',path.name,flush=True)
    nb=nbformat.read(path,as_version=4)
    client=NotebookClient(nb,timeout=1200,kernel_name='python3',resources={'metadata':{'path':str(WORK/'notebooks')}})
    try:
        client.execute()
    finally:
        nbformat.write(nb,path)
    print('PASS',path.name,round(time.monotonic()-start,1),'seconds',flush=True)
