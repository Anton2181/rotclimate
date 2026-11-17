"""Independent saved-path review; no food-kernel execution or scenario generation."""
import csv
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_urban_storage_throughput import OUT,PARENT,BASE,PLAN,LABELS,sha,read,write,total,KCAL


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed review'
    r=read(OUT/'results.json')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['food_kernel_calls']==r['new_food_scenarios']==0
    packet=dict(np.load(OUT/'source_accounting.npz'));city=list(csv.DictReader((OUT/'city_losses.csv').open()))
    monthly=list(csv.DictReader((OUT/'city_loss_months.csv').open()));assert len(city)==19 and len(monthly)==228
    source_count=0;maximum=0.;maxbound=0.;maxcity=0.;counts={};loss_totals={}
    for reading in ['central','low']:
        baseline=dict(np.load(BASE/'cases'/reading/'fields.npz'));reference=baseline['marketed'].sum(0)
        scenarios={LABELS[0]:baseline}
        for label in LABELS:
            if label!=LABELS[0]:scenarios[label]=dict(np.load(PARENT/'cases'/f'{reading}_{label}'/'fields.npz'))
            c=scenarios[label];prefix=reading+'_'+label+'_'
            cap=reference if label.endswith('365') else reference*90/365
            rate=.05 if label.startswith('loss05') else 0.
            tolerance=1e-10*np.maximum(1,np.maximum(c['marketed'].sum(0),c['dispatch'].sum(0)))
            allowance=tolerance+100*np.finfo(float).eps*np.maximum(1,c['marketed'].sum(0))
            stock=c['export_food__initial_stock'].copy();spoiled=np.zeros_like(stock);overflow=spoiled.copy();departures=spoiled.copy()
            factor=-np.expm1(np.log1p(-rate)/12)
            for month in range(12):
                stock+=c['marketed'][month]
                paid=np.minimum(stock,c['dispatch'][month]);stock-=paid
                spilled=np.maximum(stock-cap,0);stock-=spilled
                lost=stock*factor;stock-=lost
                for actual,expected in [(paid,c['departures'][month]),(stock,c['export_food__stock_path'][month+1])]:
                    error=abs(actual-expected);assert np.all(error<=allowance)
                    maximum=max(maximum,float((error/allowance).max()))
                spoiled+=lost;overflow+=spilled;departures+=paid
            expected=dict(source=c['source_indices'],capacity=cap,marketed=c['marketed'].sum(0),departures=departures,
                spoiled=spoiled,overflow=overflow,stock_change=stock-c['export_food__initial_stock'],
                pulses=np.count_nonzero(c['marketed'],axis=0),open_months=3*np.count_nonzero((c['owner']>=0)&(c['retention']>0),axis=0))
            eligible=(rate==0)&(expected['pulses']==1)&(expected['open_months']==12)
            np.testing.assert_array_equal(packet[prefix+'bound_eligible'],eligible)
            for key,value in expected.items():
                actual=packet[prefix+key]
                if key in ['source','capacity','marketed','pulses','open_months']:np.testing.assert_array_equal(actual,value)
                else:
                    error=abs(actual-value);assert np.all(error<=allowance),(reading,label,key)
                    maximum=max(maximum,float((error/allowance).max()))
            if eligible.any():
                bound=np.minimum(expected['marketed'],expected['marketed']/12+cap)
                error=abs(bound[eligible]-departures[eligible])/allowance[eligible]
                assert np.all(error<=1);maxbound=max(maxbound,float(error.max()))
            summary=next(x for x in r['summary'] if x['reading']==reading and x['scenario']==label)
            assert summary['one_pulse_all_open_origins']==int(eligible.sum())
            for key,field in [('marketed','marketed_person_years'),('departures','departures_person_years'),('spoiled','commercial_spoilage_person_years'),('overflow','commercial_overflow_person_years')]:
                assert abs(total(expected[key])/KCAL-summary[field])<=total(allowance)/KCAL
            source_count+=len(cap)
        old=scenarios['loss05_days90'];new=scenarios['loss00_days90']
        delta=new['town_food__consumed']-old['town_food__consumed']
        losing=np.flatnonzero(delta/KCAL< -1e-7);rows=[x for x in city if x['reading']==reading]
        np.testing.assert_array_equal([int(x['city_index']) for x in rows],losing)
        counts[reading]=dict(losing_cities=len(rows),annual_direct_decreases=0,annual_intertown_decreases=0,protection_flips=0)
        loss_totals[reading]=total(delta[losing])/KCAL
        for row,i in zip(rows,losing):
            increments=dict(delta_meals_person_years=delta[i]/KCAL,
                delta_direct_arrivals_person_years=total(new['direct'][:,i]-old['direct'][:,i])/KCAL,
                delta_intertown_arrivals_person_years=total(new['inter_received'][:,i]-old['inter_received'][:,i])/KCAL)
            for field,output in [('spoiled','delta_spoilage_person_years'),('overflow','delta_overflow_person_years'),
                                 ('initial_stock','delta_initial_stock_person_years'),('final_stock','delta_final_stock_person_years')]:
                increments[output]=(new['town_food__'+field][i]-old['town_food__'+field][i])/KCAL
            for key,value in increments.items():assert abs(float(row[key])-value)<1e-7,key
            prediction=increments['delta_direct_arrivals_person_years']+increments['delta_intertown_arrivals_person_years']-increments['delta_spoilage_person_years']-increments['delta_overflow_person_years']+increments['delta_initial_stock_person_years']-increments['delta_final_stock_person_years']
            error=abs(prediction-increments['delta_meals_person_years']);maxcity=max(maxcity,error)
            assert error<=1e-10*max(1,new['town_food__needed'][i],new['town_food__harvested'][i],old['town_food__harvested'][i])/KCAL
            counts[reading]['annual_direct_decreases']+=int(increments['delta_direct_arrivals_person_years']< -1e-7)
            counts[reading]['annual_intertown_decreases']+=int(increments['delta_intertown_arrivals_person_years']< -1e-7)
            counts[reading]['protection_flips']+=int(bool(old['protected_exporters'][i])!=bool(new['protected_exporters'][i]))
            mrows=[x for x in monthly if x['reading']==reading and x['cell']==row['cell']];assert len(mrows)==12
            for month,mrow in enumerate(mrows):
                assert int(mrow['month'])==month+1
                assert abs(float(mrow['delta_meals_person_years'])-(old['town_food__unmet_path'][month,i]-new['town_food__unmet_path'][month,i])/KCAL)<1e-7
                for key,field in [('direct','delta_direct_arrivals_person_years'),('inter_received','delta_intertown_arrivals_person_years')]:
                    assert abs(float(mrow[field])-(new[key][month,i]-old[key][month,i])/KCAL)<1e-7
    # Stream-check public source export against independently verified vectors.
    index={};csvcount=0
    with (OUT/'sources.csv').open() as stream:
        for row in csv.DictReader(stream):
            prefix=row['reading']+'_'+row['scenario']+'_';i=index.get(prefix,0);index[prefix]=i+1;csvcount+=1
            assert int(row['source'])==packet[prefix+'source'][i]
            for field,key in [('marketed_person_years','marketed'),('departures_person_years','departures'),('spoilage_person_years','spoiled'),('overflow_person_years','overflow')]:
                assert float(row[field])==packet[prefix+key][i]/KCAL
    assert csvcount==source_count==r['source_rows']==451024
    receipt=dict(status='passed_independent_saved_throughput_and_all_local_loss_channels',reviewer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),source_rows=source_count,city_losses=19,city_month_rows=228,
        maximum_stock_trace_tolerance_fraction=maximum,maximum_bound_tolerance_fraction=maxbound,
        maximum_city_delta_ledger_residual_person_years=maxcity,local_channels=counts,losing_city_total_meal_change_person_years=loss_totals,
        food_kernel_calls=0,new_food_scenarios=0,new_fit=False,new_validation_claim=False,actual_population_changed=False,adopt=False)
    write(OUT/'review.json',receipt);print(receipt,flush=True)


if __name__=='__main__':main()
