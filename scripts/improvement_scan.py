"""Resumable, failure-explicit Earth mechanism screen using cached WorldClim."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from multiprocessing import get_context
from earth_benchmark import load_params
from rotclimate import earth

TRAIN = ['california','iberia','southeast_us','levant','central_asia','east_china','east_australia','mexico']
HOLD = ['chile','cape','sw_australia','south_brazil','japan']
FRESH = ['pacific_nw','western_europe','eastern_europe','us_midwest','manchuria','new_zealand']
_CASES = {}
def one(job):
    label, region, params, overrides = job
    t = time.monotonic()
    try:
        if region not in _CASES:
            _CASES[region] = earth.region_case(region, 56.0)
        case = _CASES[region]
        p = load_params(params).replace(**overrides)
        result = earth.run_case(p, case)
        row = earth.compare(result, case)
        return dict(label=label, region=region, status='complete', seconds=time.monotonic()-t, metrics=row)
    except Exception as exc:
        return dict(label=label, region=region, status='failed', seconds=time.monotonic()-t, error=repr(exc))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--params',required=True); ap.add_argument('--settings',required=True)
    ap.add_argument('--out',required=True); ap.add_argument('--workers',type=int,default=4)
    a=ap.parse_args(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    settings={'base':{}, **json.loads(Path(a.settings).read_text())}
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'rotclimate').glob('*.py')}
    manifest=dict(params=json.loads(Path(a.params).read_text()), settings=settings, sources=sources, cell_km=56,
                  groups=dict(training=TRAIN,previous_holdout=HOLD,midlatitude=FRESH))
    mf=out/'manifest.json'
    if mf.exists() and json.loads(mf.read_text())!=manifest:
        raise ValueError('Resume refused: inputs or source changed; use a new output directory')
    mf.write_text(json.dumps(manifest,indent=2))
    rows={}
    for f in out.glob('case_*.json'):
        row=json.loads(f.read_text()); rows[(row['label'],row['region'])]=row
    jobs=[(label,r,a.params,o) for label,o in settings.items() for r in TRAIN+HOLD+FRESH if (label,r) not in rows]
    with get_context('fork').Pool(a.workers) as pool:
        for row in pool.imap_unordered(one,jobs,chunksize=1):
            rows[(row['label'],row['region'])]=row
            (out/f"case_{row['label']}_{row['region']}.json").write_text(json.dumps(row,indent=1))
            print(f"{len(rows)}/{len(settings)*19} {row['label']} {row['region']}: "
                  f"{row.get('metrics',{}).get('climate_distance',row.get('error'))} ({row['seconds']:.1f}s)",flush=True)
    summary={}
    for label in settings:
        rr=[rows[(label,r)] for r in TRAIN+HOLD+FRESH]
        if any(r['status']!='complete' for r in rr):
            summary[label]={'status':'failed'}; continue
        costs={r['region']:r['metrics']['climate_distance'] for r in rr}
        summary[label]={'status':'complete', **{name:sum(costs[r] for r in regions)/len(regions)
            for name,regions in {**manifest['groups'],'all':TRAIN+HOLD+FRESH}.items()},'regions':costs}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__': main()
