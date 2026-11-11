"""Independent invariants and exact overlap checks for the boundary extension."""
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.settlement_locations import site_fields
from polity.settlement_intensity import intensity_fields
from settlement_history_boundary_earth import OUT,PLAN,PRIOR
from settlement_locations_earth import sha,write
from settlement_intensity_earth import quality


def main():
    result=json.loads((OUT/'results.json').read_text());plan=json.loads(PLAN.read_text())
    for path,digest in result['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed producer source')
    checks={'plan_sha256':PLAN,'driver_sha256':ROOT/'scripts/settlement_history_boundary_earth.py',
        'positions_sha256':OUT/'positions.npz','prior_adaptive_results_sha256':PRIOR/'results.json',
        'prior_adaptive_positions_sha256':PRIOR/'positions.npz',
        'original_results_sha256':ROOT/'output/settlement_locations_20261110/results.json'}
    for key,path in checks.items():
        if result[key]!=sha(path):raise ValueError('Changed boundary evidence: '+key)
    checked=0;controls=0;prior=json.loads((PRIOR/'results.json').read_text())
    prior_rows={(r['pool'],r['variant'],r['seed']):r for r in prior['rows']}
    with np.load(OUT/'positions.npz') as positions,np.load(PRIOR/'positions.npz') as old_positions:
        for pool,receipt in result['inputs'].items():
            path=ROOT/receipt['path'];assert sha(path)==receipt['sha256']
            x=dict(np.load(path));cell=float(x['cell_km'])
            score,allowed=site_fields(x['density'],x['land'],x['water_km'],x['road'],x['elev'],cell,
                allowed=x['allowed'],aridity=x['aridity'])
            for row in [r for r in result['rows'] if r['pool']==pool]:
                key=(pool,row['variant'],row['seed']);name='__'.join(map(str,key));p=positions[name]
                assert len(p)==row['n_model']==row['requested'] and row['shortfall']==0
                assert len(np.unique(p,axis=0))==len(p) and np.all(allowed[p[:,0],p[:,1]])
                intensity,spacing=intensity_fields(score,allowed,row['requested'],cell,
                    history=x['history']**(800./row['scale_km']),coefficient=row['coefficient'])
                assert abs(intensity.sum()*cell**2-row['requested'])<1e-8
                pairs=cKDTree(p*cell).query_pairs(float(spacing.max()),output_type='ndarray')
                if len(pairs):
                    a,b=p[pairs[:,0]],p[pairs[:,1]]
                    threshold=.5*(spacing[a[:,0],a[:,1]]+spacing[b[:,0],b[:,1]])
                    assert np.all(np.linalg.norm((a-b)*cell,axis=1)>threshold-1e-10)
                assert abs(row['Q']-quality(row))<1e-14
                if row['scale_km']==450:
                    assert row==prior_rows[key] and np.array_equal(p,old_positions[name]);controls+=1
                checked+=1
    assert checked==plan['grid']['evaluations']==100 and controls==20
    write(OUT/'review.json',dict(status='passed',reviewer_sha256=sha(Path(__file__)),
        source_result_sha256=sha(OUT/'results.json'),rows_checked=checked,overlap_controls_exact=controls,
        count_and_eligibility=True,symmetric_pair_constraints=True,target_intensity_normalization=True,
        no_population_or_food_changes=True,adopt=False))
    print('Verified100 draws and20 exact controls; all count/eligibility/pair/normalization checks pass.')


if __name__=='__main__':main()
