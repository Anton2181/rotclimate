"""Geometric kernel support only; does not run, score or alter climate."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy.ndimage import gaussian_filter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json
PLAN=ROOT/'calibration/nested_pressure_context_20261127/plan.json'
OUT=ROOT/'output/nested_pressure_context_20261127'


def main():
    target=OUT/'kernel_support.json'
    assert not target.exists()
    plan=json.loads(PLAN.read_text())
    params=json.loads((ROOT/plan['params']).read_text())
    rows=[]
    for s in plan['cases']:
        assert file_hash(ROOT/s['control_cells'])==s['control_cells_sha256']
        with np.load(ROOT/s['control_cells']) as z:
            ii,jj=z['i'],z['j']
        row=dict(region=s['region'])
        for label,size,offset in [('child',s['child_shape'],0),('parent',s['parent_shape'],52)]:
            for scale in ['slp_scale_km','slp_local_km']:
                # A unit indicator has zero exterior, so convolution counts
                # kernel mass on supplied finite-grid cells. Not T forcing.
                mass=gaussian_filter(np.ones(size),params[scale]/56.,mode='constant',cval=0.)
                missing=1.-mass[ii+offset,jj+offset]
                assert (missing>=-1e-14).all() and (missing<=1.+1e-14).all()
                row[label+'_'+scale]=dict(mean_unknown_exterior_weight=float(missing.mean()),
                    minimum=float(missing.min()),maximum=float(missing.max()))
        rows.append(row)
    write_json(target,dict(status='geometry_only_kernel_support_not_climate_or_uncertainty',
        plan_sha256=file_hash(PLAN),producer_sha256=file_hash(__file__),statistics=rows,climate_integrations=0,
        interpretation='Fraction of original truncate4 separable Gaussian weight outside supplied grid at scored cells. This is not the temperature error there, pressure/wind error, skill or domain-convergence evidence.'))
    for r in rows:
        print(r['region'],r['child_slp_scale_km']['mean_unknown_exterior_weight'],
              r['parent_slp_scale_km']['mean_unknown_exterior_weight'])


if __name__=='__main__':
    main()
