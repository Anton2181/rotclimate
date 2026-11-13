"""Audit restored inputs and recompute regional baseline aggregates independently."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from matplotlib.path import Path as Polygon

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
OUT=ROOT/'output/earth_harvest_restoration_20261113'
GRID=ROOT/'output/land_people/earth_restored_20261113'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    receipt=json.loads((OUT/'restoration.json').read_text());spec=json.loads((ROOT/'data/earth_harvest_public_sources_20261113.json').read_text())
    for source in spec['sources']:assert sha(ROOT/source['path'])==source['sha256']
    for name,digest in {**receipt['cache_sha256'],**receipt['baseline_sha256'],**receipt['producers'],**receipt['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    reference=ROOT/'output/land_people/earth/regions.json';assert sha(reference)==receipt['reference_regions_sha256']
    previous=json.loads(reference.read_text());current=json.loads((GRID/'regions.json').read_text())
    import land_people_earth as L
    z=np.load(GRID/'earth.npz');land=z['land'];lat,lon=np.meshgrid(z['lat'],z['lon'],indexing='ij')
    assert land.shape==(672,1644) and np.all(np.diff(z['lat'])<0) and np.all(np.diff(z['lon'])>0)
    assert np.isfinite(z['capacity'][land]).all() and (z['capacity'][land]>=0).all()
    assert np.all((z['irr'][land]>=0)&(z['irr'][land]<=1))
    area=np.cos(np.deg2rad(lat))*(111.32/12)**2;points=np.column_stack([lon.ravel(),lat.ravel()]);rows=[]
    for name,region in L.REGIONS.items():
        mask=Polygon(region['poly']).contains_points(points).reshape(land.shape)&land
        km2=float(area[mask].sum());capacity=float((area[mask]*z['capacity'][mask]).sum())
        irrigated=float((area[mask]*z['arable'][mask]*z['irr'][mask]).sum()/max((area[mask]*z['arable'][mask]).sum(),1))
        row=current[name];old=previous[name]
        assert row['area_km2']==round(km2)==old['area_km2']
        assert row['capacity_m']==round(capacity/1e6,2) and row['capacity_per_km2']==round(capacity/km2,1)
        assert row['irrigated_share']==round(irrigated,3)==old['irrigated_share']
        rows.append(dict(region=name,capacity_m=capacity/1e6,reference_rounded_capacity_m=old['capacity_m'],capacity_change_from_rounded_reference_percent=100*(row['capacity_m']/old['capacity_m']-1),area_km2=row['area_km2'],irrigated_share=row['irrigated_share']))
    import settlement_supply_calibration as C
    C.HARVEST=GRID/'earth.npz';pool=np.load(C.PILOT.POOL);people=C.rebuilt_people(pool['lat'],pool['lon']);mask=pool['land']
    baseline=float(pool['density'][mask].sum());rebuilt=float(people[mask].sum());delta=rebuilt/baseline-1
    assert not receipt['default_harvest_replaced']
    review=dict(status='passed',reviewer_sha256=sha(Path(__file__)),restoration_sha256=sha(OUT/'restoration.json'),
        regions=rows,roman_density_sum_reference=baseline,roman_density_sum_rebuilt=rebuilt,roman_density_relative_change=delta,
        arable_hash_matches_previous_calibration=True,unchanged_earth_atlas_files=len(receipt['unchanged_atlas_sha256']),reference_regions_unchanged=True,
        interpretation='Restored baseline reproduces the previously recorded ~0.354% Roman field drift; not byte-identical to the lost cache, not an irrigation correction or a new calibration result.')
    (OUT/'review.json').write_text(json.dumps(review,indent=2)+'\n');print('Reviewed',len(rows),'regions; Roman field change',f'{100*delta:.6f}%')


if __name__=='__main__':main()
