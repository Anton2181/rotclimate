"""Fetch pinned public CC-BY VDSA evidence; never executes source Stata code."""
from pathlib import Path
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1]
FILES=['2. Variable Descriptions.xlsx','VDSA data management for agricultural performance.do','README.docx',
       '4. Data on VDSA agricultural productivity at plot level.zip',
       'Data on VDSA agricultural productivity at hhlevel.zip','Cultivation.zip','General Endowments Schedule.zip']


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--cache',type=Path,default=ROOT/'data/cache/vdsa_8224522');a=ap.parse_args();a.cache.mkdir(parents=True,exist_ok=True)
    record=a.cache/'record.json'
    if record.exists():m=json.loads(record.read_text())
    else:
        with urllib.request.urlopen('https://zenodo.org/api/records/8224522',timeout=60) as r:m=json.load(r)
        record.write_text(json.dumps(m,indent=2)+'\n')
    if m['doi']!='10.5281/zenodo.8224522' or m['metadata']['license']['id']!='cc-by-4.0':raise ValueError('Pinned source identity/license changed')
    def fetch(f):
        path=a.cache/f['key'];checksum=f['checksum']
        def valid():return path.exists() and 'md5:'+hashlib.md5(path.read_bytes()).hexdigest()==checksum
        if not valid():
            temp=path.with_name(path.name+'.part')
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(f['links']['self'],timeout=60) as r,temp.open('wb') as out:
                        while chunk:=r.read(1024*1024):out.write(chunk)
                    if 'md5:'+hashlib.md5(temp.read_bytes()).hexdigest()!=checksum:raise ValueError('Source checksum mismatch')
                    temp.replace(path);break
                except Exception:
                    temp.unlink(missing_ok=True)
                    if attempt==2:raise
                    time.sleep(1)
        print('Verified',f['key'],flush=True)
        return dict(name=f['key'],bytes=path.stat().st_size,source_checksum=checksum,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),url=f['links']['self'])
    chosen=[f for f in m['files'] if f['key'] in FILES]
    if len(chosen)!=len(FILES):raise ValueError('Missing pinned files')
    with ThreadPoolExecutor(max_workers=3) as pool:files=list(pool.map(fetch,chosen))
    out=ROOT/'calibration/earth_components_20261105/vdsa_source.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(dict(record=8224522,doi=m['doi'],license=m['metadata']['license'],creators=m['metadata']['creators'],publication_date=m['metadata']['publication_date'],files=files),indent=2)+'\n')


if __name__=='__main__':main()
