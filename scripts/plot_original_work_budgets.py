"""Read-only spatial rendering of the two original partial B600 crop-work budgets."""
import csv
from pathlib import Path
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,LogNorm
from matplotlib.patches import Patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_original_work_map_20261117'
WORK=ROOT/'output/urban_component_work_20261116'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared'
CAL=ROOT/'output/urban_earth_calendars_20261116/calendars.npz'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_work_diagnostic_map.json'


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists(),'Preserve completed original work inspection map'
    sources={};protected={}
    for folder in [ROOT/'output/urban_columella_concordance_20261117',ROOT/'output/urban_warehouse_work_20261117']:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('local_source_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q.get(key,{}).items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json');protected.update(q['protected_sha256'])
    with np.load(CAL) as z:source=z['source_indices']
    assert source.dtype.kind in 'iu' and len(np.unique(source))==len(source)==56378
    paths=[Path(__file__),PLAN,CAL]
    frames={};summaries=[];values=dict(source_indices=source)
    geometry=None
    for reading in ['central','low']:
        case=WORK/'hours600/cases'/f'{reading}.npz';prepared=ANNUAL/f'low_{reading}.npz';monthly=MONTHLY/'cases'/reading/'fields.npz'
        paths.extend([case,prepared,monthly])
        with np.load(case) as z:b={key:z[key] for key in ['rural','B_workers','B_annual_available','B_annual_used']}
        with np.load(prepared) as z:g={key:z[key] for key in ['land','lat','grid_lon','cell_km','rural']}
        with np.load(monthly) as z:np.testing.assert_array_equal(source,z['source_indices']);np.testing.assert_array_equal(b['rural'],z['rural'])
        np.testing.assert_array_equal(b['rural'],g['rural'][source]);np.testing.assert_array_equal(b['B_workers'],b['rural']*.4)
        if geometry is None:geometry={key:g[key] for key in ['land','lat','grid_lon','cell_km']}
        else:
            for key,value in geometry.items():np.testing.assert_array_equal(value,g[key])
        annual=b['B_annual_available'];used=b['B_annual_used'];unused=annual-used;defined=b['B_workers']>0
        np.testing.assert_array_equal(annual,b['B_workers']*600)
        tol=1e-8*np.maximum(1,annual);assert np.all(unused>=-tol)
        raw_util=np.divide(100*used,annual,out=np.full_like(annual,np.nan),where=defined)
        plot_util=np.clip(raw_util,0,100) # display only;the raw arrays are retained.
        plot_unused=np.maximum(unused,0)/float(g['cell_km'])**2
        positive=defined&(plot_unused>0)
        frames[reading]=(plot_util,plot_unused,defined)
        for key,value in [('annual_available',annual),('annual_used',used),('raw_unused',unused),('plot_utilization',plot_util),
                          ('plot_unused_hours_per_km2',plot_unused),('defined',defined)]:values[f'{reading}_{key}']=value
        summaries.append(dict(reading=reading,source_cells=len(source),positive_workforce_cells=int(defined.sum()),
            undefined_utilization_cells=int((~defined).sum()),cell_area_km2=float(g['cell_km'])**2,
            annual_listed_allowance_hours=float(annual.sum()),annual_listed_used_hours=float(used.sum()),
            raw_unspent_listed_hours=float(unused.sum()),raw_unspent_fraction=float(unused.sum()/annual.sum()),
            sources_at_annual_limit=int((defined&(unused<=tol)).sum()),display_negative_unused_clips=int((unused<0).sum()),
            display_percent_clips=int((defined&((raw_util<0)|(raw_util>100))).sum()),
            positive_allowance_below_log_floor=int((positive&(plot_unused<.01)).sum()),
            positive_allowance_above_log_ceiling=int((positive&(plot_unused>10000)).sum()),
            zero_display_allowance_cells=int((defined&(plot_unused==0)).sum()),
            interpretation='Original partial listed cereal-work scenario;unspent allowance is not available logisticsstaff.'))
    OUT.mkdir(exist_ok=True);np.savez_compressed(OUT/'local_plot_values.npz',**values)
    with (OUT/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(summaries[0]));w.writeheader();w.writerows(summaries)
    write(OUT/'summary.json',summaries)
    lat=geometry['lat'];lon=geometry['grid_lon'];land=geometry['land'];shape=land.shape
    fig,axes=plt.subplots(2,2,figsize=(14,10),sharex=True,sharey=True)
    util_image=allowance_image=None
    for col,reading in enumerate(['central','low']):
        util,allowance,defined=frames[reading]
        for row in range(2):
            ax=axes[row,col];ax.contourf(lon,lat,land.astype(int),levels=[.5,1.5],colors=['#eeeeea'],zorder=0)
            ax.contour(lon,lat,land.astype(int),levels=[.5],colors=['#a3a6a1'],linewidths=.35,zorder=2)
            ax.set_xlim(-17,51);ax.set_ylim(23,56);ax.set_aspect(1/np.cos(np.deg2rad(38)))
            ax.grid(alpha=.14);ax.tick_params(labelsize=8)
            frame=np.full(shape,np.nan)
            if row==0:
                frame.ravel()[source[defined]]=util[defined]
                util_image=ax.pcolormesh(lon,lat,frame,cmap='YlOrRd',vmin=0,vmax=100,shading='nearest',zorder=1)
                ax.set_title(f'{reading.capitalize()} · listed annual use',fontsize=12)
            else:
                zeros=defined&(allowance==0);background=np.full(shape,np.nan);background.ravel()[source[zeros]]=1
                ax.pcolormesh(lon,lat,background,cmap=ListedColormap(['#c5c8c7']),vmin=0,vmax=1,shading='nearest',zorder=1)
                positive=defined&(allowance>0);frame.ravel()[source[positive]]=allowance[positive]
                allowance_image=ax.pcolormesh(lon,lat,frame,cmap='viridis',norm=LogNorm(vmin=.01,vmax=10000),shading='nearest',zorder=1)
                ax.set_title(f'{reading.capitalize()} · unspent listed allowance',fontsize=12)
                ax.set_xlabel('Longitude (°E)')
        axes[0,col].text(.025,.025,f"{100*summaries[col]['raw_unspent_fraction']:.2f}% of listed annual allowance unspent",
            transform=axes[0,col].transAxes,fontsize=8.5,bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
    for row in range(2):axes[row,0].set_ylabel('Latitude (°N)')
    fig.subplots_adjust(left=.06,right=.89,top=.88,bottom=.16,hspace=.18,wspace=.10)
    cax1=fig.add_axes([.91,.56,.014,.27]);cb1=fig.colorbar(util_image,cax=cax1);cb1.set_label('Listed crop-work use (%)',fontsize=9)
    cax2=fig.add_axes([.91,.22,.014,.27]);cb2=fig.colorbar(allowance_image,cax=cax2,extend='both');cb2.set_label('Unspent listed hours / km²',fontsize=9)
    fig.suptitle('Original physical-source crop-work budgets · B600 scenario',fontsize=16,y=.97)
    fig.text(.5,.92,'Same original production/population cases and scales · diagnostic rendering with no new food or climate run',ha='center',fontsize=10)
    fig.legend(handles=[Patch(facecolor='#c5c8c7',label='Zero unspent allowance (positive workforce)'),
        Patch(facecolor='#eeeeea',label='Land without a displayed source/positive workforce')],loc='lower center',bbox_to_anchor=(.5,.075),ncol=2,frameon=False,fontsize=9)
    fig.text(.5,.035,'Listed cereal tasks are partial. Reaping alone has monthly timing;unspent allowance is not warehouse staff.\n'
        'Tiny roundoff is clipped only for display;raw budgets and original work tolerance remain unchanged.',ha='center',fontsize=9)
    figure=OUT/'original_work_budgets.png';fig.savefig(figure,dpi=180);plt.close(fig)
    for path in paths:sources[str(path.relative_to(ROOT))]=sha(path)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='rendered_original_partial_work_budgets_pending_independent_value_review',sources_sha256=sources,
        protected_sha256=protected,files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},original_cases=2,source_cells_per_case=56378,
        plot_panels=4,percent_scale=[0,100],positive_log_hours_km2_scale=[.01,10000],zero_allowance_separate=True,
        undefined_workforce_not_zero_utilization=True,raw_budgets_changed=False,solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))
    print('Rendered original four-panel work inspection map;unspent fractions',*[s['raw_unspent_fraction'] for s in summaries],flush=True)


if __name__=='__main__':main()
