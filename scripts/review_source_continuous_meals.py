"""Independent one-harvest fixed points and scalar ledgers for every origin."""
import csv,gzip,json,math,sys
from pathlib import Path
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_continuous_meals_20261113'
NAMES=('initial_stock','final_stock','peak_stock','harvested','needed','consumed','unmet','spoiled','overflow','shortfall_days','ledger_residual','periodic_residual')

@njit
def scalar_all(energy,people,month,continuous):
    count=len(people);values=np.zeros((12,count));paths=np.zeros((13,count));missing=np.zeros((12,count));h=-math.log(.95)/365;dt=365/12;d=math.exp(-h*dt)
    sum12=0.
    for z in range(1,13):sum12+=d**z
    sum11=sum12-d**12
    for j in range(count):
        q=energy[j];annual=people[j]*2500*365;rate=annual/365;cap=annual;meal=annual/12;k=int(month[j])
        # Single annual harvest, fixed 365-day meal capacity. The continuous
        # pre-harvest stock is zero: that capacity cannot pay a year plus loss.
        if continuous:pre=0.
        else:
            unbounded=(q*d**12-meal*sum12)/(1-d**12)
            clipped=cap*d**12-meal*sum11;pre=max(0.,min(unbounded,clipped))
        stock=pre
        # Rotate from just before harvest to the calendar-year boundary.
        for step in range((12-k)%12):
            supply=q if step==0 else 0.
            if continuous:stock=max(0.,min(cap,stock+supply)*d-rate*(1-d)/h)
            else:stock=min(cap,max(0.,stock+supply-meal))*d
        initial=stock;peak=stock;eaten=unmet=loss=spill=days=0.;paths[0,j]=stock
        for m in range(12):
            supply=q if m==k else 0.;available=stock+supply
            if continuous:
                spill+=max(0.,available-cap);stock=min(cap,available);peak=max(peak,stock);empty=math.log1p(stock*h/rate)/h if rate else float('inf');fed=min(dt,empty);meal_eaten=rate*fed;gap=rate*(dt-fed);after=max(0.,stock*math.exp(-h*fed)+rate*math.expm1(-h*fed)/h)
                if empty<=dt:after=0.
                loss+=max(0.,stock-after-meal_eaten);stock=after;days+=dt-fed if rate else 0.
            else:
                meal_eaten=min(available,meal);gap=meal-meal_eaten;remaining=available-meal_eaten;spill+=max(0.,remaining-cap);remaining=min(cap,remaining);peak=max(peak,remaining);lost=remaining*(-math.expm1(-h*dt));loss+=lost;stock=remaining-lost
                if gap>1e-10*max(1.,q,annual):days+=dt
            eaten+=meal_eaten;unmet+=gap;missing[m,j]=gap;paths[m+1,j]=stock
        values[:,j]=np.array([initial,stock,peak,q,annual,eaten,unmet,loss,spill,days,initial+q-stock-eaten-loss-spill,abs(stock-initial)])
    return values,paths,missing

def main():
    r=json.loads((OUT/'results.json').read_text());checked=csv_count=0;actor_rows=0;largest_error=0.
    for path,d in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/path)==d,path
    for path,d in r['files_sha256'].items():assert sha(OUT/path)==d
    assert len(r['rows'])==16
    for key in r['cases']:
        mode=key.split('_')[0];f=dict(np.load(OUT/(key+'_fields.npz')));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'))
        for context in ('local','outside'):
            prefix=context+'__';nodes=f[prefix+'nodes'];bits=x['boundaries'][nodes];month=np.array([next((m for m in range(12) if int(bit)&(1<<m)),0) for bit in bits]);np.testing.assert_array_equal(month,f[prefix+'harvest_bin']);np.testing.assert_array_equal(bits,f[prefix+'boundaries']);assert np.all((f[prefix+'produced']==0)|(bits!=0))
            if context=='outside':assert (f[prefix+'owner']==-1).all() and (f[prefix+'actor']==-1).all()
            else:np.testing.assert_array_equal(f[prefix+'owner'],x['owner']);np.testing.assert_array_equal(f[prefix+'actor'],x['actor'][x['owner']])
            for account in ('A','B'):
                values,paths,missing=scalar_all(f[prefix+'produced'],f[prefix+'people'],month,account=='B');scale=np.maximum(1.,f[prefix+'capacity'])
                for i,name in enumerate(NAMES):
                    actual=f[prefix+account+'__'+name];assert np.all(abs(values[i]-actual)<=1e-9*scale),(key,context,account,name,float(np.max(abs(values[i]-actual)/scale)))
                for actual,expected in [(paths,f[prefix+account+'__stock_path']),(missing,f[prefix+account+'__unmet_path'])]:
                    error=float(np.max(abs(actual-expected)/scale[None,:]));largest_error=max(largest_error,error);assert error<=1e-9,(key,context,account,error)
                passed=values[6]<=1e-8*np.maximum(1.,values[4]);np.testing.assert_array_equal(passed,f[prefix+account+'__food_pass']);row=next(v for v in r['rows'] if v['key']==key and v['context']==context and v['accounting']==account)
                assert row['origins']==len(nodes) and row['positive_people_origins']==int((f[prefix+'people']>0).sum()) and row['food_pass']==int(passed.sum()) and row['positive_people_food_pass']==int((passed&(f[prefix+'people']>0)).sum())
                for name in ('needed','consumed','unmet','spoiled','overflow','ledger_residual'):assert abs(row[name]-float(values[NAMES.index(name)].sum()))<=1e-9*max(1.,float(scale.sum()))
                for a in row.get('actors',[]):
                    mask=f[prefix+'actor']==a['actor'];assert a['origins']==int(mask.sum()) and a['food_pass']==int((mask&passed).sum());assert abs(a['unmet']-float(values[6,mask].sum()))<=1e-9*max(1.,float(scale[mask].sum()));actor_rows+=1
                checked+=len(nodes)
        with gzip.open(OUT/(key+'_origins.csv.gz'),'rt',newline='') as stream:
            counts={'local':0,'outside':0}
            for v in csv.DictReader(stream):
                context=v['context'];j=counts[context];counts[context]+=1;p=context+'__';assert v['case']==key
                for column,name,conv in [('origin_grid_node','nodes',int),('owner_provider','owner',int),('actor','actor',int),('people','people',float),('produced_kcal','produced',float),('A_unmet_kcal','A__unmet',float),('B_unmet_kcal','B__unmet',float)]:assert conv(v[column])==f[p+name][j]
                assert int(v['harvest_bin'])==f[p+'harvest_bin'][j]+1
                for account in 'AB':assert v[account+'_food_pass']==str(bool(f[p+account+'__food_pass'][j]))
                csv_count+=1
            assert all(counts[c]==len(f[c+'__nodes']) for c in counts)
        print('Independent closed-form stocks,scalar ledgers and every CSV passed',key,flush=True)
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),origin_account_inventories_checked=checked,csv_origin_rows_checked=csv_count,actor_rows_checked=actor_rows,all16comparison_rows=True,one_pulse_fixed_points_and_scalar_paths=True,largest_path_error_per_annual_meals=largest_error,path_tolerance_per_annual_meals=1e-9,all_maps_unchanged=True,scope='Fixed rural meal diagnostic only;no new source exports or complete provisioning qualification.'))
if __name__=='__main__':main()
