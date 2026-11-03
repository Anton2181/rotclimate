"""Source-backed work counts; manufactured operation-window scenarios."""
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
    from harvest.labour import FarmOperation,plan_farm
    from local_benchmark_protocol import file_hash,write_json
    manifest=ROOT/'research_notes/farm_labour_20261103.json';source=json.loads(manifest.read_text())
    for name,expected in source['cached_sources_sha256'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Cached primary source changed: '+name)
    for crop,tasks in source['workdays_per_iugerum'].items():
        if sum(tasks.values())!=source['published_totals_workdays_per_iugerum'][crop]:
            raise ValueError('Transcribed tasks do not match published total')
    scenario=source['scenario'];T=scenario['year_days']//scenario['step_days']
    hours=np.full((T,1),scenario['available_human_hours_per_step'])
    shifted=hours.copy();shifted[50:52]+=80;shifted[56:72]-=10
    if hours.sum()!=shifted.sum():raise ValueError('Matched annual labour budget changed')
    maximum=scenario['maximum_workers']*scenario['max_hours_per_worker_day']*scenario['step_days']
    if max(hours.max(),shifted.max())>maximum:raise ValueError('Prescribed staffing exceeds worker envelope')
    def tasks(crop,*,annual=False,wide=False,half_prep=False):
        operations=[]
        for name,days in source['workdays_per_iugerum'][crop].items():
            first,last=scenario['operation_steps'][name]
            if name=='reap' and wide:last=56
            allowed=np.ones(T,bool) if annual else (np.arange(T)>=first)&(np.arange(T)<last)
            work=days*scenario['hours_per_workday']/scenario['iugerum_hectares']
            if name=='plough' and half_prep:work*=.5
            operations.append(FarmOperation(name,0,allowed,[work]))
        return operations
    specs=[('Annual aggregation control','wheat',tasks('wheat',annual=True),hours,4.),
        ('10-day reaping window','wheat',tasks('wheat'),hours,4.),
        ('30-day reaping window','wheat',tasks('wheat',wide=True),hours,4.),
        ('Same annual budget, harvest staffing','wheat',tasks('wheat'),shifted,4.),
        ('Half preparation work only','wheat',tasks('wheat',half_prep=True),hours,4.),
        ('Twice the available land','wheat',tasks('wheat'),hours,8.),
        ('Barley, 10-day reaping window','barley',tasks('barley'),hours,4.)]
    records={};plans=[]
    for label,crop,operations,available,land in specs:
        # Output 1 per ha means maximize completed cultivated area, not food.
        plan=plan_farm([1.],operations,land_hectares=land,available_hours=available)
        plans.append(plan)
        records[label]=dict(crop=crop,feasible_area_hectares=plan.land_used,available_land_hectares=land,
            available_annual_work_hours=float(available.sum()),used_work_hours=float(plan.resource_hours_used.sum()),
            work_hours_per_hectare=sum(float(op.hours_per_hectare[0]) for op in operations),
            available_work_hours=available[:,0].tolist(),used_work_hours_by_step=plan.resource_hours_used[:,0].tolist(),
            operations=[dict(name=op.name,allowed_steps=np.flatnonzero(op.allowed).tolist(),hours_per_hectare=op.hours_per_hectare,
                completed_hectares_by_step=plan.completed_hectares[:,i].tolist()) for i,op in enumerate(operations)],
            land_area_marginal=plan.land_output_marginal,work_area_marginals=plan.work_output_marginals[:,0].tolist(),
            maximum_work_budget_overrun=float(np.max(plan.resource_hours_used-available)),
            maximum_task_residual=float(np.max(np.abs(plan.task_residual))))
    # Closed-form controls independently known from the declared rates/limits.
    expected=[4.,80/(1.5*8/.25),4.,4.,80/(1.5*8/.25),80/(1.5*8/.25),80/(1.*8/.25)]
    if not np.allclose([r['feasible_area_hectares'] for r in records.values()],expected):
        raise ValueError('Analytical operation-window controls failed')
    fig,(ax,bars)=plt.subplots(1,2,figsize=(13,5.4),layout='constrained',gridspec_kw=dict(width_ratios=[1,1.45]))
    days=np.arange(T)*5
    baseline=plans[1].resource_hours_used[:,0];reallocated=plans[3].resource_hours_used[:,0]
    ax.step(days,hours[:,0],where='post',c='#777',ls='--',label='Original availability')
    ax.step(days,shifted[:,0],where='post',c='#38857c',ls='--',label='Harvest-staffing availability')
    ax.step(days,baseline,where='post',c='#b66a36',label='Work: 1.67 ha, narrow window')
    ax.step(days,reallocated,where='post',c='#245c83',label='Work: 4 ha, harvest staffing')
    ax.axvspan(250,260,color='#e4cdb0',alpha=.5)
    ax.set(xlabel='Manufactured calendar day',ylabel='Human work hours per five-day step',title='Same 2,920 annual farm hours; different staffing')
    ax.legend(fontsize=8,loc='upper left');ax.grid(alpha=.15)
    values=[r['feasible_area_hectares'] for r in records.values()];labels=list(records)
    bar=bars.barh(labels,values,color=['#999','#b66a36','#38857c','#245c83','#b66a36','#b66a36','#8161a3'])
    bars.invert_yaxis();bars.bar_label(bar,fmt='%.2f ha',padding=4,fontsize=9)
    bars.set(xlabel='Area completing every listed field operation, hectares',xlim=(0,4.65),title='Land and annual hours alone miss the harvest bottleneck')
    bars.grid(axis='x',alpha=.15)
    fig.suptitle('Columella’s listed wheat/barley work counts · manufactured work windows and availability\nPartial field-work budget to the threshing floor; no food, whole-household labour or ancient farm-size prediction',fontsize=11)
    out=ROOT/'output/farm_labour_20261103';out.mkdir(exist_ok=True)
    image=out/'seasonal_farm_labour.png';fig.savefig(image,dpi=140);plt.close(fig)
    write_json(out/'review.json',dict(status='seasonal_farm_operation_prototype',production_atlas_changed=False,
        independent_historical_validation=False,food_output_predicted=False,
        source_manifest_sha256=file_hash(manifest),figure_sha256=file_hash(image),cases=records,
        sources_sha256={name:file_hash(ROOT/name) for name in ['harvest/labour.py','scripts/demo_farm_labour.py']},
        scope='Columella2.12 listed task counts are historical prescriptions, not complete work. Explicit approximate .25ha/iugerum, 8h/day and manufactured operation windows. Maximize completed hectares, not edible food or farm profit. Draft services assumed available, no animal feed/care budget. Unused farm-allocation hours are not leisure or surplus labour. Fractional continuous activity/task scheduling, no operation precedence beyond supplied windows. Local LP marginals are numerical scarcity derivatives, not historical land/labour regime or inequality classifications.'))
    print(json.dumps({name:dict(area=r['feasible_area_hectares'],hours=r['used_work_hours']) for name,r in records.items()},indent=2))


if __name__=='__main__':main()
