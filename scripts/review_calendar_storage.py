"""Measure reserve ambiguity under explicit pulse/constant-demand scenarios."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import csv
    import json
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from harvest.calendar_sample import load_frozen_calendar_sample
    from harvest.crop_sequences import crop_windows,optimize_sequences
    from harvest.calendar_stocks import calendar_stock_bounds
    from local_benchmark_protocol import file_hash,write_json
    sample=load_frozen_calendar_sample()
    cat=crop_windows(*sample.climate,sample.irrigation,keep=sample.keep,rain_keep=sample.rain_keep)
    perennial=sample.baseline['kcal_dates']
    choice=optimize_sequences(cat,sample.can_double,perennial_energy=perennial)
    bounds={}
    for steps in [73,365]:
        bounds[steps]=calendar_stock_bounds(cat,choice,sample.can_double,year_steps=steps,perennial_energy=perennial)
        print('Completed stock-clock scenario:',steps,flush=True)
    stock=bounds[73];daily=bounds[365];paired=choice.second>=0
    timed=stock.annual_schedules>0
    spread=stock.maximum_days-stock.minimum_days
    ambiguous=timed&(spread>1e-7)
    clock_drift=max(float(np.nanmax(np.abs(getattr(stock,key)-getattr(daily,key))))
                    for key in ['minimum_days','maximum_days'])
    out=ROOT/'output/calendar_storage_20261103';out.mkdir(parents=True,exist_ok=True)
    path=out/'calendar_reserves.csv'
    with path.open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['sample','grid_row','grid_column','annual_schedules','unknown_perennial_timing',
            'minimum_reserve_days_5day_clock','maximum_reserve_days_5day_clock','minimum_reserve_days_daily_clock','maximum_reserve_days_daily_clock'])
        for i,index in enumerate(sample.indices):
            row,column=divmod(int(index),sample.grid_shape[1])
            values=[getattr(bounds[steps],key)[i] for steps in [73,365] for key in ['minimum_days','maximum_days']]
            writer.writerow([i,row,column,int(stock.annual_schedules[i]),bool(stock.perennial_timing_unknown[i])]+[
                '' if not np.isfinite(value) else f'{value:.8f}' for value in values])
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    axes[0].scatter(stock.minimum_days[paired],stock.maximum_days[paired],s=22,color='#3d8779',alpha=.5)
    axes[0].plot([180,365],[180,365],':',color='#555')
    axes[0].set(xlabel='Smallest reserve among equal-energy calendars (days)',ylabel='Largest reserve (days)',
                title=f'{int(paired.sum())} sample cells with a chosen crop pair',xlim=(180,365),ylim=(180,365))
    axes[1].hist(spread[ambiguous],bins=15,color='#b68346',edgecolor='white')
    axes[1].set(xlabel='Reserve range across equal-energy calendars (days)',ylabel='Sample cells',
                title=f'{int(ambiguous.sum())} cells have calendar-dependent reserves')
    for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.2)
    fig.suptitle('Conditional storage needs across equally productive crop calendars\nAssumed harvest pulses · uniform consumption equal to annual harvest · zero loss · five-day accounting',fontsize=12)
    image=out/'calendar_storage_bounds.png';fig.savefig(image,dpi=135);plt.close(fig)
    write_json(out/'receipt.json',dict(status='conditional_inventory_scenario',production_atlas_changed=False,
        independent_agronomic_validation=False,granary_or_loss_coefficients_fitted=False,
        sample_cells=len(sample.indices),timed_annual_cells=int(timed.sum()),
        unknown_perennial_timing_cells=int(stock.perennial_timing_unknown.sum()),
        calendar_dependent_reserve_cells=int(ambiguous.sum()),maximum_reserve_range_days=float(np.nanmax(spread)),
        single_pulse_reserve_days_5day_clock=360,single_pulse_reserve_days_daily_clock=364,
        maximum_5day_vs_daily_bound_difference_days=clock_drift,
        minimum_timed_reserve_days=float(np.nanmin(stock.minimum_days)),maximum_timed_reserve_days=float(np.nanmax(stock.maximum_days)),
        clock_scenarios=[dict(steps=73,days_per_step=5),dict(steps=365,days_per_step=1)],
        csv_sha256=file_hash(path),figure_sha256=file_hash(image),
        inputs_sha256=sample.previous['inputs_sha256'],
        literature_manifest_sha256=file_hash(ROOT/'research_notes/crop_sequences_20261103.json'),
        sources_sha256={name:file_hash(ROOT/name) for name in ['harvest/calendar_stocks.py','harvest/crop_sequences.py',
            'harvest/calendar_sample.py','harvest/food_stocks.py','scripts/review_calendar_storage.py','harvest/export.py','scripts/land_people.py']},
        scope='Bounds over tied optimal ANNUAL schedules under inherited crop comparison rules. Food pulses occur at rounded climate-bin maturity boundaries; annual consumption equals edible harvest and is uniform. No assumed ancient granary capacity, spoilage percentage, seed deduction, famine frequency, real harvest date or population. Perennial timing remains explicitly unknown; blank CSV bounds are not zeros. Formula independently checked against the existing cyclic food ledger; numeric agreement is not agronomic validation.'))
    print(json.dumps({k:v for k,v in json.loads((out/'receipt.json').read_text()).items() if k.endswith('cells') or k.endswith('days')},indent=2))


if __name__=='__main__':main()
