"""Seal both quota cases and independently check all public comparison tables."""
import csv
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from urban_fixed_dispatch import OUT,PARENT,ANNUAL,gate
from urban_earth_monthly import read,write,sha,total,KCAL


def rows(name):return list(csv.DictReader((OUT/name).open()))


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed qualification'
    sources,protected=gate();r=read(OUT/'results.json');tests=read(OUT/'tests.json')
    assert r['status']=='reviewed_two_fixed_dispatch_cases_with_four_exact_controls'
    assert '10 passed' in tests['stdout'] and tests['status']=='passed'
    for name,digest in r['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    packet=dict(np.load(OUT/'town_model.npz'));town=rows('towns.csv');diff=rows('differences.csv');previous=rows('previous_losers.csv')
    monthly=rows('months.csv');regional=rows('regions.csv');maximum=0.;maxledger=0.;shipments=0
    assert len(town)==6510 and len(diff)==2170 and len(previous)==19 and len(monthly)==72 and len(regional)==30
    for reading in ['central','low']:
        for label in ['loss05_days90','loss00_days90']:
            path=OUT/'controls'/f'{reading}_{label}.json';c=read(path);assert c['arrays_exact']==70
            assert c['sources_sha256']==sources and c['protected_sha256']==protected
        folder=OUT/'cases'/reading;case=read(folder/'results.json');v=read(folder/'review.json')
        for file,key in [('results.json','results_sha256'),('fields.npz','fields_sha256')]:assert sha(folder/file)==v[key]
        assert v['reviewer_sha256']==sha(ROOT/'scripts/review_urban_fixed_dispatch.py')
        for name,digest in v['reviewer_dependency_sha256'].items():assert sha(ROOT/name)==digest,name
        assert case['sources_sha256']==sources and case['protected_sha256']==protected
        assert not case['actual_population_changed'] and not case['adopt']
        maximum=max(maximum,v['maximum_fraction_of_original_inventory_tolerance']);maxledger=max(maxledger,abs(v['grain_residual_person_years']))
        shipments+=v['independent_shipments']
        req=packet[reading+'_request'];a=dict(np.load(ANNUAL/f'low_{reading}.npz'))
        meals={};fields={}
        for label,suffix in [('loss05_own','loss05_days90'),('loss00_own','loss00_days90'),('loss00_fixed',None)]:
            path=folder/'fields.npz' if suffix is None else PARENT/'cases'/f'{reading}_{suffix}'/'fields.npz'
            c=dict(np.load(path));fields[label]=c
            np.testing.assert_array_equal(packet[reading+'_'+label+'_consumed'],c['town_food__consumed'])
            np.testing.assert_array_equal(packet[reading+'_'+label+'_unmet'],c['town_food__unmet_path'])
            meals[label]=c['town_food__consumed']/KCAL
        olddelta=meals['loss00_own']-meals['loss05_own'];newdelta=meals['loss00_fixed']-meals['loss05_own']
        quotadelta=meals['loss00_fixed']-meals['loss00_own'];oldloser=olddelta< -1e-7;newloser=newdelta< -1e-7
        np.testing.assert_array_equal(packet[reading+'_previous_loser'],oldloser);np.testing.assert_array_equal(packet[reading+'_new_loser'],newloser)
        stats=r['city_effects'][reading];assert stats['previous_losers']==int(oldloser.sum())
        assert stats['all_losers_vs_five_percent']==int(newloser.sum())==0
        assert np.all(newdelta[oldloser]>=-1e-7)
        assert stats['fixed_vs_own_gaining_cities']==int((quotadelta>1e-7).sum())
        assert stats['fixed_vs_own_losing_cities']==int((quotadelta< -1e-7).sum())
        assert stats['fixed_vs_own_meal_delta_person_years']==total(quotadelta)
        drows=[row for row in diff if row['reading']==reading]
        for key,expected in [('own_zero_vs_five_meals_person_years',olddelta),('fixed_zero_vs_five_meals_person_years',newdelta),('fixed_vs_own_meals_person_years',quotadelta)]:
            np.testing.assert_array_equal([float(row[key]) for row in drows],expected)
        assert [row for row in drows if row['previous_zero_loss_loser']=='True']==[row for row in previous if row['reading']==reading]
        old,new=fields['loss00_own'],fields['loss00_fixed']
        for i,row in enumerate(drows):
            for name,key in [('direct','delta_direct_arrivals_person_years'),('inter_received','delta_intertown_arrivals_person_years'),('inter_exported','delta_intertown_exports_person_years')]:
                assert abs(float(row[key])-total(new[name][:,i]-old[name][:,i])/KCAL)<1e-7
            for name,key in [('spoiled','delta_spoilage_person_years'),('overflow','delta_overflow_person_years'),('initial_stock','delta_initial_stock_person_years'),('final_stock','delta_final_stock_person_years')]:
                assert float(row[key])==(new['town_food__'+name][i]-old['town_food__'+name][i])/KCAL
        lat=packet[reading+'_lat'];lon=packet[reading+'_lon'];egypt=(lon>=29)&(lon<=32.6)&(lat<=32)
        masks={'all':np.ones(len(req),bool),'west':a['lon']<=np.median(a['lon']),'east':a['lon']>np.median(a['lon']),'egypt_proper':egypt,'other':~egypt}
        for label,quantity in meals.items():
            trows=[row for row in town if row['reading']==reading and row['scenario']==label]
            np.testing.assert_array_equal([float(row['meals_person_years']) for row in trows],quantity)
            summary=next(x for x in r['summary'] if x['reading']==reading and x['scenario']==label)
            assert abs(summary['meal_fraction']-total(quantity)/total(req))<1e-14
            c=fields[label]
            for month in range(12):
                mrow=next(x for x in monthly if x['reading']==reading and x['scenario']==label and int(x['month'])==month+1)
                expected=total(req)/12-total(c['town_food__unmet_path'][month])/KCAL
                assert abs(float(mrow['meals_person_years'])-expected)<1e-7
            for name,mask in masks.items():
                reg=next(x for x in regional if x['reading']==reading and x['scenario']==label and x['region']==name)
                assert abs(float(reg['meals_person_years'])-total(quantity[mask]))<1e-7
                assert abs(float(reg['delta_meals_vs_five_percent_person_years'])-total((quantity-meals['loss05_own'])[mask]))<1e-7
    assert maximum<=1
    paths=[Path(__file__),ROOT/'scripts/review_urban_fixed_dispatch.py',ROOT/'scripts/render_urban_fixed_dispatch.py',
        ROOT/'reports/URBAN_FIXED_DISPATCH_20261117.md',ROOT/'calibration/urban_diagnosis_20261117/storage_dispatch_source_scope.json']
    sources.update({str(path.relative_to(ROOT)):sha(path) for path in paths})
    files={str(path.relative_to(OUT)):sha(path) for path in OUT.rglob('*') if path.is_file() and path.name!='fields.npz'}
    q=dict(status='passed_two_fixed_baseline_dispatch_cases_and_four_exact_controls',sources_sha256=sources,files_sha256=files,
        protected_sha256=protected,**r['counts'],adapter_tests=10,physical_source_cases=112756,inventory_groups=8,
        independent_shipments=shipments,maximum_fraction_of_original_inventory_tolerance=maximum,max_grain_residual_person_years=maxledger,
        previous_local_losses_removed_in_both_cases=True,new_local_losses_vs_five_percent=0,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/storage_dispatch_source_scope.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
