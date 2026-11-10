"""Isolated performance probe; never edits a running calibration's model sources."""
from dataclasses import asdict
import inspect
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from rotclimate import earth,joint,moisture
from rotclimate.config import Params


def proposed_function():
    """Make the reviewed three-line change in this interpreter only."""
    before=inspect.getsource(moisture.solve_moisture)
    replacements={
        '    lamE_all = lamE\n':'    lamE_all = lamE\n    previous_mixed = None\n',
        '            mixed = mix(W)\n            new = solver.solve':
            '            mixed = mix(W) if previous_mixed is None else previous_mixed\n            new = solver.solve',
        '            mixed = mix(W) if mix is not None else W\n':
            '            mixed = mix(W) if mix is not None else W\n            previous_mixed = mixed if mix is not None else None\n',
    }
    after=before
    for old,new in replacements.items():
        if after.count(old)!=1:raise ValueError('Unexpected source shape; do not reinterpret probe')
        after=after.replace(old,new)
    namespace=dict(vars(moisture))
    exec(compile(after,'<isolated_moisture_mix_reuse>','exec'),namespace)
    return before,after,namespace['solve_moisture']


def main():
    import numpy as np
    out=ROOT/'output/moisture_mix_reuse_20261110';out.mkdir(parents=True,exist_ok=True)
    fit=ROOT/'calibration/joint_ocean_land_20261110/reference_params.json'
    base=joint.earth_profile(Params.from_json(fit));case=earth.region_case('japan',56)
    before,after,proposal=proposed_function();original=moisture.solve_moisture
    sources=[Path(__file__),fit,*sorted((ROOT/'rotclimate').glob('*.py'))]
    identity=freeze(out/'protocol.json',dict(region='japan',case_sha256=case_hash(case),params=asdict(base),
        sequence=['warmup','baseline','reuse','reuse','baseline'],
        sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
        scope='One reused-region ABBA timing and exact-replay pilot, no adoption, fitting or independent validation. '
              'CPU time is primary; wall time includes concurrent calibration contention.'))
    (out/'source_before.py').write_text(before);(out/'source_proposed.py').write_text(after)
    reference=None;rows=[]
    try:
        for mode in ['warmup','baseline','reuse','reuse','baseline']:
            moisture.solve_moisture=proposal if mode=='reuse' else original
            cpu=time.process_time();wall=time.perf_counter()
            result=earth.run_case(base,case,steps=base.steps_per_year)
            row=dict(mode=mode,cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
            assert result.numerics['all_checks_passed']
            if reference is None:
                reference=result
            else:
                for key in ['T','Tsl','P','W','u','v','E','snow','days']:
                    if not np.array_equal(getattr(result,key),getattr(reference,key)):
                        raise ValueError('Climate field changed: '+key)
                if result.numerics!=reference.numerics:
                    raise ValueError('Numerical history changed')
            row['all_fields_and_numerics_identical']=True;rows.append(row)
            print(json.dumps(row),flush=True)
    finally:
        moisture.solve_moisture=original
    for p in sources:
        if file_hash(p)!=json.loads((out/'protocol.json').read_text())['sources_sha256'][str(p.relative_to(ROOT))]:
            raise ValueError('Source changed during probe')
    baseline=np.mean([r['cpu_seconds'] for r in rows if r['mode']=='baseline'])
    reused=np.mean([r['cpu_seconds'] for r in rows if r['mode']=='reuse'])
    write_json(out/'summary.json',dict(status='passed',identity=identity,rows=rows,
        cpu_ratio=float(reused/baseline),adopted=False,
        limit='One-region pilot; no claim of general speedup or permission to change frozen campaign sources.'))


if __name__=='__main__':main()
