"""Restore public Earth harvest inputs in cache and rebuild a separate baseline.

This repeats an already exposed baseline, not a new calibration or adoption.
Does not overwrite the committed default regional summary or atlas files.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'data/earth_harvest_public_sources_20261113.json'
OUT=ROOT/'output/earth_harvest_restoration_20261113'
GRID=ROOT/'output/land_people/earth_restored_20261113'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    spec=json.loads(SPEC.read_text());OUT.mkdir(parents=True,exist_ok=True)
    protected={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'atlases/earth_fit').rglob('*')) if p.is_file()}
    reference=ROOT/'output/land_people/earth/regions.json';reference_hash=sha(reference)
    def fetch(s):
        path=ROOT/s['path'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            partial=path.with_suffix(path.suffix+'.part')
            try:
                with urllib.request.urlopen(s['url'],timeout=60) as response,partial.open('wb') as target:
                    while data:=response.read(1048576):target.write(data)
                assert sha(partial)==s['sha256'],f'Source changed: {s["path"]}'
                partial.replace(path)
            finally:partial.unlink(missing_ok=True)
        assert sha(path)==s['sha256'] and path.stat().st_size==s['bytes'],s['path']
        if path.suffix=='.zip':
            with zipfile.ZipFile(path) as archive:assert archive.testzip() is None
        else:assert json.loads(path.read_text())['type']=='FeatureCollection'
        print('Verified',s['path'],flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,spec['sources']))
    log=[]
    for command in [['scripts/arable_slope_earth.py'],['scripts/land_people_earth.py','--out',str(GRID.relative_to(ROOT))]]:
        result=subprocess.run([sys.executable,'-u',*command],cwd=ROOT,check=True,text=True,capture_output=True)
        log.append(dict(command=command,stdout=result.stdout));print(result.stdout,flush=True)
    arable=ROOT/'data/cache/arable_slope_earth/arable_5m.npz'
    assert sha(arable)==spec['reference_arable_sha256'],'ETOPO/arable changed; retain rebuild as diagnostic only'
    assert sha(reference)==reference_hash
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    paths=[Path(__file__),SPEC,ROOT/'scripts/arable_slope_earth.py',ROOT/'scripts/land_people_earth.py',ROOT/'scripts/land_people.py',ROOT/'data/arable_slope_model.json']
    receipt=dict(status='restored_separate_baseline_not_adopted',sources=spec['sources'],etopo_url=spec['etopo_url'],
        cache_sha256={str(p.relative_to(ROOT)):sha(p) for p in [arable,ROOT/'data/cache/arable_slope_earth/etopo60_window.npy']},
        baseline_sha256={str(p.relative_to(ROOT)):sha(p) for p in [GRID/'earth.npz',GRID/'regions.json']},
        producers={str(p.relative_to(ROOT)):sha(p) for p in paths},unchanged_atlas_sha256=protected,
        reference_regions_sha256=reference_hash,commands=log,default_harvest_replaced=False)
    (OUT/'restoration.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Restored separate baseline; default regional summary and Earth atlas unchanged')


if __name__=='__main__':main()
