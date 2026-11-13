"""Matched packed-versus-source-filled destination food under all24fixed plans."""
import argparse,csv,gzip,io,json,subprocess,sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.event_food_stocks import periodic_event_food_year
from polity.delivery_partition import lagged_return_times
from polity.source_filled_deliveries import source_filled_deliveries
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_filled_destination_20261113';SRC=ROOT/'output/source_food_events_20261113';CAL=ROOT/'output/continuous_food_visit_calendars_20261112';PARENT=ROOT/'output/settlement_continuous_destination_20261112';PLAN=ROOT/'calibration/source_filled_destination_20261113/plan.json'


def aggregate(site,time,a,b,missing):
    order=np.lexsort((time,site));site,time,a,b,missing=[v[order] for v in (site,time,a,b,missing)];starts=np.r_[0,1+np.flatnonzero((np.diff(site)!=0)|(np.diff(time)!=0))]
    return dict(site=site[starts].astype('i4'),time=time[starts],A_cargo=np.add.reduceat(a,starts),B_cargo=np.add.reduceat(b,starts),unfilled_retained_potential=np.add.reduceat(missing,starts),trips=np.diff(np.r_[starts,len(site)]))


def run_case(task):
    row,out=task;out=Path(out);case=row['case'];key=row['key'];mode=row['climate'];policy=row['policy'];src=dict(np.load(SRC/(case+'_fields.npz')));folder=PARENT/f'{mode}_h{row["hours_worker_year"]}_load120000_all_open';f=dict(np.load(folder/'fields.npz'));n=len(f['total']);sources={str((SRC/(case+'_fields.npz')).relative_to(ROOT)):sha(SRC/(case+'_fields.npz')),str((folder/'fields.npz').relative_to(ROOT)):sha(folder/'fields.npz')}
    input_path=ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz';sources[str(input_path.relative_to(ROOT))]=sha(input_path)
    with np.load(CAL/'selected_fields.npz') as z:selection=z[key+'__policy'];mandatory=z[key+'__selected_mandatory_complete']
    pieces=[]
    for month in range(12):
        for pol in (('baseline','joint') if policy=='selected' else (policy,)):
            path=CAL/key/pol/f'calendar_{month:02d}.npz';sources[str(path.relative_to(ROOT))]=sha(path)
            with np.load(path) as c:
                keep=selection[c['collection_site']]==int(pol=='joint') if policy=='selected' else np.ones(len(c['collection_site']),bool);site=c['collection_site'][keep];origin=c['collection_origin'][keep];serial=c['collection_serial'][keep];end=c['collection_end'][keep];cargo=c['packed_cargo'][keep];ids=month*(1<<48)+origin*(1<<24)+serial
                pieces.append(dict(site=site,time=lagged_return_times(end,month),raw=cargo,ids=ids))
    physical={name:np.concatenate([v[name] for v in pieces]) for name in pieces[0]};supply=source_filled_deliveries(physical['ids'],physical['raw'],src['pickup__id'],src['pickup__requested'],src['pickup__withdrawn'],src['pickup__unfilled'])
    ev=aggregate(physical['site'],physical['time'],supply.retained_packed_potential,supply.retained_source_filled,supply.retained_unfilled_potential);np.testing.assert_allclose(ev['B_cargo']+ev['unfilled_retained_potential'],ev['A_cargo'],rtol=1e-12,atol=1e-6)
    if policy=='selected':
        previous={}
        with np.load(CAL/'selected_fields.npz') as z:
            for name in z.files:
                if name.startswith(key+'__food_'):previous[name.removeprefix(key+'__food_')]=z[name]
        olds=[]
        for pol in ('baseline','joint'):
            path=CAL/key/pol/'events.npz';sources[str(path.relative_to(ROOT))]=sha(path);e=dict(np.load(path));keep=selection[e['site']]==int(pol=='joint');olds.append({n:v[keep] for n,v in e.items()})
        old={name:np.concatenate([v[name] for v in olds]) for name in olds[0]};order=np.lexsort((old['time'],old['site']));old={name:v[order] for name,v in old.items()}
    else:
        path=CAL/key/policy/'fields.npz';sources[str(path.relative_to(ROOT))]=sha(path);z=dict(np.load(path));previous={name.removeprefix('C__'):v for name,v in z.items() if name.startswith('C__')};mandatory=z['mandatory_complete'];path=CAL/key/policy/'events.npz';sources[str(path.relative_to(ROOT))]=sha(path);old=dict(np.load(path))
    for name in ('site','time','trips'):np.testing.assert_array_equal(ev[name],old[name])
    np.testing.assert_array_equal(ev['A_cargo'],old['cargo'])
    eo=np.searchsorted(ev['site'],np.arange(n+1));fields=dict(active=f['active'],people=f['total'],staff=f['staff'],capacity=f['total']*2500*90,mandatory_complete=mandatory,source_rural_food_pass=src['provider__rural_food_pass'],source_export_request_pass=src['provider__export_request_pass'],source_both_pass=src['provider__both_pass']);rows=[]
    for account in ('A','B'):
        values={}
        for site in np.flatnonzero(f['active']):
            sl=slice(eo[site],eo[site+1]);inventory=periodic_event_food_year(ev['time'][sl],ev[account+'_cargo'][sl],demand_rate=f['total'][site]*2500,capacity=f['total'][site]*2500*90)
            for name,value in asdict(inventory).items():
                if name not in values:values[name]=np.zeros(n)
                values[name][site]=value
        passed=f['active']&(values['unmet']<=1e-8*np.maximum(1.,values['needed']));values['food_pass']=passed
        if account=='A':
            for name,value in previous.items():
                if name=='no_shortage':np.testing.assert_array_equal(passed,value.astype(bool)&f['active'])
                else:np.testing.assert_array_equal(values[name],value)
        for name,value in values.items():fields[account+'__'+name]=value
        both=passed&mandatory&fields['source_both_pass'];fields[account+'__all_gates_pass']=both
        summary={name:row[name] for name in ('case','key','policy','climate','hours_worker_year','crew')};summary.update(accounting=account,scored_providers=int(f['active'].sum()),destination_food_pass=int(passed.sum()),mandatory_complete=int(mandatory.sum()),source_export_pass=int(fields['source_export_request_pass'].sum()),source_rural_pass=int(fields['source_rural_food_pass'].sum()),all_gates_pass=int(both.sum()),raw_source_unfilled=row['raw_unfilled'],counterfactual_retained_missing=row['raw_unfilled']*.95,actors=[])
        for name,value in values.items():
            if name!='food_pass':summary[name]=float(value.sum())
        x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));fields['actor']=x['actor']
        for actor in range(18):
            mask=x['actor']==actor;ar=dict(actor=actor,scored_providers=int((mask&f['active']).sum()),destination_food_pass=int((mask&passed).sum()),all_gates_pass=int((mask&both).sum()))
            for name,value in values.items():
                if name!='food_pass':ar[name]=float(value[mask].sum())
            summary['actors'].append(ar)
        rows.append(summary)
    assert not (fields['B__food_pass']&~fields['A__food_pass']).any();assert not fields['A__all_gates_pass'].any() and not fields['B__all_gates_pass'].any()
    assert np.all(fields['B__unmet']+1e-8*np.maximum(1.,fields['A__needed'])>=fields['A__unmet'])
    files={}
    for suffix,data in [('events',ev),('fields',fields)]:path=out/(case+'_'+suffix+'.npz');np.savez_compressed(path,**data);files[path.name]=sha(path)
    print('Matched source-filled destination built',case,'A/B food passes',rows[0]['destination_food_pass'],rows[1]['destination_food_pass'],flush=True)
    return dict(rows=rows,files=files,sources=sources)


def main(out=OUT,jobs=2):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes();out.mkdir(parents=True,exist_ok=True)
    r=json.loads((SRC/'results.json').read_text());review=json.loads((SRC/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(SRC/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_source_pickup_calendars.py')
    for name,digest in {**r['sources'],**r['producers']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(SRC/name)==digest,name
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,ROOT/'polity/source_filled_deliveries.py',ROOT/'polity/delivery_partition.py',ROOT/'harvest/event_food_stocks.py']};test=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_source_filled_deliveries.py','tests/test_event_food_stocks.py','tests/test_delivery_partition.py','tests/test_source_food_events.py'],cwd=ROOT,capture_output=True,text=True,check=True);write(out/'controls.json',dict(status='passed_before_production',output=test.stdout,producers=producers))
    protected={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'atlases/earth_fit').rglob('*')) if p.is_file()}
    with ProcessPoolExecutor(max_workers=jobs) as pool:cases=list(pool.map(run_case,[(row,str(out)) for row in r['rows']]))
    sources={str((SRC/'results.json').relative_to(ROOT)):sha(SRC/'results.json'),str((SRC/'review.json').relative_to(ROOT)):sha(SRC/'review.json'),str((CAL/'selected_fields.npz').relative_to(ROOT)):sha(CAL/'selected_fields.npz')};files={};rows=[]
    for c in cases:sources.update(c['sources']);files.update(c['files']);rows+=c['rows']
    write(out/'results.json',dict(status='matched_source_filled_destination_diagnostic',rows=rows,sources=sources,producers=producers,files_sha256=files,unchanged_atlas_sha256=protected,scope='A exact priorC packed cargo versus Bsource-withdrawn raw*.95once at SAMEreturns/lag. All source rural failures retained;no certified shipments,new residents or map/default adoption.'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--jobs',type=int,default=2);a=p.parse_args();main(a.out,a.jobs)
