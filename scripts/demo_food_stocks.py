"""Manufactured seasonal-food example; no world prediction or atlas adoption."""
from pathlib import Path
from dataclasses import asdict
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from harvest.food_stocks import periodic_food_year,minimum_zero_loss_capacity
    need=np.ones(365)
    supplies={'One harvest':np.zeros(365),'Two equal harvests':np.zeros(365),'Even daily supply (control)':np.ones(365)}
    supplies['One harvest'][182]=365
    supplies['Two equal harvests'][[90,273]]=182.5
    capacity=200.;results={};required={};arrays={}
    fig,axes=plt.subplots(1,2,figsize=(13,4.6),layout='constrained')
    colors=['#a94b38','#35865d','#3275a4']
    for color,(name,harvest) in zip(colors,supplies.items()):
        result=periodic_food_year(harvest,need,capacity,record=True)
        assert result.harvested==result.needed==365 and result.periodic_converged
        required[name]=float(minimum_zero_loss_capacity(harvest,need))
        results[name]={key:np.asarray(value).item() for key,value in asdict(result).items() if key not in ['stock_path','unmet_path']}
        arrays[name.replace(' ','_')+'_stocks']=result.stock_path
        arrays[name.replace(' ','_')+'_unmet']=result.unmet_path
        axes[0].plot(range(366),result.stock_path,color=color,lw=2,
            label=name+f' · {int(round(float(result.shortfall_days)))} shortage days')
    axes[0].set(xlabel='Day of the supplied year',ylabel='Stored food, days of the specified demand',ylim=(0,215),xlim=(0,365))
    axes[0].axhline(capacity,color='#555',ls='--',lw=1,label='Assumed storage capacity')
    axes[0].legend(frameon=False,fontsize=8)
    bars=axes[1].bar(range(3),list(required.values()),color=colors,width=.6)
    axes[1].set(xticks=range(3),xticklabels=['One harvest','Two harvests','Daily control'],
        ylabel='Minimum no-loss storage, days of specified demand',ylim=(0,420))
    axes[1].axhline(capacity,color='#555',ls='--',lw=1)
    for bar,value in zip(bars,required.values()):axes[1].text(bar.get_x()+bar.get_width()/2,value+8,f'{value:g}',ha='center')
    for ax in axes:ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('The same annual food can produce very different hungry seasons\nManufactured schedules · identical harvest and demand totals · zero spoilage · repeating inventory',fontsize=13)
    out=ROOT/'output/food_stock_prototype_20261103';out.mkdir(exist_ok=True)
    image=out/'seasonal_storage_demo.png';fig.savefig(image,dpi=135);plt.close(fig)
    path=out/'seasonal_storage_demo.npz';np.savez_compressed(path,**arrays)
    write_json(out/'receipt.json',dict(status='numerical_prototype',production_atlas_changed=False,
        crop_or_storage_coefficients_fitted=False,annual_harvest_energy=365,annual_food_need_energy=365,
        daily_food_need_energy=1,storage_capacity_energy=capacity,loss_fraction_year=0,
        results=results,minimum_zero_loss_capacity=required,figure_sha256=file_hash(image),arrays_sha256=file_hash(path),
        sources_sha256={name:file_hash(ROOT/name) for name in ['harvest/food_stocks.py','scripts/demo_food_stocks.py']},
        scope='Manufactured energy schedules only, not ancient crop yields, harvest calendars, famine probabilities, population estimates or added FORGE storage. Energy units may be MJ/km2; days-of-demand divide stock by the specified daily demand. Periodic inventory is distinct from meeting food needs.'))
    print(json.dumps(dict(minimum_storage=required,shortfall_days={n:r['shortfall_days'] for n,r in results.items()}),indent=2))


if __name__=='__main__':main()
