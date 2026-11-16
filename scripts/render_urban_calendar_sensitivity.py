"""Reviewed exact-energy timing comparisons; no bounds or date-validation claim."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_calendar_sensitivity_20261116'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116'
WORK=ROOT/'output/urban_component_work_20261116'
KCAL=912500.


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    catalogue=dict(np.load(OUT/'catalogue/windows.npz'))
    summary=[];town_rows=[];month_rows=[];region_rows=[];ambiguity=[];data={};inputs={};compact={}
    count=sum(((catalogue['boundary_bits']>>m)&1).astype(np.uint8) for m in range(12))
    for reading in ['central','low']:
        a=dict(np.load(ANNUAL/'wind_1981/prepared'/f'low_{reading}.npz'))
        b=dict(np.load(WORK/'hours600/cases'/f'{reading}.npz'))
        first=dict(np.load(MONTHLY/'cases'/reading/'fields.npz'));first_result=read(MONTHLY/'cases'/reading/'results.json')
        first_meals=first['town_food__consumed']/KCAL;request=first['request']
        for component,label in enumerate(['base','flood']):
            positive=catalogue['potential'][component]>0;ambiguous=positive&(count[component]>1)
            energy=catalogue['potential'][component];grain=b['B_produced_components'][component]
            ambiguity.append(dict(reading=reading,component=label,positive_components=int(positive.sum()),ambiguous_components=int(ambiguous.sum()),
                ambiguous_potential_share=float(energy[ambiguous].sum()/energy.sum()),
                ambiguous_produced_grain_share=float(grain[ambiguous].sum()/grain.sum())))
        for timing in ['first','earliest','latest']:
            folder=MONTHLY/'cases'/reading if timing=='first' else OUT/'cases'/f'{reading}_{timing}'
            r=read(folder/'results.json');review=read(folder/'review.json');c=dict(np.load(folder/'fields.npz'))
            assert review['results_sha256']==sha(folder/'results.json') and review['fields_sha256']==sha(folder/'fields.npz')
            assert review['maximum_fraction_of_original_inventory_tolerance']<=1
            inputs[str((folder/'review.json').relative_to(ROOT))]=sha(folder/'review.json')
            meals=c['town_food__consumed']/KCAL;delta=meals-first_meals;percentage=100*delta/request
            changed=abs(delta)>1e-7
            summary.append(dict(reading=reading,timing=timing,meal_fraction=r['monthly_audit']['town_meal_fraction'],
                change_percentage_points=100*(r['monthly_audit']['town_meal_fraction']-first_result['monthly_audit']['town_meal_fraction']),
                change_meals_person_years=float(delta.sum()),rural_unmet_person_years=r['monthly_audit']['rural_unmet_person_years'],
                fully_supported_city_cells=r['monthly_audit']['final_fully_supported_towns'],
                increased_city_cells=int((delta>1e-7).sum()),decreased_city_cells=int((delta< -1e-7).sum()),
                max_absolute_city_change_percentage_points=float(abs(percentage).max())))
            for region,values in r['regions'].items():
                region_rows.append(dict(reading=reading,timing=timing,region=region,**values))
            for month in range(12):
                month_rows.append(dict(reading=reading,timing=timing,month=month+1,
                    meal_fraction=1-float(c['town_food__unmet_path'][month].sum()/(request.sum()*KCAL/12)),
                    harvested_person_years=float(c['harvest'][month].sum()/KCAL)))
            if timing!='first':
                for i,node in enumerate(a['nodes']):
                    town_rows.append(dict(reading=reading,timing=timing,cell=int(node),
                        lat=float(a['lat'].ravel()[node]),lon=float(a['grid_lon'].ravel()[node]),requested_people=float(request[i]),
                        first_meals_person_years=float(first_meals[i]),scenario_meals_person_years=float(meals[i]),
                        change_meals_person_years=float(delta[i]),change_percentage_points=float(percentage[i])))
                data[reading,timing]=(a,c,r,percentage,changed)
                for key,value in dict(request=request,nodes=a['nodes'],meals=meals,monthly_unmet=c['town_food__unmet_path']).items():
                    compact[f'{reading}_{timing}_{key}']=value
    for name,rows in [('summary',summary),('towns',town_rows),('months',month_rows),('regions',region_rows),('ambiguity',ambiguity)]:
        table(OUT/f'{name}.csv',rows)
    np.savez_compressed(OUT/'town_model.npz',**compact)
    fig,(left,right)=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    labels=[];all_values=[]
    for i,(reading,timing) in enumerate([('central','earliest'),('central','latest'),('low','earliest'),('low','latest')]):
        row=next(v for v in summary if v['reading']==reading and v['timing']==timing)
        left.bar(i,row['change_percentage_points'],color='#438395' if reading=='central' else '#bd874d')
        left.text(i,row['change_percentage_points']+(0.001 if row['change_percentage_points']>=0 else -.001),
            f'{row["change_percentage_points"]:+.4f}',ha='center',va='bottom' if row['change_percentage_points']>=0 else 'top',fontsize=9)
        labels.append(f'{reading}\n{timing}')
        a,c,r,delta,changed=data[reading,timing];values=delta[changed];all_values.extend(values)
        jitter=np.linspace(-.18,.18,len(values))
        right.scatter(i+jitter,values,s=12,alpha=.65,c='#438395' if reading=='central' else '#bd874d')
    left.axhline(0,c='#474c51',lw=.8);right.axhline(0,c='#474c51',lw=.8)
    left.set(xticks=np.arange(4),xticklabels=labels,ylabel='Change in aggregate city meals (percentage points)',title='Requested-population-weighted aggregate change')
    left.margins(y=.2)
    right.set(xticks=np.arange(4),xticklabels=labels,ylabel='Change per city cell (percentage points)',title='City cells with a material change only')
    for ax in [left,right]:ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig.suptitle('Equal grain and work, different model harvest dates',fontsize=15)
    fig.supxlabel('Differences from original first-best calendars. Earliest/latest are two attainable recipes,not bounds,probabilities or observed dates.',fontsize=10)
    fig.savefig(OUT/'comparison.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
    maximum=max(abs(np.asarray(all_values))) if all_values else 1.
    for row,timing in enumerate(['earliest','latest']):
        for column,reading in enumerate(['central','low']):
            ax=axes[row,column];a,c,r,delta,changed=data[reading,timing]
            lat=a['lat'].ravel();lon=a['grid_lon'].ravel();land=a['land'].ravel();nodes=a['nodes']
            ax.scatter(lon[land],lat[land],c='#e7eaec',s=.8,rasterized=True)
            ax.scatter(lon[nodes],lat[nodes],c='#b3b9bd',s=9,rasterized=True)
            points=ax.scatter(lon[nodes[changed]],lat[nodes[changed]],c=delta[changed],s=27,
                cmap='RdBu',vmin=-maximum,vmax=maximum,edgecolors='#454a50',linewidths=.25)
            ax.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)',title=f'{reading.capitalize()} • {timing} maturity boundary')
            ax.set_xlim(lon[nodes].min()-2,lon[nodes].max()+2);ax.set_ylim(lat[nodes].min()-2,lat[nodes].max()+2)
            ax.set_aspect(1/np.cos(np.deg2rad(38)))
    bar=fig.colorbar(points,ax=axes,orientation='horizontal',fraction=.025,pad=.01)
    bar.set_label('Monthly city meal fraction: change from first-best baseline (percentage points)')
    fig.suptitle('Exact-energy timing alternatives • fixed original requests and policy shares',fontsize=14)
    fig.supxlabel('One shared workforce and unchanged grain,stores,losses and routes. Gray = no material change. No new city occupancy or atlas adoption.',fontsize=9)
    fig.savefig(OUT/'city_changes.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained');months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    for column,reading in enumerate(['central','low']):
        for timing,color in [('first','#596169'),('earliest','#438395'),('latest','#bd874d')]:
            rows=[v for v in month_rows if v['reading']==reading and v['timing']==timing]
            axes[0,column].plot(np.arange(12),[v['harvested_person_years']/1e6 for v in rows],'o-',c=color,label=timing)
            axes[1,column].plot(np.arange(12),[100*v['meal_fraction'] for v in rows],'o-',c=color,label=timing)
        axes[0,column].set(title=reading.capitalize(),ylabel='Harvested grain (million person-years)')
        axes[1,column].set(ylabel='Requested city meals supplied (%)')
        for row in range(2):
            axes[row,column].set_xticks(np.arange(12),months);axes[row,column].grid(alpha=.18)
    axes[0,0].legend(frameon=False)
    fig.suptitle('Large harvest-date changes and their conditional monthly meal response',fontsize=14)
    fig.supxlabel('All schedules retain exact annual grain and work.365d source/export and90d town stores remain scenario assumptions; buffering effects are not isolated here.',fontsize=9)
    fig.savefig(OUT/'monthly_response.png',dpi=160);plt.close(fig)
    files=['summary.csv','towns.csv','months.csv','regions.csv','ambiguity.csv','town_model.npz','comparison.png','city_changes.png','monthly_response.png']
    receipt=dict(status='rendered_reviewed_exact_energy_calendar_sensitivity',producer_sha256=sha(Path(__file__)),
        inputs_sha256=inputs,files_sha256={name:sha(OUT/name) for name in files},food_cases=4,baseline_cases=2,
        city_rows=len(town_rows),month_rows=len(month_rows),regional_rows=len(region_rows),ambiguity_rows=len(ambiguity),
        interpretation='Two recipes,not global robustness bounds; local effects and aggregate effects have different magnitudes.',
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False)
    (OUT/'presentation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'],flush=True)


if __name__=='__main__':main()
