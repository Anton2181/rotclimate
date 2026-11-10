"""Re-use the existing equation observer with current, exact r44 controls."""
from pathlib import Path
import json
import os
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from check_moisture_sources import audit_one
from local_benchmark_protocol import file_hash,freeze,write_json
from rotclimate import earth


def main():
    plan_path=ROOT/'calibration/r44_rainfall_sources_20261110/plan.json'
    plan=json.loads(plan_path.read_text());out=ROOT/'output/r44_rainfall_sources_20261110'
    out.mkdir(parents=True,exist_ok=True)
    paths=[plan_path,Path(__file__),ROOT/'scripts/check_moisture_sources.py',
        ROOT/'scripts/benchmark_local.py',ROOT/'scripts/earth_benchmark.py',
        ROOT/'scripts/rainfall_metrics.py',ROOT/'scripts/local_benchmark_protocol.py',
        ROOT/plan['physics'],*sorted((ROOT/'rotclimate').glob('*.py'))]
    for filename in plan['spec_files']:
        paths.append(ROOT/filename);earth.REGIONS.update(json.loads((ROOT/filename).read_text()))
    for name,archive in plan['archives'].items():
        paths.extend([ROOT/archive/'cases'/(name+'.json'),ROOT/archive/'cells'/(name+'.npz')])
    sources={str(p.relative_to(ROOT)):file_hash(p) for p in paths}
    identity=freeze(out/'protocol.json',dict(plan=plan,sources_sha256=sources))
    rows=[]
    # One extra worker-equivalent; leave the existing calibration running unchanged.
    for name,archive in plan['archives'].items():
        row=audit_one((name,dict(plan,archive=archive),identity,str(out)))
        rows.append(row)
        if row['status']!='passed':raise RuntimeError('Preserved failed observer control: '+name)
    if any(file_hash(ROOT/name)!=digest for name,digest in sources.items()):
        raise ValueError('Source changed during the diagnostic')
    write_json(out/'summary.json',dict(status='passed',identity=identity,rows=rows,
        scope=plan['scope'],interpretation=plan['interpretation'],physics_adopted='r44'))
    print('All four exact controls and equation reconstructions passed.',flush=True)


if __name__=='__main__':main()
