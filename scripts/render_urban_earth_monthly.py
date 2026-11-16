"""Reviewed fixed-request Earth monthly meal maps and accounting tables."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_earth_monthly_20261116'
BASE=ROOT/'output/urban_component_work_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116'
KCAL=912500.


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    data={};inputs={};maximum=0.;town_rows=[];monthly_rows=[];regional_rows=[];summary=[];compact={}
    for reading in ['central','low']:
        folder=OUT/'cases'/reading;r=read(folder/'results.json');review=read(folder/'review.json')
        assert review['status']=='passed_fixed_request_monthly_inventories_routes_and_grain_ledger'
        assert review['results_sha256']==sha(folder/'results.json') and review['fields_sha256']==sha(folder/'fields.npz')
        inputs[str((folder/'review.json').relative_to(ROOT))]=sha(folder/'review.json')
        c=dict(np.load(folder/'fields.npz'));a=dict(np.load(ANNUAL/'wind_1981/prepared'/f'low_{reading}.npz'))
        b=dict(np.load(BASE/'hours600/cases'/f'{reading}.npz'))
        request=c['request'];meals=c['town_food__consumed']/KCAL;delta=100*(meals-b['B_fed'])/request
        maximum=max(maximum,float(abs(delta).max()));data[reading]=(r,c,a,b)
        nodes=a['nodes'];lat=a['lat'].ravel()[nodes];lon=a['grid_lon'].ravel()[nodes]
        fully=c['town_food__unmet']<=1e-8*np.maximum(1,c['town_food__needed'])
        for i,node in enumerate(nodes):
            town_rows.append(dict(reading=reading,cell=int(node),lat=float(lat[i]),lon=float(lon[i]),requested_people=float(request[i]),
                annual_B_fed_people=float(b['B_fed'][i]),monthly_meals_person_years=float(meals[i]),
                monthly_meal_fraction=float(meals[i]/request[i]),monthly_unmet_person_years=float(c['town_food__unmet'][i]/KCAL),
                change_from_annual_percentage_points=float(delta[i]),all_fixed_meals_within_tolerance=bool(fully[i])))
        for month in range(12):
            needed=float(request.sum()*KCAL/12);unmet=float(c['town_food__unmet_path'][month].sum())
            monthly_rows.append(dict(reading=reading,month=month+1,meal_fraction=1-unmet/needed,
                unmet_person_years=unmet/KCAL,grain_arrivals_person_years=float(c['arrivals'][month].sum()/KCAL)))
        for name,values in r['regions'].items():
            regional_rows.append(dict(reading=reading,region=name,annual_B_fraction=values['annual_B_fed_people']/values['requested_people'],**values))
        summary.append(dict(reading=reading,annual_B_fed_fraction=r['annual_B_fed_share'],
            monthly_meal_fraction=r['monthly_audit']['town_meal_fraction'],
            annual_B_rural_deficit_person_years=read(BASE/'hours600/results.json')['cases'][reading]['B']['rural_deficit_person_years'],
            monthly_rural_deficit_person_years=r['monthly_audit']['rural_unmet_person_years'],
            monthly_city_unmet_person_years=r['monthly_audit']['town_unmet_person_years'],
            annual_B_fully_supported_city_cells=int((b['B_fed']>=request*(1-1e-8)).sum()),
            monthly_fully_supported_city_cells=int(fully.sum())))
        for key,value in dict(nodes=nodes,request=request,annual_B_fed=b['B_fed'],monthly_consumed=c['town_food__consumed'],
            monthly_unmet=c['town_food__unmet_path'],monthly_meal_fraction=meals/request,fully_supported=fully).items():
            compact[reading+'_'+key]=value
    table(OUT/'towns.csv',town_rows);table(OUT/'months.csv',monthly_rows);table(OUT/'regions.csv',regional_rows);table(OUT/'summary.csv',summary)
    np.savez_compressed(OUT/'town_model.npz',**compact)
    fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
    for column,reading in enumerate(['central','low']):
        r,c,a,b=data[reading];nodes=a['nodes'];lat=a['lat'].ravel();lon=a['grid_lon'].ravel();land=a['land'].ravel()
        meal=100*c['town_food__consumed']/(c['request']*KCAL)
        difference=meal-100*b['B_fed']/c['request']
        for row in range(2):
            ax=axes[row,column];ax.scatter(lon[land],lat[land],s=.8,c='#e6e9eb',rasterized=True)
            if row==0:
                points=ax.scatter(lon[nodes],lat[nodes],c=meal,s=14,cmap='viridis',vmin=0,vmax=100,rasterized=True)
                level_artist=points
                ax.set_title(f'{reading.capitalize()} • {r["monthly_audit"]["town_meal_fraction"]*100:.2f}% of requested meals',fontsize=12)
            else:
                ax.scatter(lon[nodes],lat[nodes],s=9,c='#b6bbbf',rasterized=True)
                changed=abs(c['town_food__consumed']/KCAL-b['B_fed'])>1e-7
                points=ax.scatter(lon[nodes[changed]],lat[nodes[changed]],c=difference[changed],s=25,
                    cmap='RdBu',vmin=-maximum,vmax=maximum,edgecolors='#41454a',linewidths=.25)
                difference_artist=points;ax.set_title(f'{reading.capitalize()} • monthly meals minus annual B',fontsize=12)
            ax.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)')
            ax.set_xlim(lon[nodes].min()-2,lon[nodes].max()+2);ax.set_ylim(lat[nodes].min()-2,lat[nodes].max()+2)
            ax.set_aspect(1/np.cos(np.deg2rad(38)))
    bar=fig.colorbar(level_artist,ax=axes[0,:],orientation='horizontal',fraction=.04,pad=.01)
    bar.set_label('Fixed yearly city meals supplied (%)')
    bar=fig.colorbar(difference_artist,ax=axes[1,:],orientation='horizontal',fraction=.04,pad=.01)
    bar.set_label('Change from annual B benchmark (percentage points); gray = no material change')
    fig.suptitle('Earth monthly cereal-food pilot • fixed city requests and physical component work,600h',fontsize=14)
    fig.supxlabel('Model calendars,protected365d source/90d town stores,5%stock loss and one-bin freight delays. No demographic iteration or new occupancy forecast.',fontsize=9)
    fig.savefig(OUT/'meal_maps.png',dpi=160);plt.close(fig)
    fig,(left,right)=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    months=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    for reading,color in [('central','#3d7897'),('low','#be8242')]:
        r,_,_,_=data[reading];values=[row['meal_fraction']*100 for row in monthly_rows if row['reading']==reading]
        left.plot(np.arange(12),values,'o-',color=color,label=f'{reading}: monthly meals')
        left.axhline(100*r['annual_B_fed_share'],linestyle='--',color=color,alpha=.65,label=f'{reading}: annual B aggregate')
    left.set(xticks=np.arange(12),xticklabels=months,ylim=(80,100),ylabel='Requested city meals supplied (%)',title='Monthly meals and annual aggregate benchmarks')
    left.grid(alpha=.2);left.legend(frameon=False,fontsize=8,loc='lower right')
    bottom=np.zeros(2)
    categories=[('Rural meals',['rural_meals_kcal'],'#748b66'),('City meals',['town_meals_kcal'],'#3d7897'),
        ('Stock spoilage',['rural_spoiled_kcal','export_spoiled_kcal','town_spoiled_kcal'],'#b18c50'),
        ('Freight loss',['source_freight_loss_kcal','intertown_freight_loss_kcal'],'#aa6662'),
        ('Unused/unmarketed',['source_unused_kcal','town_unused_kcal'],'#c4c8cb')]
    for label,keys,color in categories:
        values=np.array([sum(data[reading][0]['monthly_audit']['ledger'][key] for key in keys)/KCAL/1e6 for reading in ['central','low']])
        right.bar([0,1],values,bottom=bottom,color=color,label=label);bottom+=values
    right.set(xticks=[0,1],xticklabels=['Central','Low'],ylabel='Grain calories (million person-years)',title='The physical annual grain ledger')
    right.legend(frameon=False,fontsize=8,loc='center left',bbox_to_anchor=(1, .5))
    fig.suptitle('Same production and requests; monthly food/storage/dispatch assumptions made explicit',fontsize=13)
    fig.supxlabel('Dashed lines are annual totals,not monthly forecasts. Unused includes unmarketed grain and overflow. Grain accounts do not determine actual population.',fontsize=9)
    fig.savefig(OUT/'monthly_accounting.png',dpi=160);plt.close(fig)
    files=['towns.csv','months.csv','regions.csv','summary.csv','town_model.npz','meal_maps.png','monthly_accounting.png']
    receipt=dict(status='rendered_reviewed_fixed_request_monthly_meals',producer_sha256=sha(Path(__file__)),
        inputs_sha256=inputs,files_sha256={name:sha(OUT/name) for name in files},city_rows=len(town_rows),
        monthly_rows=len(monthly_rows),regional_rows=len(regional_rows),actual_population_changed=False,new_validation_claim=False,adopt=False)
    (OUT/'presentation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'],flush=True)


if __name__=='__main__':main()
