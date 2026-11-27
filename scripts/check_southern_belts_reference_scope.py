"""Prove the guarded source addition is inactive for every r58 reference grid.

No forecast integration. Read the historical private inputs without modifying
them; verify every actual case ID and the exact scope of the source edit.
"""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/'output/climate_reference_20261127'
MODEL=REFERENCE/'model'
OUT=ROOT/'output/southern_zonal_belts_fix_20261127'
sys.path[:0]=[str(MODEL/'scripts'),str(MODEL),str(ROOT/'scripts')]
from local_benchmark_protocol import case_hash,file_hash,write_json


def main():
    assert not (OUT/'reference_scope.json').exists()
    before=(MODEL/'rotclimate/model.py').read_text()
    after=(ROOT/'rotclimate/model.py').read_text()
    anchor='        if p.zonal_land_friction > 0:\n'
    start=after.index('        if np.any(lat < np.minimum(phi_hs, 0.0)):\n')
    end=after.index(anchor,start)
    addition=after[start:end]
    assert after[:start]+after[end:]==before
    qualification=json.loads((REFERENCE/'qualification.json').read_text())
    new_sources={}
    for name,digest in qualification['model_sources_sha256'].items():
        new_sources[name]=file_hash(ROOT/name)
        if name!='rotclimate/model.py':
            assert new_sources[name]==digest,name
    from rotclimate import earth
    from rotclimate.config import Params
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    plan=json.loads((ROOT/'calibration/current_climate_reference_20261127/plan.json').read_text())
    specs=json.loads((ROOT/plan['region_specs']).read_text())
    earth.REGIONS.update(specs)
    base=Params.from_json(ROOT/plan['params'])
    rows=[]
    for s in plan['cases']:
        case=earth.region_case(s['region'],56.,1100.)
        assert case_hash(case)==s['case_identity'],s['region']
        p=earth.earth_params(base,case)
        threshold=min(-(p.hadley_edge-abs(p.hadley_shift))*p.planet_radius**-.5,0.)
        count=int((case.grid.lat<threshold).sum())
        assert count==0,(s['region'],threshold)
        rows.append(dict(region=s['region'],case_identity=s['case_identity'],
            full_grid_lat_min=float(case.grid.lat.min()),branch_potential_latitude_below=threshold,
            cells_that_could_enter_new_branch_for_any_season=count))
    # Also disclose which completed finite parent domains could activate it.
    nested=json.loads((ROOT/'calibration/nested_pressure_context_20261127/plan.json').read_text())
    parent_rows=[]
    for s in nested['cases']:
        capture=ROOT/'output/nested_pressure_context_20261127'/('parent_'+s['part'])/'cells'/(s['region']+'_context.npz')
        with np.load(capture) as z:
            threshold=min(-(base.hadley_edge-abs(base.hadley_shift))*base.planet_radius**-.5,0.)
            parent_rows.append(dict(region=s['region'],full_grid_lat_min=float(z['full_lat'].min()),
                potentially_affected_full_grid_cells=int((z['full_lat']<threshold).sum())))
    write_json(OUT/'reference_scope.json',dict(status='r58_reference_all97_new_guard_inactive_proof_not_reintegrated',
        source_model_before_sha256=qualification['model_sources_sha256']['rotclimate/model.py'],
        source_model_after_sha256=file_hash(ROOT/'rotclimate/model.py'),new_model_sources_sha256=new_sources,
        exact_source_change='Only the guarded southern extra-tropical wind block inserted; every other byte matches old model.py.',
        inserted_block=addition,producer_sha256=file_hash(__file__),
        reference_qualification_sha256=file_hash(REFERENCE/'qualification.json'),
        params_sha256=file_hash(ROOT/plan['params']),regions=rows,finite_parent_domains=parent_rows,
        climate_integrations=0,interpretation='For fixed r58 Earth parameters and ALL full97 grids, branch is false for every s in[-1,1], including primer. Original numerical operations/inputs are unchanged. Historical protocols keep their original source hashes; this is an explicit compatibility proof, not new97 integrations or expanded climate validation.'))
    print('All97 actual case IDs exact; new branch inactive on every full grid for all seasons.')
    print('Potentially affected finite parents:',parent_rows)


if __name__=='__main__':
    main()
