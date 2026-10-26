"""Publish a four-region observation-calendar audit, without redefining old fits."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/earth_calendar_20261026'
    review=json.loads((out/'review.json').read_text())
    protocol=json.loads((out/'protocol.json').read_text())
    if not review['complete'] or review['physics_or_atlas_adoption'] or review['benchmark_default_change']:
        raise ValueError('Need the completed audit with no default/adoption change')
    for name,expected in protocol['sources'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Calendar audit source changed: '+name)
    rows={r['region']:r for r in review['records']}
    names=protocol['plan']['regions']
    labels=['North India','Iran plateau','Iberia','East Australia']
    for name,row in rows.items():
        if (row['identity']!=review['identity'] or row['status']!='passed' or not row['legacy_exact']
                or not row['numerics']['all_checks_passed'] or file_hash(out/f'{name}.npz')!=row['arrays_sha256']):
            raise ValueError('Changed or unverified calendar result')
    data=ROOT/'atlases/climate_accuracy/data'
    fig,axes=plt.subplots(1,2,figsize=(11.5,4.8),constrained_layout=True)
    for ax,kind,metric,title,unit in [
        (axes[0],'temperature','monthly_mae_C','Monthly temperature MAE change','°C'),
        (axes[1],'rain','monthly_mae_mm','Monthly rainfall MAE change','mm')]:
        values=[rows[n]['scores']['gregorian'][kind][metric]-rows[n]['scores']['equal'][kind][metric] for n in names]
        ax.barh(np.arange(4),values,color=['#b37c4c' if v>0 else '#3c8890' for v in values])
        ax.axvline(0,color='#444444',lw=.7)
        for i,v in enumerate(values):
            ax.annotate(f'{v:+.4f}',(v,i),xytext=(4 if v>=0 else -4,0),textcoords='offset points',
                        ha='left' if v>=0 else 'right',va='center',fontsize=10)
        ax.set(yticks=np.arange(4),yticklabels=labels,title=title,xlabel=f'Gregorian minus equal-month score ({unit})')
        ax.invert_yaxis();ax.margins(x=.3);ax.grid(axis='x',alpha=.12)
    fig.suptitle('Matching observation months changes the measurement slightly',fontsize=16)
    fig.supxlabel('Same r39 physical/numerical inputs and step series; four reused regions, including a mirrored southern case.\n'
                  'These are changes of evaluation definition, not physical climate improvements. Annual simulated rain is preserved to <1e-12 mm.',fontsize=9)
    first=data/'earth_calendar_scores.png';fig.savefig(first,dpi=150);plt.close(fig)
    from earth_calendar import MONTH_DAYS
    fig,ax=plt.subplots(figsize=(10.5,3.7),constrained_layout=True)
    ax.bar(np.arange(12),MONTH_DAYS,color='#4c8d91',label='Non-leap Gregorian month')
    ax.axhline(365/12,color='#284d70',lw=2,label='Equal model month: 365/12 days')
    for month,total in enumerate(MONTH_DAYS):ax.text(month,total+.2,f'{total:g}',ha='center',fontsize=9)
    ax.set(xticks=np.arange(12),xticklabels=list('JFMAMJJASOND'),ylim=(0,34),
           ylabel='Monthly total (mm)',title='Constant 1 mm/day rain: totals depend on month duration')
    ax.legend(frameon=False,fontsize=9);ax.grid(axis='y',alpha=.15)
    fig.supxlabel('The audit aggregates actual model intervals into observation periods. It does not reconstruct daily data from old monthly means.\n'
                  '365-day non-leap convention; observed climatological leap-year effects and prescribed-forcing interpolation remain separate approximations.',fontsize=9)
    second=data/'earth_calendar_duration.png';fig.savefig(second,dpi=150);plt.close(fig)
    summary=dict(complete=True,physics_changed=False,benchmark_default_changed=False,
        regions=names,records={n:{key:rows[n][key] for key in ['scores','observed_month_order','month_days','mirrored','annual_rain_integral_max_difference_mm']} for n in names},
        scope=protocol['plan']['decision'],provenance=dict(protocol_sha256=file_hash(out/'protocol.json'),
            review_sha256=file_hash(out/'review.json'),plotter_sha256=file_hash(Path(__file__))),
        images_sha256={p.name:file_hash(p) for p in [first,second]})
    write_json(data/'earth_calendar.json',summary)
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text()
    start,end='<!--earth-calendar-start-->','<!--earth-calendar-end-->'
    section='''<!--earth-calendar-start--><section aria-labelledby="calendar-h"><h2 id="calendar-h">Observation-calendar alignment</h2>
<p>The historical Earth benchmark compares twelve equal model months with WorldClim's calendar-month observations. A separate audit now aggregates the actual unchanged r39 time series into declared 365-day Gregorian periods, including circular month boundaries for a mirrored southern region.</p>
<p>All four reused-region simulations pass numerical checks and reproduce the archived equal-month controls exactly. Calendar-aligned rainfall MAE is lower by only <strong>0.02–0.12 mm/month</strong>, while temperature MAE rises <strong>0.009–0.032°C</strong>. Annual simulated rain is unchanged to rounding precision. The mismatch exists, but it does not explain the large monsoon or coastal errors.</p>
<figure><a href="data/earth_calendar_scores.png"><img src="data/earth_calendar_scores.png" width="1725" height="720" loading="lazy" alt="Four-region audit: small rainfall-MAE reductions and small temperature-MAE increases when observation month boundaries are aligned"></a><figcaption>The two methods score the same physical climate. Their differences are evaluation changes, not a new calibrated fit. This four-region audit does not remeasure the 31-region or 3,667-city headline statistics.</figcaption></figure>
<figure><a href="data/earth_calendar_duration.png"><img src="data/earth_calendar_duration.png" width="1575" height="555" loading="lazy" alt="Constant daily rain totals 28 to 31 millimeters in actual months versus 30.42 millimeters in every equal model month"></a><figcaption>A known-answer example explains the duration mismatch. The audit uses a non-leap 365-day calendar and the existing half-year southern mirror; leap-year and forcing-interpolation approximations remain. Model physics, defaults, historical scores and all atlas climate fields stay unchanged.</figcaption></figure>
<p><a href="data/earth_calendar.json" download>Download both calendar definitions and paired scores</a> · <a href="../../reports/EARTH_CALENDAR_20261026.md">Calendar method and scope</a></p></section><!--earth-calendar-end-->'''
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    note='<p class="note" data-calendar-scope>Headline measurements retain the historical equal-month (365/12-day) benchmark. The separate four-region observation-calendar audit below changes no physical fit or headline statistic.</p>'
    if 'data-calendar-scope' not in content:
        content=content.replace('<h2>The rainfall problem is regional</h2>',note+'\n<h2>The rainfall problem is regional</h2>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_evaluation_audit_only',page_sha256=file_hash(page),
        metadata_sha256=file_hash(data/'earth_calendar.json'),images_sha256=summary['images_sha256'],
        physics_or_atlas_climate_adoption=False,benchmark_default_change=False))


if __name__=='__main__':main()
