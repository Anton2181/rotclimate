"""Summarize adapted foraging scenarios by coarse-grid Whittaker climate biome.

Read completed products only: no climate or foraging integration. The coarse
climate is reconstructed exactly as in the foraging export, then classified
without extrapolating outside the digitized Whittaker envelopes.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from foraging.export import area_average,land_average
from harvest.export import climate_arrays,geometry,physical_metadata,surface_months
from rotclimate.biomes import classify,LABELS,SOURCE

FITS=('free_fit','earth_fit','whittaker_fit')
FIELDS=('density_people_km2','foraging_hours_day','meat_fraction',
        'scarcity_days_year','converged','unsupported','land_fraction','cell_area_km2')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_packet(data,metadata):
    blob=(data/'foraging.bin').read_bytes()
    if hashlib.sha256(blob).hexdigest()!=metadata['binary_sha256']:
        raise ValueError('Foraging packet hash differs: '+str(data))
    result={}
    for name in FIELDS:
        spec=metadata['arrays'][name]
        value=np.frombuffer(blob,dtype=np.dtype(spec['dtype']),
            count=int(np.prod(spec['shape'])),offset=spec['offset_bytes']).reshape(spec['shape'])
        if list(value.shape)!=metadata['shape']:raise ValueError('Mismatched scenario field: '+name)
        result[name]=value
    return result


def weighted_mean(values,weights):
    denominator=float(weights.sum())
    return float((values*weights).sum()/denominator) if denominator>0 else None


def summarize_fit(atlas,record):
    data=atlas/'data'
    fm=json.loads((data/'foraging.json').read_text());am=json.loads((data/'atlas.json').read_text())
    fingerprint=hashlib.sha256(json.dumps(fm['inputs'],sort_keys=True).encode()).hexdigest()
    if fm['fingerprint']!=fingerprint or record['fingerprint']!=fingerprint:
        raise ValueError('Unpaired completed scenario identity: '+atlas.name)
    if sha(data/'atlas.bin')!=fm['inputs']['climate_sha256']:
        raise ValueError('Changed scenario climate: '+atlas.name)
    if physical_metadata(am)!=fm['inputs']['physical_metadata']:
        raise ValueError('Changed physical metadata: '+atlas.name)
    for path,digest in fm['inputs']['sources'].items():
        if sha(ROOT/path)!=digest:raise ValueError('Changed frozen scenario source: '+path)
    native=climate_arrays(data,am);native_shape=tuple(fm['inputs']['native_shape'])
    if native['elev'].shape!=native_shape:raise ValueError('Changed native geography shape')
    geo,geo_inputs=geometry(am,native_shape)
    if json.loads(json.dumps(geo_inputs))!=fm['geography_inputs']:raise ValueError('Changed scenario geography')
    shape=tuple(fm['shape']);fraction=geo['land_fraction'].astype(float)
    coarse_fraction=area_average(fraction,shape)
    temperature,precipitation,_,_=surface_months(am,native)
    t=land_average(temperature,fraction,shape)
    p=land_average(precipitation,fraction,shape)
    a=read_packet(data,fm);land=coarse_fraction>0
    np.testing.assert_array_equal(a['land_fraction'][land],coarse_fraction.astype(np.float32)[land])
    for name,value in a.items():
        if not np.isfinite(value[land]).all():raise ValueError('Nonfinite scenario land field: '+name)
    for key in ('converged','unsupported'):
        if not np.isin(a[key][land],[0,1]).all():raise ValueError('Invalid status field: '+key)
    if ((a['density_people_km2'][land]<0).any() or (a['cell_area_km2'][land]<=0).any()
            or not np.isfinite(t[:,land]).all() or not np.isfinite(p[:,land]).all()):
        raise ValueError('Invalid scenario area, climate or density')
    annual_t=t.mean(0);annual_p=p.sum(0)
    biome=classify(annual_t,annual_p,land)
    if not np.isin(biome[land],np.arange(len(LABELS))).all():raise ValueError('Unexpected land biome')
    area=np.where(land,a['cell_area_km2'].astype(float),0.)
    density=np.where(land,a['density_people_km2'].astype(float),0.)
    people=density*area
    rows=[]
    for code,label in enumerate(LABELS):
        own=land&(biome==code)
        own_area=area[own];own_people=people[own]
        total_area=float(own_area.sum());population=float(own_people.sum())
        rows.append(dict(fit=atlas.name,biome_id=code,biome=label,
            analysis_land_cells=int(own.sum()),land_area_km2=total_area,
            land_area_share=total_area/float(area.sum()),scenario_people=population,
            mean_density_people_km2=population/total_area if total_area else None,
            population_weighted_foraging_hours_day=weighted_mean(a['foraging_hours_day'][own],own_people),
            population_weighted_meat_energy_share=weighted_mean(a['meat_fraction'][own],own_people),
            population_weighted_intake_shortfall_days_year=weighted_mean(a['scarcity_days_year'][own],own_people),
            nonconverged_land_share=weighted_mean(1-a['converged'][own].astype(float),own_area),
            nonconverged_scenario_people_share=weighted_mean(1-a['converged'][own].astype(float),own_people),
            unsupported_land_share=weighted_mean(a['unsupported'][own].astype(float),own_area),
            area_weighted_mean_annual_temperature_c=weighted_mean(annual_t[own],own_area),
            area_weighted_annual_precipitation_mm=weighted_mean(annual_p[own],own_area)))
    np.testing.assert_allclose(sum(r['land_area_km2'] for r in rows),fm['summary']['land_km2'],rtol=3e-7,atol=.01)
    np.testing.assert_allclose(sum(r['scenario_people'] for r in rows),fm['summary']['total_scenario_people'],rtol=3e-7,atol=.01)
    return rows,dict(foraging_fingerprint=fingerprint,
        files_sha256={str((data/n).relative_to(ROOT)):sha(data/n) for n in ['foraging.json','foraging.bin','atlas.json','atlas.bin']},
        analysis_shape=list(shape),land_area_km2=float(area.sum()),scenario_people=float(people.sum()),
        full_export_summary=fm['summary'],run=fm['run'],
        classifications_reconstruct_exact_export_climate=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--atlases',type=Path,default=ROOT/'output/foraging_20261027/staging')
    parser.add_argument('--export-status',type=Path,default=ROOT/'output/foraging_20261027/export_status.json')
    parser.add_argument('--out',type=Path,default=ROOT/'output/foraging_20261027/biomes')
    args=parser.parse_args();status=json.loads(args.export_status.read_text())
    if status.get('status')!='passed' or any(status.get('atlases',{}).get(name,{}).get('status')!='passed' for name in FITS):
        raise SystemExit('All three staged exports must finish and verify before biome summaries')
    rows=[];fits={}
    for name in FITS:
        atlas=args.atlases.resolve()/name
        own,receipt=summarize_fit(atlas,status['atlases'][name]);rows.extend(own);fits[name]=receipt
    args.out.parent.mkdir(parents=True,exist_ok=True)
    payload=dict(status='passed',climate_integrations=0,foraging_simulations=0,
        method='Reconstruct the export\'s own coastal-land-weighted monthly ground climate on its independent coarse grid. Classify mean of twelve equal-bin temperatures and sum of twelve precipitations with the existing digitized Whittaker polygons; assign each coarse cell once. Never extrapolate outside the diagram. Sum stored coastal land areas and density times those areas. Weight effort, diet and intake shortfall by scenario people; weight convergence shares by land area. Biomes remain in polygon-ID order, not ranked by a development score.',
        interpretation='Finite-horizon adapted FORGE scenarios, not validated carrying capacities, agricultural support, historical censuses or a ranking of civilization. Intake shortfall includes ordinary reserve drawdown; it is not famine mortality.',
        caveats=[
            'Classification of coarse mean climate differs from fractional biome areas in the fine atlas; mixed and coastal cells can change category. These shares do not replace the normal atlas\'s biome coverage percentages.',
            'Outside-diagram climates remain a separate class. Empty classes and zero-population means are explicitly null.',
            'Foraging resources are proxy scenarios. Biome labels do not alter the human kernel or its resource parameters.',
            'Annual-state nonconvergence and multiyear population cycles remain visible; a final-window mean is not certified equilibrium.',
            'A spatial association among modeled outputs and modeled biome classes is not causal evidence about societal development.'
        ],biome_classification_source=SOURCE,
        sources_sha256={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),
            'rotclimate/biomes.py':sha(ROOT/'rotclimate/biomes.py'),
            'data/whittaker_biomes.csv':sha(ROOT/'data/whittaker_biomes.csv'),
            str(args.export_status.resolve().relative_to(ROOT)):sha(args.export_status)},
        fits=fits,rows=rows)
    json_path=args.out.with_suffix('.json');csv_path=args.out.with_suffix('.csv')
    json_path.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    with csv_path.open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(status='passed',rows=len(rows),json=str(json_path),csv=str(csv_path)),indent=2))


if __name__=='__main__':main()
