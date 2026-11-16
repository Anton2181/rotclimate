"""Replay the already qualified floodplain harvest in isolated cache paths."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import floodplain_earth as F

OUT=ROOT/'output/urban_population_recipe_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/population_recipe_replay.json'
RESTORE=OUT/'restored'
AMENDMENT=PLAN.parent/'population_recipe_compatibility_a1.json'


def old_world_default_adapter(function):
    def adapted(*args,extra_crops=None,old_world=True,**kwargs):
        if extra_crops not in (None,{}) or old_world is not True:
            raise ValueError('Legacy replay accepts only default Old World crops')
        return function(*args,**kwargs)
    return adapted


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert subprocess.check_output(['git','show','HEAD:'+str(AMENDMENT.relative_to(ROOT))],cwd=ROOT)==AMENDMENT.read_bytes()
    prior=ROOT/'output/urban_hinterland_provenance_20261116';r=json.loads((prior/'results.json').read_text());review=json.loads((prior/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(prior/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_hinterland_provenance.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    expected=json.loads((ROOT/'output/supply_people_level_20261114/results.json').read_text())['harvest_grid_sha256']
    archived=json.loads((ROOT/'output/floodplain_rule_20261114/results.json').read_text())
    assert sha(ROOT/'scripts/floodplain_earth.py')==archived['producer_sha256']
    spec=ROOT/'data/earth_harvest_public_sources_20261113.json';public=json.loads(spec.read_text())
    for source in public['sources']:
        p=ROOT/source['path'];assert p.exists(),f'Restore the already exposed public source first: {p}'
        assert sha(p)==source['sha256'] and p.stat().st_size==source['bytes'],source['path']
    arable=ROOT/'data/cache/arable_slope_earth/arable_5m.npz';assert sha(arable)==public['reference_arable_sha256']
    OUT.mkdir(parents=True,exist_ok=True)
    paths=[Path(__file__),PLAN,AMENDMENT,ROOT/'tests/test_urban_crop_compatibility.py',spec,ROOT/'scripts/floodplain_earth.py',ROOT/'scripts/land_people_earth.py',ROOT/'scripts/land_people.py',
           ROOT/'scripts/arable_slope_earth.py',ROOT/'polity/seasons.py',ROOT/'polity/transport.py',ROOT/'harvest/models.py',
           ROOT/'rotclimate/biomes.py',ROOT/'output/floodplain_rule_20261114/results.json',ROOT/'output/land_people/earth_floodplain/regions.json',
           ROOT/'output/supply_people_level_20261114/results.json']
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    protected=dict(r['protected_sha256']);protected.update(r['sources_sha256'])
    for name in ['results.json','review.json',*r['files_sha256']]:protected[str((prior/name).relative_to(ROOT))]=sha(prior/name)
    for p in (ROOT/'atlases/earth_fit').rglob('*'):
        if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    for p in [ROOT/'output/land_people/earth_floodplain/regions.json',ROOT/'output/floodplain_rule_20261114/basins.json']:
        if p.exists():protected[str(p.relative_to(ROOT))]=sha(p)
    receipt=dict(status='running',expected_grid_sha256=expected,sources_sha256=sources,protected_sha256=protected,
                 public_sources_verified=len(public['sources']),raw_or_model_parameters_changed=False,climate_fit=False,adopt=False)
    try:
        F.OUT=RESTORE/'basin';F.GRID=RESTORE/'grid'
        compute=F.L.compute
        def compatible_compute(*args,**kwargs):
            legacy=F.L.analyse
            F.L.analyse=old_world_default_adapter(legacy)
            try:return compute(*args,**kwargs)
            finally:F.L.analyse=legacy
        F.L.compute=compatible_compute
        try:F.main()
        finally:F.L.compute=compute
        grid=F.GRID/'earth.npz';regions=F.GRID/'regions.json';fields=F.OUT/'fields.npz'
        receipt['actual_grid_sha256']=sha(grid)
        assert receipt['actual_grid_sha256']==expected,'Restored grid differs from qualified archived identity'
        assert regions.read_bytes()==(ROOT/'output/land_people/earth_floodplain/regions.json').read_bytes(),'Archived region summary differs'
        with np.load(fields) as z:
            qualifying=int((z['s']>0).sum())
        assert qualifying==archived['qualifying_cells']
        for name,digest in protected.items():assert sha(ROOT/name)==digest,name
        receipt.update(status='passed_exact_qualified_grid_replay',qualifying_cells=qualifying,archived_regions_byte_exact=True,
                       files_sha256={str(p.relative_to(ROOT)):sha(p) for p in [grid,regions,fields,F.OUT/'basins.json']})
    except Exception as error:
        receipt.update(status='failed_preserved_unqualified_candidate',error=f'{type(error).__name__}: {error}')
        (OUT/'restoration.json').write_text(json.dumps(receipt,indent=2)+'\n')
        raise
    (OUT/'restoration.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Qualified floodplain grid restored EXACTLY;archived regions exact;1275 qualifying cells;all atlas assets unchanged',flush=True)


if __name__=='__main__':main()
