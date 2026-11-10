"""Display rainfall seasonality from verified fresh r44 reference archives.

Display only: does not rescore a search or change its candidate selection.
"""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash, write_json
from report_joint_ocean_land_refit import CAMPAIGN, SOURCE


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    campaign=json.loads(CAMPAIGN.read_text()); rows={}; summaries={}
    for filename,digest in campaign['reference_sha256'].items():
        path=ROOT/filename
        if file_hash(path)!=digest:raise ValueError('Changed reference')
        summary=json.loads(path.read_text())
        protocol=json.loads((path.parent/'protocol.json').read_text())
        for name,row in summary['regions'].items():
            if row['status']!='passed' or not row['numerics']['all_checks_passed']:
                raise ValueError('Unverified reference: '+name)
            rows[name]=(row,path.parent,protocol['region_specs'][name])
        summaries[filename]=digest
    assert len(rows)==49
    # Include both annual-amount and timing failures; examples, not a new test pool.
    names=['japan','bengal','north_queensland','patagonia']
    labels=['Japan','Bengal','North Queensland','Patagonia']
    fig,axes=plt.subplots(2,2,figsize=(12,7.5),layout='constrained')
    examples=[]
    for ax,name,label in zip(axes.ravel(),names,labels):
        row,folder,spec=rows[name]; path=folder/'cells'/(name+'.npz')
        if file_hash(path)!=row['cells_sha256']:raise ValueError('Changed monthly archive: '+name)
        with np.load(path) as archive:
            model=np.asarray(archive['Ps'],float).mean(1)
            observed=np.asarray(archive['Po'],float).mean(1)
        if spec['lat0']<0:
            model=np.roll(model,6);observed=np.roll(observed,6)
        rain=row['rain']; ratio=rain['sim_mean_annual_mm']/rain['obs_mean_annual_mm']
        ax.plot(range(1,13),observed,'o-',color='#28647c',label='WorldClim observed',ms=4)
        ax.plot(range(1,13),model,'s-',color='#b15c37',label='r44 modeled',ms=4)
        ax.set(title=f'{label} · annual total {ratio:.2f} × observed',ylabel='Mean monthly rain · mm',
               xticks=range(1,13),xticklabels=list('JFMAMJJASOND'),ylim=(0,None))
        ax.grid(alpha=.2);ax.legend(fontsize=8)
        ax.text(.02,.97,f"Local monthly MAE {rain['monthly_mae_mm']:.1f} mm\n"
                f"Within 25% annual total: {100*rain['annual_within_25pct']:.0f}% of wet cells",
                transform=ax.transAxes,va='top',fontsize=8,
                bbox=dict(facecolor='white',edgecolor='none',alpha=.85,pad=3))
        examples.append(dict(region=name,case_sha256=row['case_identity'],archive_sha256=row['cells_sha256'],
            model_regional_monthly_mm=model.tolist(),observed_regional_monthly_mm=observed.tolist(),
            metrics=rain))
    fig.suptitle('Current r44 rainfall · annual totals can conceal seasonal and spatial errors',fontsize=13)
    fig.supxlabel('Actual Earth calendar (southern regions unrolled) · regional means hide local errors\n'
                  'Same fresh development references used by the joint refit; no new validation or model gain.',fontsize=9)
    data=ROOT/'atlases/climate_accuracy/data'
    fig.savefig(data/'joint_refit_reference_rainfall.png',dpi=150);plt.close(fig)
    keys=['monthly_mae_mm','annual_within_25pct','annual_median_abs_relative_error','seasonality_total_variation']
    metrics={key:float(np.mean([row['rain'][key] for row,_,_ in rows.values()])) for key in keys}
    write_json(data/'joint_refit_reference_rainfall.json',dict(status='verified_reference_display',
        n_regions=49,equal_region_means=metrics,examples=examples,reference_sha256=summaries,
        precision='Curves from stored float32 monthly fields; canonical metrics from full-precision summary.',
        limits='Four illustrative reused regions; no new objective, selection criterion or validation pool.'))
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
