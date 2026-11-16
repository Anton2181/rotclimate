"""Reviewed fixed-share annual work comparison: tables and diagnostic maps."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_component_work_20261116'
PRIOR=ROOT/'output/urban_seasonal_transfer_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    scenarios=[];town_rows=[];regions=[];inputs={};images={}
    for hours in [600,300]:
        folder=OUT/f'hours{hours}';result=read(folder/'results.json');review=read(folder/'review.json')
        assert review['status']=='passed_shared_component_work_and_fixed_share_supply_review'
        assert review['results_sha256']==sha(folder/'results.json')
        for name,digest in result['files_sha256'].items():assert sha(folder/name)==digest,name
        inputs[str((folder/'review.json').relative_to(ROOT))]=sha(folder/'review.json')
        towns=dict(np.load(folder/'town_model.npz'))
        fig,axes=plt.subplots(1,2,figsize=(14,6),layout='constrained')
        max_loss=0.;prepared={}
        for reading in ['central','low']:
            a=dict(np.load(PRIOR/'wind_1981/prepared'/f'low_{reading}.npz'));prepared[reading]=a
            delta=100*(towns[reading+'_B_fed']-towns[reading+'_A_fed'])/towns[reading+'_request']
            max_loss=max(max_loss,float(abs(delta).max()))
        maximum=max_loss*1.02
        for ax,reading in zip(axes,['central','low']):
            a=prepared[reading];request=towns[reading+'_request'];nodes=towns[reading+'_nodes']
            before=towns[reading+'_A_fed'];after=towns[reading+'_B_fed'];delta=100*(after-before)/request
            lat=a['lat'].ravel();lon=a['grid_lon'].ravel();land=a['land'].ravel()
            ax.scatter(lon[land],lat[land],s=1,c='#e8eaeb',rasterized=True)
            ax.scatter(lon[nodes],lat[nodes],s=10,c='#aeb4b7',rasterized=True)
            changed=abs(after-before)>1e-7
            points=ax.scatter(lon[nodes[changed]],lat[nodes[changed]],c=delta[changed],s=42,
                cmap='RdBu',vmin=-maximum,vmax=maximum,edgecolors='#3a3d40',linewidths=.35)
            ax.set(xlabel='Longitude (°E)',ylabel='Latitude (°N)',title=f'{reading.capitalize()} density • {changed.sum()} city cells change')
            ax.set_xlim(lon[nodes].min()-2,lon[nodes].max()+2);ax.set_ylim(lat[nodes].min()-2,lat[nodes].max()+2)
            ax.set_aspect(1/np.cos(np.deg2rad(38)))
            ax.text(.02,.02,f'Support change: {after.sum()-before.sum():,.0f} people',transform=ax.transAxes,
                    bbox={'facecolor':'white','edgecolor':'none','alpha':.9},fontsize=10)
            for i,node in enumerate(nodes):
                town_rows.append(dict(hours=hours,reading=reading,cell=int(node),lat=float(lat[node]),lon=float(lon[node]),
                    requested_people=float(request[i]),A_fed_people=float(before[i]),B_fed_people=float(after[i]),
                    delta_fed_people=float(after[i]-before[i]),delta_fed_percentage_points=float(delta[i])))
            summary=result['cases'][reading];A,B=summary['A'],summary['B']
            scenarios.append(dict(hours=hours,reading=reading,marketed_share=summary['marketed_share'],
                A_grown_person_years=A['grown_person_years'],B_grown_person_years=B['grown_person_years'],
                A_rural_deficit_person_years=A['rural_deficit_person_years'],B_rural_deficit_person_years=B['rural_deficit_person_years'],
                A_fed_share=A['fed_by_region']['all']['fed_share'],B_fed_share=B['fed_by_region']['all']['fed_share'],
                A_egypt_fed_share=A['fed_by_region']['egypt_proper']['fed_share'],B_egypt_fed_share=B['fed_by_region']['egypt_proper']['fed_share'],
                delta_city_support_people=float(after.sum()-before.sum()),changed_city_cells=int(changed.sum()),
                B_peak_limited_sources=summary['peak_limited_B_cells']))
            for model,values in [('A',A),('B',B)]:
                for name,value in values['fed_by_region'].items():
                    regions.append(dict(hours=hours,reading=reading,model=model,region=name,**value))
        fig.suptitle(f'{hours} field hours per worker • annual city grain support, physical component work B minus original A',fontsize=13)
        colorbar=fig.colorbar(points,ax=axes,orientation='horizontal',fraction=.05,pad=.02)
        colorbar.set_label('Change in city request supported (percentage points); gray locations have no material change')
        fig.supxlabel('Fixed original requests, marketed shares and270road-km haul limit. Annual grain allocation only; no seasonal stores or new settlement populations.',fontsize=9)
        target=OUT/f'city_support_{hours}.png';fig.savefig(target,dpi=160);plt.close(fig);images[target.name]=sha(target)
    table(OUT/'scenarios.csv',scenarios);table(OUT/'towns.csv',town_rows);table(OUT/'regions.csv',regions)
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained');x=np.arange(len(scenarios))
    for ax,one,two,title in [(axes[0],'A_fed_share','B_fed_share','All city requests'),(axes[1],'A_egypt_fed_share','B_egypt_fed_share','Egypt proper city requests')]:
        A=100*np.array([s[one] for s in scenarios]);B=100*np.array([s[two] for s in scenarios])
        ax.bar(x-.18,A,.36,color='#547e99',label='A: original blended work')
        ax.bar(x+.18,B,.36,color='#c48848',label='B: physical component work')
        ax.set(xticks=x,xticklabels=[f'{s["hours"]}h\n{s["reading"]}' for s in scenarios],ylim=(0,106),ylabel='Annual request supported (%)',title=title)
        for i in x:ax.text(i,max(A[i],B[i])+1.5,f'{B[i]-A[i]:+.3f} pp',ha='center',fontsize=9)
        ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    axes[0].legend(frameon=False,loc='lower left');fig.suptitle('Shared physical workforce comparison at unchanged policy settings',fontsize=14)
    fig.supxlabel('Partial listed cereal tasks. Requests remain fixed; percentages describe annual grain support,not observed occupancy.',fontsize=9)
    target=OUT/'comparison.png';fig.savefig(target,dpi=160);plt.close(fig);images[target.name]=sha(target)
    receipt=dict(status='rendered_reviewed_paired_annual_work_comparison',producer_sha256=sha(Path(__file__)),
        inputs_sha256=inputs,image_sha256=images,files_sha256={name:sha(OUT/name) for name in ['scenarios.csv','towns.csv','regions.csv']},
        scenarios=4,town_rows=len(town_rows),regional_rows=len(regions),new_settlement_map=False,seasonal_food_trial=False,adopt=False)
    (OUT/'presentation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'],flush=True)


if __name__=='__main__':main()
