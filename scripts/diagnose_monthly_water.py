"""Map conserved daily water supplies over the common available wet/dry interval.

This is a mechanism diagnostic, never a substitute for complete-month scores.
"""
from pathlib import Path
import argparse,json,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load
from resume_rainfall_month import checked_prefix


def diagnose(source,out):
    source=source.resolve();out=out.resolve();plan=json.loads((source/'frozen_protocol.json').read_text())
    literal=ROOT/'calibration/regional_rainfall_benchmark_20261029/plan.json';assert literal.read_bytes()==(source/'frozen_protocol.json').read_bytes()
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    regions=[];diagnostics={};fields={};inputs={};summaries={}
    for region in ['north_india','mexico','pacific_nw']:
        cases=[next(c for c in plan['cases'] if c['kind']=='prototype' and c['region']==region and c['initial_water']==initial and c['primary']) for initial in ['wet','dry']]
        ends=[]
        for case in cases:
            paths=list((source/case['name']/region/'forced').glob('day_*_900.json'));ends.append(max([int(p.stem.split('_')[1]) for p in paths],default=0))
        end=min(ends);start=14
        if end<=start:continue
        regions.append(region);ref=load(ROOT/plan['reference_footprints'][region]);mask=ref['score_mask'];weights=ref['valid_area_km2'][mask];weights=weights/weights.sum();summaries[region]=dict(start_after_day=start,end_day=end,evaluation_days=end-start,full_month=end==45,branches={})
        for case in cases:
            folder=source/case['name'];initial,last,rows,hashes=checked_prefix(folder,region,900,end)
            inputs.update({str((folder/n).relative_to(ROOT)):h for n,h in hashes.items()})
            first=load(folder/region/'forced'/f'day_{start}_900.npz');duration=end-start
            rain=(last['rain']-first['rain'])/duration;liquid_change=(last['surface_liquid']-first['surface_liquid'])/duration;vapor_change=(last['vapor']-first['vapor']).sum(0)/duration
            evaporation=rain-liquid_change;net_import=vapor_change+liquid_change
            # These source identities are exact for the declared liquid-only
            # model: there is no runoff, lateral soil flow, or omitted ice pool.
            assert np.max(abs(rain-evaporation-net_import+vapor_change))<1e-11
            values=dict(rain=rain,evaporation=evaporation,net_column_import=net_import,vapor_storage_change=vapor_change,surface_storage_change=liquid_change)
            name=case['initial_water'];fields[region+'_'+name]=values
            summaries[region]['branches'][name]={key:float(weights@value[mask]) for key,value in values.items()}
            diagnostics[case['name']]=dict(available_daily_budgets_verified=end,period_start_day=start+1,period_end_day=end,scored_area_mean_rates_mm_day=summaries[region]['branches'][name],identity='P = E + net column horizontal import - vapor storage change; inferred from conserved stores, not independent water-origin tracers.')
        fields[region+'_geo']=ref
    assert regions,'No paired evaluation-day checkpoints yet'
    fig,axes=plt.subplots(2*len(regions),4,figsize=(16,7.5*len(regions)),squeeze=False)
    keys=['rain','evaporation','net_column_import','vapor_storage_change'];titles=['Rain','Net evaporation','Net column water import','Vapor storage change']
    for index,region in enumerate(regions):
        geo=fields[region+'_geo'];entry=summaries[region];label=f"days {entry['start_after_day']+1}–{entry['end_day']} ({entry['evaluation_days']} days)"
        for col,(key,title) in enumerate(zip(keys,titles)):
            data=[fields[region+'_'+name][key] for name in ['wet','dry']];limit=max(float(max(np.max(abs(value)) for value in data)),.01);signed=key!='rain'
            for branch,name in enumerate(['wet','dry']):
                ax=axes[2*index+branch,col];plot=ax.pcolormesh(geo['longitude'],geo['latitude'],data[branch],shading='nearest',cmap='RdBu_r' if signed else 'YlGnBu',vmin=-limit if signed else 0,vmax=limit)
                coast=ax.contour(geo['longitude'],geo['latitude'],geo['land'].astype(float),levels=[.5],colors='#203d4a',linewidths=1.)
                coast.set_path_effects([pe.withStroke(linewidth=2.8,foreground='white')])
                mask=geo['score_mask'];ax.scatter(geo['longitude'][mask],geo['latitude'][mask],s=9,facecolors='none',edgecolors='#111',linewidths=.5)
                ax.set_title(region.replace('_',' ')+f' {name}: '+title,fontsize=10);ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');fig.colorbar(plot,ax=ax,shrink=.7,label='mm/day')
                mean=entry['branches'][name][key];ax.text(.02,.02,f'Fixed-footprint mean: {mean:+.3f}\n{label}',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.88,edgecolor='none'))
    fig.suptitle('Where is the rainwater coming from? Paired saved-state water budgets',fontsize=15);fig.text(.5,.008,'Matched available evaluation days only • circles: frozen scoring cells • common wet/dry scales per column and region • inferred flux identities, not water-origin tracers',ha='center',fontsize=9);fig.tight_layout(rect=(0,.035,1,.95))
    out.mkdir(parents=True,exist_ok=True);picture=out/'water_supply.png';fig.savefig(picture,dpi=145);plt.close(fig)
    np.savez_compressed(out/'water_fields.npz',**{region+'_'+name+'_'+key:value for region in regions for name in ['wet','dry'] for key,value in fields[region+'_'+name].items()})
    result=dict(status='paired_available_evaluation_days_only',summaries=summaries,diagnostics=diagnostics,input_sha256=inputs,figure_sha256=file_hash(picture),fields_sha256=file_hash(out/'water_fields.npz'),diagnostic_sha256=file_hash(Path(__file__)),new_integrations_started=0,complete_month_score_produced=False,scope='Read-only conserved-store identities. Paired branches use their common available days after the fixed prelude. No incomplete-month rainfall error, pooled skill score, water-origin fractions or physical adoption.')
    write_json(out/'diagnosis.json',result);print(json.dumps(dict(summaries=summaries,figure=str(picture.relative_to(ROOT))),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();diagnose(a.source,a.out)
