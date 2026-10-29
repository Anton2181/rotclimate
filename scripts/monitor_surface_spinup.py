"""Read-only matched daily progress maps and column-water accounting."""
from pathlib import Path
import argparse,json,sys
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json


def load(path):
    with np.load(path) as f:return {k:f[k] for k in f.files}


def monitor(wet,dry,out,*,final=False):
    out.mkdir(parents=True,exist_ok=True);stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S');checks={};inputs={};reproduction={}
    fig,axes=plt.subplots(4,3,figsize=(15,14))
    for col,region in enumerate(['north_india','mexico','pacific_nw']):
        available={name:[d for d in [1,2,3] if (folder/region/'forced'/f'day_{d}_900.json').exists()] for name,folder in [('wet',wet),('dry',dry)]}
        common=sorted(set(available['wet'])&set(available['dry']))
        # Reproduce each completed wet day1 against the earlier frozen24h run.
        for dt in [900,450]:
            snap=wet/region/'forced'/f'day_1_{dt}.npz';prior=ROOT/'output/surface_forcing_20261029'/region/'forced'/f'{dt}.npz'
            if snap.exists():
                a,b=load(snap),load(prior);diffs={k:float(abs(a[k]-b[k]).max()) for k in b}
                for k in b:np.testing.assert_allclose(a[k],b[k],rtol=1e-11,atol=1e-8)
                reproduction[region+'_'+str(dt)]=dict(maximum_absolute_differences=diffs,checkpoint_sha256=file_hash(snap),prior_sha256=file_hash(prior))
        if not common:
            for ax in axes[:,col]:ax.text(.5,.5,region.replace('_',' ')+'\nNo matched daily checkpoint yet',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off()
            checks[region]=dict(available_days=available,matched_day=None);continue
        day=common[-1];snapshots={};budgets={}
        for name,folder in [('wet',wet),('dry',dry)]:
            start=folder/region/('initial.npz' if day==1 else f'forced/day_{day-1}_900.npz')
            finish=folder/region/'forced'/f'day_{day}_900.npz';record_path=folder/region/'forced'/f'day_{day}_900.json';record=json.loads(record_path.read_text())
            assert file_hash(finish)==record['fields_sha256'];a,b=load(start),load(finish);snapshots[name]=b
            initial=folder/region/'initial.npz';geo=load(initial)
            rain=b['day_rain'];evap=rain-(b['surface_liquid']-a['surface_liquid'])
            convergence=(b['vapor']-a['vapor']).sum(0)+b['surface_liquid']-a['surface_liquid']
            previous_water=0. if day==1 else json.loads((folder/region/'forced'/f'day_{day-1}_900.json').read_text())['net_outward_water_kg_m2']
            expected_import=-(record['net_outward_water_kg_m2']-previous_water)
            water_error=float(abs(convergence.mean()-expected_import));evap_error=float(abs(evap.mean()-record['net_evaporation_kg_m2']))
            if max(water_error,evap_error)>1e-8:raise ValueError('Daily actual column-water budget failed')
            budgets[name]=dict(mean_daily_rain_mm=float(rain.mean()),mean_net_evaporation_kg_m2=float(evap.mean()),mean_horizontal_water_import_kg_m2=float(convergence.mean()),
                actual_column_water_budget_error_kg_m2=water_error,surface_rain_evap_identity_error_kg_m2=evap_error,evap=evap,convergence=convergence)
            for p in [start,finish,record_path,initial]:inputs[str(p.relative_to(ROOT))]=file_hash(p)
        fields=[snapshots['wet']['day_rain'],snapshots['dry']['day_rain'],budgets['wet']['evap']-budgets['dry']['evap'],budgets['wet']['convergence']-budgets['dry']['convergence']]
        rainmax=max(float(fields[0].max()),float(fields[1].max()),1e-10)
        for i,field in enumerate(fields):
            ax=axes[i,col];delta=i>=2;limit=max(float(abs(field).max()),1e-10)
            im=ax.pcolormesh(geo['longitude'],geo['latitude'],field,shading='nearest',cmap='RdBu_r' if delta else 'YlGnBu',vmin=-limit if delta else 0,vmax=limit if delta else rainmax)
            coast=ax.contour(geo['longitude'],geo['latitude'],geo['land'].astype(float),levels=[.5],colors='#243c48',linewidths=1.);coast.set_path_effects([pe.withStroke(linewidth=2.6,foreground='white')])
            ax.set_title(region.replace('_',' ')+f' day{day} — '+['wet-start rain','dry-start rain','wet −dry evaporation','wet −dry water convergence'][i],fontsize=10)
            ax.set_xlabel('Longitude');ax.set_ylabel('Latitude');fig.colorbar(im,ax=ax,shrink=.8,label='Daily rain (mm)' if i<2 else 'Daily difference (kg/m²)')
        checks[region]=dict(available_days=available,matched_day=day,budgets={n:{k:v for k,v in c.items() if k not in ['evap','convergence']} for n,c in budgets.items()})
    if final and any(c['matched_day']!=3 for c in checks.values()):raise ValueError('Final day-three map requires all matched day-three checkpoints')
    fig.suptitle('Day-three land-water sensitivity: daily rain and column budgets,900-second runs' if final else 'Progress only: matched daily rainfall and water budgets,900-second runs',fontsize=14)
    fig.text(.5,.01,'Day index is shown per region • initial land liquid50 versus0 kg/m² before conversion rain • no monthly climate skill or equilibrium claim',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.035,1,.97));picture=out/('progress_'+stamp+'.png');fig.savefig(picture,dpi=140);plt.close(fig)
    result=dict(status='read_only_progress_snapshot',new_integrations_started=0,regions=checks,wet_first_day_reproduction=reproduction,inputs=inputs,
        interpretation='Evaporation inferred from actual surface rain/mass change. Horizontal water import inferred from actual atmospheric+surface column storage change; all internal rain/evap cancels. This is net convergence, not moisture-origin attribution.',figure=str(picture.relative_to(ROOT)),figure_sha256=file_hash(picture))
    write_json(out/('progress_'+stamp+'.json'),result);print(json.dumps(dict(figure=result['figure'],matched_days={n:c['matched_day'] for n,c in checks.items()},first_day_reproductions=len(reproduction)),indent=2));return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--wet',type=Path,required=True);ap.add_argument('--dry',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();monitor(a.wet.resolve(),a.dry.resolve(),a.out.resolve())
