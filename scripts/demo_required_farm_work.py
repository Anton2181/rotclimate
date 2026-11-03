"""Minimum listed field work for a declared, uncalibrated net-food target."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from harvest.labour import FarmOperation,minimum_farm_work,plan_farm,InfeasibleFarmPlan
    from local_benchmark_protocol import file_hash,write_json
    source_path=ROOT/'research_notes/farm_labour_20261103.json';source=json.loads(source_path.read_text())
    scenario=source['scenario'];T=scenario['year_days']//scenario['step_days']
    # Deliberately supplied normalized food outputs, NOT historical yields.
    crops=['wheat','barley'];food=np.array([100.,80.]);target=300.
    availability=np.full((T,1),scenario['available_human_hours_per_step'])
    def operations(wide):
        tasks=[]
        for a,crop in enumerate(crops):
            for name,days in source['workdays_per_iugerum'][crop].items():
                first,last=scenario['operation_steps'][name]
                if name=='reap' and wide:last=56
                window=(np.arange(T)>=first)&(np.arange(T)<last)
                tasks.append(FarmOperation(crop+': '+name,a,window,[days*scenario['hours_per_workday']/scenario['iugerum_hectares']]))
        return tasks
    cases={}
    specs=[('Ample land',4.,True),('Tighter land',3.5,True),('Minimum sufficient land',3.,True),
        ('Insufficient land',2.9,True),('Narrow harvest window',4.,False)]
    for label,land,wide in specs:
        tasks=operations(wide)
        ceiling=plan_farm(food,tasks,land_hectares=land,available_hours=availability)
        try:
            p=minimum_farm_work(food,tasks,required_output=target,land_hectares=land,available_hours=availability)
        except InfeasibleFarmPlan:
            cases[label]=dict(status='infeasible',available_land=land,harvest_window_days=30 if wide else 10,
                required_food_units=target,maximum_food_units=ceiling.output,minimum_listed_work_hours=None,
                hectares=None,shortfall_at_maximum_output=target-ceiling.output)
            continue
        cases[label]=dict(status='feasible',available_land=land,harvest_window_days=30 if wide else 10,
            required_food_units=target,maximum_food_units=ceiling.output,produced_food_units=p.output,
            minimum_listed_work_hours=float(p.resource_hours_used.sum()),hectares=dict(zip(crops,p.hectares.tolist())),
            unused_farm_allocation_hours=float(p.unused_resource_hours.sum()),
            local_target_work_marginal=p.required_output_work_marginal,
            task_residual_max=float(np.max(np.abs(p.task_residual))),
            work_budget_overrun=float(np.max(p.resource_hours_used-availability)),
            operations=[dict(name=op.name,activity=op.activity,allowed_steps=np.flatnonzero(op.allowed).tolist(),
                hours_per_hectare=op.hours_per_hectare,completed_hectares=p.completed_hectares[:,i].tolist()) for i,op in enumerate(tasks)])
    expected={'Ample land':(780.,[0.,3.75]),'Tighter land':(856.,[1.,2.5]),'Minimum sufficient land':(1008.,[3.,0.])}
    for label,(hours,areas) in expected.items():
        if not np.isclose(cases[label]['minimum_listed_work_hours'],hours) or not np.allclose(list(cases[label]['hectares'].values()),areas):
            raise ValueError('Analytical land/work tradeoff failed')
    if not np.isclose(cases['Insufficient land']['maximum_food_units'],290.) or not np.isclose(cases['Narrow harvest window']['maximum_food_units'],200.):
        raise ValueError('Analytical infeasibility ceiling failed')
    fig,(areas,work)=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
    labels=list(cases);x=np.arange(len(labels));wheat=[];barley=[]
    for r in cases.values():
        wheat.append(np.nan if r['hectares'] is None else r['hectares']['wheat'])
        barley.append(np.nan if r['hectares'] is None else r['hectares']['barley'])
    areas.bar(x,wheat,label='Wheat',color='#c4a353');areas.bar(x,barley,bottom=wheat,label='Barley',color='#438b76')
    areas.set(ylabel='Selected crop area, ha',ylim=(0,4.3),title='Meet the same target with different land budgets');areas.legend()
    for i,(label,r) in enumerate(cases.items()):
        if r['status']=='feasible':
            b=work.bar([i],[r['minimum_listed_work_hours']],color='#315d83');work.bar_label(b,fmt='%.0f h',padding=4)
        else:
            for ax in [areas,work]:ax.text(i,.1 if ax==areas else 35,'Infeasible',color='#a3342a',ha='center',rotation=90)
    work.set(ylabel='Minimum listed field-task human hours',ylim=(0,1180),title='Land scarcity can increase required field work')
    for ax in [areas,work]:
        ax.set_xticks(x,labels,rotation=25,ha='right',fontsize=8);ax.set_xlim(-.65,len(labels)-.35);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Declared annual food target: 300 arbitrary units · supplied outputs: wheat100 /barley80 per ha\nColumella field-task counts; manufactured availability and windows; no total subsistence-work prediction',fontsize=11)
    folder=ROOT/'output/farm_work_targets_20261103';folder.mkdir(exist_ok=True)
    image=folder/'required_field_work.png';fig.savefig(image,dpi=140);plt.close(fig)
    write_json(folder/'review.json',dict(status='conditional_required_field_work_prototype',production_atlas_changed=False,
        historical_food_yields_estimated=False,total_subsistence_work_estimated=False,
        required_food_units=target,assumed_food_per_hectare=dict(zip(crops,food.tolist())),available_annual_farm_hours=float(availability.sum()),
        cases=cases,source_manifest_sha256=file_hash(source_path),figure_sha256=file_hash(image),
        sources_sha256={p:file_hash(ROOT/p) for p in ['harvest/labour.py','scripts/demo_required_farm_work.py']},
        scope='Prescribed net-food coefficients in arbitrary common units; neither yields nor the requirement is estimated from ancient evidence. Listed field work only, assumes draft services; no threshing/processing/care/storage/household budget. Minimum-work LP selects complete annual crop activities with seasonal deadlines; unavailable workload is null, not zero. Annual net-output target only; seasonal consumption and food stocks are not integrated. This is not an inequality, famine-frequency, leisure or population prediction.'))
    print(json.dumps({k:{field:r[field] for field in ['status','maximum_food_units','minimum_listed_work_hours','hectares']} for k,r in cases.items()},indent=2))


if __name__=='__main__':main()
