"""Read-only daily progress and saved-state budgets; no incomplete-month scores."""
from pathlib import Path
import argparse,json,sys
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load,energy


def monitor(source,out):
    source=source.resolve();out=out.resolve()
    plan=json.loads((source/'frozen_protocol.json').read_text());literal=ROOT/'calibration/regional_rainfall_benchmark_20261029/plan.json';assert literal.read_bytes()==(source/'frozen_protocol.json').read_bytes()
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    records={};references={};inputs={}
    for spec in plan['cases']:
        if spec['kind']!='prototype' or not spec['primary']:continue
        region=spec['region'];name=spec['initial_water'];p=json.loads((ROOT/spec['plan']).read_text());folder=source/spec['name']/region;initial_path=folder/'initial.npz'
        if not initial_path.exists():continue
        initial=load(initial_path);ref=references.setdefault(region,load(ROOT/plan['reference_footprints'][region]));mask=ref['score_mask'];weights=ref['valid_area_km2'][mask];weights=weights/weights.sum();m=-np.diff(initial['pressure_edges'])/9.80665;e0=energy(initial,m);w0=float(initial['vapor'].sum()+initial['surface_liquid'].sum());cells=mask.size;rows=[];previous=initial
        inputs[str(initial_path.relative_to(ROOT))]=file_hash(initial_path)
        for day in range(1,46):
            stem=folder/'forced'/f'day_{day}_900';jp=stem.with_suffix('.json')
            if not jp.exists():break
            d=json.loads(jp.read_text());a=load(stem.with_suffix('.npz'));assert file_hash(stem.with_suffix('.npz'))==d['fields_sha256']
            ee=abs(energy(a,m)-e0-d['net_external_energy_j_m2']*cells)/abs(e0);we=abs(a['vapor'].sum()+a['surface_liquid'].sum()-w0+d['net_outward_water_kg_m2']*cells)/w0;assert max(ee,we)<1e-10
            evaporation=a['day_rain']-a['surface_liquid']+previous['surface_liquid'];assert abs(evaporation.mean()-d['net_evaporation_kg_m2'])<1e-9
            rows.append(dict(day=day,rain_mm_day=float(weights@a['day_rain'][mask]),liquid_kg_m2=float(weights@a['surface_liquid'][mask]),skin_temperature_k=float(weights@a['surface_temperature'][mask]),evaporation_mm_day=float(weights@evaporation[mask]),actual_energy_relative_error=float(ee),actual_water_relative_error=float(we),fields_sha256=d['fields_sha256']))
            inputs[str(jp.relative_to(ROOT))]=file_hash(jp);inputs[str(stem.with_suffix('.npz').relative_to(ROOT))]=d['fields_sha256'];previous=a
        records.setdefault(region,{})[name]=dict(rows=rows,available_days=len(rows),complete_evaluation_days=max(0,len(rows)-14),month=p['calendar']['month'])
    available=[region for region in ['north_india','mexico','pacific_nw'] if any(v['available_days'] for v in records.get(region,{}).values())];assert available,'No complete daily checkpoint yet'
    fig,axes=plt.subplots(len(available),3,figsize=(14,4*len(available)),squeeze=False)
    for row,region in enumerate(available):
        for name,color in [('wet','#187aa7'),('dry','#d68a35')]:
            data=records.get(region,{}).get(name,{}).get('rows',[]);days=[r['day'] for r in data]
            for ax,key in zip(axes[row],['rain_mm_day','liquid_kg_m2','skin_temperature_k']):ax.plot(days,[r[key] for r in data],color=color,marker='.',label=name+f' ({len(days)}/45 days)')
        ref=references[region];mask=ref['score_mask'];w=ref['valid_area_km2'][mask];month=7 if region!='mexico' else 8;observed=float(np.average(ref['observed_monthly_rain'][month-1][mask]/31,weights=w))
        axes[row,0].plot([14.5,45.5],[observed,observed],ls='--',color='#28774d',label='WorldClim month mean')
        for ax,title,unit in zip(axes[row],['Daily rain on scoring footprints','Surface liquid on scoring footprints','Model skin temperature, flattened terrain'],['mm/day','kg/m²','K']):
            ax.axvspan(.5,14.5,color='#d0d0d0',alpha=.35);ax.axvline(14.5,color='#777',lw=.8);ax.set_xlim(.5,45.5);ax.set_title(region.replace('_',' ')+': '+title,fontsize=10);ax.set_xlabel('Elapsed model day (shaded: fixed prelude)');ax.set_ylabel(unit);ax.grid(alpha=.2);ax.legend(fontsize=8)
    now=datetime.now(ZoneInfo('Europe/Warsaw'));stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True,exist_ok=True);picture=out/('progress_'+stamp+'.png')
    fig.suptitle('Monthly rainfall benchmark — available daily checkpoints',fontsize=14);fig.text(.5,.01,now.strftime('%Y-%m-%d %H:%M %Z')+' • monthly-normal guide is not daily observed weather • no incomplete-month candidate scores',ha='center',fontsize=9);fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(picture,dpi=150);plt.close(fig)
    result=dict(status='in_progress_daily_states_verified',new_integrations_started=0,records=records,input_sha256=inputs,figure=str(picture.relative_to(ROOT)),figure_sha256=file_hash(picture),monitor_sha256=file_hash(Path(__file__)),scope='Read-only available daily checkpoints under fixed scoring footprints. All available daily numerical water/energy budgets verified. No partial evaluation month is scored or substituted for a complete candidate month; reference guide is a monthly climatological mean.')
    write_json(out/('progress_'+stamp+'.json'),result);write_json(out/'latest.json',result);print(json.dumps(dict(figure=result['figure'],days={r:{n:v['available_days'] for n,v in branches.items()} for r,branches in records.items()}),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();monitor(a.source,a.out)
