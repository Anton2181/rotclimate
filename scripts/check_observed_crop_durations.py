"""Run the declared descriptive comparison with Sacks et al.'s calendar records."""
from pathlib import Path
from collections import Counter
import argparse
import csv
import json
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def number(value):
    try:
        value=float(value)
        return value if np.isfinite(value) else None
    except (ValueError,TypeError):
        return None


def duration_distance(days, minimum, maximum):
    return max(minimum-days,days-maximum,0.)


def score_records(rows, plan):
    ids=Counter(row['Data.ID'] for row in rows)
    records=[];excluded=[]
    for row in rows:
        crop=plan['crop_map'].get(row['Crop'].strip())
        reason=None
        if crop is None:reason='unmapped_crop'
        elif not row['Data.ID'] or ids[row['Data.ID']]!=1:reason='missing_or_duplicate_id'
        plant=number(row['Plant.median']);harvest=number(row['Harvest.median']);days=number(row['tot.days'])
        if reason is None and (plant is None or harvest is None or not 1<=plant<=365 or not 1<=harvest<=365 or days is None or not 0<days<365):
            reason='invalid_or_missing_dates_or_duration'
        if reason:
            excluded.append(dict(id=row['Data.ID'],crop=row['Crop'],reason=reason));continue
        low,high=plan['model_duration_days'][crop]
        qualifier=row['Qualifier'].strip()
        if qualifier in ('','NA'):qualifier='Unqualified'
        cold=number(row['ndays.growing.season.below.0'])
        if cold is not None and cold<0:raise ValueError('Invalid cold-exposure duration')
        records.append(dict(id=row['Data.ID'],crop=crop,qualifier=qualifier,location=row['Location'],level=row['Level'],
            source_flagged_exclude='exclude' in qualifier.lower(),
            source=row['Source'],growing_days=days,model_minimum_days=low,model_maximum_days=high,
            distance_outside_duration_envelope=duration_distance(days,low,high),
            climate_days_below_zero_in_season=cold,planting_median=plant,harvest_median=harvest,
            circular_date_duration_difference=abs((harvest-plant)%365-days)))
    return records,excluded


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    folder=ROOT/'calibration/crop_calendar_observations_20261103'
    plan=json.loads((folder/'plan.json').read_text())
    raw=ROOT/'data/cache/sacks2010/All_data_with_climate.csv'
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='fetch the declared public CSV if missing; enforce its exact SHA256')
    args=parser.parse_args()
    if not raw.exists() and args.download:
        import hashlib
        import urllib.request
        payload=urllib.request.urlopen(plan['raw_url'],timeout=30).read()
        if hashlib.sha256(payload).hexdigest()!=plan['raw_sha256']:raise ValueError('Downloaded source differs from declaration')
        raw.parent.mkdir(parents=True,exist_ok=True);raw.write_bytes(payload)
    if file_hash(raw)!=plan['raw_sha256'] or file_hash(ROOT/'scripts/land_people.py')!=plan['production_source_sha256']:
        raise ValueError('Declared raw data or production model changed')
    rows=list(csv.DictReader(raw.read_text(encoding='utf-8-sig').splitlines()))
    records,excluded=score_records(rows,plan)
    assert len(records)+len(excluded)==len(rows)
    groups={}
    for crop,qualifier in sorted({(r['crop'],r['qualifier']) for r in records}):
        cases=[r for r in records if (r['crop'],r['qualifier'])==(crop,qualifier)]
        days=np.array([r['growing_days'] for r in cases]);distance=np.array([r['distance_outside_duration_envelope'] for r in cases])
        cold=[r['climate_days_below_zero_in_season'] for r in cases if r['climate_days_below_zero_in_season'] is not None]
        groups[crop+' · '+qualifier]=dict(records=len(cases),unique_locations=len({r['location'] for r in cases}),
            source_flagged_exclude=cases[0]['source_flagged_exclude'],
            duration_quantiles_days=dict(zip(['p10','p25','median','p75','p90'],[float(v) for v in np.quantile(days,[.1,.25,.5,.75,.9])])),
            model_minimum_days=cases[0]['model_minimum_days'],model_maximum_days=cases[0]['model_maximum_days'],
            outside_envelope={str(tolerance):dict(count=int(np.sum(distance>tolerance)),fraction=float(np.mean(distance>tolerance))) for tolerance in plan['tolerance_days']},
            cold_summary_available=len(cold),cold_summary_missing=len(cases)-len(cold),
            cold_exposure_records=sum(v>0 for v in cold),cold_exposure_fraction=None if not cold else float(np.mean(np.asarray(cold)>0)))
    out=ROOT/'output/observed_crop_durations_20261103';out.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(13,max(5.4,len(groups)*.4+1.8)),layout='constrained')
    for y,(name,g) in enumerate(groups.items()):
        q=g['duration_quantiles_days']
        axes[0].plot([g['model_minimum_days'],g['model_maximum_days']],[y,y],lw=15,color='#b8d8cf',solid_capstyle='butt')
        axes[0].plot([q['p10'],q['p90']],[y,y],lw=2,color='#3a4447')
        axes[0].scatter([q['median']],[y],color='#222',s=32,zorder=3)
        if g['cold_exposure_fraction'] is not None:
            axes[1].barh(y,100*g['cold_exposure_fraction'],color='#527f9d')
            axes[1].text(min(100*g['cold_exposure_fraction']+2,87),y,
                f'{g["cold_exposure_records"]}/{g["cold_summary_available"]}',va='center',fontsize=9)
        else:
            axes[1].text(2,y,'No climate summary',va='center',fontsize=9,color='#666')
    axes[0].set(yticks=range(len(groups)),yticklabels=list(groups),xlabel='Sowing-to-harvest duration (days)',
                title='Observed duration distribution vs model envelope',xlim=(0,365))
    fig.legend(handles=[Line2D([0],[0],lw=8,color='#b8d8cf',label='Model duration range'),
                           Line2D([0],[0],lw=2,color='#333',marker='o',label='Observed 10–90% and median')],loc='outside lower center',ncol=2,fontsize=9)
    axes[1].set(yticks=range(len(groups)),yticklabels=[],xlabel='Records with any cold exposure (%)',xlim=(0,110),
                title='Source interpolated-climate exposure below 0°C')
    # Missing summaries have text but no bar; explicit shared limits prevent
    # autoscaling from shifting the two panels onto different crop rows.
    for ax in axes:
        ax.set_ylim(len(groups)-.5,-.5)
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.2)
    fig.suptitle('Modern crop-calendar records · Sacks et al. (2010)\nDescriptive duration/exposure check · source Exclude qualifiers retained separately for audit\nNo tuning, ancient yield inference or pointwise validation',fontsize=12)
    image=out/'observed_durations.png';fig.savefig(image,dpi=135);plt.close(fig)
    result=dict(status='descriptive_observation_check',production_atlas_changed=False,parameters_tuned=False,
        full_agronomic_validation=False,raw_records=len(rows),eligible_records=len(records),groups=groups,
        unflagged_records=sum(not r['source_flagged_exclude'] for r in records),
        source_flagged_records=sum(r['source_flagged_exclude'] for r in records),
        source_quality_handling='Original Exclude qualifiers retained as separate groups, flagged as such; not pooled into unflagged evidence. Basic parser eligibility is not author approval of every raw record.',
        exclusions=dict(Counter(r['reason'] for r in excluded)),excluded=excluded,records=records,
        raw_url=plan['raw_url'],raw_sha256=file_hash(raw),plan_sha256=file_hash(folder/'plan.json'),
        plan_commit=__import__('subprocess').check_output(['git','log','-1','--format=%H','--',str((folder/'plan.json').relative_to(ROOT))],cwd=ROOT,text=True).strip(),
        production_source_sha256=plan['production_source_sha256'],observer_sha256=file_hash(Path(__file__)),
        figure_sha256=file_hash(image),
        scope=plan['inference_limits']+' Duration envelope coverage is a necessary timing check, not a predicted-date or yield score. Cold exposure flags missing process representation; its percentage is not an exact model rejection rate. Location records and multiple seasons can be correlated; no confidence intervals calculated.')
    write_json(out/'result.json',result)
    print(json.dumps({k:result[k] for k in ['raw_records','eligible_records','exclusions']},indent=2))
    print(json.dumps(groups,indent=2))


if __name__=='__main__':main()
