"""Independently reconstruct annual resource/energy ledgers from stored packets."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(atlas):
    data=Path(atlas)/'data';m=json.loads((data/'foraging.json').read_text())
    for name,digest in m['inputs']['sources'].items():
        assert sha(ROOT/name)==digest,'Changed model/export source: '+name
    for name,key in [('atlas.bin','climate_sha256'),('harvest.bin','province_binary_sha256'),('harvest.json','province_metadata_sha256')]:
        assert sha(data/name)==m['inputs'][key],name
    blob=(data/'foraging.bin').read_bytes();assert hashlib.sha256(blob).hexdigest()==m['binary_sha256']
    a={k:np.frombuffer(blob,dtype=s['dtype'],count=int(np.prod(s['shape'])),offset=s['offset_bytes']).reshape(s['shape']).astype(float) for k,s in m['arrays'].items()}
    land=np.isfinite(a['land_fraction'])&(a['land_fraction']>0);checks={}
    def closure(name,positive,negative):
        supply=sum(a[k] for k in positive);loss=sum(a[k] for k in negative)
        residual=np.abs(supply-loss);scale=sum(np.abs(a[k]) for k in positive+negative)
        # Independent sums of stored float32 annual terms accumulate rounding.
        tolerance=2e-6+4e-7*scale
        assert np.all(residual[land]<=tolerance[land]),(name,float(residual[land].max()))
        checks[name]=dict(maximum_absolute=float(residual[land].max()),maximum_scaled=float((residual[land]/np.maximum(scale[land],1.)).max()))
    closure('plant_stock_kg_dm_km2',['annual_start_plant_stock_kg_dm_km2','annual_plant_supply_kg_dm_km2'],
        ['annual_plant_harvest_kg_dm_km2','annual_plant_decay_kg_dm_km2','plant_stock_kg_dm_km2'])
    closure('meat_stock_kg_dm_km2',['annual_start_meat_stock_kg_dm_km2','annual_meat_supply_kg_dm_km2'],
        ['annual_meat_harvest_kg_dm_km2','annual_meat_decay_kg_dm_km2','annual_unused_prey_kg_dm_km2','meat_stock_kg_dm_km2'])
    closure('fat_energy_mj_person',['annual_intake_mj_person'],
        ['annual_expenditure_mj_person','annual_reproduction_mj_person','annual_fat_energy_change_mj_person'])
    for source,supply in [('annual_plant_kgdm_km2','annual_plant_supply_kg_dm_km2'),('annual_meat_kgdm_km2','annual_meat_supply_kg_dm_km2')]:
        np.testing.assert_allclose(a[source][land],a[supply][land],rtol=2e-6,atol=1e-6)
    np.testing.assert_allclose(a['fat_kg'][land]-a['energy_debt_mj'][land]/m['parameters']['kernel_parameters']['fat_deficit_mj_kg'],a['effective_fat_kg'][land],rtol=3e-6,atol=2e-6)
    assert np.all(a['averaging_years_used'][land]==np.minimum(a['years_simulated'][land],m['run']['averaging_years']))
    return dict(status='passed',atlas=str(atlas),foraging_fingerprint=m['fingerprint'],
        source_hashes_checked=len(m['inputs']['sources']),stored_annual_ledgers=checks,
        land_cells=int(land.sum()),climate_and_agriculture_unchanged=True,
        per_capita_energy_note='Per-capita final-year energy accounting is not a conserved whole-population demographic energy budget.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('atlases',nargs='+');parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=dict(status='passed',checks=[verify(Path(p)) for p in args.atlases],script_sha256=sha(Path(__file__)))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
