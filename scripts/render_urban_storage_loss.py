"""Reviewed factorial city maps, complete differences and factor interactions."""
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from urban_storage_loss import OUT, BASE, ANNUAL, COMBOS
from urban_earth_monthly import read, write, sha, total, KCAL

LABELS = ['loss05_days365'] + [x[0] for x in COMBOS]
TITLES = ['5% loss, 365-day stores (baseline)', '5% loss, 90-day stores', 'Zero loss, 365-day stores', 'Zero loss, 90-day stores']


def table(name, rows):
    with (OUT/name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def effects(values):
    a, b, c, d = [np.asarray(v) for v in values]
    return dict(capacity_at_five_percent=b-a, capacity_at_zero_loss=d-c,
        zero_loss_at_365_days=c-a, zero_loss_at_90_days=d-b,
        capacity_average_effect=((b-a)+(d-c))/2,
        zero_loss_average_effect=((c-a)+(d-b))/2,
        interaction=d-b-c+a)


def main():
    assert not (OUT/'results.json').exists(), 'Preserve completed presentation'
    towns=[]; months=[]; regions=[]; summaries=[]; cityeffects=[]; regioneffects=[]; montheffects=[]
    packet={}; sources={}; data={}; aggregate_effects={}; maxratio=0.; maxledger=0.; shipments=0
    for reading in ['central', 'low']:
        a = dict(np.load(ANNUAL/f'low_{reading}.npz')); baseline = dict(np.load(BASE/'cases'/reading/'fields.npz'))
        parent = read(BASE/'cases'/reading/'results.json')
        control = read(OUT/'controls'/f'{reading}.json'); assert control['arrays_exact']==70
        sources[str((OUT/'controls'/f'{reading}.json').relative_to(ROOT))] = sha(OUT/'controls'/f'{reading}.json')
        scenarios={LABELS[0]:baseline}; results={LABELS[0]:parent['monthly_audit']}
        for label, loss, days in COMBOS:
            folder=OUT/'cases'/f'{reading}_{label}'; review=read(folder/'review.json'); r=read(folder/'results.json')
            assert review['status']=='passed_fixed_reference_storage_loss_stock_routes_and_ledger'
            for filename, key in [('results.json', 'results_sha256'), ('fields.npz', 'fields_sha256')]: assert sha(folder/filename)==review[key]
            assert sha(ROOT/'scripts/review_urban_storage_loss.py')==review['reviewer_sha256']
            sources[str((folder/'review.json').relative_to(ROOT))]=sha(folder/'review.json')
            maxratio=max(maxratio,review['maximum_fraction_of_original_inventory_tolerance'])
            maxledger=max(maxledger,abs(review['grain_residual_person_years']));shipments+=review['independent_shipments']
            scenarios[label]=dict(np.load(folder/'fields.npz'));results[label]=r['audit']
        nodes=a['nodes'];lat=a['lat'].ravel()[nodes];lon=a['grid_lon'].ravel()[nodes];request=baseline['request']
        egypt=(lon>=29)&(lon<=32.6)&(lat<=32)
        masks={'all':np.ones(len(request),bool),'west':a['lon']<=np.median(a['lon']),'east':a['lon']>np.median(a['lon']),
               'egypt_proper':egypt,'other':~egypt}
        meals={label:c['town_food__consumed']/KCAL for label,c in scenarios.items()}
        monthly={label:request[None]/12-c['town_food__unmet_path']/KCAL for label,c in scenarios.items()}
        ce=effects([meals[label] for label in LABELS]);aggregate_effects[reading]={key:total(value) for key,value in ce.items()}
        for i,node in enumerate(nodes):
            cityeffects.append(dict(reading=reading,cell=int(node),lat=float(lat[i]),lon=float(lon[i]),requested_people=float(request[i]),
                **{key+'_person_years':float(value[i]) for key,value in ce.items()},
                **{key+'_percentage_points':float(100*value[i]/request[i]) for key,value in ce.items()}))
        me=effects([monthly[label].sum(1) for label in LABELS])
        for month in range(12):
            montheffects.append(dict(reading=reading,month=month+1,**{key+'_person_years':float(value[month]) for key,value in me.items()}))
        for region,mask in masks.items():
            regioneffects.append(dict(reading=reading,region=region,requested_people=total(request[mask]),
                **{key+'_person_years':total(value[mask]) for key,value in ce.items()},
                **{key+'_percentage_points':100*total(value[mask])/total(request[mask]) for key,value in ce.items()}))
        for key,value in dict(nodes=nodes,lat=lat,lon=lon,request=request).items():packet[reading+'_'+key]=value
        for label,c in scenarios.items():
            delta=meals[label]-meals[LABELS[0]];audit=results[label]
            fully=c['town_food__unmet']<=1e-8*np.maximum(1,c['town_food__needed'])
            summary=dict(reading=reading,scenario=label,meal_fraction=audit['town_meal_fraction'],
                delta_percentage_points=100*total(delta)/total(request),town_meals_person_years=total(meals[label]),
                delta_meals_person_years=total(delta),rural_unmet_person_years=audit['rural_unmet_person_years'],
                city_unmet_person_years=audit['town_unmet_person_years'],full_meal_cities=int(fully.sum()),
                gaining_cities=int((delta>1e-7).sum()),losing_cities=int((delta< -1e-7).sum()),
                maximum_city_gain_pp=float((100*delta/request).max()),maximum_city_loss_pp=float((100*delta/request).min()),
                spoiled_person_years=sum(audit['ledger'][key] for key in ['rural_spoiled_kcal','export_spoiled_kcal','town_spoiled_kcal'])/KCAL,
                unused_person_years=sum(audit['ledger'][key] for key in ['source_unused_kcal','town_unused_kcal'])/KCAL,
                freight_loss_person_years=sum(audit['ledger'][key] for key in ['source_freight_loss_kcal','intertown_freight_loss_kcal'])/KCAL)
            summaries.append(summary)
            for i,node in enumerate(nodes):
                towns.append(dict(reading=reading,scenario=label,cell=int(node),lat=float(lat[i]),lon=float(lon[i]),
                    requested_people=float(request[i]),meals_person_years=float(meals[label][i]),meal_fraction=float(meals[label][i]/request[i]),
                    unmet_person_years=float(c['town_food__unmet'][i]/KCAL),delta_meals_person_years=float(delta[i]),
                    delta_percentage_points=float(100*delta[i]/request[i]),all_fixed_meals_within_tolerance=bool(fully[i])))
            for month in range(12):
                townmeal=total(monthly[label][month]);base=total(monthly[LABELS[0]][month]);monthlyneed=total(request)/12
                months.append(dict(reading=reading,scenario=label,month=month+1,meal_fraction=townmeal/monthlyneed,
                    meals_person_years=townmeal,delta_meals_person_years=townmeal-base,
                    delta_percentage_points=100*(townmeal-base)/monthlyneed,
                    source_harvest_person_years=total(c['harvest'][month])/KCAL,
                    rural_unmet_person_years=total(c['rural_food__unmet_path'][month])/KCAL,
                    marketed_person_years=total(c['marketed'][month])/KCAL,
                    dispatched_person_years=total(c['departures'][month])/KCAL,
                    direct_arrivals_person_years=total(c['direct'][month])/KCAL,
                    intertown_departures_person_years=total(c['inter_exported'][month])/KCAL,
                    intertown_arrivals_person_years=total(c['inter_received'][month])/KCAL))
            for region,mask in masks.items():
                regions.append(dict(reading=reading,scenario=label,region=region,requested_people=total(request[mask]),
                    meals_person_years=total(meals[label][mask]),meal_fraction=total(meals[label][mask])/total(request[mask]),
                    delta_meals_person_years=total(delta[mask]),delta_percentage_points=100*total(delta[mask])/total(request[mask])))
            for key,value in dict(consumed=c['town_food__consumed'],unmet=c['town_food__unmet_path'],fully_supported=fully).items():
                packet[reading+'_'+label+'_'+key]=value
        data[reading]=(a,scenarios,meals,ce)
    for name,rows in [('towns.csv',towns),('months.csv',months),('regions.csv',regions),('summary.csv',summaries),
                      ('city_effects.csv',cityeffects),('region_effects.csv',regioneffects),('month_effects.csv',montheffects)]:table(name,rows)
    np.savez_compressed(OUT/'town_model.npz',**packet)
    for reading,(a,scenarios,meals,ce) in data.items():
        nodes=a['nodes'];lat=a['lat'].ravel();lon=a['grid_lon'].ravel();land=a['land'].ravel();request=scenarios[LABELS[0]]['request']
        fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
        for ax,label,title in zip(axes.flat,LABELS,TITLES):
            ax.scatter(lon[land],lat[land],s=.8,c='#e6e9eb',rasterized=True)
            points=ax.scatter(lon[nodes],lat[nodes],c=100*meals[label]/request,s=16,cmap='viridis',vmin=0,vmax=100,rasterized=True)
            coverage=100*total(meals[label])/total(request)
            ax.set_title(f'{title}\n{coverage:.3f}% of fixed city meals',fontsize=12)
            ax.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)',xlim=(lon[nodes].min()-2,lon[nodes].max()+2),ylim=(lat[nodes].min()-2,lat[nodes].max()+2))
            ax.set_aspect(1/np.cos(np.deg2rad(38)))
        bar=fig.colorbar(points,ax=axes,orientation='horizontal',fraction=.035,pad=.02);bar.set_label('Requested annual city meals supplied (%)')
        fig.suptitle(f'{reading.capitalize()} density • fixed-infrastructure storage/loss experiment',fontsize=15)
        fig.supxlabel('Original B600h grain and harvest dates; fixed requests, policy shares and routes. Capacity days use ORIGINAL marketed grain. No occupancy change.',fontsize=9)
        fig.savefig(OUT/f'{reading}_meal_maps.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(17,9),layout='constrained')
    effectnames=['capacity_at_five_percent','zero_loss_at_365_days','interaction']
    effecttitles=['90-day minus 365-day commercial capacity (5% loss)','Zero minus 5% stock loss (365-day capacity)','Interaction: loss effect at 90 days minus at 365 days']
    limits=[max(float(abs(100*data[r][3][key]/data[r][1][LABELS[0]]['request']).max()) for r in data) for key in effectnames]
    for row,(reading,(a,scenarios,meals,ce)) in enumerate(data.items()):
        nodes=a['nodes'];lat=a['lat'].ravel();lon=a['grid_lon'].ravel();request=scenarios[LABELS[0]]['request']
        for col,(key,title,limit) in enumerate(zip(effectnames,effecttitles,limits)):
            ax=axes[row,col];ax.scatter(lon[a['land'].ravel()],lat[a['land'].ravel()],s=.6,c='#e6e9eb',rasterized=True)
            pts=ax.scatter(lon[nodes],lat[nodes],c=100*ce[key]/request,s=12,cmap='RdBu',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),rasterized=True)
            ax.set_title(f'{reading.capitalize()} • {title}',fontsize=9);ax.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)')
            ax.set_xlim(lon[nodes].min()-2,lon[nodes].max()+2);ax.set_ylim(lat[nodes].min()-2,lat[nodes].max()+2)
            ax.set_aspect(1/np.cos(np.deg2rad(38)))
            bar=fig.colorbar(pts,ax=ax,orientation='horizontal',fraction=.04,pad=.03);bar.set_label('Change in supplied meals (percentage points)',fontsize=8)
    fig.suptitle('Storage/loss effects and interaction at each fixed city request',fontsize=14)
    fig.savefig(OUT/'factor_effect_maps.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for ax,reading in zip(axes,['central','low']):
        for label,title in zip(LABELS,TITLES):
            rows=[row for row in months if row['reading']==reading and row['scenario']==label]
            ax.plot(range(1,13),[100*row['meal_fraction'] for row in rows],label=title,marker='.',linewidth=1.4)
        ax.set(title=reading.capitalize(),xlabel='Month',ylabel='Requested city meals supplied (%)',ylim=(0,101),xticks=range(1,13));ax.grid(alpha=.2)
    axes[1].legend(fontsize=8);fig.savefig(OUT/'monthly_meals.png',dpi=160);plt.close(fig)
    result=dict(status='reviewed_six_case_fixed_infrastructure_factorial',sources_sha256=sources,
        summary=summaries,aggregate_effects_person_years=aggregate_effects,
        counts=dict(new_cases=6,original_controls=2,exact_arrays_per_control=70,city_rows=len(towns),month_rows=len(months),region_rows=len(regions),
                    city_effect_rows=len(cityeffects),month_effect_rows=len(montheffects),region_effect_rows=len(regioneffects)),
        physical_source_cases=6*56378,inventory_groups=24,independent_shipments=shipments,
        maximum_fraction_of_original_inventory_tolerance=maxratio,max_grain_residual_person_years=maxledger,
        empirical_granary_calibration=False,new_fit=False,new_validation_claim=False,actual_population_changed=False,adopt=False)
    write(OUT/'results.json',result)
    print('Rendered',result['counts'],flush=True)


if __name__=='__main__':main()
