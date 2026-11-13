"""Fixed rural source meals: old monthly versus continuous physical storage."""
import argparse,csv,gzip,io,json,subprocess,sys
from dataclasses import asdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.field_support import fixed_rural_food
from harvest.continuous_food_stocks import periodic_continuous_food_year
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_continuous_meals_20261113';PLAN=ROOT/'calibration/source_continuous_meals_20261113/plan.json';PARENT=ROOT/'output/settlement_continuous_destination_20261112'

def main(out=OUT):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    out.mkdir(parents=True,exist_ok=True)
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,ROOT/'harvest/field_support.py',ROOT/'harvest/continuous_food_stocks.py',ROOT/'harvest/food_stocks.py']}
    check=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_source_meal_chronology.py','tests/test_continuous_food_stocks.py','tests/test_food_stocks.py'],cwd=ROOT,capture_output=True,text=True,check=True);write(out/'controls.json',dict(status='passed_before_production',output=check.stdout,producers=producers))
    sources={};rows=[];cases=[];files={};protected={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'atlases/earth_fit').rglob('*')) if p.is_file()}
    for mode in ('raw','corrected'):
        source=ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz';sources[str(source.relative_to(ROOT))]=sha(source);x=dict(np.load(source))
        for hours in (600,300):
            key=f'{mode}_h{hours}';folder=PARENT/(key+'_load120000_all_open');r=json.loads((folder/'results.json').read_text());review=json.loads((folder/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(folder/'results.json')
            for n in ('fields.npz','results.json','review.json'):sources[str((folder/n).relative_to(ROOT))]=sha(folder/n)
            f=dict(np.load(folder/'fields.npz'));fields={};b=io.StringIO(newline='');writer=csv.writer(b);writer.writerow(['case','context','origin_grid_node','owner_provider','actor','harvest_bin','people','produced_kcal','A_unmet_kcal','B_unmet_kcal','A_food_pass','B_food_pass'])
            for context in ('local','outside'):
                nodes=x['local_index'] if context=='local' else f['outside_index'];people=f['rural'] if context=='local' else f['outside_people'];energy=f['produced_kcal'] if context=='local' else f['outside_produced'];bound=x['boundaries'][nodes]
                old=fixed_rural_food(energy,bound,people*2500*365);a=old.year;capacity=people*2500*365;new=periodic_continuous_food_year(old.harvest,old.need,capacity,loss_fraction_year=.05,step_days=365/12,record=True)
                if context=='local':
                    for name in ('initial_stock','final_stock','harvested','needed','consumed','unmet','spoiled','overflow','ledger_residual'):np.testing.assert_array_equal(getattr(a,name),f['rural_'+name])
                else:np.testing.assert_array_equal(a.unmet,f['outside_unmet'])
                owners=x['owner'] if context=='local' else np.full(len(nodes),-1,'i8');actors=x['actor'][owners] if context=='local' else np.full(len(nodes),-1,'i8');month=(((bound[None,:]>>np.arange(12)[:,None])&1)>0).argmax(axis=0)
                for name,value in dict(nodes=nodes,people=people,produced=energy,capacity=capacity,owner=owners,actor=actors,harvest_bin=month,boundaries=bound).items():fields[context+'__'+name]=value
                for account,inventory in [('A',a),('B',new)]:
                    for name,value in asdict(inventory).items():
                        if value is not None:fields[context+'__'+account+'__'+name]=value
                    passed=inventory.unmet<=1e-8*np.maximum(1.,inventory.needed);fields[context+'__'+account+'__food_pass']=passed
                    row=dict(key=key,climate=mode,hours_worker_year=hours,context=context,accounting=account,origins=len(nodes),positive_people_origins=int((people>0).sum()),food_pass=int(passed.sum()),positive_people_food_pass=int((passed&(people>0)).sum()),people=float(people.sum()),produced=float(energy.sum()))
                    for name in ('needed','consumed','unmet','spoiled','overflow','ledger_residual'):row[name]=float(np.sum(getattr(inventory,name)))
                    if context=='local':row['actors']=[dict(actor=i,origins=int((actors==i).sum()),food_pass=int((passed&(actors==i)).sum()),unmet=float(inventory.unmet[actors==i].sum())) for i in range(18)]
                    rows.append(row)
                for j,node in enumerate(nodes):writer.writerow([key,context,int(node),int(owners[j]),int(actors[j]),int(month[j])+1,float(people[j]),float(energy[j]),float(a.unmet[j]),float(new.unmet[j]),bool(fields[context+'__A__food_pass'][j]),bool(fields[context+'__B__food_pass'][j])])
            path=out/(key+'_fields.npz');np.savez_compressed(path,**fields);files[path.name]=sha(path);path=out/(key+'_origins.csv.gz');path.write_bytes(gzip.compress(b.getvalue().encode(),mtime=0));files[path.name]=sha(path);cases.append(key);print('Source meals built',key,flush=True)
    write(out/'results.json',dict(status='fixed_source_meal_inventory_diagnostic',rows=rows,cases=cases,sources=sources,producers=producers,files_sha256=files,unchanged_atlas_sha256=protected,scope='A monthly meals-before-clip versus B continuous meals with immediate clip. Same harvest,people,365day capacity;no new export stream,shipments,residents or maps.'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
