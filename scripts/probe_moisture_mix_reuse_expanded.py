"""Broader exact-field and counterbalanced CPU checks for the isolated cache."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from probe_moisture_mix_reuse import proposed_function
from rotclimate import earth,joint,moisture
from rotclimate.config import Params


def main():
    import numpy as np
    out=ROOT/'output/moisture_mix_reuse_20261110_expanded';out.mkdir(parents=True,exist_ok=True)
    specs=['calibration/local_accuracy_20261023/regions_dev12.json',
           'calibration/sealed_20261031/regions.json','calibration/sealed_20261031b/regions.json']
    for path in specs:earth.REGIONS.update(json.loads((ROOT/path).read_text()))
    baseline='calibration/joint_ocean_land_20261110/reference_params.json'
    c3='calibration/joint_ocean_land_20261110/warm_C3_start_params.json'
    jobs=[('bengal',baseline),('north_queensland',baseline),('patagonia',baseline),('japan',c3)]
    cases={name:earth.region_case(name,56) for name,_ in jobs}
    sources=[Path(__file__),ROOT/'scripts/probe_moisture_mix_reuse.py',
        *[ROOT/p for p in specs],ROOT/baseline,ROOT/c3,*sorted((ROOT/'rotclimate').glob('*.py'))]
    hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sources}
    identity=freeze(out/'protocol.json',dict(jobs=jobs,
        cases_sha256={name:case_hash(case) for name,case in cases.items()},sources_sha256=hashes,
        sequence=['warmup','baseline','reuse','reuse','baseline'],
        scope='Isolated unchanged-physics counterbalanced timing on known cases, no calibration or adoption. '
              'CPU ratios, not wall time under concurrent search contention. All fields/numerical histories must be exact.'))
    before,after,proposal=proposed_function();original=moisture.solve_moisture
    (out/'source_before.py').write_text(before);(out/'source_proposed.py').write_text(after)
    records=[]
    try:
        for name,fit in jobs:
            base=joint.earth_profile(Params.from_json(ROOT/fit));case=cases[name]
            reference=None;rows=[]
            for mode in ['warmup','baseline','reuse','reuse','baseline']:
                moisture.solve_moisture=proposal if mode=='reuse' else original
                cpu=time.process_time();wall=time.perf_counter()
                result=earth.run_case(base,case,steps=base.steps_per_year)
                row=dict(mode=mode,cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
                if not result.numerics['all_checks_passed']:raise ValueError('Numerical failure')
                if reference is None:reference=result
                else:
                    for key in ['T','Tsl','P','W','u','v','E','snow','days']:
                        if not np.array_equal(getattr(result,key),getattr(reference,key)):
                            raise ValueError('Changed field: '+name+' '+key)
                    if result.numerics!=reference.numerics:raise ValueError('Changed numerical history')
                row['all_fields_and_numerics_identical']=True;rows.append(row)
                print(name,json.dumps(row),flush=True)
            a=np.mean([r['cpu_seconds'] for r in rows if r['mode']=='baseline'])
            b=np.mean([r['cpu_seconds'] for r in rows if r['mode']=='reuse'])
            record=dict(region=name,fit=fit,params=asdict(base),case_sha256=case_hash(case),
                rows=rows,baseline_cpu_seconds=float(a),reuse_cpu_seconds=float(b),cpu_ratio=float(b/a))
            records.append(record);write_json(out/(name+'.json'),record)
    finally:moisture.solve_moisture=original
    if any(file_hash(ROOT/name)!=digest for name,digest in hashes.items()):raise ValueError('Sources changed')
    write_json(out/'summary.json',dict(status='passed',identity=identity,records=records,adopted=False,
        scope='Known-case performance/replay check only; no new independent climate validation or accuracy gain.'))


if __name__=='__main__':main()
