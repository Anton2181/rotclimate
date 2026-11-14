"""Capture all fixed weather-grid cells before regional reference ETo outputs."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'calibration/regional_reference_forcing_20261114/plan.json'
DEST=ROOT/'data/source/regional_reference_forcing_20261114'


def digest(data):return hashlib.sha256(data).hexdigest()


def capture(cell,grid):
    path=DEST/(cell['id']+'.json')
    query=dict(parameters=','.join(grid['parameters']),community='AG',longitude=cell['longitude'],latitude=cell['latitude'],start=grid['start'],end=grid['end'],format='JSON',**{'time-standard':grid['time_standard']})
    url='https://power.larc.nasa.gov/api/temporal/daily/point?'+urllib.parse.urlencode(query)
    if not path.exists():
        for attempt in range(5):
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
                with urllib.request.urlopen(request,timeout=60) as response:data=response.read()
                json.loads(data);path.write_bytes(data);break
            except (urllib.error.URLError,TimeoutError):
                if attempt==4:raise
                time.sleep(min(2**attempt,8))
    raw=path.read_bytes();data=json.loads(raw)
    assert len(data['geometry']['coordinates'])==3,'Provider grid elevation required'
    assert data['header']['time_standard']=='LST'
    semantic=json.dumps(dict(parameters=data['properties']['parameter'],geometry=data['geometry'],units=data['parameters'],fill_value=data['header']['fill_value']),sort_keys=True,separators=(',',':')).encode()
    return dict(cell=cell,url=url,file=str(path.relative_to(ROOT)),sha256=digest(raw),semantic_sha256=digest(semantic),geometry=data['geometry'],parameters=data['parameters'],fill_value=data['header']['fill_value'],source_header=data['header'])


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());grid=plan['weather_grid'];DEST.mkdir(parents=True,exist_ok=True)
    records=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks={pool.submit(capture,cell,grid):cell['id'] for cell in grid['cells']}
        for future in as_completed(tasks):
            result=future.result();records.append(result)
            print('Captured',len(records),'/30',result['cell']['id'],flush=True)
    records.sort(key=lambda r:r['cell']['id'])
    receipt=dict(status='captured_before_regional_eto_and_field_outputs',plan_sha256=digest(PLAN.read_bytes()),capturer_sha256=digest(Path(__file__).read_bytes()),sources=records,adopt=False)
    (DEST/'sources.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('All30declared weather cells retained')


if __name__=='__main__':main()
