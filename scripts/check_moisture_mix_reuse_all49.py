"""Full development-field equivalence for an isolated mixing-cache proposal.

Paired order is for equality only. It is not a timing experiment.
"""
from dataclasses import asdict
import hashlib
import json
from multiprocessing import Pool
import os
from pathlib import Path
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from probe_moisture_mix_reuse import proposed_function
from rotclimate import earth,joint,moisture
from rotclimate.config import Params
from rotclimate.koppen import monthly_stats

OUT=ROOT/'output/moisture_mix_reuse_20261110_all49_float_resolution'


def one(job):
    import numpy as np
    name,specs,record,archive,identity=job;earth.REGIONS.update(specs)
    case=earth.region_case(name,56.0)
    if case_hash(case)!=record['case_identity']:raise ValueError('Changed case: '+name)
    base=joint.earth_profile(Params.from_json(ROOT/'calibration/joint_ocean_land_20261110/reference_params.json'))
    path=OUT/(name+'.json')
    if path.exists():
        previous=json.loads(path.read_text())
        if previous['identity']!=identity or previous['status']!='passed':raise ValueError('Changed saved check')
        return previous
    original=moisture.solve_moisture;proposal=proposed_function()[2]
    try:
        control=earth.run_case(base,case,steps=base.steps_per_year)
        moisture.solve_moisture=proposal
        optimized=earth.run_case(base,case,steps=base.steps_per_year)
    finally:moisture.solve_moisture=original
    if not control.numerics['all_checks_passed'] or control.numerics!=optimized.numerics:
        raise ValueError('Failed or changed numerical histories: '+name)
    arrays={}
    for key in ['T','Tsl','P','W','u','v','E','snow','days']:
        a,b=getattr(control,key),getattr(optimized,key)
        ah,bh=(hashlib.sha256(v.tobytes(order='C')).hexdigest() for v in (a,b))
        if a.shape!=b.shape or a.dtype!=b.dtype or ah!=bh:
            raise ValueError('Field bytes changed: '+name+' '+key)
        arrays[key]=dict(shape=list(a.shape),dtype=a.dtype.str,sha256=ah)
    # Tie the control back to the already frozen fresh r44 reference.
    if file_hash(ROOT/archive)!=record['cells_sha256']:raise ValueError('Changed original archive')
    st=monthly_stats(control.T,control.P,control.days,base.year_days,
        summer_solstice=base.winter_solstice_day+base.year_days/2)
    g=case.grid;mask=g.inmap & g.land & np.isfinite(case.obs_T).all(0)&np.isfinite(case.obs_P).all(0)
    with np.load(ROOT/archive) as old:
        if not np.array_equal(st['Tm'][:,mask].astype(np.float32),old['Ts']):raise ValueError('Control temperature drift')
        if not np.array_equal(st['Pm'][:,mask].astype(np.float32),old['Ps']):raise ValueError('Control rainfall drift')
    result=dict(status='passed',identity=identity,region=name,case_sha256=case_hash(case),
        exact_reference_monthly_climate=True,all_field_bytes_and_numerics_equal=True,
        field_bytes=arrays,numerics=control.numerics)
    write_json(path,result);print(name,'all field bytes and numerical history match',flush=True)
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    campaign=ROOT/'calibration/joint_ocean_land_20261110/campaign.json'
    plan=json.loads(campaign.read_text());records={};specs={};paths=[]
    for filename,digest in plan['reference_sha256'].items():
        path=ROOT/filename
        if file_hash(path)!=digest:raise ValueError('Changed paired reference')
        summary=json.loads(path.read_text());assert summary['complete']
        protocol=path.parent/'protocol.json';specs.update(json.loads(protocol.read_text())['region_specs'])
        paths.extend([path,protocol])
        for name,record in summary['regions'].items():
            records[name]=(record,str((path.parent/'cells'/(name+'.npz')).relative_to(ROOT)))
    assert len(records)==49
    before,after,_=proposed_function()
    sources=[Path(__file__),ROOT/'scripts/probe_moisture_mix_reuse.py',
        ROOT/'scripts/local_benchmark_protocol.py',campaign,
        ROOT/'calibration/joint_ocean_land_20261110/reference_params.json',
        *sorted((ROOT/'rotclimate').glob('*.py')),*paths]
    hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sources}
    identity=freeze(OUT/'protocol.json',dict(sources_sha256=hashes,regions=list(records),
        proposal_sha256=hashlib.sha256(after.encode()).hexdigest(),
        scope='49 reused development regions, paired exact-byte/numerical equivalence, not timing or new climate validation. '
              'Core files remain unchanged; only this worker interpreter swaps the function.'))
    (OUT/'source_before.py').write_text(before);(OUT/'source_proposed.py').write_text(after)
    with Pool(2) as pool:
        rows=list(pool.imap_unordered(one,[(n,specs,r,a,identity) for n,(r,a) in records.items()],chunksize=1))
    if any(file_hash(ROOT/n)!=h for n,h in hashes.items()):raise ValueError('Source changed during check')
    write_json(OUT/'summary.json',dict(status='passed',identity=identity,verified_regions=len(rows),
        rows=sorted(rows,key=lambda r:r['region']),adopted=False,
        scope='Exact field/numerical replay only. No independent climate validation, accuracy gain or timing claim.'))


if __name__=='__main__':main()
