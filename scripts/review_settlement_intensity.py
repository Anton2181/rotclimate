"""Verify saved Earth proposals with independent count, eligibility and pair checks."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_intensity_earth import OUT,PLAN,ORIGINAL,quality
from settlement_locations_earth import sha,write
from polity.settlement_locations import site_fields
from polity.settlement_intensity import intensity_fields


def main():
    result=json.loads((OUT/'results.json').read_text())
    if sha(ORIGINAL/'results.json')!=result['original_results_sha256']:
        raise ValueError('Changed original fixed-spacing evidence')
    if sha(PLAN)!=result['plan_sha256']:raise ValueError('Changed protocol')
    for path,digest in result['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed producer source')
    if sha(OUT/'positions.npz')!=result['positions_sha256']:raise ValueError('Changed positions')
    positions=dict(np.load(OUT/'positions.npz'));checked=[]
    for pool,receipt in result['inputs'].items():
        path=ROOT/receipt['path']
        if sha(path)!=receipt['sha256']:raise ValueError('Changed input')
        x=dict(np.load(path));cell=float(x['cell_km'])
        score,allowed=site_fields(x['density'],x['land'],x['water_km'],x['road'],x['elev'],cell,
            allowed=x['allowed'],aridity=x['aridity'])
        for row in [r for r in result['rows'] if r['pool']==pool]:
            p=positions[pool+'__'+row['variant']+'__'+str(row['seed'])]
            assert len(p)==row['n_model']==row['requested'] and row['shortfall']==0
            assert len(np.unique(p,axis=0))==len(p) and np.all(allowed[p[:,0],p[:,1]])
            intensity,spacing=intensity_fields(score,allowed,row['requested'],cell,
                history=x['history']**(800./row['scale_km']),coefficient=row['coefficient'])
            assert abs(intensity.sum()*cell**2-row['requested'])<1e-8
            pairs=cKDTree(p*cell).query_pairs(float(spacing.max()),output_type='ndarray')
            if len(pairs):
                a,b=p[pairs[:,0]],p[pairs[:,1]]
                threshold=.5*(spacing[a[:,0],a[:,1]]+spacing[b[:,0],b[:,1]])
                distance=np.linalg.norm((a-b)*cell,axis=1)
                assert np.all(distance>threshold-1e-10)
            assert abs(row['Q']-quality(row))<1e-14
            checked.append(dict(pool=pool,variant=row['variant'],seed=row['seed'],count=len(p),
                                nearby_pairs_checked=len(pairs)))
        assert sha(path)==receipt['sha256']
    assert len(checked)==108
    write(OUT/'review.json',dict(status='passed',source_result_sha256=sha(OUT/'results.json'),
        rows_checked=len(checked),inputs_unchanged=True,count_and_eligibility=True,
        symmetric_pair_constraints=True,target_intensity_normalization=True,rows=checked))
    print('Verified108 draws: counts, eligibility, symmetric pairs, target normalization and unchanged inputs.')


if __name__=='__main__':main()
