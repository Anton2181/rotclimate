"""Direct source/block/fold reconstruction of the count and coverage audit."""
import collections
import json
from pathlib import Path
import sys
import numpy as np
import openpyxl
import shapefile
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity import earth as E
from polity_earth_check import WINDOWS

OUT=ROOT/'output/settlement_counts_20261111';CONFIG=ROOT/'calibration/settlement_counts_20261111'
ORIGINAL=ROOT/'output/settlement_locations_20261110'


def equal(a,b):
    if b is None:assert a is None
    elif np.isinf(b):assert a=='infinite'
    else:assert np.isclose(a,b,rtol=1e-10,atol=1e-10),(a,b)


def direct_metrics(y,p,area):
    if np.any((y>0)&(p==0)):d=float('inf')
    else:
        good=y>0;d=float(2*(np.sum(p-y)+np.sum(y[good]*np.log(y[good]/p[good]))))
    total=float(y.sum());pred=float(p.sum())
    return dict(source_records=total,predicted_count=pred,land_km2=float(area.sum()),blocks=len(y),
        deviance=d,deviance_per_source_record=d/total if total else None,deviance_per_10000km2=10000*d/area.sum(),
        total_count_relative_error=abs(pred-total)/total if total else None,
        count_mass_to_relocate_after_normalization=float(np.abs(y/total-p/pred).sum()/2) if total and pred else None,
        count_rank=float(spearmanr(y,p).statistic) if len(y)>1 and np.ptp(y)>0 and np.ptp(p)>0 else None,
        positive_observation_zero_prediction_blocks=int(np.sum((y>0)&(p==0))))


def main():
    r=json.loads((OUT/'results.json').read_text())
    for key,path in {'plan_sha256':CONFIG/'plan.json','correction_sha256':CONFIG/'multiplicity_correction.json',
        'coverage_plan_sha256':CONFIG/'coverage_domain.json','module_sha256':ROOT/'polity/settlement_counts.py',
        'coverage_module_sha256':ROOT/'polity/population_coverage.py','producer_sha256':ROOT/'scripts/settlement_counts_earth.py',
        'positions_sha256':ORIGINAL/'positions.npz','blocks_sha256':OUT/'blocks.npz','predictions_sha256':OUT/'predictions.npz'}.items():assert sha(path)==r[key]
    for path,digest in {**r['parent_artifacts'],**r['matching_sources']}.items():assert sha(ROOT/path)==digest
    # Raw workbook read, retaining source areas without median filling.
    wb=openpyxl.load_workbook(ROOT/'data/cache/hanson2016/cities.xlsx',read_only=True,data_only=True)
    try:
        city_rows=list(wb['Cities'].values);area_rows=list(wb['Areas'].values)
    finally:wb.close()
    cities=[dict(zip(city_rows[0],v)) for v in city_rows[1:] if v[0]]
    areas=collections.defaultdict(list)
    for row in area_rows[1:]:
        if row[0]:areas[row[0]].append(row)
    date_selected=[c for c in cities if isinstance(c['Start Date'],(float,int)) and c['Start Date']<=150
                   and (not isinstance(c['End Date'],(float,int)) or c['End Date']>=150)]
    for label,subset in [('all_cities',cities),('AD150',date_selected)]:
        s=r['source_support']['roman'][label];states=collections.Counter();basis=collections.Counter();multiplicity=collections.Counter();nondefault=0
        for c in subset:
            values=areas[c['Primary Key']];multiplicity[str(len(values))]+=1
            if not values:states['missing_area_record']+=1;continue
            if len(values)>1:states['ambiguous_area_records']+=1;continue
            v=values[0][1];basis[str(values[0][2])]+=1
            try:n=float(v)
            except (ValueError,TypeError):n=float('nan')
            if not np.isfinite(n):states['nonnumeric_or_nonfinite']+=1
            elif n<=0:states['nonpositive']+=1
            else:
                states['positive_numeric']+=1
                if n in (20,30):states['exact20_or30ha_candidate']+=1
                else:nondefault+=1
        assert s['city_records']==len(subset) and s['area_states']==dict(states)
        assert s['raw_estimate_basis_counts']==dict(basis) and s['area_join_multiplicities']==dict(multiplicity)
        assert s['positive_nondefault_value_candidates']==nondefault
    reader=shapefile.Reader(str(ROOT/'data/cache/han_ad2/shp/CountyPointsWithPopulation'),encoding='utf-8')
    all_han=[v.as_dict() for v in reader.iterRecords()]
    for year,s in r['source_support']['han'].items():
        selected=[v for v in all_han if v['YEAR']==year]
        assert s['records']==len(selected) and s['unique_county_IDs']==len({v['CountyID'] for v in selected})
        assert s['source_type_counts']==dict(collections.Counter(v['TYPE'] for v in selected))
        assert s['adjustment_flag_counts']==dict(collections.Counter(str(v['Adjusted_o']) for v in selected))
        assert s['directly_recorded_flag_counts']==dict(collections.Counter(str(v['DirectReco']) for v in selected))
        numbers=np.array([v['CountyPOP'] if v['CountyPOP'] is not None else np.nan for v in selected],float)
        states={k:int(mask.sum()) for k,mask in [('nonnumeric_or_nonfinite',~np.isfinite(numbers)),('negative',numbers<0),('zero',numbers==0),('positive',numbers>0)] if mask.any()}
        assert s['county_population_states']==states;equal(s['positive_county_population_sum'],float(numbers[numbers>0].sum()))
    for path,digest in r['source_support']['han_source_hashes'].items():assert sha(ROOT/path)==digest
    assert r['source_support']['roman']['source_sha256']==sha(ROOT/'data/cache/hanson2016/cities.xlsx')
    with np.load(OUT/'blocks.npz') as z:blocks={k:z[k] for k in z.files}
    reconstructed={};block_cases=0
    with np.load(ORIGINAL/'positions.npz') as positions:
      for pool in ['han','rome']:
        with np.load(ORIGINAL/f'{pool}_inputs.npz') as z:x=dict(z)
        spec=WINDOWS[pool];g=dict(x,lat0=spec['lat0'],lon0=spec['lon0'])
        observations=E.han_seats() if pool=='han' else [dict(lat=float(c['Latitude (Y)']),lon=float(c['Longitude (X)'])) for c in date_selected
            if isinstance(c['Latitude (Y)'],(float,int)) and isinstance(c['Longitude (X)'],(float,int))]
        row,col,inside=E.to_cells(g,np.array([s['lat'] for s in observations]),np.array([s['lon'] for s in observations]))
        h,w=x['land'].shape;rr,cc=np.clip(row,0,h-1),np.clip(col,0,w-1)
        _,indices=ndi.distance_transform_edt(~x['land'],return_indices=True)
        ids=indices[0,rr,cc]*w+indices[1,rr,cc]
        assert np.array_equal(np.unique(ids[inside]),x['real'])
        land=x['allowed']&x['land'];accepted=inside&land.ravel()[ids];record_cells=ids[accepted]
        expected=r['source_matching'][pool]
        for k,v in dict(original_records=len(observations),inside_window_records=int(inside.sum()),allowed_source_records=len(record_cells),
            distinct_allowed_cells=len(np.unique(record_cells)),outside_window_records=int((~inside).sum()),
            inside_but_not_allowed_records=int((inside&~land.ravel()[ids]).sum()),legacy_nearest_land_rescued_inside_records=int((inside&~x['land'][rr,cc]).sum())).items():assert expected[k]==v
        # Independent actual frozen sampler supplies its coverage flag.
        _,_,covered=E.earth_people(x['lat'],x['lon'])
        cv=r['population_coverage'][pool]
        for k,v in dict(required_land_cells=int(land.sum()),covered_land_cells=int((covered&land).sum()),
            missing_land_cells=int((~covered&land).sum()),source_records_outside_coverage=int((~covered.ravel()[record_cells]).sum()),
            distinct_source_cells_outside_coverage=len(np.unique(record_cells[~covered.ravel()[record_cells]]))).items():assert cv[k]==v
        equal(cv['missing_land_km2'],float((~covered&land).sum()*float(x['cell_km'])**2))
        assert cv['full_domain_qualified']==bool(covered[land].all())
        for domain in ['full_frozen','covered_only']:
          valid=land if domain=='full_frozen' else land&covered
          observed=record_cells[valid.ravel()[record_cells]];baseline=positions[pool+'__baseline']
          baseline_cells=baseline[:,0]*w+baseline[:,1];baseline_cells=baseline_cells[valid.ravel()[baseline_cells]]
          for nominal in [100,300]:
            step=round(nominal/float(x['cell_km']));key=f'{domain}_{pool}_{nominal}km'
            columns=collections.defaultdict(list);index=0
            for y0 in range(0,h,step):
              for x0 in range(0,w,step):
                y1,x1=min(h,y0+step),min(w,x0+step);mask=valid[y0:y1,x0:x1]
                if mask.any():
                    area=float(mask.sum()*float(x['cell_km'])**2)
                    pop=float((x['density'][y0:y1,x0:x1]*mask).sum()*float(x['cell_km'])**2)
                    records=observed[(observed//w>=y0)&(observed//w<y1)&(observed%w>=x0)&(observed%w<x1)]
                    nbase=int(((baseline_cells//w>=y0)&(baseline_cells//w<y1)&(baseline_cells%w>=x0)&(baseline_cells%w<x1)).sum())
                    ym,xm=(y0+y1-1)/2,(x0+x1-1)/2
                    values=dict(area=area,population=pop,record_count=len(records),distinct_cell_count=len(set(records)),baseline_count=nbase,
                        fold=2*int(ym>=h/2)+int(xm>=w/2),block_id=index,centre_x_km=(xm-(w-1)/2)*float(x['cell_km']),centre_y_km=((h-1)/2-ym)*float(x['cell_km']))
                    for name,v in values.items():columns[name].append(v)
                    block_cases+=1
                index+=1
            b={k:np.array(v) for k,v in columns.items()};reconstructed[key]=b
            for name,values in b.items():np.testing.assert_allclose(blocks[key+'__'+name],values,rtol=1e-12,atol=1e-6)
            metadata=r['blocks'][key]
            assert metadata['allowed_source_records']==int(b['record_count'].sum())
            assert metadata['distinct_source_cells']==int(b['distinct_cell_count'].sum())
            assert metadata['baseline_sites']==int(b['baseline_count'].sum())
            assert metadata['actual_block_km']==step*float(x['cell_km'])
    with np.load(OUT/'predictions.npz') as z:predictions={k:z[k] for k in z.files}
    metric_cases=0;fold_cases=0
    assert len(r['rows'])==176
    for row in r['rows']:
        key=f'{row["domain"]}_{row["pool"]}_{row["nominal_km"]}km';b=reconstructed[key];y=b[row['target']]
        p=np.zeros(len(y))
        for fold in range(4):
            held=b['fold']==fold
            if row['model']=='archived_production_descriptive':p[held]=b['baseline_count'][held]
            else:
                train_pools=[row['pool']] if row['scale_scope']=='role_specific' else ['han','rome']
                count=exposure=0.
                for pool in train_pools:
                    o=reconstructed[f'{row["domain"]}_{pool}_{row["nominal_km"]}km'];train=o['fold']!=fold
                    count+=o[row['target']][train].sum()
                    exposure+=(o['area'][train]*(o['population'][train]/o['area'][train])**row['beta']).sum()
                scale=count/exposure if exposure else (0. if count==0 else None)
                equal(row['training_scales'][str(fold)],scale)
                p[held]=(scale or 0)*b['area'][held]*(b['population'][held]/b['area'][held])**row['beta']
                f=row['folds'][str(fold)];equal(f['training_count'],count);equal(f['training_exposure'],exposure)
                assert f['training_scale_identified']==(scale is not None)
            expected=direct_metrics(y[held],p[held],b['area'][held])
            for field,value in expected.items():equal(row['folds'][str(fold)][field],value);metric_cases+=1
            fold_cases+=1
        for field,value in direct_metrics(y,p,b['area']).items():equal(row['total'][field],value);metric_cases+=1
        if row['model']!='archived_production_descriptive':
            label=key+'__'+row['target']+'__'+row['model'];np.testing.assert_allclose(p,predictions[label],rtol=1e-10,atol=1e-10)
    for domain,ranking in r['ranking'].items():
        for entry in ranking:
            rows=[row for row in r['rows'] if row['domain']==domain and row['nominal_km']==100 and row['target']=='record_count'
                  and row['model']==f'role_specific_beta{entry["beta"]:g}']
            values=[]
            for row in rows:
                value=row['total']['deviance_per_source_record'];value=float('inf') if value=='infinite' else value
                equal(entry['pool_deviance_per_source_record'][row['pool']],value);values.append(value)
            equal(entry['equal_pool_deviance_per_source_record'],float(np.mean(values)))
    assert not r['adopt'] and not r['ledger_or_physics_changed'] and r['chosen_for_production'] is None
    assert r['status']=='full_domain_coverage_failure_restricted_development_only'
    write(OUT/'review.json',dict(status='passed',source_results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        source_workbook_and_shapefile_support_reconstructed=True,inherited_matching_and_multiplicity_reconstructed=True,
        independent_frozen_sampler_coverage_reconstructed=True,direct_block_cases=block_cases,held_fold_cases=fold_cases,
        scalar_metric_checks=metric_cases,all176_rows_checked=True,full_region_fit_qualified=False,adopt=False))
    print('Count review passed:',block_cases,'blocks',fold_cases,'held fold cases',metric_cases,'metrics.')


if __name__=='__main__':main()
