"""Capture the predeclared NASA POWER daily inputs without calculating ETo."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'calibration/reference_eto_20261114/plan.json'
DEST=ROOT/'data/source/reference_eto_20261114'


def digest(data):return hashlib.sha256(data).hexdigest()


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());weather=plan['weather'];DEST.mkdir(parents=True,exist_ok=True)
    receipt=[]
    for site in plan['sites']:
        query=dict(parameters=','.join(weather['parameters']),community='AG',longitude=site['longitude'],latitude=site['latitude'],start=weather['start'],end=weather['end'],format='JSON',**{'time-standard':weather['time_standard']})
        url=weather['url']+'?'+urllib.parse.urlencode(query)
        path=DEST/(site['id']+'.json')
        if not path.exists():
            for attempt in range(4):
                try:
                    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
                    with urllib.request.urlopen(request,timeout=60) as response:raw=response.read()
                    json.loads(raw);path.write_bytes(raw);break
                except (urllib.error.URLError,TimeoutError):
                    if attempt==3:raise
                    time.sleep(2*(attempt+1))
        raw=path.read_bytes();data=json.loads(raw)
        parameters=data['properties']['parameter'];coordinates=data['geometry']['coordinates']
        assert len(coordinates)==3 and all(isinstance(v,(int,float)) for v in coordinates),'Provider grid elevation required'
        assert set(weather['parameters'])<=set(parameters)
        semantic=json.dumps(dict(parameters=parameters,geometry=data['geometry'],units=data['parameters'],fill_value=data['header']['fill_value']),sort_keys=True,separators=(',',':')).encode()
        receipt.append(dict(site=site,url=url,file=str(path.relative_to(ROOT)),sha256=digest(raw),semantic_sha256=digest(semantic),geometry=data['geometry'],parameters=data['parameters'],fill_value=data['header']['fill_value'],source_header=data['header']))
        print(site['id'],'raw bytes',len(raw),'geometry',coordinates,'dates',len(parameters['T2M']),flush=True)
    result=dict(status='captured_before_weather_eto_outputs',plan_sha256=digest(PLAN.read_bytes()),capturer_sha256=digest(Path(__file__).read_bytes()),sources=receipt,adopt=False)
    (DEST/'sources.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Captured all three declared source snapshots')


if __name__=='__main__':main()
