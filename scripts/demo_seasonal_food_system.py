"""Manufactured water -> crop harvest -> storage -> town provisioning example."""
from pathlib import Path
from dataclasses import asdict
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from harvest.upland_food import UplandSeason,upland_food_year
    from harvest.soil_water import available_water,soil_water_year
    from polity.food_transport import FoodRoute,provision_food
    from scripts.land_people import CROPS
    from local_benchmark_protocol import file_hash,write_json
    day=np.arange(365);rain=np.where(day<100,4.,1.5)
    et0=3.5+np.sin(2*np.pi*(day-80)/365)
    # One accounting hectare, inherited potential net edible crop energies;
    # energy unit is 10,000kcal. Consumption and capacities are supplied
    # illustrative budgets, not population or ancient granary estimates.
    seasons=[]
    for name,start,duration in [('wheat',10,122),('millet',165,100)]:
        c=CROPS[name]
        energy=c['grain']*1000*c['edible']*c['kcal']*(1-c['seed'])/10000
        seasons.append(UplandSeason(name,start,duration,energy,c['kc'],c['ky'],.55))
    active=np.zeros(365,bool)
    for s in seasons:active[(s.start+np.arange(s.duration))%365]=True
    fields={};cases={};arrays={}
    for water in [0.,1.]:
        fields[water]=upland_food_year(rain,et0,seasons,total_available=100,fallow_coefficient=.15,
            fallow_depletion_fraction=.55,minimum_et_ratio=.5,
            irrigation_request=np.where(active,5.,0.),irrigation_supply=np.where(active,water,0.))
    scenarios=[('Rainfed, small stores',0.,120.,5.,False),
               ('Rainfed, larger stores',0.,240.,30.,False),
               ('Finite irrigation',1.,240.,30.,False),
               ('Finite water, seasonal route closure',1.,240.,30.,True),
               ('Ample farm storage',1.,365.,30.,False),
               ('Ample storage, seasonal closure',1.,365.,30.,True)]
    for name,water,farmcap,towncap,closed in scenarios:
        field=fields[water]
        supply=np.zeros((73,2));supply[:,0]=field.harvest.reshape(73,5).sum(1)
        need=np.broadcast_to([5.,2.],(73,2)).copy()
        capacity=np.full(73,4.);capacity[:26]=0. if closed else 4.
        route=FoodRoute(0,1,1,capacity,1.,1.)
        food=provision_food(supply,need,[route],storage_capacity=[farmcap,towncap],priority=[0,1])
        cases[name]=dict(net_harvest=float(supply.sum()),rural_consumed=float(food.consumed[:,0].sum()),
            rural_need=365.,town_consumed=float(food.consumed[:,1].sum()),town_need=146.,
            spilled=float(food.spilled.sum()),storage_loss=food.storage_loss,transport_loss=food.transport_loss,
            food_ledger_residual=food.annual_ledger_residual,water_ledger_residual=float(field.water.ledger_residual),
            water_periodic_residual=float(field.water.periodic_residual),irrigation_applied_mm=float(field.water.irrigation_applied),
            irrigation_unmet_mm=float(field.water.irrigation_unmet),seasons=field.seasons,
            assumed_farm_store=farmcap,assumed_town_store=towncap,seasonal_closure=closed)
        arrays[name]=food
    # Independent published-water benchmark included in the receipt.
    taw=available_water(.32,.12,.8)
    benchmark=soil_water_year(np.zeros(10),np.full(10,5.),1.2,total_available=taw,
        depletion_fraction=.4,initial_stored=taw-55,record=True)
    reference=np.array([61,67,72.8,78.3,83.4,88.2,92.6,96.9,100.8,104.5])
    out=ROOT/'output/seasonal_food_system_20261103';out.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(16,4.9),layout='constrained')
    for water,color,label in [(0.,'#b68346','Rainfed'),(1.,'#347d75','Finite irrigation')]:
        axes[0].plot(np.arange(366),100-fields[water].water.depletion_path,color=color,label=label)
    axes[0].set(xlabel='Day of supplied year',ylabel='Available root-zone water (mm)',ylim=(0,105))
    axes[0].legend(frameon=False,fontsize=8)
    labels=['Small\nstores','Larger\nstores','Finite\nirrigation','Route\nclosure','Ample\nfarm store','Ample +\nclosure']
    axes[1].bar(range(6),[cases[n]['town_consumed']/146*100 for n in arrays],color=['#bca87c','#b68346','#347d75','#507d9a','#347d75','#507d9a'])
    axes[1].set(xticks=range(6),xticklabels=labels,ylabel='Specified town food need met (%)',ylim=(0,105))
    axes[1].tick_params(axis='x',labelsize=8)
    for name,color in [(scenarios[4][0],'#347d75'),(scenarios[5][0],'#507d9a')]:
        axes[2].plot(np.arange(73)*5,arrays[name].stocks[:,1],color=color,label=name)
    axes[2].set(xlabel='Day of supplied year',ylabel='Town grain stock (food units)')
    axes[2].axvspan(0,130,color='#ccc',alpha=.25,label='Assumed departure closure')
    axes[2].legend(frameon=False,fontsize=7)
    for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2)
    fig.suptitle('From field water to harvest, stored food and town supply\nManufactured example · prescribed seasons and needs · rural consumption prioritized · no predicted town population',fontsize=12)
    image=out/'seasonal_food_system.png';fig.savefig(image,dpi=135);plt.close(fig)
    receipt=dict(status='manufactured_integrated_scenario',production_atlas_changed=False,population_predicted=False,
        energy_unit_kcal=10000.,cases=cases,
        fao56_example37_max_depletion_error_mm=float(np.max(np.abs(benchmark.depletion_path[1:]-reference))),
        assumptions=dict(rain_mm=797.5,reference_et='3.5+sin(2pi(day-80)/365) mm/day',
            prescribed_seasons=[asdict(s) for s in seasons],fixed_root_zone_available_mm=100.,fallow_coefficient=.15,
            severe_deficit_guard=.5,root_depletion_fraction=.55,inventory_steps=73,inventory_step_days=5,
            irrigation_net_supply_mm_day=[0,1],route_delay_steps=1,route_capacity_food_units_step=4,
            closure_steps=26,storage_survival=1.,route_retention=1.,priorities=[0,1]),
        sources_sha256={name:file_hash(ROOT/name) for name in ['harvest/soil_water.py','harvest/upland_food.py',
            'polity/food_transport.py','scripts/demo_seasonal_food_system.py','scripts/land_people.py']},
        figure_sha256=file_hash(image),scope='Conditional supplied upland seasons; no calendar search, frost survival or ancient cultivar validation. No half-weight secondary crop or repeated seed deduction. Water and food ledgers close separately. Finite field irrigation is an input, not routed river water. Scenario route costs/delays/capacities and granaries are assumed; current gravity weights are not grain quantities. No rice/perennial process or town-size prediction.')
    write_json(out/'receipt.json',receipt)
    print(json.dumps(cases,indent=2))


if __name__=='__main__':main()
