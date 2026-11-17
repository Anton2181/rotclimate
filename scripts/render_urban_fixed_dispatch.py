"""Maps and full city/month/region comparisons for the two quota controls."""
import csv
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from urban_fixed_dispatch import OUT,PARENT,ANNUAL,AUDIT
from urban_earth_monthly import read,write,sha,total,KCAL

LABELS=['loss05_own','loss00_own','loss00_fixed']
TITLES=['5% loss, original quota','Zero loss, own-scenario quota','Zero loss, fixed baseline quota']


def table(name,rows):
    with (OUT/name).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    assert not (OUT/'results.json').exists(),'Preserve completed presentation'
    towns=[];months=[];regions=[];differences=[];previous=[];summaries=[];data={};packet={};sources={};stats={}
    previous_rows=list(csv.DictReader((AUDIT/'city_losses.csv').open()))
    sources[str((AUDIT/'city_losses.csv').relative_to(ROOT))]=sha(AUDIT/'city_losses.csv')
    for reading in ['central','low']:
        a=dict(np.load(ANNUAL/f'low_{reading}.npz'));review=read(OUT/'cases'/reading/'review.json')
        assert review['status']=='passed_fixed_baseline_dispatch_stocks_routes_and_ledger'
        assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_fixed_dispatch.py')
        for file,key in [('results.json','results_sha256'),('fields.npz','fields_sha256')]:assert sha(OUT/'cases'/reading/file)==review[key]
        sources[str((OUT/'cases'/reading/'review.json').relative_to(ROOT))]=sha(OUT/'cases'/reading/'review.json')
        folders=[PARENT/'cases'/f'{reading}_loss05_days90',PARENT/'cases'/f'{reading}_loss00_days90',OUT/'cases'/reading]
        cases={label:dict(np.load(folder/'fields.npz')) for label,folder in zip(LABELS,folders)}
        results={label:read(folder/'results.json')['audit'] for label,folder in zip(LABELS,folders)}
        request=cases[LABELS[0]]['request'];nodes=a['nodes'];lat=a['lat'].ravel()[nodes];lon=a['grid_lon'].ravel()[nodes]
        egypt=(lon>=29)&(lon<=32.6)&(lat<=32)
        masks={'all':np.ones(len(request),bool),'west':a['lon']<=np.median(a['lon']),'east':a['lon']>np.median(a['lon']),
               'egypt_proper':egypt,'other':~egypt}
        meals={label:c['town_food__consumed']/KCAL for label,c in cases.items()}
        olddelta=meals['loss00_own']-meals['loss05_own'];newdelta=meals['loss00_fixed']-meals['loss05_own']
        quotadelta=meals['loss00_fixed']-meals['loss00_own'];oldloser=olddelta< -1e-7;newloser=newdelta< -1e-7
        np.testing.assert_array_equal(nodes[oldloser],[int(row['cell']) for row in previous_rows if row['reading']==reading])
        stats[reading]=dict(previous_losers=int(oldloser.sum()),remaining_previous_losers=int((oldloser&newloser).sum()),
            new_losers_vs_five_percent=int((~oldloser&newloser).sum()),all_losers_vs_five_percent=int(newloser.sum()),
            fixed_vs_own_gaining_cities=int((quotadelta>1e-7).sum()),fixed_vs_own_losing_cities=int((quotadelta< -1e-7).sum()),
            fixed_vs_own_meal_delta_person_years=total(quotadelta),fixed_vs_five_percent_meal_delta_person_years=total(newdelta),
            maximum_city_loss_vs_five_percent_pp=float((100*newdelta/request).min()),
            previous_loser_meals_change_vs_five_percent_person_years=total(newdelta[oldloser]))
        for key,value in dict(nodes=nodes,lat=lat,lon=lon,request=request,previous_loser=oldloser,new_loser=newloser).items():packet[reading+'_'+key]=value
        old=cases['loss00_own'];new=cases['loss00_fixed']
        for i,node in enumerate(nodes):
            channels=dict(delta_direct_arrivals_person_years=total(new['direct'][:,i]-old['direct'][:,i])/KCAL,
                delta_intertown_arrivals_person_years=total(new['inter_received'][:,i]-old['inter_received'][:,i])/KCAL,
                delta_intertown_exports_person_years=total(new['inter_exported'][:,i]-old['inter_exported'][:,i])/KCAL)
            for key,label in [('spoiled','delta_spoilage_person_years'),('overflow','delta_overflow_person_years'),('initial_stock','delta_initial_stock_person_years'),('final_stock','delta_final_stock_person_years')]:
                channels[label]=float((new['town_food__'+key][i]-old['town_food__'+key][i])/KCAL)
            prediction=channels['delta_direct_arrivals_person_years']+channels['delta_intertown_arrivals_person_years']-channels['delta_spoilage_person_years']-channels['delta_overflow_person_years']+channels['delta_initial_stock_person_years']-channels['delta_final_stock_person_years']
            tolerance=1e-10*max(1,old['town_food__harvested'][i],new['town_food__harvested'][i],new['town_food__needed'][i])/KCAL
            assert abs(prediction-quotadelta[i])<=tolerance
            row=dict(reading=reading,cell=int(node),lat=float(lat[i]),lon=float(lon[i]),requested_people=float(request[i]),
                own_zero_vs_five_meals_person_years=float(olddelta[i]),fixed_zero_vs_five_meals_person_years=float(newdelta[i]),
                fixed_vs_own_meals_person_years=float(quotadelta[i]),fixed_vs_own_percentage_points=float(100*quotadelta[i]/request[i]),
                previous_zero_loss_loser=bool(oldloser[i]),fixed_quota_zero_loss_loser=bool(newloser[i]),
                old_protected_exporter=bool(old['protected_exporters'][i]),new_protected_exporter=bool(new['protected_exporters'][i]),
                meal_delta_ledger_residual_person_years=float(quotadelta[i]-prediction),**channels)
            differences.append(row)
            if oldloser[i]:previous.append(row)
        for label,c in cases.items():
            audit=results[label];fully=c['town_food__unmet']<=1e-8*np.maximum(1,c['town_food__needed'])
            ledger=audit['ledger']
            summaries.append(dict(reading=reading,scenario=label,meal_fraction=audit['town_meal_fraction'],
                meals_person_years=total(meals[label]),delta_meals_vs_five_percent_person_years=total(meals[label]-meals['loss05_own']),
                delta_vs_five_percent_pp=100*total(meals[label]-meals['loss05_own'])/total(request),
                full_meal_city_cells=int(fully.sum()),rural_unmet_person_years=audit['rural_unmet_person_years'],
                departures_person_years=total(c['departures'])/KCAL,marketed_person_years=total(c['marketed'])/KCAL,
                commercial_overflow_person_years=total(c['export_food__overflow'])/KCAL,
                source_unused_person_years=ledger['source_unused_kcal']/KCAL,town_unused_person_years=ledger['town_unused_kcal']/KCAL,
                freight_loss_person_years=(ledger['source_freight_loss_kcal']+ledger['intertown_freight_loss_kcal'])/KCAL,
                source_cyclic_transit_person_years=total(c['direct'][0])/KCAL,intertown_cyclic_transit_person_years=total(c['inter_received'][0])/KCAL))
            for i,node in enumerate(nodes):
                towns.append(dict(reading=reading,scenario=label,cell=int(node),lat=float(lat[i]),lon=float(lon[i]),requested_people=float(request[i]),
                    meals_person_years=float(meals[label][i]),meal_fraction=float(meals[label][i]/request[i]),
                    delta_vs_five_percent_pp=float(100*(meals[label][i]-meals['loss05_own'][i])/request[i]),all_meals_within_tolerance=bool(fully[i])))
            for month in range(12):
                quantity=total(request)/12-total(c['town_food__unmet_path'][month])/KCAL
                baseline=total(request)/12-total(cases['loss05_own']['town_food__unmet_path'][month])/KCAL
                months.append(dict(reading=reading,scenario=label,month=month+1,meals_person_years=quantity,meal_fraction=quantity/(total(request)/12),
                    delta_meals_vs_five_percent_person_years=quantity-baseline,
                    direct_arrivals_person_years=total(c['direct'][month])/KCAL,intertown_arrivals_person_years=total(c['inter_received'][month])/KCAL,
                    departure_request_person_years=total(c['dispatch'][month])/KCAL,paid_departures_person_years=total(c['departures'][month])/KCAL))
            for name,mask in masks.items():
                regions.append(dict(reading=reading,scenario=label,region=name,requested_people=total(request[mask]),
                    meals_person_years=total(meals[label][mask]),meal_fraction=total(meals[label][mask])/total(request[mask]),
                    delta_meals_vs_five_percent_person_years=total((meals[label]-meals['loss05_own'])[mask])))
            for key,value in dict(consumed=c['town_food__consumed'],unmet=c['town_food__unmet_path'],fully_supported=fully).items():packet[reading+'_'+label+'_'+key]=value
        data[reading]=(a,cases,meals)
    for name,rows in [('towns.csv',towns),('differences.csv',differences),('previous_losers.csv',previous),('months.csv',months),('regions.csv',regions),('summary.csv',summaries)]:table(name,rows)
    np.savez_compressed(OUT/'town_model.npz',**packet)
    fig,axes=plt.subplots(2,3,figsize=(18,9),layout='constrained')
    for row,(reading,(a,cases,meals)) in enumerate(data.items()):
        nodes=a['nodes'];lon=a['grid_lon'].ravel();lat=a['lat'].ravel();request=cases['loss05_own']['request']
        for col,(label,title) in enumerate(zip(LABELS,TITLES)):
            ax=axes[row,col];ax.scatter(lon[a['land'].ravel()],lat[a['land'].ravel()],s=.7,c='#e6e9eb',rasterized=True)
            points=ax.scatter(lon[nodes],lat[nodes],c=100*meals[label]/request,s=12,cmap='viridis',vmin=0,vmax=100,rasterized=True)
            ax.set_title(f'{reading.capitalize()} • {title}\n{100*total(meals[label])/total(request):.4f}% of fixed city meals',fontsize=11)
            ax.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)',xlim=(lon[nodes].min()-2,lon[nodes].max()+2),ylim=(lat[nodes].min()-2,lat[nodes].max()+2))
            ax.set_aspect(1/np.cos(np.deg2rad(38)))
    bar=fig.colorbar(points,ax=axes,orientation='horizontal',fraction=.035,pad=.02);bar.set_label('Requested annual city meals supplied (%)')
    fig.suptitle('Isolating the dispatch-quota response to zero storage loss',fontsize=15)
    fig.supxlabel('All panels: commercial capacity 90 days of original marketed grain; original grain, dates, work, requests, shares and routes fixed. No occupancy change.',fontsize=10)
    fig.savefig(OUT/'meal_maps.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
    comparisons=[('loss00_own','Fixed quota minus own-scenario quota'),('loss05_own','Zero loss, fixed quota minus 5% loss')]
    limits={base:max(float(abs(100*(meals['loss00_fixed']-meals[base])/cases['loss05_own']['request']).max())
                     for a,cases,meals in data.values()) for base,title in comparisons}
    for row,(reading,(a,cases,meals)) in enumerate(data.items()):
        nodes=a['nodes'];lon=a['grid_lon'].ravel();lat=a['lat'].ravel();request=cases['loss05_own']['request']
        previous_loss=meals['loss00_own']-meals['loss05_own']< -1e-7
        for col,(base,title) in enumerate(comparisons):
            ax=axes[row,col];ax.scatter(lon[a['land'].ravel()],lat[a['land'].ravel()],s=.7,c='#e6e9eb',rasterized=True)
            values=100*(meals['loss00_fixed']-meals[base])/request;limit=limits[base]
            points=ax.scatter(lon[nodes],lat[nodes],c=values,s=14,cmap='RdBu',vmin=-limit,vmax=limit,rasterized=True)
            ax.scatter(lon[nodes[previous_loss]],lat[nodes[previous_loss]],s=34,facecolors='none',edgecolors='#222222',linewidths=.8)
            ax.set_title(f'{reading.capitalize()} • {title}',fontsize=11)
            ax.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)',xlim=(lon[nodes].min()-2,lon[nodes].max()+2),ylim=(lat[nodes].min()-2,lat[nodes].max()+2))
            ax.set_aspect(1/np.cos(np.deg2rad(38)))
            bar=fig.colorbar(points,ax=ax,orientation='horizontal',fraction=.04,pad=.04);bar.set_label('Change in supplied meals (percentage points)')
    fig.suptitle('Quota-control meal differences • rings mark the previous 19 losing city cells',fontsize=14)
    fig.savefig(OUT/'quota_effect_maps.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for ax,reading in zip(axes,['central','low']):
        for label,title in zip(LABELS,TITLES):
            rows=[row for row in months if row['reading']==reading and row['scenario']==label]
            ax.plot(range(1,13),[100*row['meal_fraction'] for row in rows],label=title,marker='.')
        ax.set(title=reading.capitalize(),xlabel='Month',ylabel='City meals supplied (%)',xticks=range(1,13),ylim=(0,101));ax.grid(alpha=.2)
    axes[1].legend(fontsize=8);fig.savefig(OUT/'monthly_meals.png',dpi=160);plt.close(fig)
    write(OUT/'results.json',dict(status='reviewed_two_fixed_dispatch_cases_with_four_exact_controls',sources_sha256=sources,
        summary=summaries,city_effects=stats,counts=dict(new_cases=2,exact_controls=4,food_arrays_per_control=70,
        city_rows=len(towns),difference_rows=len(differences),previous_loser_rows=len(previous),month_rows=len(months),region_rows=len(regions)),
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False))
    print(stats,flush=True)


if __name__=='__main__':main()
